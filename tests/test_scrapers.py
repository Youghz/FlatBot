"""Tests for scrapers using saved HTML fixtures.

These tests parse real HTML without making network requests,
so they also serve as regression tests if the sites change their HTML.
"""

import pathlib

import pytest
from bs4 import BeautifulSoup

from scrapers.centris import _build_urls, _parse_card

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

CONFIG = {
    "criteria": {
        "city": "Montreal",
        "neighbourhoods": ["Villeray", "Mile-Ex", "Petite-Patrie", "Rosemont", "Petite-Italie", "Ahuntsic"],
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
        # Parse with relaxed config to get at least one result
        relaxed_config = {"criteria": {**CONFIG["criteria"], "price_min": 0, "price_max": 99999, "bedrooms_min": 0}}
        results = [_parse_card(c, relaxed_config) for c in cards]
        listings = [r for r in results if r is not None]
        assert len(listings) > 0, "No listings parsed from Centris cards"

    def test_parsed_listing_has_required_fields(self, cards):
        relaxed_config = {"criteria": {**CONFIG["criteria"], "price_min": 0, "price_max": 99999, "bedrooms_min": 0}}
        listing = None
        for card in cards:
            listing = _parse_card(card, relaxed_config)
            if listing:
                break
        assert listing is not None
        assert listing.listing_id.startswith("centris_")
        assert listing.price > 0
        assert listing.url.startswith("https://")
        assert listing.source == "centris"

    def test_bedroom_count_populated(self, cards):
        relaxed_config = {"criteria": {**CONFIG["criteria"], "price_min": 0, "price_max": 99999, "bedrooms_min": 0}}
        listings = [_parse_card(c, relaxed_config) for c in cards]
        listings = [item for item in listings if item is not None]
        with_bedrooms = [item for item in listings if item.bedrooms > 0]
        assert len(with_bedrooms) > 0, "No listings have bedroom count — div.cac parsing may be broken"


class TestKijjiFixture:
    @pytest.fixture
    def soup(self):
        html = (FIXTURES / "kijiji_search.html").read_text()
        return BeautifulSoup(html, "html.parser")

    def test_cards_found(self, soup):
        cards = soup.select("[data-testid='listing-card']")
        if not cards:
            cards = soup.select("section ul > li")
        assert len(cards) > 0, "No Kijiji cards found in fixture — HTML structure may have changed"

    def test_listing_links_present(self, soup):
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
                "neighbourhoods": ["Plateau", "Mile-End"],
            }
        }
        urls = _build_urls(config)
        slugs = [u.split("~")[-1] for u in urls]
        assert "montreal-le-plateau-mont-royal" in slugs
