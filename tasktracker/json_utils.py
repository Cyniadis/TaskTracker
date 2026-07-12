"""JSON-backed persistence for tasks and app settings.

Kept deliberately dumb: read the whole file, write the whole file. The
task list is small enough that this is simpler and safer than trying to
patch records in place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .consts import DEFAULT_DAILY_LIMIT_MINUTES, SETTINGS_FILE, TASKS_FILE
from .task import Task


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
    _write_json(path, {"daily_limit": daily_limit})
