"""Create test fixtures from user corrections on listings.

When a user corrects a listing field in the dashboard, this service:
1. Fetches the original listing HTML page
2. Saves it as a test fixture (HTML + TXT)
3. Appends a labeled entry to samples.json
"""

import json
import logging
from pathlib import Path

from bs4 import BeautifulSoup

from flat_research.db import ListingRecord

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "labeling"
SAMPLES_FILE = FIXTURES_DIR / "samples.json"


def _next_fixture_id(source: str) -> str:
    """Generate the next fixture_id by incrementing the max index in samples.json."""
    samples = _load_samples()
    max_idx = 0
    for s in samples:
        try:
            idx = int(s["fixture_id"].split("_")[0])
            max_idx = max(max_idx, idx)
        except (ValueError, KeyError):
            pass
    return f"{max_idx + 1:02d}_{source}"


def _load_samples() -> list[dict]:
    if not SAMPLES_FILE.exists():
        return []
    with open(SAMPLES_FILE) as f:
        return json.load(f)


def _save_samples(samples: list[dict]) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(SAMPLES_FILE, "w") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False, default=str)


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

    Args:
        listing: The ListingRecord after DB update
        corrections: Dict of field names → corrected values (the user's edits)

    Returns:
        The fixture_id if created, None on failure
    """
    source = listing.source
    fixture_id = _next_fixture_id(source)

    # Fetch and save HTML
    html = _fetch_html(listing.url, source)
    if html:
        html_path = FIXTURES_DIR / f"{fixture_id}.html"
        html_path.write_text(html, encoding="utf-8")

        # Extract plain text for debugging
        soup = BeautifulSoup(html, "html.parser")
        txt = soup.get_text(" ", strip=True)[:5000]
        txt_path = FIXTURES_DIR / f"{fixture_id}.txt"
        txt_path.write_text(txt, encoding="utf-8")

    # Build the sample entry
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
        "description": listing.description[:300],
        # Labels = the corrected values (ground truth from user)
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

    # Append to samples.json
    samples = _load_samples()
    samples.append(entry)
    _save_samples(samples)

    logger.info(f"Created test fixture {fixture_id} from user correction on {listing.listing_id}")
    return fixture_id
