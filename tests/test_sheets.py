"""Tests for Google Sheets sanitization, helpers, and deduplication."""

from unittest.mock import MagicMock, patch

import pytest

from flat_research.models import Listing
from flat_research.sheets import HEADERS, _sanitize_cell, add_listings


class TestSanitizeCell:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("Normal text", "Normal text"),
            ("=SUM(A1:A10)", "'=SUM(A1:A10)"),
            ("+cmd('calc')", "'+cmd('calc')"),
            ("-1+1", "'-1+1"),
            ("@import('evil')", "'@import('evil')"),
            ("", ""),
            ("$2,500", "$2,500"),  # $ is safe
            (123, 123),  # non-string passthrough
        ],
    )
    def test_sanitize(self, value, expected):
        assert _sanitize_cell(value) == expected


def _make_listing(**kwargs):
    defaults = {
        "source": "kijiji",
        "title": "Test listing",
        "price": 2500.0,
        "url": "https://example.com/1",
        "address": "123 rue Test",
        "neighbourhood": "Villeray",
        "bedrooms": 3,
        "furnished": True,
        "parking": False,
        "description": "Description",
        "listing_id": "kijiji_001",
    }
    defaults.update(kwargs)
    return Listing(**defaults)


class TestDeduplication:
    @patch("flat_research.sheets._get_or_create_spreadsheet")
    @patch("flat_research.sheets._get_client")
    def test_skips_existing_ids(self, mock_client, mock_spreadsheet):
        mock_sheet = MagicMock()
        mock_sheet.row_count = 2
        mock_sheet.col_values.return_value = ["ID", "kijiji_001"]  # header + existing
        mock_spreadsheet.return_value.sheet1 = mock_sheet
        mock_spreadsheet.return_value.url = "https://sheet"

        listings = [
            _make_listing(listing_id="kijiji_001"),  # exists
            _make_listing(listing_id="kijiji_002", title="New one"),  # new
        ]

        new, url = add_listings(listings, {"google_sheets": {"spreadsheet_name": "test", "spreadsheet_id": "abc"}})

        assert len(new) == 1
        assert new[0].listing_id == "kijiji_002"
        mock_sheet.append_rows.assert_called_once()
        rows = mock_sheet.append_rows.call_args[0][0]
        assert len(rows) == 1
        assert rows[0][0] == "kijiji_002"

    @patch("flat_research.sheets._get_or_create_spreadsheet")
    @patch("flat_research.sheets._get_client")
    def test_no_new_listings_skips_append(self, mock_client, mock_spreadsheet):
        mock_sheet = MagicMock()
        mock_sheet.row_count = 2
        mock_sheet.col_values.return_value = ["ID", "kijiji_001"]
        mock_spreadsheet.return_value.sheet1 = mock_sheet
        mock_spreadsheet.return_value.url = "https://sheet"

        listings = [_make_listing(listing_id="kijiji_001")]

        new, url = add_listings(listings, {"google_sheets": {"spreadsheet_name": "test", "spreadsheet_id": "abc"}})

        assert len(new) == 0
        mock_sheet.append_rows.assert_not_called()

    @patch("flat_research.sheets._get_or_create_spreadsheet")
    @patch("flat_research.sheets._get_client")
    def test_row_format_matches_headers(self, mock_client, mock_spreadsheet):
        mock_sheet = MagicMock()
        mock_sheet.row_count = 1
        mock_sheet.col_values.return_value = ["ID"]
        mock_spreadsheet.return_value.sheet1 = mock_sheet
        mock_spreadsheet.return_value.url = "https://sheet"

        listings = [_make_listing()]

        add_listings(listings, {"google_sheets": {"spreadsheet_name": "test", "spreadsheet_id": "abc"}})

        rows = mock_sheet.append_rows.call_args[0][0]
        assert len(rows[0]) == len(HEADERS)
