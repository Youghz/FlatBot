"""Multi-user scraper job.

Scrapes once with union criteria from all users, then filters
and notifies per user.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from flat_research.db import (
    SearchCriteria,
    criteria_to_config,
    get_all_active_criteria,
    get_db,
    get_seen_listing_ids,
    mark_listings_seen,
    save_listings,
)
from flat_research.http_client import create_session
from flat_research.models import Listing
from flat_research.notifier import send_notification
from flat_research.parsing import matches_criteria
from flat_research.scrapers import SCRAPERS

logger = logging.getLogger(__name__)


def compute_union_criteria(all_criteria: list[SearchCriteria]) -> dict:
    """Compute the widest (least restrictive) criteria from all users.

    This is used to build API query parameters that cover all users' needs.
    Per-user filtering happens after scraping.
    """
    all_hoods: dict[str, list[str]] = {}
    price_min = min(c.price_min for c in all_criteria)
    price_max = max(c.price_max for c in all_criteria)
    bedrooms_min = min(c.bedrooms_min for c in all_criteria)

    for c in all_criteria:
        hoods = c.neighbourhoods or {}
        if isinstance(hoods, dict):
            for name, variants in hoods.items():
                if name not in all_hoods:
                    all_hoods[name] = list(variants)
                else:
                    existing = set(all_hoods[name])
                    all_hoods[name].extend(v for v in variants if v not in existing)

    return {
        "criteria": {
            "neighbourhoods": all_hoods,
            "price_min": price_min,
            "price_max": price_max,
            "bedrooms_min": bedrooms_min,
            "furnished": False,
            "parking": False,
        },
        "sources": list(SCRAPERS.keys()),
    }


def scrape_all(config: dict) -> list[Listing]:
    """Run all scrapers in parallel and return combined raw listings."""
    all_listings: list[Listing] = []
    sources = config.get("sources", [])
    timeout_s = 240

    active_scrapers = {}
    for name in sources:
        if name in SCRAPERS:
            active_scrapers[name] = (SCRAPERS[name], create_session())

    if not active_scrapers:
        return all_listings

    with ThreadPoolExecutor(max_workers=len(active_scrapers)) as pool:
        futures = {pool.submit(fn, config, session): name for name, (fn, session) in active_scrapers.items()}
        for future in as_completed(futures, timeout=timeout_s):
            name = futures[future]
            try:
                results = future.result()
                all_listings.extend(results)
                logger.info(f"{name}: {len(results)} listings scraped")
            except Exception as e:
                logger.error(f"{name} scraper failed: {e}")

    logger.info(f"Total listings scraped: {len(all_listings)}")
    return all_listings


def run_multi_user() -> bool:
    """Scrape once with union criteria, then filter and notify per user."""
    db = get_db()
    try:
        user_criteria_pairs = get_all_active_criteria(db)
        if not user_criteria_pairs:
            logger.info("No active users with criteria. Nothing to do.")
            return True

        all_criteria = [criteria for _, criteria in user_criteria_pairs]
        union_config = compute_union_criteria(all_criteria)
        logger.info(f"Scraping for {len(user_criteria_pairs)} users with union criteria")

        all_listings = scrape_all(union_config)
        if not all_listings:
            logger.info("No listings scraped this cycle.")
            return True

        # Save all scraped listings to DB
        save_listings(db, all_listings)
        logger.info("Listings saved to DB")

        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        notified_count = 0

        for user, criteria in user_criteria_pairs:
            user_config = criteria_to_config(criteria)
            seen_ids = get_seen_listing_ids(db, user.id)

            new_for_user = [
                listing
                for listing in all_listings
                if matches_criteria(listing, user_config) and listing.listing_id not in seen_ids
            ]

            if not new_for_user:
                continue

            logger.info(f"User {user.email}: {len(new_for_user)} new listings")

            if user.telegram_chat_id and bot_token:
                sent = send_notification(new_for_user, user.telegram_chat_id, bot_token)
                if sent:
                    mark_listings_seen(db, user.id, [listing.listing_id for listing in new_for_user])
                    notified_count += 1
                else:
                    logger.error(f"User {user.email}: notification failed, will retry next cycle")
            else:
                has_chat = bool(user.telegram_chat_id)
                has_token = bool(bot_token)
                logger.warning(f"User {user.email}: skipping notification (chat_id={has_chat}, bot_token={has_token})")

        logger.info(f"Cycle complete: {notified_count} users notified")
        return True

    except Exception as e:
        logger.error(f"Multi-user scrape failed: {e}")
        return False
    finally:
        db.close()
