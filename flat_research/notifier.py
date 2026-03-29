"""Telegram notification for new listings."""

import logging
from html import escape

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _furnished_icon(v) -> str:
    if v is True or v == "semi":
        return "🛋 Meublé"
    if v is False:
        return "📦 Non meublé"
    return "❓ Meublé inconnu"


def _parking_icon(v) -> str:
    if v is True:
        return "🅿️ Parking"
    if v is False:
        return "🚫 Pas de parking"
    return "❓ Parking inconnu"


def _move_in_label(v: str) -> str:
    if v == "immediate":
        return "🔑 Disponible maintenant"
    if v:
        return f"📅 Emménagement: {v}"
    return ""


def _format_listing(listing) -> str:
    title = escape(listing.title[:80])
    address = escape(listing.address)
    neighbourhood = escape(listing.neighbourhood) if listing.neighbourhood else ""

    # Header: title + price
    lines = [f"<b>{title}</b>"]
    lines.append(f"💰 <b>{listing.price:.0f}$</b>/mois  •  🛏 {listing.bedrooms} ch.")

    # Location
    loc = address
    if neighbourhood and neighbourhood.lower() not in address.lower():
        loc = f"{address} ({neighbourhood})"
    lines.append(f"📍 {loc}")

    # Attributes on one line
    attrs = [_furnished_icon(listing.furnished), _parking_icon(listing.parking)]
    lines.append(" • ".join(attrs))

    # Move-in date
    move_in = _move_in_label(listing.move_in_date)
    if move_in:
        lines.append(move_in)

    # Link + source
    lines.append(f'🔗 <a href="{listing.url}">Voir l\'annonce</a>  <i>({listing.source})</i>')

    return "\n".join(lines)


def send_notification(new_listings: list, chat_id: str, bot_token: str, dashboard_url: str = "") -> bool:
    """Send a Telegram message with new listings to a specific chat.

    Returns True if all messages were sent successfully, False otherwise.
    """
    if not bot_token or not chat_id:
        logger.warning("Telegram bot_token or chat_id not configured. Skipping notification.")
        return False

    if not new_listings:
        return True

    url = TELEGRAM_API.format(token=bot_token)

    n = len(new_listings)
    plural = "s" if n > 1 else ""
    header = f"🏠 <b>{n} nouveau{'x' if n > 1 else ''} logement{plural}</b>\n\n"

    body = "\n\n".join(_format_listing(listing) for listing in new_listings)

    footer = ""
    if dashboard_url:
        footer = f'\n\n📊 <a href="{dashboard_url}">Voir le dashboard</a>'

    full_text = header + body + footer

    # Telegram has a 4096 char limit per message
    messages = []
    while full_text:
        messages.append(full_text[:4000])
        full_text = full_text[4000:]

    for msg in messages:
        if not _send_message(url, chat_id, msg):
            return False
    return True


def _send_message(url: str, chat_id: str | int, text: str) -> bool:
    """Send a single Telegram message. Returns True on success."""
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
        return True
    except requests.RequestException as e:
        logger.error(f"Telegram notification failed: {e}")
        if resp is not None:
            logger.error(f"Response: {resp.text[:200]}")
        return False
