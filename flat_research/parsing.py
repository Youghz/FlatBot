"""Shared parsing utilities for rental listings.

Handles Quebec notation (5½ = 3 bedrooms), price extraction,
move-in date parsing, furnished/parking detection, surface area extraction,
and neighbourhood matching.
"""

import re
from datetime import date, datetime


def extract_surface_sqft(text: str) -> int:
    """Extract surface area in square feet from text. Returns 0 if not found.

    Supports: "450 pc", "1250 pi ca", "1000 sq ft", "675 sqft",
              "500 pieds carrés", "Superficie brute 450"
    """
    patterns = [
        r"(\d[\d\s]*)\s*(?:pi(?:eds?)?\s*ca(?:rrés?)?|pc\b|p\.c\.)",  # Quebec: pi ca, pc, pieds carrés
        r"(\d[\d\s]*)\s*(?:sq\.?\s*ft|sqft|square\s*feet)",  # English: sq ft, sqft
        r"Superficie\s+(?:brute\s+)?(\d[\d\s]*)",  # Centris: "Superficie brute 450"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(" ", "")
            try:
                return int(value)
            except ValueError:
                continue
    return 0


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


_FURNISHED_NEG = [
    "non meublé",
    "non meuble",
    "non-meublé",
    "non-meuble",
    "pas meublé",
    "pas meuble",
    "sans meubles",
    "sans meuble",
    "unfurnished",
    "not furnished",
    "nothing included",
    "rien d'inclus",
    "rien inclus",
]
_FURNISHED_POS = [
    "meublé",
    "furnished",
    "meubles inclus",
    "meubles fournis",
    "meubles sont fournis",
    "semi-meublé",
    "semi-meuble",
    "semi meublé",
    "fully furnished",
    "tout équipé",
    "tout equipe",
    "clé en main",
    "cle en main",
    "turnkey",
]
# "meuble" without accent removed — matches "immeuble" (false positive)
# Appliance keywords → "semi" (electros only, not real furniture)
_SEMI_FURNISHED = [
    "électros inclus",
    "electros inclus",
    "électro inclus",
    "electro inclus",
    "appliances included",
    "5 électros",
    "5 electros",
    "cuisinière inclus",
    "cuisiniere inclus",
    "inclue frigo",
    "inclus frigo",
    "frigo inclus",
    "fridge included",
    "réfrigérateur",
    "refrigerateur",
    "lave-vaisselle",
    "dishwasher",
]
_PARKING_NEG = [
    "pas de parking",
    "pas de stationnement",
    "no parking",
    "sans parking",
    "sans stationnement",
    "garage à vélo",
    "garage a velo",
    "vente de garage",
]
_PARKING_POS = ["parking", "stationnement", "garage"]


def check_furnished_parking(text: str) -> tuple[bool | None | str, bool | None]:
    """Detect furnished/parking status from text.

    Returns:
        furnished: True (fully furnished), "semi" (appliances only), False (explicitly not), None (unknown)
        parking: True, False, None
    """
    text_lower = text.lower()

    # Furnished detection: negation > positive > semi > None
    if any(p in text_lower for p in _FURNISHED_NEG):
        furnished: bool | None | str = False
    elif any(w in text_lower for w in _FURNISHED_POS):
        # Check if it's actually semi-meublé
        if "semi-meublé" in text_lower or "semi-meuble" in text_lower or "semi meublé" in text_lower:
            furnished = "semi"
        else:
            furnished = True
    elif any(w in text_lower for w in _SEMI_FURNISHED):
        furnished = "semi"
    else:
        furnished = None

    # Parking detection
    if any(p in text_lower for p in _PARKING_NEG):
        parking: bool | None = False
    elif any(w in text_lower for w in _PARKING_POS):
        parking = True
    else:
        parking = None

    return furnished, parking


def has_furnished_negation(text: str) -> bool:
    """Check if text explicitly denies furnished status."""
    return any(p in text.lower() for p in _FURNISHED_NEG)


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

MONTH_FR_ABBREV = {
    "janv": 1,
    "févr": 2,
    "fevr": 2,
    "avr": 4,
    "juil": 7,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "déc": 12,
    "dec": 12,
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

MONTH_EN_ABBREV = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# Merge all month names — full names first (longer match wins)
ALL_MONTHS: dict[str, int] = {**MONTH_FR_ABBREV, **MONTH_EN_ABBREV, **MONTH_FR, **MONTH_EN}

# Pre-compiled patterns (built once at import time)
_MONTH_PATTERN = "|".join(sorted(ALL_MONTHS.keys(), key=len, reverse=True))
_RE_DAY_MONTH_YEAR = re.compile(
    rf"(\d{{1,2}})\s*(?:er|st|nd|rd|th)?\s*({_MONTH_PATTERN})\.?\s*(\d{{4}})?", re.IGNORECASE
)
_RE_MONTH_DAY_YEAR = re.compile(
    rf"({_MONTH_PATTERN})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*,?\s*(\d{{4}})?", re.IGNORECASE
)
_RE_MONTH_YEAR = re.compile(rf"({_MONTH_PATTERN})\.?\s+(\d{{4}})", re.IGNORECASE)
_RE_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_RE_DMY_SLASH = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_RE_IMMEDIATE = re.compile(
    r"imm[ée]diat|immediate(?:ly)?|disponible\s+maintenant|available\s+now|d[èe]s\s+maintenant",
    re.IGNORECASE,
)


def extract_move_in_date(text: str) -> str:
    """Extract move-in date from text. Returns YYYY-MM-DD, 'immediate', or ''."""
    # Immediate availability
    if _RE_IMMEDIATE.search(text):
        return "immediate"

    # Try "1er juillet 2025", "15 août 2025", "1 sept. 2025"
    match = _RE_DAY_MONTH_YEAR.search(text)
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower().rstrip(".")
        month = ALL_MONTHS.get(month_name)
        if month:
            year = int(match.group(3)) if match.group(3) else date.today().year
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                pass

    # Try "juillet 2025", "July 2025" (no day → assume 1st)
    # Must check before month-day-year to avoid "juillet 2026" matching as day=20
    month_year = _RE_MONTH_YEAR.search(text)
    if month_year:
        month_name = month_year.group(1).lower().rstrip(".")
        month = ALL_MONTHS.get(month_name)
        if month:
            year = int(month_year.group(2))
            try:
                return date(year, month, 1).isoformat()
            except ValueError:
                pass

    # Try "August 1st 2025", "May 31, 2025" (English month-day-year order)
    match_mdy = _RE_MONTH_DAY_YEAR.search(text)
    if match_mdy:
        month_name = match_mdy.group(1).lower().rstrip(".")
        day = int(match_mdy.group(2))
        month = ALL_MONTHS.get(month_name)
        if month:
            year = int(match_mdy.group(3)) if match_mdy.group(3) else date.today().year
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                pass

    # Try YYYY-MM-DD
    iso_match = _RE_ISO_DATE.search(text)
    if iso_match:
        try:
            d = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            return d.isoformat()
        except ValueError:
            pass

    # Try DD/MM/YYYY
    dmy_match = _RE_DMY_SLASH.search(text)
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


def _get_hood_search_terms(criteria: dict) -> list[str]:
    """Build flat list of neighbourhood search terms from config.

    Supports two config formats:
      - dict: {name: [variant, ...]}  (new format with variants)
      - list: [name, ...]             (legacy format, uses name as-is)
    """
    neighbourhoods = criteria["neighbourhoods"]
    terms: list[str] = []
    if isinstance(neighbourhoods, dict):
        for variants in neighbourhoods.values():
            terms.extend(v.lower() for v in variants)
    else:
        terms.extend(n.lower() for n in neighbourhoods)
    return terms


def get_neighbourhood_names(criteria: dict) -> list[str]:
    """Return the canonical neighbourhood names from config."""
    neighbourhoods = criteria["neighbourhoods"]
    if isinstance(neighbourhoods, dict):
        return list(neighbourhoods.keys())
    return list(neighbourhoods)


def matches_criteria(listing, config: dict) -> bool:
    criteria = config["criteria"]

    # Price
    if listing.price < criteria["price_min"] or listing.price > criteria["price_max"]:
        return False

    # Bedrooms (min and optional max)
    if listing.bedrooms < criteria["bedrooms_min"]:
        return False
    bedrooms_max = criteria.get("bedrooms_max")
    if bedrooms_max is not None and listing.bedrooms > bedrooms_max:
        return False

    # Furnished — reject only if explicitly False (not furnished), accept True and None (unknown)
    if criteria.get("furnished") and listing.furnished is False:
        return False

    # Parking — same tri-state logic
    if criteria.get("parking") and listing.parking is False:
        return False

    # Move-in date — exclude listings with move-in date before this threshold
    # (filters out outdated/past listings)
    move_in_after = criteria.get("move_in_after")
    if move_in_after and listing.move_in_date:
        if listing.move_in_date != "immediate":
            try:
                move_date = datetime.strptime(listing.move_in_date, "%Y-%m-%d").date()
                limit_date = datetime.strptime(move_in_after, "%Y-%m-%d").date()
                if move_date < limit_date:
                    return False
            except ValueError:
                pass

    # Neighbourhood (fuzzy match via configured variants)
    search_terms = _get_hood_search_terms(criteria)
    text = f"{listing.address} {listing.title} {listing.neighbourhood} {listing.description}".lower()
    if not any(term in text for term in search_terms):
        return False

    return True
