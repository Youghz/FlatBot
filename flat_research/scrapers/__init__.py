"""Scraper registry."""

from flat_research.scrapers import centris, kijiji, rentals

SCRAPERS = {
    "kijiji": kijiji.scrape,
    "centris": centris.scrape,
    "rentals": rentals.scrape,
}
