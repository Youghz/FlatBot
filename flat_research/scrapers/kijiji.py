"""Scraper for Kijiji Montreal rental listings.

Parses JSON-LD from search results (stable structured data),
then fetches detail pages for move-in date / furnished / parking info.
"""

import json
import logging
import re

from bs4 import BeautifulSoup

from flat_research.http_client import create_session, get
from flat_research.models import Listing
from flat_research.parsing import (
    check_furnished_parking,
    extract_bedrooms_from_text,
    extract_move_in_date,
    is_move_in_past,
    matches_criteria,
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


def _fetch_detail_description(session, url: str) -> str:
    """Fetch a Kijiji detail page and return the full description text."""
    try:
        resp = get(session, url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try JSON-LD on detail page (has full description)
        script = soup.find("script", type="application/ld+json")
        if script:
            try:
                data = json.loads(script.string)
                desc = data.get("description", "")
                if desc:
                    return desc
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: get all visible text
        return soup.get_text(" ", strip=True)[:2000]
    except Exception as e:
        logger.debug(f"Could not fetch Kijiji detail {url}: {e}")
        return ""


def scrape(config: dict, session=None) -> list[Listing]:
    """Scrape Kijiji for matching rental listings."""
    listings = []
    criteria = config["criteria"]

    params = {
        "rb": criteria["price_min"],
        "re": criteria["price_max"],
        "numberbedrooms": criteria["bedrooms_min"],
    }
    search_furnished = criteria.get("furnished", False)
    search_parking = criteria.get("parking", False)
    if search_furnished:
        params["furnished"] = 1
    if search_parking:
        params["numberparkingspots"] = 1

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{KIJIJI_BASE}{CATEGORY_PATH}?{query_string}"
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

            # Price from offers
            offers = item.get("offers", {})
            try:
                price = float(offers.get("price", 0))
            except (ValueError, TypeError):
                price = 0.0

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

            # Fetch detail page for full description
            detail_text = _fetch_detail_description(session, item_url)
            full_text = f"{title} {detail_text}" if detail_text else f"{title} {search_description}"

            # Detect furnished/parking from full text
            furnished, parking = check_furnished_parking(full_text)
            # If search filters require furnished/parking and text detection fails,
            # trust the Kijiji search filter
            if search_furnished and not furnished:
                furnished = True
            if search_parking and not parking:
                parking = True

            # Move-in date from full text
            move_in_date = extract_move_in_date(full_text)
            if is_move_in_past(move_in_date):
                logger.debug(f"Skipping past move-in: {title} ({move_in_date})")
                continue

            listing = Listing(
                source="kijiji",
                title=title,
                price=price,
                url=item_url,
                address=address,
                neighbourhood="",
                bedrooms=bedrooms,
                furnished=furnished,
                parking=parking,
                description=(detail_text or search_description)[:300],
                listing_id=f"kijiji_{lid}",
                move_in_date=move_in_date,
            )

            if matches_criteria(listing, config):
                listings.append(listing)

        except Exception as e:
            logger.warning(f"Error parsing Kijiji item: {e}")
            continue

    logger.info(f"Kijiji: {len(listings)} listings match criteria")
    return listings
