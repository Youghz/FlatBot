"""Regression tests against hand-labeled listing fixtures.

Each fixture is a real listing page (HTML) saved offline. Labels are the
ground truth from manual annotation. Tests verify that our parsing logic
extracts the correct values from the description text.
"""

import json as _json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from flat_research.parsing import check_furnished_parking, extract_bedrooms_from_text, extract_move_in_date

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "labeling"


def _load_samples() -> list[dict]:
    with open(FIXTURES_DIR / "samples.json") as f:
        return _json.load(f)


def _extract_kijiji(html: str) -> dict:
    """Extract listing data from Kijiji detail page, mimicking the scraper."""
    import re

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # JSON-LD for title, description, bedrooms
    script = soup.find("script", type="application/ld+json")
    if script:
        data = _json.loads(script.string)
        title = data.get("name", "")
        desc = data.get("description", "")
        bedrooms = data.get("numberOfBedrooms")
        bedrooms = int(bedrooms) if bedrooms is not None else extract_bedrooms_from_text(f"{title} {desc}")
    else:
        title, desc, bedrooms = "", page_text[:3000], 0

    # Kijiji JSON-LD descriptions are often truncated — also extract the
    # visible "Description" section and structured attributes from the page
    desc_idx = page_text.find("Description ")
    if desc_idx >= 0:
        visible_desc = page_text[desc_idx : desc_idx + 1500]
        desc = f"{desc} {visible_desc}"

    # Structured fields from page text (Kijiji attribute section)
    structured_furnished = None
    if "Furnished Yes" in page_text:
        structured_furnished = True
    elif "Furnished No" in page_text:
        structured_furnished = False

    structured_parking = None
    park_match = re.search(r"(\d+)\s+Parking\s+Included", page_text)
    if park_match:
        structured_parking = int(park_match.group(1)) > 0

    # Enrich from description text (may have more detail than Kijiji's checkboxes)
    text = f"{title} {desc}"
    text_furnished, text_parking = check_furnished_parking(text)

    # Text overrides structured when it provides additional info
    # e.g. "Stationnement disponible" in desc overrides "0 Parking Included"
    furnished = text_furnished if text_furnished is not None else structured_furnished
    parking = text_parking if text_parking is not None else structured_parking

    return {"text": text, "bedrooms": bedrooms, "furnished": furnished, "parking": parking}


def _extract_centris(html: str) -> dict:
    """Extract listing data from Centris detail page."""
    import re

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # Extract description + characteristics sections (avoid boilerplate filters)
    parts = []
    # "Caractéristiques additionnelles" is the structured attributes section
    carac_idx = page_text.find("Caractéristiques additionnelles")
    if carac_idx >= 0:
        parts.append(page_text[carac_idx : carac_idx + 300])
    # Find the listing description (after "Description" + centris ID pattern)

    desc_matches = list(re.finditer(r"Description\s+(?:[A-Z]|[0-9])", page_text))
    if desc_matches:
        # Take the last one (the actual listing description, not nav)
        last_desc = desc_matches[-1]
        parts.append(page_text[last_desc.start() : last_desc.start() + 800])

    # Bedrooms from structured "X chambres" in page
    bedrooms = 0
    bed_match = re.search(r"(\d+)\s+chambre", page_text)
    if bed_match:
        bedrooms = int(bed_match.group(1))
    if not bedrooms:
        bedrooms = extract_bedrooms_from_text(page_text[:500])

    text = " ".join(parts) if parts else page_text[:3000]

    # Centris structured: check "Caractéristiques additionnelles" for meublé/semi-meublé
    furnished, parking = check_furnished_parking(text)

    # If no parking info in description, default to False (Centris listings rarely have parking)
    if parking is None:
        parking = False

    # If no furnished info in description, default to False
    if furnished is None:
        furnished = False

    return {"text": text, "bedrooms": bedrooms, "furnished": furnished, "parking": parking}


def _extract_rentals(html: str) -> dict:
    """Extract listing data from Rentals.ca detail page."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)[:3000]
    bedrooms = extract_bedrooms_from_text(text)
    return {"text": text, "bedrooms": bedrooms}


def _extract(fixture_id: str) -> dict:
    """Extract text and bedrooms from a fixture, using source-appropriate logic."""
    html = (FIXTURES_DIR / f"{fixture_id}.html").read_text(encoding="utf-8")
    source = fixture_id.split("_", 1)[1]
    if source == "kijiji":
        return _extract_kijiji(html)
    if source == "centris":
        return _extract_centris(html)
    return _extract_rentals(html)


SAMPLES = _load_samples()
IDS = [s["fixture_id"] for s in SAMPLES]


@pytest.mark.parametrize("sample", SAMPLES, ids=IDS)
class TestFurnishedDetection:
    def test_furnished(self, sample):
        data = _extract(sample["fixture_id"])
        # Use structured detection if available, else parse from text
        if "furnished" in data:
            detected = data["furnished"]
        else:
            detected, _ = check_furnished_parking(data["text"])
        label = sample["label_furnished"]
        if label == "semi":
            assert detected in (True, "semi"), f"{sample['fixture_id']}: expected semi/True, got {detected}"
        else:
            assert detected == label, f"{sample['fixture_id']}: expected {label}, got {detected}"


@pytest.mark.parametrize("sample", SAMPLES, ids=IDS)
class TestParkingDetection:
    def test_parking(self, sample):
        data = _extract(sample["fixture_id"])
        if "parking" in data:
            detected = data["parking"]
        else:
            _, detected = check_furnished_parking(data["text"])
        label = sample["label_parking"]
        assert detected == label, f"{sample['fixture_id']}: expected {label}, got {detected}"


@pytest.mark.parametrize("sample", SAMPLES, ids=IDS)
class TestBedroomDetection:
    def test_bedrooms(self, sample):
        data = _extract(sample["fixture_id"])
        label = sample["label_bedrooms"]
        assert data["bedrooms"] == label, f"{sample['fixture_id']}: expected {label}, got {data['bedrooms']}"


@pytest.mark.parametrize("sample", SAMPLES, ids=IDS)
class TestMoveInDateDetection:
    def test_move_in_date(self, sample):
        label = sample["label_move_in_date"]
        if not label:
            pytest.skip("no label_move_in_date for this sample")
        data = _extract(sample["fixture_id"])
        detected = extract_move_in_date(data["text"])
        assert detected == label, f"{sample['fixture_id']}: expected {label}, got {detected}"
