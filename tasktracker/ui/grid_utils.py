"""Shared helpers for turning Task lists into AgGrid tables."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from st_aggrid import JsCode

from ..consts import FREQUENCY_EDITOR_JS, DATE_FORMAT
from ..task import Task

DATE_COLUMNS = ("due_date", "done_date")

_DATE_TYPE_DEFINITIONS_JS = r"""
{
  dateString: {
    baseDataType: "dateString",
    extendsDataType: "dateString",
    valueParser: (params) =>
      params.newValue != null && params.newValue.match(/^\d{2}\/\d{2}\/\d{4}$/)
        ? params.newValue
        : null,
    valueFormatter: (params) => (params.value == null ? "" : params.value),
    dataTypeMatcher: (value) =>
      typeof value === "string" && !!value.match(/^\d{2}\/\d{2}\/\d{4}$/),
    dateParser: (value) => {
      if (value == null || value === "") { return undefined; }
      const parts = value.split("/");
      return parts.length === 3
        ? new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]))
        : undefined;
    },
    dateFormatter: (value) => {
      if (value == null) { return undefined; }
      const day = String(value.getDate()).padStart(2, "0");
      const month = String(value.getMonth() + 1).padStart(2, "0");
      return `${day}/${month}/${value.getFullYear()}`;
    },
  },
}
"""


def tasks_to_dataframe(tasks: list[Task]) -> pd.DataFrame:
    """Convert tasks into a display-ready dataframe with ISO date strings."""
    if not tasks:
        return pd.DataFrame()
    df = pd.DataFrame.from_records([task.to_dict() for task in tasks])
    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", dayfirst=False).dt.strftime(DATE_FORMAT)
    return df


def due_date_cell_style(today_str: str) -> JsCode:
    """Highlight due dates that aren't today in red/bold. `today_str` must match DATE_FORMAT."""
    return JsCode(f"""function(params) {{
    if (!params.value) {{ return {{ color: 'primary' }}; }}
    const isToday = params.value === '{today_str}';
    return isToday ? {{ color: 'primary' }} : {{ color: '#d32f2f', fontWeight: 'bold' }};
}}""")


@st.cache_resource(show_spinner=False)
def frequency_cell_editor() -> JsCode:
    return JsCode(FREQUENCY_EDITOR_JS.read_text(encoding="utf-8"))

@st.cache_resource(show_spinner=False)
def date_type_definitions() -> JsCode:
    """dd/mm/yyyy dateString override, shared by the Today and General grids."""
    return JsCode(_DATE_TYPE_DEFINITIONS_JS)

def find_task_by_id(tasks: list[Task], task_id: int) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise KeyError(f"No task with id={task_id}")
