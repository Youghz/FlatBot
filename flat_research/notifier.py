"""Telegram notification for new listings."""

import logging
from html import escape

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _furnished_icon(v) -> str:
    return "🛋 Meublé" if v else "📦 Non meublé"


def _parking_icon(v) -> str:
    return "🅿️ Parking" if v else "🚫 Pas de parking"


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
    url = escape(listing.url)
    source = escape(listing.source)

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
    lines.append(f'🔗 <a href="{url}">Voir l\'annonce</a>  <i>({source})</i>')

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

    formatted = [_format_listing(listing) for listing in new_listings]

    footer = ""
    if dashboard_url:
        footer = f'\n\n📊 <a href="{escape(dashboard_url)}">Voir le dashboard</a>'

    # Split into messages that fit Telegram's 4096 char limit
    # Split between listings, never mid-HTML-tag
    messages = []
    current = header
    for entry in formatted:
        candidate = current + entry + "\n\n"
        if len(candidate) > 3800 and current != header:
            messages.append(current.rstrip())
            current = entry + "\n\n"
        else:
            current = candidate
    current += footer
    messages.append(current.rstrip())

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
