"""Shared parsing utilities for rental listings.

Handles Quebec notation (5½ = 3 bedrooms), price extraction,
move-in date parsing, furnished/parking detection, and neighbourhood matching.
"""

import re
from datetime import date, datetime


def extract_bedrooms_from_text(text: str) -> int:
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


def parse_price(text: str) -> float:
    """Extract numeric price from text like '$2,500.00'."""
    nums = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    if nums:
        try:
            return float(nums[0])
        except ValueError:
            return 0.0
    return 0.0


def check_furnished_parking(text: str) -> tuple[bool, bool]:
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


MONTH_FR = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}

MONTH_EN = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def extract_move_in_date(text: str) -> str:
    """Extract move-in date from text. Returns YYYY-MM-DD, 'immediate', or ''."""
    text_lower = text.lower()

    # Immediate availability
    if any(w in text_lower for w in ["immédiat", "immediat", "immediate", "disponible maintenant", "available now"]):
        return "immediate"

    # Try "1er juillet 2025", "15 août 2025", "1 septembre"
    all_months = {**MONTH_FR, **MONTH_EN}
    month_pattern = "|".join(all_months.keys())
    match = re.search(rf"(\d{{1,2}})\s*(?:er)?\s*({month_pattern})\s*(\d{{4}})?", text_lower)
    if match:
        day = int(match.group(1))
        month = all_months[match.group(2)]
        year = int(match.group(3)) if match.group(3) else date.today().year
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass

    # Try YYYY-MM-DD or DD/MM/YYYY
    iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso_match:
        return iso_match.group(0)

    dmy_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if dmy_match:
        day, month, year = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass

    return ""


def is_move_in_past(move_in_date: str) -> bool:
    """Check if a move-in date is in the past."""
    if not move_in_date or move_in_date == "immediate":
        return False
    try:
        return datetime.strptime(move_in_date, "%Y-%m-%d").date() < date.today()
    except ValueError:
        return False


# Neighbourhood variants for fuzzy matching
HOOD_VARIANTS = {
    "villeray": ["villeray", "saint-michel", "parc-extension", "parc extension"],
    "mile-ex": ["mile-ex", "mile ex", "marconi-alexandra"],
    "mile-end": ["mile-end", "mile end"],
    "plateau": ["plateau", "plateau-mont-royal", "plateau mont-royal"],
    "petite-patrie": ["petite-patrie", "petite patrie", "la petite-patrie"],
    "rosemont": ["rosemont"],
    "petite-italie": ["petite-italie", "petite italie", "little italy", "jean-talon"],
    "ahuntsic": ["ahuntsic", "cartierville", "sault-au-récollet"],
}


def matches_criteria(listing, config: dict) -> bool:
    criteria = config["criteria"]

    # Price filter
    if listing.price < criteria["price_min"] or listing.price > criteria["price_max"]:
        return False

    # Bedrooms filter
    if listing.bedrooms < criteria["bedrooms_min"]:
        return False

    # Neighbourhood filter (fuzzy match including common variants)
    target_names = [n.lower() for n in criteria["neighbourhoods"]]
    search_terms = []
    for name in target_names:
        search_terms.extend(HOOD_VARIANTS.get(name, [name]))

    text = f"{listing.address} {listing.title} {listing.neighbourhood} {listing.description}".lower()
    hood_match = any(term in text for term in search_terms)
    if not hood_match:
        return False

    return True
