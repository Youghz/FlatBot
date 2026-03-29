"""Tests for Telegram notification formatting."""

from unittest.mock import patch

from flat_research.models import Listing
from flat_research.notifier import send_notification


def make_listing(**kwargs) -> Listing:
    defaults = {
        "source": "kijiji",
        "title": "Bel appart 5½ Villeray",
        "price": 2500.0,
        "url": "https://example.com/listing/1",
        "address": "123 rue de Villeray",
        "neighbourhood": "Villeray",
        "bedrooms": 3,
        "furnished": True,
        "parking": True,
        "description": "Grand logement lumineux",
        "listing_id": "kijiji_123",
    }
    defaults.update(kwargs)
    return Listing(**defaults)


BOT_TOKEN = "fake-token"
CHAT_ID = "-123456"


class TestNotifierFormatting:
    @patch("flat_research.notifier.requests.post")
    def test_sends_message_with_listing_info(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        listing = make_listing()
        send_notification([listing], CHAT_ID, BOT_TOKEN)

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert "Bel appart" in payload["text"]
        assert "2500" in payload["text"]
        assert "Villeray" in payload["text"]
        assert payload["parse_mode"] == "HTML"

    @patch("flat_research.notifier.requests.post")
    def test_skips_when_no_token(self, mock_post):
        send_notification([make_listing()], CHAT_ID, "")
        mock_post.assert_not_called()

    @patch("flat_research.notifier.requests.post")
    def test_skips_when_no_listings(self, mock_post):
        send_notification([], CHAT_ID, BOT_TOKEN)
        mock_post.assert_not_called()

    @patch("flat_research.notifier.requests.post")
    def test_escapes_html_in_title(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        listing = make_listing(title="<script>alert('xss')</script>")
        send_notification([listing], CHAT_ID, BOT_TOKEN)

        payload = mock_post.call_args[1]["json"]
        assert "<script>" not in payload["text"]
        assert "&lt;script&gt;" in payload["text"]

    @patch("flat_research.notifier.requests.post")
    def test_chunks_long_messages(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        listings = [make_listing(title=f"Listing {i} " + "x" * 200, listing_id=f"kijiji_{i}") for i in range(30)]
        send_notification(listings, CHAT_ID, BOT_TOKEN)

        assert mock_post.call_count >= 2
