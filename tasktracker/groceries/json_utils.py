"""JSON-backed persistence for the grocery list.

Mirrors tasktracker/json_utils.py's tasklist.json handling exactly, just
pointed at groceries.json and GroceryItem instead of Task — kept in its own
module so the groceries feature never needs to touch the main json_utils.py
file. Reuses the generic _read_json/_write_json helpers from there rather
than duplicating them.
"""
from __future__ import annotations

from pathlib import Path

from ..consts import GROCERIES_FILE
from ..json_utils import _read_json, _write_json
from .grocery import GroceryItem


def json_to_grocery_list(json_data: list[dict]) -> list[GroceryItem]:
    """Convert a list of raw JSON dicts into `GroceryItem` objects."""
    return [GroceryItem.from_dict(item) for item in json_data]


def grocery_list_to_json(items: list[GroceryItem]) -> list[dict]:
    """Convert `GroceryItem` objects back into JSON-serializable dicts."""
    return [item.to_dict() for item in items]


def load_groceries(path: Path = GROCERIES_FILE) -> list[GroceryItem]:
    """Load all grocery items from `path` (empty list if the file is missing)."""
    raw_items = _read_json(path) or []
    return json_to_grocery_list(raw_items)


def save_groceries(items: list[GroceryItem], path: Path = GROCERIES_FILE) -> None:
    """Write all grocery items to `path`, overwriting its previous contents."""
    _write_json(path, grocery_list_to_json(items))


def next_grocery_id(items: list[GroceryItem]) -> int:
    """Return the next unused grocery item id (max existing id + 1, or 0 if empty)."""
    return max((item.id for item in items), default=-1) + 1
