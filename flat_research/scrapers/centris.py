"""Scraper for Centris.ca Montreal rental listings.

Centris renders listings server-side. We build a filtered URL using their
path-based filter convention and parse the HTML cards directly.
"""

import logging

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

CENTRIS_BASE = "https://www.centris.ca"

# Centris URL path slugs for target neighbourhoods
BOROUGH_SLUGS = {
    "Villeray": "montreal-villeray-saint-michel-parc-extension",
    "Mile-Ex": "montreal-villeray-saint-michel-parc-extension",
    "Mile-End": "montreal-le-plateau-mont-royal",
    "Plateau": "montreal-le-plateau-mont-royal",
    "Petite-Patrie": "montreal-rosemont-la-petite-patrie",
    "Rosemont": "montreal-rosemont-la-petite-patrie",
    "Petite-Italie": "montreal-villeray-saint-michel-parc-extension",
    "Ahuntsic": "montreal-ahuntsic-cartierville",
}

NEIGHBOURHOOD_KEYWORDS = {
    "villeray": "Villeray",
    "mile-ex": "Mile-Ex",
    "mile ex": "Mile-Ex",
    "mile-end": "Mile-End",
    "mile end": "Mile-End",
    "petite-patrie": "Petite-Patrie",
    "petite patrie": "Petite-Patrie",
    "rosemont": "Rosemont",
    "petite-italie": "Petite-Italie",
    "petite italie": "Petite-Italie",
    "plateau": "Plateau",
    "plateau-mont-royal": "Plateau",
    "plateau mont-royal": "Plateau",
    "ahuntsic": "Ahuntsic",
}


def _build_urls(config: dict) -> list[str]:
    """Build Centris search URLs with filters in the path."""
    from flat_research.parsing import get_neighbourhood_names

    neighbourhood_names = get_neighbourhood_names(config["criteria"])

    # Deduplicate borough slugs (multiple neighbourhoods map to same borough)
    slugs = list(dict.fromkeys(BOROUGH_SLUGS[n] for n in neighbourhood_names if n in BOROUGH_SLUGS))

    urls = []
    for slug in slugs:
        url = f"{CENTRIS_BASE}/fr/propriete~a-louer~{slug}"
        urls.append(url)

    return urls


def _fetch_detail(session: requests.Session, url: str) -> dict:
    """Fetch a Centris detail page and extract structured listing info.

    Returns dict with 'furnished', 'parking', 'move_in_date' keys,
    or empty dict on failure.
    """
    try:
        resp = get(session, url)
    except Exception as e:
        logger.debug(f"Could not fetch Centris detail {url}: {e}")
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # Extract "Caractéristiques additionnelles" section (contains meublé, semi-meublé, etc.)
    # and "Description" section for furnished/parking detection
    parts = []
    for keyword in ["Caractéristiques additionnelles", "Description"]:
        idx = page_text.find(keyword)
        if idx >= 0:
            parts.append(page_text[idx : idx + 500])
    detection_text = " ".join(parts) if parts else page_text[:3000]

    furnished, parking = check_furnished_parking(detection_text)
    furnished = coerce_bool(furnished)
    parking = coerce_bool(parking)

    # Extract "Date d'emménagement" from structured field on the page
    move_in_date = ""
    date_idx = page_text.find("Date d\u2019emménagement")
    if date_idx < 0:
        date_idx = page_text.find("Date d'emménagement")
    if date_idx >= 0:
        date_section = page_text[date_idx : date_idx + 100]
        move_in_date = extract_move_in_date(date_section)
        # "X jours après l'acceptation" = effectively immediate
        if not move_in_date and "après" in date_section.lower():
            move_in_date = "immediate"

    # Surface area from "Superficie brute XXX pc"
    surface_sqft = extract_surface_sqft(page_text)

    return {
        "furnished": furnished,
        "parking": parking,
        "move_in_date": move_in_date,
        "surface_sqft": surface_sqft,
    }


def _parse_card(card, session: requests.Session | None = None) -> Listing | None:
    """Parse a single Centris property-thumbnail-item card into a Listing."""
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

    # URL
    link_el = card.select_one("a.property-thumbnail-summary-link")
    href = link_el.get("href", "") if link_el else ""
    url = href if href.startswith("http") else f"{CENTRIS_BASE}{href}"

    # Address
    addr_el = card.select_one(".address, .property-thumbnail-address")
    address = addr_el.get_text(strip=True) if addr_el else ""
    if not address:
        address = title

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
        bedrooms = extract_bedrooms_from_text(specs_text)

    # Furnished / parking / move-in / surface from detail page
    detail = _fetch_detail(session, url) if session else {}
    furnished = detail.get("furnished", False)
    parking = detail.get("parking", False)
    move_in_date = detail.get("move_in_date", "")
    surface_sqft = detail.get("surface_sqft", 0)

    # Fallback to card text if detail page returned no furnished/parking info
    if furnished is False and parking is False and not detail.get("furnished") and not detail.get("parking"):
        f, p = check_furnished_parking(specs_text)
        if f is not None:
            furnished = bool(f)
        if p is not None:
            parking = bool(p)
    if not move_in_date:
        move_in_date = extract_move_in_date(specs_text)

    # Neighbourhood detection — search address, title, URL, and description
    neighbourhood = ""
    combined = f"{address} {title} {url} {specs_text}".lower()
    for key, name in NEIGHBOURHOOD_KEYWORDS.items():
        if key in combined:
            neighbourhood = name
            break

    if is_move_in_past(move_in_date):
        return None

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
        listing_id=f"centris_{lid}",
        move_in_date=move_in_date,
        surface_sqft=surface_sqft,
    )


def scrape(config: dict, session: requests.Session | None = None) -> list[Listing]:
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
                listing = _parse_card(card, session)
                if listing and listing.listing_id not in seen_ids:
                    seen_ids.add(listing.listing_id)
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"Error parsing Centris card: {e}")

    logger.info(f"Centris: {len(listings)} listings parsed")
    return listings
