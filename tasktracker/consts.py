"""Central place for filesystem paths and app-wide constants."""
from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent

TASKS_FILE = PROJECT_ROOT / "tasklist.json"
SETTINGS_FILE = PROJECT_ROOT / "cache.json"
FREQUENCY_EDITOR_JS = PACKAGE_DIR / "ui" / "assets" / "FrequencyCellEditor.js"

DEFAULT_DAILY_LIMIT_MINUTES = 60
PRIORITY_INCREMENT = 0.5
