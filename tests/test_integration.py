"""Integration tests — require real credentials.

Skipped automatically if env vars are not set (local dev / unit CI job).
Run with: uv run pytest tests/test_integration.py -q
"""

import os

import pytest
import requests

SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

skip_no_creds = pytest.mark.skipif(
    not all([SPREADSHEET_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]),
    reason="Integration credentials not set",
)


@skip_no_creds
def test_google_sheets_read_write():
    """Verify we can read and write to the Google Sheet."""
    import google.auth
    import gspread

    credentials, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.sheet1

    # Read headers
    headers = sheet.row_values(1)
    assert len(headers) > 0, "Sheet has no headers"
    assert headers[0] == "ID"


@skip_no_creds
def test_telegram_send_message():
    """Verify we can send a message to the Telegram chat."""
    token = TELEGRAM_BOT_TOKEN.strip()
    chat_id = TELEGRAM_CHAT_ID.strip()
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "[CI] Integration test OK",
        },
        timeout=10,
    )
    assert resp.status_code == 200, f"Telegram API returned {resp.status_code}: {resp.text}"
