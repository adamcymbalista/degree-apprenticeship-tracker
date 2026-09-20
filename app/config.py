"""Loads config.yaml. One function, no class - there's only ever one config."""
from __future__ import annotations

import os
from functools import lru_cache

import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict:
    path = path or os.environ.get("TRACKER_CONFIG", DEFAULT_CONFIG_PATH)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
