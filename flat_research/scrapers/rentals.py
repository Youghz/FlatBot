"""Scraper for Rentals.ca Montreal rental listings.

Uses the Rentals.ca GraphQL API. Authenticates with a public API key
to obtain a JWT, then queries rentalListings with price/bedroom filters.
"""

import logging

from flat_research.http_client import create_session
from flat_research.models import Listing
from flat_research.parsing import matches_criteria

logger = logging.getLogger(__name__)

RENTALS_GQL_URL = "https://rentals.ca/graphql"
RENTALS_GQL_KEY = "kJFM-mm4c-xg6B-qiwy"
RENTALS_BASE = "https://rentals.ca"
MAX_RESULTS = 50

_AUTH_MUTATION = "mutation($k:String!){acquireAuthInfo(credentials:{apiKey:$k}){jwt}}"

_SEARCH_QUERY = """
query SearchListings(
  $first: PositiveInt,
  $after: String,
  $place: PlaceInput!,
  $filters: RentalListingsConnectionFilterSet
) {
  rentalListings(
    first: $first,
    after: $after,
    place: $place,
    filters: $filters
  ) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        name
        path
        rentRange
        bedsRange
        type
        parking {
          parkingTypes { parkingType }
          parkingSpotsPerRental
        }
        address {
          neighbourhood { name }
          street
          city { name }
        }
      }
    }
  }
}
"""


def _authenticate(session) -> str:
    """Acquire a JWT access token from the Rentals.ca GraphQL API."""
    payload = {
        "query": _AUTH_MUTATION,
        "variables": {"k": RENTALS_GQL_KEY},
    }
    resp = session.post(
        RENTALS_GQL_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["acquireAuthInfo"]["jwt"]["accessToken"]


def _build_filters(criteria: dict) -> dict:
    """Build GraphQL filter object from config criteria."""
    filters: dict = {}

    price_min = criteria.get("price_min", 0)
    price_max = criteria.get("price_max", 99999)
    filters["rent"] = [price_min, price_max]

    bedrooms_min = criteria.get("bedrooms_min", 0)
    if bedrooms_min > 0:
        filters["beds"] = list(range(bedrooms_min, bedrooms_min + 5))

    if criteria.get("furnished"):
        filters["furnished"] = ["yes", "fully"]

    if criteria.get("parking"):
        filters["parkingSpots"] = [1, 2, 3, 4, 5]

    return filters


def _node_to_listing(node: dict) -> Listing | None:
    """Convert a GraphQL rental listing node to a Listing object."""
    lid = node.get("id", "")
    if not lid:
        return None

    # Price — rentRange is [min, max]; use min for single-unit, avg for buildings
    rent_range = node.get("rentRange") or [0, 0]
    price = rent_range[0] if rent_range[0] == rent_range[1] else rent_range[0]

    # Bedrooms — bedsRange is [min, max]
    beds_range = node.get("bedsRange") or [0, 0]
    bedrooms = int(beds_range[0]) if beds_range else 0

    # URL
    path = node.get("path", "")
    url = f"{RENTALS_BASE}/{path}" if path else ""

    # Address
    address_obj = node.get("address") or {}
    street = address_obj.get("street", "")
    city_name = (address_obj.get("city") or {}).get("name", "")
    address = f"{street}, {city_name}" if street and city_name else street or city_name

    # Neighbourhood
    hood_obj = address_obj.get("neighbourhood") or {}
    neighbourhood = hood_obj.get("name", "")

    # Parking
    parking_obj = node.get("parking") or {}
    parking_types = parking_obj.get("parkingTypes") or []
    has_parking = len(parking_types) > 0

    # Title
    name = node.get("name") or ""
    title = name if name else street

    return Listing(
        source="rentals",
        title=title,
        price=price,
        url=url,
        address=address,
        neighbourhood=neighbourhood,
        bedrooms=bedrooms,
        furnished=False,  # API filters furnished but doesn't return it per-listing
        parking=has_parking,
        description=f"{title} - {address}",
        listing_id=f"rentals_{lid}",
        move_in_date="",
    )


def scrape(config: dict, session=None) -> list[Listing]:
    """Scrape Rentals.ca for matching rental listings."""
    listings = []
    criteria = config["criteria"]

    if session is None:
        session = create_session()

    # Authenticate
    try:
        token = _authenticate(session)
    except Exception as e:
        logger.error(f"Rentals.ca authentication failed: {e}")
        return listings

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    filters = _build_filters(criteria)
    variables = {
        "first": MAX_RESULTS,
        "place": {"namedArea": "montreal,qc,ca"},
        "filters": filters,
    }

    logger.info(f"Scraping Rentals.ca: filters={filters}")

    seen_ids = set()
    cursor = None

    # Paginate through results (max 2 pages to stay reasonable)
    for page in range(2):
        if cursor:
            variables["after"] = cursor

        payload = {"query": _SEARCH_QUERY, "variables": variables}

        try:
            resp = session.post(RENTALS_GQL_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Rentals.ca GraphQL request failed: {e}")
            break

        if data.get("errors"):
            logger.error(f"Rentals.ca GraphQL errors: {data['errors']}")
            break

        rl_data = data.get("data", {}).get("rentalListings")
        if not rl_data:
            break

        edges = rl_data.get("edges", [])
        logger.info(f"Rentals.ca page {page + 1}: {len(edges)} listings")

        for edge in edges:
            node = edge.get("node", {})
            try:
                listing = _node_to_listing(node)
                if listing and listing.listing_id not in seen_ids:
                    seen_ids.add(listing.listing_id)
                    if matches_criteria(listing, config):
                        listings.append(listing)
            except Exception as e:
                logger.warning(f"Error parsing Rentals.ca listing: {e}")

        page_info = rl_data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    logger.info(f"Rentals.ca: {len(listings)} listings match criteria")
    return listings
