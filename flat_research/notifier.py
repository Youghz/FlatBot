"""Telegram notification for new listings."""

import logging
from html import escape

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_notification(new_listings: list, chat_id: str, bot_token: str, dashboard_url: str = "") -> None:
    """Send a Telegram message with new listings to a specific chat."""
    if not bot_token or not chat_id:
        logger.warning("Telegram bot_token or chat_id not configured. Skipping notification.")
        return

    if not new_listings:
        return

    url = TELEGRAM_API.format(token=bot_token)

    summary = f"<b>{len(new_listings)} nouveau(x) logement(s) trouve(s)!</b>\n\n"

    for listing in new_listings:
        if listing.furnished is True:
            furnished = "Meublé"
        elif listing.furnished is False:
            furnished = "Non meublé"
        else:
            furnished = "Meublé: ?"
        if listing.parking is True:
            parking = "Parking"
        elif listing.parking is False:
            parking = "Pas de parking"
        else:
            parking = "Parking: ?"
        title_short = escape(listing.title[:80])
        address = escape(listing.address)

        summary += (
            f"<b>{title_short}</b>\n"
            f"{listing.price:.0f}$/mois | {listing.bedrooms} ch\n"
            f"{address}\n"
            f"{furnished} | {parking}\n"
            f'<a href="{listing.url}">Voir l\'annonce</a> ({listing.source})\n\n'
        )

    if dashboard_url:
        summary += f'<a href="{dashboard_url}">Voir le dashboard</a>'

    # Telegram has a 4096 char limit per message
    messages = []
    while summary:
        messages.append(summary[:4000])
        summary = summary[4000:]

    for msg in messages:
        _send_message(url, chat_id, msg)


def _send_message(url: str, chat_id: str | int, text: str) -> None:
    payload = {
        "chat_id": int(chat_id),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = None
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram notification sent")
    except requests.RequestException as e:
        logger.error(f"Telegram notification failed: {e}")
        if resp is not None:
            logger.error(f"Response: {resp.text[:200]}")
