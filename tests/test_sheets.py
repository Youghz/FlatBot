"""Tests for Google Sheets sanitization and helpers."""

import pytest

from sheets import _sanitize_cell


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
