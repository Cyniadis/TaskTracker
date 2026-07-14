"""Shared helpers for turning Task lists into AgGrid tables."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from st_aggrid import JsCode

from ..consts import FREQUENCY_EDITOR_JS, DATE_FORMAT
from ..task import Task

DATE_COLUMNS = ("due_date", "done_date")


def tasks_to_dataframe(tasks: list[Task]) -> pd.DataFrame:
    """Convert tasks into a display-ready dataframe with ISO date strings."""
    if not tasks:
        return pd.DataFrame()
    df = pd.DataFrame.from_records([task.to_dict() for task in tasks])
    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", dayfirst=False).dt.strftime(DATE_FORMAT)
    return df


def due_date_cell_style(today_iso: str) -> JsCode:
    """Highlight due dates that aren't today in red/bold."""
    return JsCode(f"""function(params) {{
    if (!params.value) {{ return {{ color: 'primary' }}; }}
    const valueDate = new Date(params.value);
    const isToday = !isNaN(valueDate.getTime()) && valueDate.toISOString().slice(0, 10) === '{today_iso}';
    return isToday ? {{ color: 'primary' }} : {{ color: '#d32f2f', fontWeight: 'bold' }};
}}""")


@st.cache_resource(show_spinner=False)
def frequency_cell_editor() -> JsCode:
    return JsCode(FREQUENCY_EDITOR_JS.read_text(encoding="utf-8"))


def find_task_by_id(tasks: list[Task], task_id: int) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise KeyError(f"No task with id={task_id}")
