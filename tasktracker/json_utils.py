"""JSON-backed persistence for tasks and app settings.

Kept deliberately dumb: read the whole file, write the whole file. The
task list is small enough that this is simpler and safer than trying to
patch records in place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .consts import DEFAULT_DAILY_LIMIT_MINUTES, CACHE_FILE, TASKS_FILE, PROJECT_ROOT,DATE_FORMAT, TODAY
from .task import Task, normalize_date, Frequency

def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc}") from exc


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def json_to_task_list(json_data: dict) -> list[Task]:
    return [Task.from_dict(item) for item in json_data]

def task_list_to_json(tasks: list[Task]) -> dict: 
    return [task.to_dict() for task in tasks]

def load_tasks(path: Path = TASKS_FILE) -> list[Task]:
    raw_tasks = _read_json(path) or []
    return json_to_task_list(raw_tasks)


def save_tasks(tasks: list[Task], path: Path = TASKS_FILE) -> None:
    _write_json(path, task_list_to_json(tasks))


def load_daily_limit() -> int:
    cached_params = _read_json(CACHE_FILE)
    return cached_params.get("daily_limit", DEFAULT_DAILY_LIMIT_MINUTES)

def save_daily_limit(daily_limit: int) -> None:
    cached_params = _read_json(CACHE_FILE)
    cached_params['daily_limit'] = daily_limit
    _write_json(CACHE_FILE, cached_params)


def validate_and_parse_tasks(raw_data: Any) -> list[Task]:
    """Parse+validate raw JSON data (already `json.loads`-ed) into a list of Task objects.

    Raises `ValueError` with a human-readable message on the first problem found.
    Used for imported task files, where we can't trust the shape of the data.
    """
    if not isinstance(raw_data, list):
        raise ValueError("The file must contain a JSON array of tasks.")

    if not raw_data:
        raise ValueError("The task list is empty.")

    tasks: list[Task] = []
    seen_ids: set[int] = set()

    for idx, item in enumerate(raw_data):
        label = f"Task #{idx}"

        if not isinstance(item, dict):
            raise ValueError(f"{label}: expected a JSON object, got {type(item).__name__}.")

        if "id" not in item:
            raise ValueError(f"{label}: missing required field 'id'.")
        if not isinstance(item["id"], int):
            raise ValueError(f"{label}: field 'id' must be an integer.")
        if item["id"] in seen_ids:
            raise ValueError(f"{label}: duplicate id {item['id']}.")

        if "name" not in item or not str(item.get("name", "")).strip():
            raise ValueError(f"{label} (id={item['id']}): missing or empty required field 'name'.")

        if "frequency" in item and item["frequency"] is not None:
            freq_text = str(item["frequency"])
            parsed_freq = Frequency.parse(freq_text)
            if str(parsed_freq) != freq_text.lower():
                raise ValueError(
                    f"{label} ('{item['name']}'): invalid 'frequency' value '{item['frequency']}' "
                    "(expected format like '2xsemaine')."
                )

        for field_name in ("priority", "initial_priority"):
            if field_name in item and item[field_name] is not None:
                if not isinstance(item[field_name], (int, float)) or isinstance(item[field_name], bool):
                    raise ValueError(f"{label} ('{item['name']}'): field '{field_name}' must be a number.")

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


def import_tasks_from_json_bytes(raw_bytes: bytes) -> list[Task]:
    """Decode + validate an uploaded tasks JSON file. Raises ValueError on any problem."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"File is not valid UTF-8 text: {exc}") from exc

    try:
        raw_data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"File is not valid JSON: {exc}") from exc

    return validate_and_parse_tasks(raw_data)
