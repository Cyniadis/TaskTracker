"""Central place for filesystem paths and app-wide constants."""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

# All app data (tasks and cache) lives relative to the current working
# directory the Streamlit app was launched from.
PROJECT_ROOT = Path(os.getcwd())

TASKS_FILE = PROJECT_ROOT / "tasklist.json"
CACHE_FILE = PROJECT_ROOT / "cache.json"

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
