"""Tests for config loading and env var resolution."""

import os
import pytest
from main import _resolve_env_vars


class TestResolveEnvVars:
    def test_resolves_string(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "secret123")
        assert _resolve_env_vars("${MY_TOKEN}") == "secret123"

    def test_leaves_unknown_vars(self):
        result = _resolve_env_vars("${NONEXISTENT_VAR_12345}")
        assert result == "${NONEXISTENT_VAR_12345}"

    def test_resolves_in_dict(self, monkeypatch):
        monkeypatch.setenv("BOT_TOKEN", "abc")
        data = {"telegram": {"token": "${BOT_TOKEN}", "name": "mybot"}}
        result = _resolve_env_vars(data)
        assert result["telegram"]["token"] == "abc"
        assert result["telegram"]["name"] == "mybot"

    def test_resolves_in_list(self, monkeypatch):
        monkeypatch.setenv("ITEM", "hello")
        assert _resolve_env_vars(["${ITEM}", "world"]) == ["hello", "world"]

    def test_passthrough_non_string(self):
        assert _resolve_env_vars(42) == 42
        assert _resolve_env_vars(None) is None
