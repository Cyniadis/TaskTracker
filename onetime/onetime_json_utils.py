"""JSON-backed persistence for one-time (no-frequency) tasks.

Mirrors tasktracker/tt_json_utils.py's tasklist.json handling, pointed at
onetime_tasks.json instead. Kept in its own module, like
groceries/grocery_json_utils.py, so this feature never needs to touch the
main tt_json_utils.py file.

Frequency validation is deliberately dropped from the import validator
below (unlike tt_json_utils.validate_and_parse_tasks) — one-time tasks
never read their `frequency` field for anything, so there's nothing
meaningful to validate there.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common.consts import ONETIME_TASKS_FILE
from common.common_json_utils import read_json, write_json
from common.common_utils import normalize_date
from tasktracker.task import Task


def json_to_task_list(json_data: list[dict]) -> list[Task]:
    """Convert a list of raw JSON dicts into `Task` objects."""
    return [Task.from_dict(item) for item in json_data]


def task_list_to_json(tasks: list[Task]) -> list[dict]:
    """Convert `Task` objects back into JSON-serializable dicts."""
    return [task.to_dict() for task in tasks]


def load_onetime_tasks(path: Path = ONETIME_TASKS_FILE) -> list[Task]:
    """Load all one-time tasks from `path` (empty list if the file is missing)."""
    raw_tasks = read_json(path) or []
    return json_to_task_list(raw_tasks)


def save_onetime_tasks(tasks: list[Task], path: Path = ONETIME_TASKS_FILE) -> None:
    """Write all one-time tasks to `path`, overwriting its previous contents."""
    write_json(path, task_list_to_json(tasks))


# -- import validation --------------------------------------------------------

def validate_and_parse_onetime_tasks(raw_data: Any) -> list[Task]:
    """Parse+validate raw JSON data into a list of Task objects for import.

    Same shape checks as tt_json_utils.validate_and_parse_tasks, minus the
    frequency check — see module docstring.
    """
    if not isinstance(raw_data, list):
        raise ValueError("The file must contain a JSON array of tasks.")

    if not raw_data:
        raise ValueError("The one-time task list is empty.")

    tasks: list[Task] = []
    seen_ids: set[str] = set()

    for idx, item in enumerate(raw_data):
        label = f"Task #{idx}"

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

        if "duration" in item and item["duration"] is not None:
            if not isinstance(item["duration"], int) or isinstance(item["duration"], bool) or item["duration"] < 0:
                raise ValueError(f"{label} ('{item['name']}'): field 'duration' must be a non-negative integer.")

        for field_name in ("due_date", "done_date"):
            if field_name in item and item[field_name] not in (None, ""):
                try:
                    normalize_date(item[field_name])
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"{label} ('{item['name']}'): invalid '{field_name}' value '{item[field_name]}': {exc}"
                    ) from exc

        try:
            task = Task.from_dict(item)
        except TypeError as exc:
            raise ValueError(f"{label} ('{item.get('name', '?')}'): {exc}") from exc

        seen_ids.add(task.id)
        tasks.append(task)

    return tasks


def import_onetime_tasks_from_json_bytes(raw_bytes: bytes) -> list[Task]:
    """Decode + validate an uploaded one-time-tasks JSON file. Raises ValueError on any problem."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc

    try:
        raw_data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"File is not valid JSON: {exc}") from exc

    return validate_and_parse_onetime_tasks(raw_data)
