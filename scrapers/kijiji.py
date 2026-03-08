"""Scraper for Kijiji Montreal rental listings."""

import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from http_client import create_session, get

logger = logging.getLogger(__name__)

KIJIJI_BASE = "https://www.kijiji.ca"

# Kijiji category IDs for Montreal real estate rentals
# Long-term rentals in Greater Montreal
CATEGORY_PATH = "/b-appartement-condo/ville-de-montreal/c37l1700281"


@dataclass
class Listing:
    source: str = ""
    title: str = ""
    price: float = 0.0
    url: str = ""
    address: str = ""
    neighbourhood: str = ""
    bedrooms: int = 0
    furnished: bool = False
    parking: bool = False
    description: str = ""
    image_url: str = ""
    listing_id: str = ""


def _extract_bedrooms_from_text(text: str) -> int:
    """Extract bedroom count from text, handling Quebec notation.

    Quebec convention: X½ means X rooms total (kitchen + living + bedrooms + ½ bathroom).
    So bedrooms = X - 2 (minus kitchen and living room).
      3½ = 1 bedroom, 4½ = 2 bedrooms, 5½ = 3 bedrooms, 6½ = 4 bedrooms.
    """
    # First try explicit "N chambres" / "N bedrooms"
    bed_match = re.search(r"(\d+)\s*(?:chambre|bedroom|bed\b|bdr)", text, re.IGNORECASE)
    if bed_match:
        return int(bed_match.group(1))

    # Quebec notation: 5½, 5 1/2, 5 et demi, 5.5
    qc_match = re.search(r"(\d)\s*[½]", text)
    if not qc_match:
        qc_match = re.search(r"(\d)\s*1/2", text)
    if not qc_match:
        qc_match = re.search(r"(\d)\s*et demi", text, re.IGNORECASE)
    if not qc_match:
        qc_match = re.search(r"\b(\d)\.5\b", text)
    if qc_match:
        total_rooms = int(qc_match.group(1))
        return max(total_rooms - 2, 0)

    return 0


def _parse_price(text: str) -> float:
    """Extract numeric price from text like '$2,500.00'."""
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    if nums:
        try:
            return float(nums[0])
        except ValueError:
            return 0.0
    return 0.0


def _matches_criteria(listing: Listing, config: dict) -> bool:
    criteria = config["criteria"]

    # Price filter
    if listing.price < criteria["price_min"] or listing.price > criteria["price_max"]:
        return False

    # Bedrooms filter
    if listing.bedrooms < criteria["bedrooms_min"]:
        return False

    # Neighbourhood filter (fuzzy match including common variants)
    hood_variants = {
        "villeray": ["villeray", "saint-michel", "parc-extension", "parc extension"],
        "mile-ex": ["mile-ex", "mile ex", "mile end", "marconi-alexandra"],
        "petite-patrie": ["petite-patrie", "petite patrie", "la petite-patrie"],
        "rosemont": ["rosemont"],
        "petite-italie": ["petite-italie", "petite italie", "little italy", "jean-talon"],
        "ahuntsic": ["ahuntsic", "cartierville", "sault-au-récollet"],
    }
    target_names = [n.lower() for n in criteria["neighbourhoods"]]
    search_terms = []
    for name in target_names:
        search_terms.extend(hood_variants.get(name, [name]))

    text = f"{listing.address} {listing.title} {listing.neighbourhood} {listing.description}".lower()
    hood_match = any(term in text for term in search_terms)
    if not hood_match:
        return False

    return True


def _check_furnished_parking(text: str) -> tuple[bool, bool]:
    text_lower = text.lower()
    neg_patterns = ["non meublé", "non meuble", "non-meublé", "pas meublé", "unfurnished"]
    if any(p in text_lower for p in neg_patterns):
        furnished = False
    else:
        furnished = any(w in text_lower for w in ["meublé", "meuble", "furnished", "meubles inclus"])
    neg_parking = ["pas de parking", "pas de stationnement", "no parking", "sans parking"]
    if any(p in text_lower for p in neg_parking):
        parking = False
    else:
        parking = any(w in text_lower for w in ["parking", "stationnement", "garage"])
    return furnished, parking


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
            price = _parse_price(price_text)

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
            bedrooms = _extract_bedrooms_from_text(full_text)

            furnished, parking = _check_furnished_parking(full_text)

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
            )

            if _matches_criteria(listing, config):
                listings.append(listing)

        except Exception as e:
            logger.warning(f"Error parsing Kijiji card: {e}")
            continue

    logger.info(f"Kijiji: {len(listings)} listings match criteria")
    return listings
