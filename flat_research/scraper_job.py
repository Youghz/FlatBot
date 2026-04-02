"""Scraper job.

Scrapes the latest 50 listings from each source (no filters),
saves everything to DB, then filters per user and notifies.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from flat_research.db import (
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


def scrape_all() -> list[Listing]:
    """Run all scrapers in parallel and return combined raw listings."""
    all_listings: list[Listing] = []
    timeout_s = 240

    # Each scraper gets its own session (Rentals creates its own internally)
    scraper_args = {}
    for name, fn in SCRAPERS.items():
        if name == "rentals":
            scraper_args[name] = (fn, {})
        else:
            scraper_args[name] = (fn, {"session": create_session()})

    with ThreadPoolExecutor(max_workers=len(scraper_args)) as pool:
        futures = {pool.submit(fn, **kwargs): name for name, (fn, kwargs) in scraper_args.items()}
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
    """Scrape latest listings, save to DB, filter and notify per user."""
    db = get_db()
    try:
        # 1. Scrape all sources (no filters — latest 50 per source)
        all_listings = scrape_all()
        if not all_listings:
            logger.info("No listings scraped this cycle.")
            return True

        # 2. Save to DB
        save_listings(db, all_listings)
        logger.info("Listings saved to DB")

        # 3. Filter per user and notify
        user_criteria_pairs = get_all_active_criteria(db)
        if not user_criteria_pairs:
            logger.info("No active users with criteria.")
            return True

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
        logger.error(f"Scrape failed: {e}")
        return False
    finally:
        db.close()
