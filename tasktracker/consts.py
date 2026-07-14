"""Central place for filesystem paths and app-wide constants."""
from __future__ import annotations

from pathlib import Path
import os 
from datetime import datetime

# PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.getcwd())
#PROJECT_ROOT = PACKAGE_DIR.parent

TASKS_FILE = PROJECT_ROOT / "tasklist.json"
CACHE_FILE = PROJECT_ROOT / "cache.json"
FREQUENCY_EDITOR_JS = PROJECT_ROOT / "tasktracker" / "ui" / "assets" / "FrequencyCellEditor.js"


DEFAULT_DAILY_LIMIT_MINUTES = 60
PRIORITY_INCREMENT = 0.5

DATE_FORMAT = "%Y-%d-%m"
TODAY = datetime.now().date()

