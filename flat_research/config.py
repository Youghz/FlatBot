"""Configuration loading with environment variable resolution."""

import os
import re

import yaml
from dotenv import load_dotenv


def _resolve_env_vars(obj):
    """Recursively replace ${VAR} placeholders with env var values."""
    if isinstance(obj, str):
        return re.sub(
            r"\$\{(\w+)\}",
            lambda m: os.environ.get(m.group(1), m.group(0)),
            obj,
        )
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_vars(i) for i in obj]
    return obj


def load_config(path: str = "config.yaml") -> dict:
    load_dotenv()
    with open(path) as f:
        config = yaml.safe_load(f)
    return _resolve_env_vars(config)
