"""Flat Research - Montreal apartment/house finder.

Usage:
    python -m flat_research              # Run once (single-user, legacy)
    python -m flat_research --schedule   # Run every hour (single-user, legacy)
    python -m flat_research --check      # Health check
    python -m flat_research --serve      # Start the web API server
    python -m flat_research --scrape-multi  # Multi-user scrape cycle (DB-based)
"""

import argparse
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yaml
from dotenv import load_dotenv

from flat_research.http_client import create_session, get
from flat_research.notifier import send_notification
from flat_research.parsing import matches_criteria
from flat_research.scrapers import SCRAPERS
from flat_research.sheets import _get_client, _get_or_create_spreadsheet, add_listings


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


def _setup_logging():
    """Use JSON logging on Cloud Run, human-readable locally."""
    if os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_JOB"):
        import json as _json

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                return _json.dumps(
                    {
                        "severity": record.levelname,
                        "message": record.getMessage(),
                        "logger": record.name,
                        "timestamp": self.formatTime(record),
                    }
                )

        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logging.root.handlers = [handler]
        logging.root.setLevel(logging.INFO)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


_setup_logging()
logger = logging.getLogger(__name__)


def run_once(config: dict) -> bool:
    """Run a single scraping cycle (single-user, legacy mode)."""
    logger.info("=== Starting scraping cycle ===")

    all_listings = []
    sources = config.get("sources", [])
    timeout_s = config.get("schedule", {}).get("timeout_seconds", 240)

    active_scrapers = {}
    for name in sources:
        if name in SCRAPERS:
            active_scrapers[name] = (SCRAPERS[name], create_session())

    with ThreadPoolExecutor(max_workers=len(active_scrapers)) as pool:
        futures = {pool.submit(fn, config, session): name for name, (fn, session) in active_scrapers.items()}
        for future in as_completed(futures, timeout=timeout_s):
            name = futures[future]
            try:
                results = future.result()
                # Filter with centralized criteria (scrapers return all parsed listings)
                matched = [listing for listing in results if matches_criteria(listing, config)]
                all_listings.extend(matched)
                logger.info(f"{name}: {len(matched)} matching listings (of {len(results)} scraped)")
            except Exception as e:
                logger.error(f"{name} scraper failed: {e}")

    logger.info(f"Total listings found: {len(all_listings)}")

    if not all_listings:
        logger.info("No matching listings found this cycle.")
        return True

    try:
        new_listings, sheet_url = add_listings(all_listings, config)
        logger.info(f"New listings added to sheet: {len(new_listings)}")
    except Exception as e:
        logger.error(f"Google Sheets update failed: {e}")
        return False

    if new_listings:
        try:
            bot_token = config["telegram"]["bot_token"]
            chat_id = config["telegram"]["chat_id"]
            send_notification(new_listings, chat_id, bot_token)
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    logger.info("=== Cycle complete ===")
    return True


def run_check(config: dict) -> bool:
    """Health check: verify each component can connect."""
    checks = {}

    try:
        session = create_session()
        resp = get(session, "https://www.kijiji.ca/b-appartement-condo/ville-de-montreal/c37l1700281")
        checks["Kijiji"] = resp.status_code == 200
    except Exception as e:
        logger.error(f"Kijiji check failed: {e}")
        checks["Kijiji"] = False

    try:
        session = create_session()
        resp = get(session, "https://www.centris.ca/fr/propriete~a-louer~montreal-rosemont-la-petite-patrie")
        checks["Centris"] = resp.status_code == 200
    except Exception as e:
        logger.error(f"Centris check failed: {e}")
        checks["Centris"] = False

    try:
        client = _get_client(config)
        spreadsheet = _get_or_create_spreadsheet(client, config)
        sheet = spreadsheet.sheet1
        sheet.row_values(1)
        checks["Google Sheets"] = True
    except Exception as e:
        logger.error(f"Google Sheets check failed: {e}")
        checks["Google Sheets"] = False

    try:
        token = config["telegram"]["bot_token"]
        chat_id = config["telegram"]["chat_id"]
        if not token or "${" in token:
            raise ValueError("bot_token not configured")
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": int(chat_id), "text": "[check] Flat Research health check OK"},
            timeout=10,
        )
        checks["Telegram"] = resp.status_code == 200
    except Exception as e:
        logger.error(f"Telegram check failed: {e}")
        checks["Telegram"] = False

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
    parser.add_argument("--serve", action="store_true", help="Start the web API server")
    parser.add_argument("--scrape-multi", action="store_true", help="Run multi-user scrape cycle (DB-based)")
    args = parser.parse_args()

    if args.serve:
        import uvicorn

        from flat_research.api import create_app

        app = create_app()
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)  # noqa: S104
        return

    if args.scrape_multi:
        from flat_research.scraper_job import run_multi_user

        ok = run_multi_user()
        sys.exit(0 if ok else 1)

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
