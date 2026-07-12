"""The 'General' tab: manage the full task library."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder

from .. import state
from .add_task_dialog import add_task_dialog
from .grid_utils import find_task_by_id, frequency_cell_editor, tasks_to_dataframe


def _on_grid_event(grid_response) -> None:
    event = grid_response.event_data
    field_name = event["column"]["colId"]
    task = find_task_by_id(st.session_state.tasks, event["data"]["id"])
    task.set_field(field_name, event.get("newValue"))
    state.persist_tasks()


def _build_grid_options(df: pd.DataFrame) -> dict:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True, editable=True)
    gb.configure_column("id", hide=True)
    gb.configure_column("name", headerName="Task", autoHeight=True, wrapText=True)
    gb.configure_column("frequency", headerName="Frequency", cellEditor=frequency_cell_editor(), cellEditorPopup=True)
    gb.configure_column("priority", headerName="Priority", cellDataType="number")
    gb.configure_column("initial_priority", headerName="Initial Priority", cellDataType="number")
    gb.configure_column("duration", headerName="Duration (min)", cellDataType="number")
    gb.configure_column("selected", headerName="Selected", hide=True)
    gb.configure_column("due_date", headerName="Due date", cellDataType="dateString")
    gb.configure_column("next_due_date", headerName="Next Due Date", cellDataType="dateString", editable=False)
    gb.configure_column("done_date", headerName="Done date", cellDataType="dateString", editable=False)
    gb.configure_column("last_done_date", headerName="Last Done Date", cellDataType="dateString", editable=False)
    gb.configure_grid_options(domLayout="autoHeight")
    return gb.build()


def render() -> None:
    st.markdown("### Edit tasks")

    if st.button("➕ Add task"):
        add_task_dialog()

    df = tasks_to_dataframe(st.session_state.tasks)
    if df.empty:
        st.info("No tasks yet — use \u201cAdd task\u201d to create your first one.")
        return

    AgGrid(
        df,
        gridOptions=_build_grid_options(df),
        height=630,
        key=st.session_state.manage_grid_key,
        update_on=["cellValueChanged"],
        callback=_on_grid_event,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )
