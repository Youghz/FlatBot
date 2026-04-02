"""Scraper for Kijiji Montreal rental listings.

Parses JSON-LD from search results (stable structured data),
then fetches detail pages for move-in date / furnished / parking info.
"""

import json
import logging
import re

import requests
from bs4 import BeautifulSoup

from flat_research.http_client import create_session, get
from flat_research.models import Listing
from flat_research.parsing import (
    check_furnished_parking,
    coerce_bool,
    extract_bedrooms_from_text,
    extract_move_in_date,
    extract_surface_sqft,
    is_move_in_past,
)

logger = logging.getLogger(__name__)

KIJIJI_BASE = "https://www.kijiji.ca"
CATEGORY_PATH = "/b-appartement-condo/ville-de-montreal/c37l1700281"


def _parse_jsonld_listings(soup: BeautifulSoup) -> list[dict]:
    """Extract listings from the JSON-LD ItemList on the search page."""
    script = soup.find("script", type="application/ld+json")
    if not script:
        logger.warning("No JSON-LD found on Kijiji search page")
        return []

    try:
        data = json.loads(script.string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse Kijiji JSON-LD: {e}")
        return []

    if data.get("@type") != "ItemList":
        logger.warning(f"Unexpected JSON-LD type: {data.get('@type')}")
        return []

    items = []
    for element in data.get("itemListElement", []):
        item = element.get("item", element)
        if item.get("@type") in ("SingleFamilyResidence", "Apartment", "House"):
            items.append(item)

    return items


def _extract_listing_id(url: str) -> str:
    """Extract numeric ID from a Kijiji listing URL."""
    match = re.search(r"/(\d+)$", url)
    return match.group(1) if match else ""


def _fetch_detail(session: requests.Session, url: str) -> dict:
    """Fetch a Kijiji detail page and return description + metadata."""
    result = {"description": "", "published_date": "", "surface_sqft": 0, "move_in_date": "", "neighbourhood": ""}
    try:
        resp = get(session, url)
        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)

        # Try JSON-LD on detail page (has full description + dates)
        script = soup.find("script", type="application/ld+json")
        if script:
            try:
                data = json.loads(script.string)
                result["description"] = data.get("description", "")
                result["published_date"] = data.get("offers", {}).get("validFrom", "")
                floor_size = data.get("floorSize", {})
                if isinstance(floor_size, dict):
                    try:
                        result["surface_sqft"] = int(float(floor_size.get("value", 0)))
                    except (ValueError, TypeError):
                        pass
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback description: get all visible text
        if not result["description"]:
            result["description"] = page_text[:2000]

        # Move-in date from structured "Available {date}" field
        avail_match = re.search(r"Available\s+(.+?)(?:\s+Furnished|\s+Utilities|\s+Apartment)", page_text)
        if avail_match:
            avail_text = avail_match.group(1).strip()
            if avail_text and avail_text != "Not":
                result["move_in_date"] = extract_move_in_date(avail_text)

        # Neighbourhood from "About {name} Explore the area" section
        hood_match = re.search(r"About\s+(.+?)\s+Explore the area", page_text)
        if hood_match:
            result["neighbourhood"] = hood_match.group(1).strip()

    except Exception as e:
        logger.debug(f"Could not fetch Kijiji detail {url}: {e}")
    return result


def scrape(session: requests.Session | None = None) -> list[Listing]:
    """Scrape latest Kijiji rental listings for Montreal (no filters)."""
    listings = []

    url = f"{KIJIJI_BASE}{CATEGORY_PATH}"
    logger.info(f"Scraping Kijiji: {url}")

    if session is None:
        session = create_session()

    try:
        resp = get(session, url)
    except Exception as e:
        logger.error(f"Kijiji request failed: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    items = _parse_jsonld_listings(soup)
    logger.info(f"Found {len(items)} Kijiji listings via JSON-LD")

    for item in items:
        try:
            item_url = item.get("url", "")
            lid = _extract_listing_id(item_url)
            if not lid:
                continue

            title = item.get("name", "")

            # Price and published date from offers
            offers = item.get("offers", {})
            try:
                price = float(offers.get("price", 0))
            except (ValueError, TypeError):
                price = 0.0
            # validFrom in Kijiji JSON-LD is the listing publication date
            published_date = offers.get("validFrom", "")

            # Address
            address = item.get("address", "")
            if isinstance(address, dict):
                address = address.get("streetAddress", "") or address.get("addressLocality", "")

            # Bedrooms
            try:
                bedrooms = int(item.get("numberOfBedrooms", 0))
            except (ValueError, TypeError):
                bedrooms = extract_bedrooms_from_text(title)

            # Search-page description (may be truncated)
            search_description = item.get("description", "")

            # Fetch detail page for full description, published date, surface
            detail = _fetch_detail(session, item_url)
            detail_text = detail["description"]
            published_date = detail["published_date"]
            full_text = f"{title} {detail_text}" if detail_text else f"{title} {search_description}"

            # Detect furnished/parking from full text — force non-None
            furnished, parking = check_furnished_parking(full_text)
            furnished = coerce_bool(furnished)
            parking = coerce_bool(parking)

            # Surface from detail page JSON-LD, fallback to text
            surface_sqft = detail["surface_sqft"]
            if not surface_sqft:
                surface_sqft = extract_surface_sqft(full_text)

            # Move-in date: prefer structured field, fallback to text parsing
            move_in_date = detail.get("move_in_date", "") or extract_move_in_date(full_text)
            if is_move_in_past(move_in_date):
                logger.debug(f"Skipping past move-in: {title} ({move_in_date})")
                continue

            # Neighbourhood from detail page "About X" section
            neighbourhood = detail.get("neighbourhood", "")

            listing = Listing(
                source="kijiji",
                title=title,
                price=price,
                url=item_url,
                address=address,
                neighbourhood=neighbourhood,
                bedrooms=bedrooms,
                furnished=furnished,
                parking=parking,
                description=(detail_text or search_description)[:300],
                listing_id=f"kijiji_{lid}",
                move_in_date=move_in_date,
                published_date=published_date,
                surface_sqft=surface_sqft,
            )
            listings.append(listing)

        except Exception as e:
            logger.warning(f"Error parsing Kijiji item: {e}")
            continue

    logger.info(f"Kijiji: {len(listings)} listings parsed")
    return listings
