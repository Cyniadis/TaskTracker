"""JSON-backed persistence for tasks and app settings.

Kept deliberately dumb: read the whole file, write the whole file. The
task list is small enough that this is simpler and safer than trying to
patch records in place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from common.consts import CACHE_FILE, DATE_FORMAT, DEFAULT_DAILY_LIMIT_MINUTES, TASKS_FILE, today
from common.common_utils import normalize_date
from common.common_json_utils import save_cache, load_cache, read_json, write_json, get_cached_value, set_cached_values, set_cached_value
from .task import Frequency, Task


# -- tasks.json --------------------------------------------------------------

def json_to_task_list(json_data: list[dict]) -> list[Task]:
    """Convert a list of raw JSON dicts into `Task` objects."""
    return [Task.from_dict(item) for item in json_data]


def task_list_to_json(tasks: list[Task]) -> list[dict]:
    """Convert `Task` objects back into JSON-serializable dicts."""
    return [task.to_dict() for task in tasks]


def load_tasks(path: Path = TASKS_FILE) -> list[Task]:
    """Load all tasks from `path` (empty list if the file is missing)."""
    raw_tasks = read_json(path) or []
    return json_to_task_list(raw_tasks)


def save_tasks(tasks: list[Task], path: Path = TASKS_FILE) -> None:
    """Write all tasks to `path`, overwriting its previous contents."""
    write_json(path, task_list_to_json(tasks))



# -- app-specific cached values --------------------------------------------
#
# Thin, typed wrappers around the generic store above, kept so call sites
# don't need to know the raw key names / defaults.

def load_cached_daily_limit() -> int:
    """Load the saved daily time budget (minutes), or the app default."""
    return get_cached_value("daily_limit", DEFAULT_DAILY_LIMIT_MINUTES)


def cache_daily_limit(daily_limit: int) -> None:
    set_cached_value("daily_limit", daily_limit)


def load_cached_task_ids() -> tuple[str | None, list[int] | None]:
    """Return (cache_date, cached_task_ids) — the date+ids of the last computed 'today' list."""
    cache_date = get_cached_value("cache_date")
    cached_tasks_ids = get_cached_value("cached_tasks_ids")
    return cache_date, cached_tasks_ids


def cache_tasks(tasks: list[Task]) -> None:
    """Remember which tasks were selected for "today", so a page reload today doesn't recompute them."""
    set_cached_values(
        cache_date=today().strftime(DATE_FORMAT),
        cached_tasks_ids=[task.id for task in tasks],
    )


def load_show_completed() -> bool:
    return get_cached_value("show_completed", True)


def cache_show_completed(show_completed: bool) -> None:
    set_cached_value("show_completed", show_completed)


def load_show_rescheduled() -> bool:
    return get_cached_value("show_rescheduled", True)


def cache_show_rescheduled(show_rescheduled: bool) -> None:
    set_cached_value("show_rescheduled", show_rescheduled)

def load_timer_state() -> tuple[datetime, float, bool] :
    cached_time = get_cached_value("timer_start_time", None)
    start_time = datetime.strptime(cached_time, "%Y-%m-%d %H:%M:%S") if cached_time is not None else None
    timer_elapsed_accum = get_cached_value("timer_elapsed_accum")
    timer_running = get_cached_value("timer_running")
    return start_time, timer_elapsed_accum, timer_running

def cache_timer_state(**kwargs) -> None:
    if "timer_start_time" in kwargs:
        timer_start_time = None if kwargs["timer_start_time"] is None else kwargs["timer_start_time"].strftime("%Y-%m-%d %H:%M:%S")
        set_cached_value("timer_start_time", timer_start_time)
    if "timer_elapsed_accum" in kwargs:
        set_cached_value("timer_elapsed_accum", kwargs["timer_elapsed_accum"])
    if "timer_running" in kwargs:
        set_cached_value("timer_running", kwargs["timer_running"])
        
# -- import validation ------------------------------------------------------

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

        if "frequency" in item and item["frequency"] is not None:
            freq_text = str(item["frequency"])
            parsed_freq = Frequency.parse(freq_text)
            if str(parsed_freq) != freq_text.lower():
                raise ValueError(
                    f"{label} ('{item['name']}'): invalid 'frequency' value '{item['frequency']}' "
                    "(expected format like '2xsemaine')."
                )
            if parsed_freq.count < 1:
                raise ValueError(
                    f"{label} ('{item['name']}'): invalid 'frequency' value '{item['frequency']}' "
                    "— the count must be at least 1."
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
