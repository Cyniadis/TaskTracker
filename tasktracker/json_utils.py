"""JSON-backed persistence for tasks and app settings.

Kept deliberately dumb: read the whole file, write the whole file. The
task list is small enough that this is simpler and safer than trying to
patch records in place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .consts import DEFAULT_DAILY_LIMIT_MINUTES, SETTINGS_FILE, TASKS_FILE, PROJECT_ROOT,DATE_FORMAT
from .task import Task
from datetime import datetime
import os

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


def load_tasks(path: Path = TASKS_FILE) -> list[Task]:
    raw_tasks = _read_json(path) or []
    return [Task.from_dict(item) for item in raw_tasks]


def save_tasks(tasks: list[Task], path: Path = TASKS_FILE) -> None:
    _write_json(path, [task.to_dict() for task in tasks])


def load_daily_limit(path: Path = SETTINGS_FILE) -> int:
    settings = _read_json(path) or {}
    return settings.get("daily_limit", DEFAULT_DAILY_LIMIT_MINUTES)


def save_daily_limit(daily_limit: int, path: Path = SETTINGS_FILE) -> None:
    settings = _read_json(path) or {}
    settings["daily_limit"] = daily_limit
    _write_json(path, settings)

def save_backup_path(path: Path = SETTINGS_FILE) -> None:
    settings = _read_json(path) or {}
    suffix = datetime.now().strftime(DATE_FORMAT)
    settings["backup_path"] = str(PROJECT_ROOT / "backups" / f"tasklist_backup_{suffix}.json")
    print(settings)
    _write_json(path, settings)

def load_backup_path(path: Path = SETTINGS_FILE) -> Path:
    settings = _read_json(path) or {}
    return Path(settings.get("backup_path", ""))


def create_tasks_backup(tasks: list[Task], path: Path = SETTINGS_FILE) -> None:
    backup_path = load_backup_path(path)
    if not backup_path: 
        save_backup_path(path)
        save_tasks(tasks, backup_path)
    else:
        date_str = Path(backup_path).stem.removeprefix("tasklist_backup_")
        date_backup = datetime.strptime(date_str, DATE_FORMAT).date()
        if not date_backup == datetime.now().date(): 
            save_backup_path(path)
            save_tasks(tasks, backup_path)

    if not os.path.isfile(backup_path):
        save_tasks(tasks, backup_path)

def load_tasks_backup(path: Path= SETTINGS_FILE) -> list[Task]:
    backup_path = load_backup_path(path)
    return load_tasks(backup_path)
