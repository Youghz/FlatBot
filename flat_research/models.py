"""Shared data models."""

from dataclasses import dataclass


@dataclass
class Listing:
    source: str = ""
    title: str = ""
    price: float = 0.0
    url: str = ""
    address: str = ""
    neighbourhood: str = ""
    bedrooms: int = 0
    furnished: bool = False
    parking: bool = False
    description: str = ""
    image_url: str = ""
    listing_id: str = ""
    move_in_date: str = ""  # YYYY-MM-DD or "immediate" or ""
