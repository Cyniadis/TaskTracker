"""JSON-backed persistence for tasks and app settings.

Kept deliberately dumb: read the whole file, write the whole file. The
task list is small enough that this is simpler and safer than trying to
patch records in place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from .consts import CACHE_FILE

# -- low-level JSON read/write ---------------------------------------------

def read_json(path: Path) -> Any:
    """Read and parse a JSON file, or return None if it doesn't exist."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc}") from exc


def write_json(path: Path, payload: Any) -> None:
    """Serialize `payload` as pretty JSON and write it to `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# -- generic cache.json key/value store -----------------------------------
#
# cache.json is just a flat dict of arbitrary values (daily_limit, cache_date,
# cached_tasks_ids, ...). These helpers let any part of the app read/write a
# single cached value without knowing about the rest of the file, so adding
# a new cached value is just "call get_cached_value / set_cached_value with
# a new key" instead of hand-rolling another read_json/write_json pair.
#
# Example — adding a brand new cached value elsewhere in the app:
#
#     from .json_utils import get_cached_value, set_cached_value
#
#     def load_last_selected_tab() -> str:
#         return get_cached_value("last_tab", "today")
#
#     def save_last_selected_tab(tab: str) -> None:
#         set_cached_value("last_tab", tab)
#
# No new file, no new read/write plumbing needed.

def load_cache() -> dict:
    return read_json(CACHE_FILE) or {}


def save_cache(cache: dict) -> None:
    write_json(CACHE_FILE, cache)


def get_cached_value(key: str, default: Any = None) -> Any:
    """Read a single value from cache.json, or `default` if missing/absent."""
    return load_cache().get(key, default)


def set_cached_value(key: str, value: Any) -> None:
    """Write a single value into cache.json, preserving the other keys."""
    cache = load_cache()
    cache[key] = value
    save_cache(cache)


def set_cached_values(**values: Any) -> None:
    """Write several values into cache.json at once (one read + one write)."""
    cache = load_cache()
    cache.update(values)
    save_cache(cache)


def delete_cached_value(key: str) -> None:
    """Remove a key from cache.json, if present."""
    cache = load_cache()
    if key in cache:
        del cache[key]
        save_cache(cache)

