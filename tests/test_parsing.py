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
            # Positive detection
            ("Appartement meublé avec stationnement", True, True),
            ("Furnished apartment with parking", True, True),
            ("Meubles inclus, garage", True, True),
            ("Semi-meublé avec garage intérieur", "semi", True),
            # Negative detection
            ("Non meublé, pas de parking", False, False),
            ("Unfurnished, no parking", False, False),
            # Tri-state: None when no mention
            ("Bel appartement lumineux", None, None),
            ("Logement vide", None, None),
            # "tout inclus" should NOT match furnished (Quebec = utilities included)
            ("Logement tout inclus chauffage eau chaude", None, None),
            ("All included utilities", None, None),
            # "garage a velo" / "vente de garage" → detected as no parking (negation)
            ("Rangement et garage à vélo disponibles", None, False),
            ("Vente de garage ce samedi", None, False),
            # Mixed: one known, one unknown
            ("Appartement meublé", True, None),
            ("Pas de stationnement", None, False),
        ],
    )
    def test_furnished_parking(self, text, furnished, parking):
        f, p = check_furnished_parking(text)
        assert f is furnished, f"furnished: expected {furnished}, got {f} for: {text}"
        assert p is parking, f"parking: expected {parking}, got {p} for: {text}"


class TestMatchesCriteria:
    CONFIG = {
        "criteria": {
            "price_min": 2000,
            "price_max": 3000,
            "bedrooms_min": 3,
            "furnished": False,
            "parking": False,
            "neighbourhoods": {
                "Villeray": ["villeray"],
                "Rosemont": ["rosemont"],
                "Petite-Patrie": ["petite-patrie", "petite patrie"],
            },
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
            "furnished": None,
            "parking": None,
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

    def test_bedrooms_max(self):
        config = {"criteria": {**self.CONFIG["criteria"], "bedrooms_max": 4}}
        assert matches_criteria(self._make_listing(bedrooms=4), config) is True
        assert matches_criteria(self._make_listing(bedrooms=5), config) is False

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
                "neighbourhoods": {"Mile-Ex": ["mile-ex", "mile ex"]},
            }
        }
        listing = self._make_listing(address="Mile Ex, Montreal")
        assert matches_criteria(listing, config) is True

    def test_plateau_match(self):
        config = {
            "criteria": {
                **self.CONFIG["criteria"],
                "neighbourhoods": {"Plateau": ["plateau", "plateau-mont-royal"]},
            }
        }
        listing = self._make_listing(address="Plateau-Mont-Royal, Montreal")
        assert matches_criteria(listing, config) is True

    def test_mile_end_match(self):
        config = {
            "criteria": {
                **self.CONFIG["criteria"],
                "neighbourhoods": {"Mile-End": ["mile-end", "mile end"]},
            }
        }
        listing = self._make_listing(address="Mile End, Montreal")
        assert matches_criteria(listing, config) is True

    def test_furnished_required_but_explicitly_false(self):
        config = {"criteria": {**self.CONFIG["criteria"], "furnished": True}}
        listing = self._make_listing(furnished=False)
        assert matches_criteria(listing, config) is False

    def test_furnished_required_and_present(self):
        config = {"criteria": {**self.CONFIG["criteria"], "furnished": True}}
        listing = self._make_listing(furnished=True)
        assert matches_criteria(listing, config) is True

    def test_furnished_required_but_unknown_passes(self):
        """Unknown (None) should pass when furnished is required — don't miss listings."""
        config = {"criteria": {**self.CONFIG["criteria"], "furnished": True}}
        listing = self._make_listing(furnished=None)
        assert matches_criteria(listing, config) is True

    def test_parking_required_but_explicitly_false(self):
        config = {"criteria": {**self.CONFIG["criteria"], "parking": True}}
        listing = self._make_listing(parking=False)
        assert matches_criteria(listing, config) is False

    def test_parking_required_and_present(self):
        config = {"criteria": {**self.CONFIG["criteria"], "parking": True}}
        listing = self._make_listing(parking=True)
        assert matches_criteria(listing, config) is True

    def test_parking_required_but_unknown_passes(self):
        """Unknown (None) should pass when parking is required — don't miss listings."""
        config = {"criteria": {**self.CONFIG["criteria"], "parking": True}}
        listing = self._make_listing(parking=None)
        assert matches_criteria(listing, config) is True

    def test_move_in_after_keeps_future(self):
        config = {"criteria": {**self.CONFIG["criteria"], "move_in_after": "2026-06-01"}}
        listing = self._make_listing(move_in_date="2026-07-01")
        assert matches_criteria(listing, config) is True

    def test_move_in_after_filters_past(self):
        config = {"criteria": {**self.CONFIG["criteria"], "move_in_after": "2026-06-01"}}
        listing = self._make_listing(move_in_date="2026-03-01")
        assert matches_criteria(listing, config) is False

    def test_move_in_after_immediate_ok(self):
        config = {"criteria": {**self.CONFIG["criteria"], "move_in_after": "2026-06-01"}}
        listing = self._make_listing(move_in_date="immediate")
        assert matches_criteria(listing, config) is True

    def test_legacy_neighbourhood_list_format(self):
        """Backward compat: neighbourhoods as a plain list still works."""
        config = {
            "criteria": {
                **self.CONFIG["criteria"],
                "neighbourhoods": ["Villeray", "Rosemont"],
            }
        }
        listing = self._make_listing(address="Villeray, Montreal")
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
