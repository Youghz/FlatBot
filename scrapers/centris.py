"""Scraper for Centris.ca Montreal rental listings.

Centris renders listings server-side. We build a filtered URL using their
path-based filter convention and parse the HTML cards directly.
"""

import re
import logging

from bs4 import BeautifulSoup

from http_client import create_session, get
from scrapers.kijiji import Listing, _extract_bedrooms_from_text

logger = logging.getLogger(__name__)

CENTRIS_BASE = "https://www.centris.ca"

# Centris URL path slugs for target neighbourhoods
BOROUGH_SLUGS = {
    "Villeray": "montreal-villeray-saint-michel-parc-extension",
    "Mile-Ex": "montreal-villeray-saint-michel-parc-extension",
    "Petite-Patrie": "montreal-rosemont-la-petite-patrie",
    "Rosemont": "montreal-rosemont-la-petite-patrie",
    "Petite-Italie": "montreal-villeray-saint-michel-parc-extension",
    "Ahuntsic": "montreal-ahuntsic-cartierville",
}

NEIGHBOURHOOD_KEYWORDS = {
    "villeray": "Villeray",
    "mile-ex": "Mile-Ex",
    "mile ex": "Mile-Ex",
    "petite-patrie": "Petite-Patrie",
    "petite patrie": "Petite-Patrie",
    "rosemont": "Rosemont",
    "petite-italie": "Petite-Italie",
    "petite italie": "Petite-Italie",
    "ahuntsic": "Ahuntsic",
}


def _build_urls(config: dict) -> list[str]:
    """Build Centris search URLs with filters in the path."""
    criteria = config["criteria"]
    neighbourhoods = criteria["neighbourhoods"]

    # Deduplicate borough slugs (multiple neighbourhoods map to same borough)
    slugs = list(dict.fromkeys(
        BOROUGH_SLUGS[n] for n in neighbourhoods if n in BOROUGH_SLUGS
    ))

    urls = []
    for slug in slugs:
        url = f"{CENTRIS_BASE}/fr/propriete~a-louer~{slug}"
        urls.append(url)

    return urls


def _parse_card(card, config: dict) -> Listing | None:
    """Parse a single Centris property-thumbnail-item card."""
    criteria = config["criteria"]

    # MLS number / listing ID
    sku_el = card.select_one("meta[itemprop='sku']")
    lid = sku_el["content"] if sku_el else ""
    if not lid:
        mls_el = card.select_one("[data-mlsnumber]")
        lid = mls_el.get("data-mlsnumber", "") if mls_el else ""
    if not lid:
        return None

    # Title
    name_el = card.select_one("meta[itemprop='name']")
    title = name_el["content"] if name_el else ""

    # Price
    price_el = card.select_one("meta[itemprop='price']")
    try:
        price = float(price_el["content"]) if price_el else 0.0
    except (ValueError, KeyError):
        price = 0.0

    # Price filter
    if price < criteria["price_min"] or price > criteria["price_max"]:
        return None

    # URL
    link_el = card.select_one("a.property-thumbnail-summary-link")
    href = link_el.get("href", "") if link_el else ""
    url = href if href.startswith("http") else f"{CENTRIS_BASE}{href}"

    # Address
    addr_el = card.select_one(".address, .property-thumbnail-address")
    address = addr_el.get_text(strip=True) if addr_el else ""
    if not address:
        address = title

    # Image
    img_el = card.select_one("img[itemprop='image']") or card.select_one("img")
    image_url = img_el.get("src", "") if img_el else ""

    # Specs from card text
    specs_text = card.get_text(" ", strip=True)

    # Bedrooms - from structured div.cac element
    cac_el = card.select_one("div.cac")
    if cac_el:
        try:
            bedrooms = int(cac_el.get_text(strip=True))
        except ValueError:
            bedrooms = 0
    else:
        bedrooms = _extract_bedrooms_from_text(specs_text)
    if bedrooms > 0 and bedrooms < criteria["bedrooms_min"]:
        return None

    # Furnished / parking
    text_lower = specs_text.lower()
    furnished = any(w in text_lower for w in ["meublé", "meuble", "furnished"])
    parking = any(w in text_lower for w in ["parking", "stationnement", "garage"])

    # Neighbourhood detection
    neighbourhood = ""
    combined = f"{address} {title} {url}".lower()
    for key, name in NEIGHBOURHOOD_KEYWORDS.items():
        if key in combined:
            neighbourhood = name
            break

    return Listing(
        source="centris",
        title=title,
        price=price,
        url=url,
        address=address,
        neighbourhood=neighbourhood,
        bedrooms=bedrooms,
        furnished=furnished,
        parking=parking,
        description=specs_text[:300],
        image_url=image_url,
        listing_id=f"centris_{lid}",
    )


def scrape(config: dict, session=None) -> list[Listing]:
    """Scrape Centris for matching rental listings."""
    listings = []
    seen_ids = set()

    if session is None:
        session = create_session()

    urls = _build_urls(config)

    for url in urls:
        logger.info(f"Scraping Centris: {url}")
        try:
            resp = get(session, url)
        except Exception as e:
            logger.error(f"Centris request failed for {url}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.property-thumbnail-item")
        logger.info(f"Found {len(cards)} Centris cards on {url}")

        for card in cards:
            try:
                listing = _parse_card(card, config)
                if listing and listing.listing_id not in seen_ids:
                    seen_ids.add(listing.listing_id)
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"Error parsing Centris card: {e}")

    logger.info(f"Centris: {len(listings)} listings match criteria")
    return listings
