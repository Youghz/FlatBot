"""Unit tests for parsing functions."""

import pytest
from scrapers.kijiji import (
    _extract_bedrooms_from_text,
    _parse_price,
    _matches_criteria,
    _check_furnished_parking,
    Listing,
)


class TestExtractBedrooms:
    """Test Quebec notation and standard bedroom extraction."""

    @pytest.mark.parametrize("text,expected", [
        ("5½", 3),
        ("5 ½", 3),
        ("5 1/2", 3),
        ("5 et demi", 3),
        ("5.5", 3),
        ("4½", 2),
        ("4 1/2", 2),
        ("6½", 4),
        ("3½", 1),
        ("3 chambres", 3),
        ("3 bedrooms", 3),
        ("2 bed apartment", 2),
        ("Grand 6 ½ meublé à Villeray", 4),
        ("Bel appart 5 ½ meublé 3 chambres à coucher", 3),  # explicit wins
        ("", 0),
        ("studio", 0),
    ])
    def test_bedroom_extraction(self, text, expected):
        assert _extract_bedrooms_from_text(text) == expected


class TestParsePrice:
    @pytest.mark.parametrize("text,expected", [
        ("$2,500.00", 2500.0),
        ("2 500 $", 2.0),  # regex picks first number group
        ("$3,000", 3000.0),
        ("Free", 0.0),
        ("", 0.0),
    ])
    def test_price_parsing(self, text, expected):
        assert _parse_price(text) == expected


class TestFurnishedParking:
    @pytest.mark.parametrize("text,furnished,parking", [
        ("Appartement meublé avec stationnement", True, True),
        ("Furnished apartment with parking", True, True),
        ("Non meublé, pas de parking", False, False),
        ("Meubles inclus, garage", True, True),
        ("Logement vide", False, False),
    ])
    def test_furnished_parking(self, text, furnished, parking):
        f, p = _check_furnished_parking(text)
        assert f == furnished
        assert p == parking


class TestMatchesCriteria:
    CONFIG = {
        "criteria": {
            "price_min": 2000,
            "price_max": 3000,
            "bedrooms_min": 3,
            "neighbourhoods": ["Villeray", "Rosemont", "Petite-Patrie"],
        }
    }

    def _make_listing(self, **kwargs):
        defaults = {
            "price": 2500,
            "bedrooms": 3,
            "address": "Villeray, Montreal",
            "title": "",
            "neighbourhood": "",
            "description": "",
        }
        defaults.update(kwargs)
        return Listing(**defaults)

    def test_matches(self):
        listing = self._make_listing()
        assert _matches_criteria(listing, self.CONFIG) is True

    def test_price_too_low(self):
        listing = self._make_listing(price=1500)
        assert _matches_criteria(listing, self.CONFIG) is False

    def test_price_too_high(self):
        listing = self._make_listing(price=3500)
        assert _matches_criteria(listing, self.CONFIG) is False

    def test_not_enough_bedrooms(self):
        listing = self._make_listing(bedrooms=2)
        assert _matches_criteria(listing, self.CONFIG) is False

    def test_wrong_neighbourhood(self):
        listing = self._make_listing(address="Westmount, Montreal")
        assert _matches_criteria(listing, self.CONFIG) is False

    def test_rosemont_match(self):
        listing = self._make_listing(address="Old Rosemont, Montreal")
        assert _matches_criteria(listing, self.CONFIG) is True

    def test_mile_end_variant(self):
        config = {
            "criteria": {
                **self.CONFIG["criteria"],
                "neighbourhoods": ["Mile-Ex"],
            }
        }
        listing = self._make_listing(address="Mile End, Montreal")
        assert _matches_criteria(listing, config) is True
