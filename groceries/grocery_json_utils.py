"""JSON-backed persistence for the grocery list.

Mirrors tasktracker/json_utils.py's tasklist.json handling exactly, just
pointed at groceries.json and GroceryItem instead of Task — kept in its own
module so the groceries feature never needs to touch the main json_utils.py
file. Reuses the generic read_json/write_json helpers from there rather
than duplicating them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common.consts import GROCERIES_FILE
from common.common_json_utils import read_json, write_json
from common.common_utils import normalize_date
from .grocery import GroceryItem, GroceryState


def json_to_grocery_list(json_data: list[dict]) -> list[GroceryItem]:
    """Convert a list of raw JSON dicts into `GroceryItem` objects."""
    return [GroceryItem.from_dict(item) for item in json_data]


def grocery_list_to_json(items: list[GroceryItem]) -> list[dict]:
    """Convert `GroceryItem` objects back into JSON-serializable dicts."""
    return [item.to_dict() for item in items]


def load_groceries(path: Path = GROCERIES_FILE) -> list[GroceryItem]:
    """Load all grocery items from `path` (empty list if the file is missing)."""
    raw_items = read_json(path) or []
    return json_to_grocery_list(raw_items)


def save_groceries(items: list[GroceryItem], path: Path = GROCERIES_FILE) -> None:
    """Write all grocery items to `path`, overwriting its previous contents."""
    write_json(path, grocery_list_to_json(items))


def next_grocery_id(items: list[GroceryItem]) -> int:
    """Return the next unused grocery item id (max existing id + 1, or 0 if empty)."""
    return max((item.id for item in items), default=-1) + 1


# -- import validation --------------------------------------------------------
#
# Mirrors tasktracker/json_utils.py's validate_and_parse_tasks /
# import_tasks_from_json_bytes, adapted for GroceryItem's smaller field set.

def validate_and_parse_groceries(raw_data: Any) -> list[GroceryItem]:
    """Parse+validate raw JSON data (already `json.loads`-ed) into a list of
    GroceryItem objects.

    Raises `ValueError` with a human-readable message on the first problem
    found. Used for imported grocery files, where we can't trust the shape
    of the data.
    """
    if not isinstance(raw_data, list):
        raise ValueError("The file must contain a JSON array of grocery items.")

    if not raw_data:
        raise ValueError("The grocery list is empty.")

    valid_states = {state.value for state in GroceryState}
    items: list[GroceryItem] = []
    seen_ids: set[str] = set()

    for idx, item in enumerate(raw_data):
        label = f"Item #{idx}"

        if not isinstance(item, dict):
            raise ValueError(f"{label}: expected a JSON object, got {type(item).__name__}.")

        if "id" not in item:
            raise ValueError(f"{label}: missing required field 'id'.")
        if not isinstance(item["id"], str):
            raise ValueError(f"{label}: field 'id' must be a string.")
        if item["id"] in seen_ids:
            raise ValueError(f"{label}: duplicate id {item['id']}.")

        if "name" not in item or not str(item.get("name", "")).strip():
            raise ValueError(f"{label} (id={item['id']}): missing or empty required field 'name'.")

        if "state" in item and item["state"] is not None and item["state"] not in valid_states:
            raise ValueError(
                f"{label} ('{item['name']}'): invalid 'state' value '{item['state']}' "
                f"(expected one of {sorted(valid_states)})."
            )

        if "last_bought_date" in item and item["last_bought_date"] not in (None, ""):
            try:
                normalize_date(item["last_bought_date"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{label} ('{item['name']}'): invalid 'last_bought_date' value "
                    f"'{item['last_bought_date']}': {exc}"
                ) from exc

        try:
            grocery_item = GroceryItem.from_dict(item)
        except TypeError as exc:
            raise ValueError(f"{label} ('{item.get('name', '?')}'): {exc}") from exc

        seen_ids.add(grocery_item.id)
        items.append(grocery_item)

    return items


def import_groceries_from_json_bytes(raw_bytes: bytes) -> list[GroceryItem]:
    """Decode + validate an uploaded groceries JSON file. Raises ValueError on any problem."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc

    try:
        raw_data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"File is not valid JSON: {exc}") from exc

    return validate_and_parse_groceries(raw_data)
