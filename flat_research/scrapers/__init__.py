"""Scraper registry."""

from flat_research.scrapers import centris, kijiji

SCRAPERS = {
    "kijiji": kijiji.scrape,
    "centris": centris.scrape,
}
