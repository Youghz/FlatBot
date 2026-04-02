"""Tests for scrapers using saved HTML/JSON fixtures.

These tests parse real data without making network requests,
so they also serve as regression tests if the sites change their structure.
"""

import json
import pathlib

import pytest
from bs4 import BeautifulSoup

from flat_research.scrapers.centris import _build_urls, _parse_card
from flat_research.scrapers.rentals import _build_filters, _node_to_listing

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

CONFIG = {
    "criteria": {
        "city": "Montreal",
        "neighbourhoods": {
            "Villeray—Saint-Michel—Parc-Extension": ["villeray", "saint-michel", "parc-extension"],
            "Rosemont—La Petite-Patrie": ["rosemont", "petite-patrie", "petite italie"],
            "Ahuntsic-Cartierville": ["ahuntsic", "cartierville"],
        },
        "bedrooms_min": 3,
        "price_min": 2000,
        "price_max": 3000,
        "furnished": True,
        "parking": True,
    }
}


class TestCentrisFixture:
    @pytest.fixture
    def cards(self):
        html = (FIXTURES / "centris_search.html").read_text()
        soup = BeautifulSoup(html, "html.parser")
        return soup.select("div.property-thumbnail-item")

    def test_cards_found(self, cards):
        assert len(cards) > 0, "No Centris cards found in fixture — HTML structure may have changed"

    def test_parse_card_returns_listing(self, cards):
        results = [_parse_card(c) for c in cards]
        listings = [r for r in results if r is not None]
        assert len(listings) > 0, "No listings parsed from Centris cards"

    def test_parsed_listing_has_required_fields(self, cards):
        listing = None
        for card in cards:
            listing = _parse_card(card)
            if listing:
                break
        assert listing is not None
        assert listing.listing_id.startswith("centris_")
        assert listing.price > 0
        assert listing.url.startswith("https://")
        assert listing.source == "centris"

    def test_bedroom_count_populated(self, cards):
        listings = [_parse_card(c) for c in cards]
        listings = [item for item in listings if item is not None]
        with_bedrooms = [item for item in listings if item.bedrooms > 0]
        assert len(with_bedrooms) > 0, "No listings have bedroom count — div.cac parsing may be broken"


class TestKijjiFixture:
    @pytest.fixture
    def soup(self):
        html = (FIXTURES / "kijiji_search.html").read_text()
        return BeautifulSoup(html, "html.parser")

    def test_jsonld_present(self, soup):
        script = soup.find("script", type="application/ld+json")
        assert script is not None, "No JSON-LD found in Kijiji fixture — page structure may have changed"

    def test_jsonld_has_listings(self, soup):
        import json

        script = soup.find("script", type="application/ld+json")
        if script:
            data = json.loads(script.string)
            items = data.get("itemListElement", [])
            assert len(items) > 0, "JSON-LD ItemList is empty"
        else:
            # Fallback: check for listing links (older fixture)
            links = soup.select("a[href*='/v-']")
            assert len(links) > 0, "No listing links found in Kijiji fixture"


class TestCentrisUrls:
    def test_build_urls_deduplicates(self):
        urls = _build_urls(CONFIG)
        # Villeray, Mile-Ex, Petite-Italie all map to same borough
        assert len(urls) == len(set(urls)), "Duplicate URLs generated"

    def test_build_urls_contains_boroughs(self):
        urls = _build_urls(CONFIG)
        slugs = [u.split("~")[-1] for u in urls]
        assert "montreal-villeray-saint-michel-parc-extension" in slugs
        assert "montreal-rosemont-la-petite-patrie" in slugs
        assert "montreal-ahuntsic-cartierville" in slugs

    def test_build_urls_includes_plateau(self):
        config = {
            "criteria": {
                **CONFIG["criteria"],
                "neighbourhoods": {
                    "Le Plateau-Mont-Royal": ["plateau", "mile-end"],
                },
            }
        }
        urls = _build_urls(config)
        slugs = [u.split("~")[-1] for u in urls]
        assert "montreal-le-plateau-mont-royal" in slugs


class TestRentalsFixture:
    @pytest.fixture
    def nodes(self):
        data = json.loads((FIXTURES / "rentals_graphql.json").read_text())
        return [edge["node"] for edge in data["data"]["rentalListings"]["edges"]]

    def test_nodes_found(self, nodes):
        assert len(nodes) > 0, "No nodes found in Rentals.ca fixture"

    def test_parse_node_returns_listing(self, nodes):
        listing = _node_to_listing(nodes[0])
        assert listing is not None

    def test_parsed_listing_has_required_fields(self, nodes):
        listing = _node_to_listing(nodes[0])
        assert listing.listing_id.startswith("rentals_")
        assert listing.price > 0
        assert listing.url.startswith("https://")
        assert listing.source == "rentals"
        assert listing.bedrooms > 0

    def test_address_populated(self, nodes):
        listing = _node_to_listing(nodes[0])
        assert "Rue" in listing.address or "rue" in listing.address

    def test_neighbourhood_from_api(self, nodes):
        listing = _node_to_listing(nodes[0])
        assert listing.neighbourhood == "Rosemont"

    def test_null_neighbourhood_handled(self, nodes):
        listing = _node_to_listing(nodes[1])
        assert listing.neighbourhood == ""

    def test_null_name_uses_street(self, nodes):
        listing = _node_to_listing(nodes[2])
        assert listing.title != ""

    def test_parking_detection(self, nodes):
        with_parking = _node_to_listing(nodes[0])
        without_parking = _node_to_listing(nodes[2])
        assert with_parking.parking is True
        assert without_parking.parking is False  # no parking data → False (no unknowns)

    def test_furnished_from_api_field(self, nodes):
        furnished = _node_to_listing(nodes[0])
        not_furnished = _node_to_listing(nodes[1])
        assert furnished.furnished is True
        assert not_furnished.furnished is False

    def test_description_populated(self, nodes):
        listing = _node_to_listing(nodes[0])
        assert "meublé" in listing.description.lower() or "Rosemont" in listing.description


class TestRentalsFilters:
    def test_build_filters_basic(self):
        criteria = {"price_min": 2000, "price_max": 3000, "bedrooms_min": 3}
        filters = _build_filters(criteria)
        assert filters["rent"] == [2000, 3000]
        assert 3 in filters["beds"]

    def test_build_filters_furnished(self):
        criteria = {"price_min": 0, "price_max": 5000, "bedrooms_min": 1, "furnished": True}
        filters = _build_filters(criteria)
        assert filters["furnished"] == ["yes", "fully"]

    def test_build_filters_parking(self):
        criteria = {"price_min": 0, "price_max": 5000, "bedrooms_min": 1, "parking": True}
        filters = _build_filters(criteria)
        assert "parkingSpots" in filters
