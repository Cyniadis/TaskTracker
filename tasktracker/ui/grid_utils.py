"""Shared helpers for turning Task lists into st.data_editor tables."""
from __future__ import annotations

import pandas as pd

from ..task import Task, Period
import streamlit as st

PERIOD_OPTIONS = [p.value for p in Period]


def tasks_to_today_dataframe(tasks: list[Task]) -> pd.DataFrame:
    """Convert tasks into a display-ready dataframe.

    Frequency is split into `frequency_count` / `frequency_period` so each
    half gets its own widget (number input / dropdown) in the editor —
    this replaces the old combined JS cell editor. Dates are kept as real
    `date` objects so `st.column_config.DateColumn` can format/parse them.
    """
    if not tasks:
        return None


    records = []
    for task in tasks:
        freq = task.frequency_obj
        records.append({
            "id": task.id,
            "name": task.name,
            "frequency": task.frequency,
            "priority": task.priority,
            "initial_priority": task.initial_priority,
            "duration": task.duration,
            "due_date": task.due_date,
            "done_date": task.done_date,
            "reschedule": ":material/edit: Reschedule"
        })
    return pd.DataFrame.from_records(records)



def tasks_to_general_dataframe(tasks: list[Task]) -> pd.DataFrame:
    """Convert tasks into a display-ready dataframe.

    Frequency is split into `frequency_count` / `frequency_period` so each
    half gets its own widget (number input / dropdown) in the editor —
    this replaces the old combined JS cell editor. Dates are kept as real
    `date` objects so `st.column_config.DateColumn` can format/parse them.
    """
    if not tasks:
        return None


    records = []
    for task in tasks:
        freq = task.frequency_obj
        records.append({
            "id": task.id,
            "name": task.name,
            "frequency_count": freq.count,
            "frequency_period": freq.period.value,
            "priority": task.priority,
            "initial_priority": task.initial_priority,
            "duration": task.duration,
            "due_date": task.due_date,
            "done_date": task.done_date,
            "schedule_today": ":material/playlist_add: Add to today",

        })
    return pd.DataFrame.from_records(records)


def find_task_by_id(tasks: list[Task], task_id: int) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise KeyError(f"No task with id={task_id}")


_THEME_COLORS = {
    "light": {
        "primaryColor": "#ff4b4b",
        "backgroundColor": "#ffffff",
        "secondaryBackgroundColor": "#f0f2f6",
        "textColor": "#31333f",
        "redColor": "#ff4b4b",
        "orangeColor": "#ffa421",
        "yellowColor": "#faca2b",
        "blueColor": "#1c83e1",
        "greenColor": "#21c354",
        "violetColor": "#803df5",
        "grayColor": "#a3a8b8",
        # Text colors (light theme)
        "redTextColor": "#bd4043",
        "orangeTextColor": "#e2660c",
        "yellowTextColor": "#926c05",
        "blueTextColor": "#0054a3",
        "greenTextColor": "#158237",
        "violetTextColor": "#583f84",
        "grayTextColor": "#31333f",

        "hiddenTextColor": "#31333f36",
        "doneTextColor": "#15823755",

    },
    "dark": {
        "primaryColor": "#ff4b4b",
        "backgroundColor": "#0e1117",
        "secondaryBackgroundColor": "#262730",
        "textColor": "#fafafa",
        "redColor": "#ff2b2b",
        "orangeColor": "#ff8700",
        "yellowColor": "#ffe312",
        "blueColor": "#0068c9",
        "greenColor": "#09ab3b",
        "violetColor": "#803df5",
        "grayColor": "#555867",
        # Text colors (dark theme)
        "redTextColor": "#ff6c6c",
        "orangeTextColor": "#ffbd45",
        "yellowTextColor": "#ffffc2",
        "blueTextColor": "#3d9df3",
        "greenTextColor": "#5ce488",
        "violetTextColor": "#b27eff",
        "grayTextColor": "#d5dae5",

        "hiddenTextColor": "#fafafa36",
        "doneTextColor": "#09ab3c55",
    },
}

def get_theme_color(name: str) -> str:
    # Detect current theme mode
    theme_type = st.context.theme.type  # "light" or "dark"
    colors = _THEME_COLORS.get(theme_type, _THEME_COLORS["dark"])
    return colors[name]




