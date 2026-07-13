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
from .task import Task, normalize_date

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


def create_tasks_backup(tasks: list[Task]) -> None:
    cached_params = _read_json(CACHE_FILE)
    backup_date = cached_params['backup_date'] 
    if normalize_date(backup_date) == normalize_date(TODAY):
        return
    else:
        print("Create task Backup")
        cached_params['backup_date'] = TODAY.strftime(DATE_FORMAT)
        cached_params["backup_tasks"]= task_list_to_json(tasks)
        _write_json(CACHE_FILE, cached_params)

    
def load_tasks_backup() -> None: 
    print("Load tasks backup")
    cached_params = _read_json(CACHE_FILE)
    cached_tasks = cached_params.get("backup_tasks", None)
    return json_to_task_list(cached_tasks)