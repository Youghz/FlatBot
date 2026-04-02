"""Tests for scraper job orchestration."""

from flat_research.scraper_job import scrape_all


class TestScrapeAll:
    def test_returns_list(self):
        """scrape_all returns a list (may be empty if no network)."""
        # This is a smoke test — in CI, scrapers may fail due to network
        result = scrape_all()
        assert isinstance(result, list)
