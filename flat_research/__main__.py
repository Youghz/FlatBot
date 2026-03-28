"""Flat Research - Montreal apartment/house finder.

Usage:
    python -m flat_research --serve         # Start the web API server
    python -m flat_research --scrape-multi  # Multi-user scrape cycle (DB-based)
    python -m flat_research --check         # Health check (scrapers only)
"""

import argparse
import logging
import os
import sys

from flat_research.http_client import create_session, get

logger = logging.getLogger(__name__)


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


def run_check() -> bool:
    """Health check: verify each scraper site is reachable."""
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
        from curl_cffi import requests as cf_requests

        resp = cf_requests.get("https://rentals.ca/montreal", impersonate="chrome", timeout=30)
        checks["Rentals.ca"] = resp.status_code == 200
    except Exception as e:
        logger.error(f"Rentals.ca check failed: {e}")
        checks["Rentals.ca"] = False

    try:
        from flat_research.scrapers.rentals import RENTALS_GQL_KEY, _authenticate

        if RENTALS_GQL_KEY:
            from curl_cffi import requests as cf_requests

            session = cf_requests.Session(impersonate="chrome")
            jwt = _authenticate(session)
            checks["Rentals.ca GraphQL auth"] = bool(jwt)
        else:
            logger.warning("RENTALS_GQL_KEY not set, skipping GraphQL auth check")
    except Exception as e:
        logger.error(f"Rentals.ca GraphQL auth check failed: {e}")
        checks["Rentals.ca GraphQL auth"] = False

    # Rentals.ca blocks datacenter IPs (403) — warn but don't fail the check
    optional = {"Rentals.ca", "Rentals.ca GraphQL auth"}

    all_ok = True
    for name, ok in checks.items():
        status = "OK" if ok else "FAIL"
        logger.info(f"  {name}: {status}")
        if not ok and name not in optional:
            all_ok = False
        elif not ok:
            logger.warning(f"  {name}: failed (non-blocking)")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="FlatBot - Montreal apartment finder")
    parser.add_argument("--serve", action="store_true", help="Start the web API server")
    parser.add_argument("--scrape-multi", action="store_true", help="Run multi-user scrape cycle (DB-based)")
    parser.add_argument("--check", action="store_true", help="Run health checks and exit")
    parser.add_argument("--migrate", action="store_true", help="Run Alembic migrations and exit")
    parser.add_argument("--reset-password", nargs=2, metavar=("EMAIL", "NEW_PASSWORD"), help="Reset a user's password")
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

    if args.migrate:
        from alembic.config import Config

        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migration complete")
        return

    if args.reset_password:
        from flat_research.auth import hash_password
        from flat_research.db import User, get_db

        email, new_password = args.reset_password
        db = get_db()
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.error(f"User {email} not found")
            sys.exit(1)
        user.password_hash = hash_password(new_password)
        db.commit()
        logger.info(f"Password reset for {email}")
        db.close()
        return

    if args.check:
        ok = run_check()
        sys.exit(0 if ok else 1)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
