"""Create test fixtures from user corrections on listings.

When a user corrects a listing field in the dashboard, this service:
1. Fetches the original listing HTML page
2. Uploads HTML + TXT + JSON label to a GCS bucket
3. These fixtures are downloaded by CI before running pytest
"""

import json
import logging
import os

from bs4 import BeautifulSoup

from flat_research.db import ListingRecord

logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("FIXTURES_BUCKET", "flatbot-fixtures")
SAMPLES_BLOB = "samples.json"


def _get_bucket():
    from google.cloud import storage

    client = storage.Client()
    return client.bucket(BUCKET_NAME)


def _load_samples_from_gcs() -> list[dict]:
    """Load samples.json from GCS. Returns empty list if not found."""
    try:
        bucket = _get_bucket()
        blob = bucket.blob(SAMPLES_BLOB)
        if blob.exists():
            return json.loads(blob.download_as_text())
    except Exception as e:
        logger.warning(f"Could not load samples from GCS: {e}")
    return []


def _save_samples_to_gcs(samples: list[dict]) -> None:
    bucket = _get_bucket()
    blob = bucket.blob(SAMPLES_BLOB)
    data = json.dumps(samples, indent=2, ensure_ascii=False, default=str)
    blob.upload_from_string(data, content_type="application/json")


def _next_fixture_id(source: str, samples: list[dict]) -> str:
    max_idx = 0
    for s in samples:
        try:
            idx = int(s["fixture_id"].split("_")[0])
            max_idx = max(max_idx, idx)
        except (ValueError, KeyError):
            pass
    return f"{max_idx + 1:02d}_{source}"


def _fetch_html(url: str, source: str) -> str:
    """Fetch the listing page HTML using the appropriate HTTP client."""
    try:
        if source == "rentals":
            from curl_cffi import requests as cf_requests

            resp = cf_requests.get(url, impersonate="chrome", timeout=30)
            return resp.text
        else:
            from flat_research.http_client import create_session, get

            session = create_session()
            resp = get(session, url)
            return resp.text
    except Exception as e:
        logger.warning(f"Could not fetch listing HTML for fixture: {e}")
        return ""


def create_fixture(listing: ListingRecord, corrections: dict) -> str | None:
    """Create a test fixture from a user-corrected listing.

    Uploads to GCS bucket:
    - {fixture_id}.html — raw listing page
    - {fixture_id}.txt — plain text extraction
    - samples.json — appended with new labeled entry

    Returns the fixture_id if created, None on failure.
    """
    try:
        source = listing.source
        samples = _load_samples_from_gcs()
        fixture_id = _next_fixture_id(source, samples)
        bucket = _get_bucket()

        # Fetch and upload HTML
        html = _fetch_html(listing.url, source)
        if html:
            bucket.blob(f"{fixture_id}.html").upload_from_string(html, content_type="text/html")

            soup = BeautifulSoup(html, "html.parser")
            txt = soup.get_text(" ", strip=True)[:5000]
            bucket.blob(f"{fixture_id}.txt").upload_from_string(txt, content_type="text/plain")

        # Build labeled entry
        entry = {
            "fixture_id": fixture_id,
            "source": source,
            "url": listing.url,
            "title": listing.title,
            "price": listing.price,
            "bedrooms": listing.bedrooms,
            "address": listing.address,
            "detected_furnished": listing.furnished,
            "detected_parking": listing.parking,
            "description": listing.description[:300] if listing.description else "",
            "label_furnished": corrections.get("furnished", listing.furnished),
            "label_parking": corrections.get("parking", listing.parking),
            "label_bedrooms": corrections.get("bedrooms", listing.bedrooms),
            "label_move_in_date": corrections.get("move_in_date", listing.move_in_date),
            "label_published_date": listing.published_date,
            "label_neighbourhood": corrections.get("neighbourhood", listing.neighbourhood),
            "label_address": listing.address,
            "label_surface_sqft": corrections.get("surface_sqft", listing.surface_sqft),
            "label_building_condition": "",
            "label_price": corrections.get("price", listing.price),
            "label_url": listing.url,
            "label_parking_type": "",
        }

        samples.append(entry)
        _save_samples_to_gcs(samples)

        logger.info(f"Created test fixture {fixture_id} in gs://{BUCKET_NAME}/ from correction on {listing.listing_id}")
        return fixture_id

    except Exception as e:
        logger.error(f"Failed to create fixture for {listing.listing_id}: {e}")
        return None
