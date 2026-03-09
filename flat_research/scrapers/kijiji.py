"""Scraper for Kijiji Montreal rental listings."""

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
    parse_price,
)

logger = logging.getLogger(__name__)

KIJIJI_BASE = "https://www.kijiji.ca"

# Kijiji category IDs for Montreal real estate rentals
# Long-term rentals in Greater Montreal
CATEGORY_PATH = "/b-appartement-condo/ville-de-montreal/c37l1700281"


def scrape(config: dict, session=None) -> list[Listing]:
    """Scrape Kijiji for matching rental listings."""
    listings = []
    criteria = config["criteria"]

    params = {
        "rb": criteria["price_min"],
        "re": criteria["price_max"],
        "numberbedrooms": criteria["bedrooms_min"],
    }
    if criteria.get("furnished"):
        params["furnished"] = 1
    if criteria.get("parking"):
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

    # Kijiji uses data-testid or specific class patterns for listing cards
    # Try multiple selectors as Kijiji changes their HTML frequently
    cards = soup.select("[data-testid='listing-card']")
    if not cards:
        cards = soup.select("div.search-item, li.regular-ad, div[data-listing-id]")
    if not cards:
        # Fallback: look for any links that look like listing URLs
        cards = soup.select("section ul li")

    logger.info(f"Found {len(cards)} raw Kijiji cards")

    for card in cards:
        try:
            # Extract listing ID
            lid = card.get("data-listing-id", "") or card.get("data-ad-id", "")
            if not lid:
                link_el = card.select_one("a[href*='/v-']")
                if link_el:
                    href = link_el.get("href", "")
                    match = re.search(r"/(\d+)$", href)
                    lid = match.group(1) if match else ""
                if not lid:
                    continue

            # Title
            title_el = card.select_one("a[class*='title'], h3, [data-testid='listing-title']")
            title = title_el.get_text(strip=True) if title_el else ""

            # Price
            price_el = card.select_one("[class*='price'], [data-testid='listing-price']")
            price_text = price_el.get_text(strip=True) if price_el else "0"
            price = parse_price(price_text)

            # URL
            link_el = card.select_one("a[href*='/v-']") or card.select_one("a")
            href = link_el.get("href", "") if link_el else ""
            listing_url = href if href.startswith("http") else f"{KIJIJI_BASE}{href}"

            # Image
            img_el = card.select_one("img")
            image_url = img_el.get("src", "") if img_el else ""

            # Address / location
            loc_el = card.select_one("[class*='location'], [data-testid='listing-location']")
            address = loc_el.get_text(strip=True) if loc_el else ""

            # Description snippet
            desc_el = card.select_one("[class*='description'], [data-testid='listing-description']")
            description = desc_el.get_text(strip=True) if desc_el else ""

            full_text = f"{title} {description} {address}"

            # Bedrooms - handles "3 chambres", "5½", "5 1/2", etc.
            bedrooms = extract_bedrooms_from_text(full_text)

            furnished, parking = check_furnished_parking(full_text)
            move_in_date = extract_move_in_date(full_text)

            if is_move_in_past(move_in_date):
                continue

            listing = Listing(
                source="kijiji",
                title=title,
                price=price,
                url=listing_url,
                address=address,
                neighbourhood="",
                bedrooms=bedrooms,
                furnished=furnished,
                parking=parking,
                description=description[:300],
                image_url=image_url,
                listing_id=f"kijiji_{lid}",
                move_in_date=move_in_date,
            )

            if matches_criteria(listing, config):
                listings.append(listing)

        except Exception as e:
            logger.warning(f"Error parsing Kijiji card: {e}")
            continue

    logger.info(f"Kijiji: {len(listings)} listings match criteria")
    return listings
