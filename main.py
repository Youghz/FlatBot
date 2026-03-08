#!/usr/bin/env python3
"""Flat Research - Montreal apartment/house finder.

Usage:
    python main.py              # Run once
    python main.py --schedule   # Run every hour (configurable)
"""

import argparse
import logging
import os
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from dotenv import load_dotenv

from http_client import create_session
from scrapers import kijiji, centris
from sheets import add_listings
from notifier import send_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _resolve_env_vars(obj):
    """Recursively replace ${VAR} placeholders with env var values."""
    if isinstance(obj, str):
        return re.sub(
            r"\$\{(\w+)\}",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            obj,
        )
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(i) for i in obj]
    return obj


def load_config(path: str = "config.yaml") -> dict:
    load_dotenv()
    with open(path) as f:
        config = yaml.safe_load(f)
    return _resolve_env_vars(config)


def run_once(config: dict) -> bool:
    """Run a single scraping cycle. Returns True on success, False on critical failure."""
    logger.info("=== Starting scraping cycle ===")

    all_listings = []
    sources = config.get("sources", [])

    # Each scraper gets its own session (connection pooling per site)
    scrapers = {}
    if "kijiji" in sources:
        scrapers["kijiji"] = (kijiji.scrape, create_session())
    if "centris" in sources:
        scrapers["centris"] = (centris.scrape, create_session())

    # Run scrapers in parallel
    with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
        futures = {
            pool.submit(fn, config, session): name
            for name, (fn, session) in scrapers.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results = future.result()
                all_listings.extend(results)
                logger.info(f"{name}: {len(results)} matching listings")
            except Exception as e:
                logger.error(f"{name} scraper failed: {e}")

    logger.info(f"Total listings found: {len(all_listings)}")

    if not all_listings:
        logger.info("No matching listings found this cycle.")
        return True

    # Add to Google Sheet (deduplication happens inside)
    try:
        new_listings, sheet_url = add_listings(all_listings, config)
        logger.info(f"New listings added to sheet: {len(new_listings)}")
        logger.info(f"Sheet URL: {sheet_url}")
    except Exception as e:
        logger.error(f"Google Sheets update failed: {e}")
        return False

    # Notify via Telegram
    if new_listings:
        try:
            send_notification(new_listings, sheet_url, config)
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False
    else:
        logger.info("No new listings to notify about.")

    logger.info("=== Cycle complete ===")
    return True


def run_check(config: dict) -> bool:
    """Health check: verify each component can connect. Returns True if all pass."""
    checks = {}

    # 1. Kijiji
    try:
        session = create_session()
        from http_client import get
        resp = get(session, "https://www.kijiji.ca/b-appartement-condo/ville-de-montreal/c37l1700281")
        checks["Kijiji"] = resp.status_code == 200
    except Exception as e:
        logger.error(f"Kijiji check failed: {e}")
        checks["Kijiji"] = False

    # 2. Centris
    try:
        session = create_session()
        from http_client import get
        resp = get(session, "https://www.centris.ca/fr/propriete~a-louer~montreal-rosemont-la-petite-patrie")
        checks["Centris"] = resp.status_code == 200
    except Exception as e:
        logger.error(f"Centris check failed: {e}")
        checks["Centris"] = False

    # 3. Google Sheets
    try:
        from sheets import _get_client, _get_or_create_spreadsheet
        client = _get_client(config)
        spreadsheet = _get_or_create_spreadsheet(client, config)
        sheet = spreadsheet.sheet1
        sheet.row_values(1)
        checks["Google Sheets"] = True
    except Exception as e:
        logger.error(f"Google Sheets check failed: {e}")
        checks["Google Sheets"] = False

    # 4. Telegram
    try:
        import requests as req
        token = config["telegram"]["bot_token"]
        chat_id = config["telegram"]["chat_id"]
        if not token or "${" in token:
            raise ValueError("bot_token not configured")
        resp = req.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "[check] Flat Research health check OK"},
            timeout=10,
        )
        checks["Telegram"] = resp.status_code == 200
    except Exception as e:
        logger.error(f"Telegram check failed: {e}")
        checks["Telegram"] = False

    # Report
    all_ok = True
    for name, ok in checks.items():
        status = "OK" if ok else "FAIL"
        logger.info(f"  {name}: {status}")
        if not ok:
            all_ok = False

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Flat Research - Montreal apartment finder")
    parser.add_argument("--schedule", action="store_true", help="Run on a schedule (every N minutes)")
    parser.add_argument("--check", action="store_true", help="Run health checks and exit")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.check:
        ok = run_check(config)
        sys.exit(0 if ok else 1)

    if args.schedule:
        interval = config["schedule"]["interval_minutes"] * 60
        logger.info(f"Running in scheduled mode every {config['schedule']['interval_minutes']} minutes")
        while True:
            try:
                run_once(config)
            except Exception as e:
                logger.error(f"Cycle failed: {e}")
            logger.info(f"Sleeping {config['schedule']['interval_minutes']} minutes...")
            time.sleep(interval)
    else:
        ok = run_once(config)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
