"""Unit tests for parsing functions."""

import pytest

from flat_research.models import Listing
from flat_research.parsing import (
    check_furnished_parking,
    extract_bedrooms_from_text,
    extract_move_in_date,
    is_move_in_past,
    matches_criteria,
)


class TestExtractBedrooms:
    """Test Quebec notation and standard bedroom extraction."""

    @pytest.mark.parametrize(
        "text,expected",
        [
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
        ],
    )
    def test_bedroom_extraction(self, text, expected):
        assert extract_bedrooms_from_text(text) == expected


class TestFurnishedParking:
    @pytest.mark.parametrize(
        "text,furnished,parking",
        [
            ("Appartement meublé avec stationnement", True, True),
            ("Furnished apartment with parking", True, True),
            ("Non meublé, pas de parking", False, False),
            ("Meubles inclus, garage", True, True),
            ("Logement vide", False, False),
        ],
    )
    def test_furnished_parking(self, text, furnished, parking):
        f, p = check_furnished_parking(text)
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
        assert matches_criteria(listing, self.CONFIG) is True

    def test_price_too_low(self):
        listing = self._make_listing(price=1500)
        assert matches_criteria(listing, self.CONFIG) is False

    def test_price_too_high(self):
        listing = self._make_listing(price=3500)
        assert matches_criteria(listing, self.CONFIG) is False

    def test_not_enough_bedrooms(self):
        listing = self._make_listing(bedrooms=2)
        assert matches_criteria(listing, self.CONFIG) is False

    def test_wrong_neighbourhood(self):
        listing = self._make_listing(address="Westmount, Montreal")
        assert matches_criteria(listing, self.CONFIG) is False

    def test_rosemont_match(self):
        listing = self._make_listing(address="Old Rosemont, Montreal")
        assert matches_criteria(listing, self.CONFIG) is True

    def test_mile_ex_variant(self):
        config = {
            "criteria": {
                **self.CONFIG["criteria"],
                "neighbourhoods": ["Mile-Ex"],
            }
        }
        listing = self._make_listing(address="Mile Ex, Montreal")
        assert matches_criteria(listing, config) is True

    def test_plateau_match(self):
        config = {
            "criteria": {
                **self.CONFIG["criteria"],
                "neighbourhoods": ["Plateau"],
            }
        }
        listing = self._make_listing(address="Plateau-Mont-Royal, Montreal")
        assert matches_criteria(listing, config) is True

    def test_mile_end_match(self):
        config = {
            "criteria": {
                **self.CONFIG["criteria"],
                "neighbourhoods": ["Mile-End"],
            }
        }
        listing = self._make_listing(address="Mile End, Montreal")
        assert matches_criteria(listing, config) is True


class TestExtractMoveInDate:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Disponible immédiatement", "immediate"),
            ("Available immediately", "immediate"),
            ("Disponible maintenant", "immediate"),
            ("Dès maintenant", "immediate"),
            ("1er juillet 2026", "2026-07-01"),
            ("15 août 2026", "2026-08-15"),
            ("1 septembre 2026", "2026-09-01"),
            ("15 June 2026", "2026-06-15"),
            ("1 sept. 2026", "2026-09-01"),
            ("15 juil. 2026", "2026-07-15"),
            ("August 1st 2026", "2026-08-01"),
            ("juillet 2026", "2026-07-01"),
            ("July 2026", "2026-07-01"),
            ("2026-07-01", "2026-07-01"),
            ("01/09/2026", "2026-09-01"),
            ("Bel appartement meublé", ""),
        ],
    )
    def test_extract_move_in(self, text, expected):
        assert extract_move_in_date(text) == expected

    def test_past_date_detected(self):
        assert is_move_in_past("2020-01-01") is True

    def test_future_date_not_past(self):
        assert is_move_in_past("2099-01-01") is False

    def test_immediate_not_past(self):
        assert is_move_in_past("immediate") is False

    def test_empty_not_past(self):
        assert is_move_in_past("") is False
