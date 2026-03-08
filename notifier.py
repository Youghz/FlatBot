"""Telegram notification for new listings."""

import logging
from html import escape

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_notification(new_listings: list, sheet_url: str, config: dict) -> None:
    """Send a Telegram message for each new listing found."""
    token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]

    if not token or not chat_id:
        logger.warning("Telegram bot_token or chat_id not configured. Skipping notification.")
        return

    url = TELEGRAM_API.format(token=token)

    if not new_listings:
        return

    summary = f"<b>{len(new_listings)} nouveau(x) logement(s) trouve(s)!</b>\n\n"

    for listing in new_listings:
        furnished = "Meuble" if listing.furnished else "Non meuble"
        parking = "Parking" if listing.parking else "Pas de parking"
        title_short = escape(listing.title[:80])
        address = escape(listing.address)

        summary += (
            f"<b>{title_short}</b>\n"
            f"{listing.price:.0f}$/mois | {listing.bedrooms} ch\n"
            f"{address}\n"
            f"{furnished} | {parking}\n"
            f"<a href=\"{listing.url}\">Voir l'annonce</a> ({listing.source})\n\n"
        )

    summary += f"<a href=\"{sheet_url}\">Voir le Google Sheet</a>"

    # Telegram has a 4096 char limit per message
    messages = []
    while summary:
        messages.append(summary[:4000])
        summary = summary[4000:]

    for msg in messages:
        _send_message(url, chat_id, msg)


def _send_message(url: str, chat_id: str, text: str) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram notification sent")
    except requests.RequestException as e:
        logger.error(f"Telegram notification failed: {e}")
        logger.error(f"Response: {resp.text[:200]}" if 'resp' in dir() else "")
