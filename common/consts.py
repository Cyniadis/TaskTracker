"""Central place for filesystem paths and app-wide constants."""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

# All app data (tasks and cache) lives relative to the current working
# directory the Streamlit app was launched from.
PROJECT_ROOT = Path(os.getcwd())
DATA_FOLDER = PROJECT_ROOT / "data"

TASKS_FILE = DATA_FOLDER / "tasklist.json"
CACHE_FILE = DATA_FOLDER / "cache.json"
GROCERIES_FILE = DATA_FOLDER / "groceries.json"
ONETIME_TASKS_FILE = DATA_FOLDER / "onetime_tasks.json"

# Change-tracking baseline for the "Changes" dialog  — 
# a snapshot of tasklist.json's content as of the last full reload
# (process start, reset_app(), import). Its own file rather than a key in
# cache.json: cache.json holds small scalar settings, this holds a whole
# task list. See tasktracker/change_tracking.py.
TASK_BASELINE_FILE = DATA_FOLDER / "task_baseline.json"

DEFAULT_DAILY_LIMIT_MINUTES = 60
PRIORITY_INCREMENT = 0.5

DATE_FORMAT = "%d/%m/%Y"


def today() -> date:
    """The current date, evaluated fresh on every call.

    Deliberately a function rather than a module-level constant: the
    Streamlit server process can stay alive for days, and a constant
    computed once at import time would silently go stale after midnight.
    """
    return datetime.now().date()
