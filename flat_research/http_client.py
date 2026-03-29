"""Shared HTTP session with retry logic and rate limiting."""

import logging
import threading
import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)

_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    respect_retry_after_header=True,
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
}

# Minimum delay between requests to the same site (seconds)
_MIN_DELAY = 1.0
_last_request_time: dict[str, float] = {}
_rate_lock = threading.Lock()


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    adapter = HTTPAdapter(max_retries=_RETRY_STRATEGY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get(session: requests.Session, url: str, timeout: int = 30) -> requests.Response:
    """GET with rate limiting per domain."""
    domain = urlparse(url).netloc

    with _rate_lock:
        now = time.monotonic()
        last = _last_request_time.get(domain, 0)
        wait = _MIN_DELAY - (now - last)
        if wait > 0:
            time.sleep(wait)
        _last_request_time[domain] = time.monotonic()

    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp
