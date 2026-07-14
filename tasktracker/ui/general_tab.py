"""The 'General' tab: manage the full task library."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder

from .add_task_dialog import add_task_dialog
from .grid_utils import find_task_by_id, frequency_cell_editor, tasks_to_dataframe

from ..json_utils import load_tasks_backup


from . import ui_state

def _on_remove_selection_click():
    selected_rows = st.session_state.selected_rows
    selected_ids: set[int] = set()
    if len(selected_rows) > 0:
        selected_ids = {int(row["id"]) for row in selected_rows.to_dict(orient="records")}
        st.session_state.tasks = [t for t in st.session_state.tasks if t.id not in selected_ids ]

def _on_grid_event(grid_response) -> None:
    event = grid_response.event_data
    event_type = event.get("type")
    if event_type == "selectionChanged":
        st.session_state.selected_rows = grid_response.selected_rows
    if event_type == "cellValueChanged":
        field_name = event["column"]["colId"]
        task = find_task_by_id(st.session_state.tasks, event["data"]["id"])
        task.set_field(field_name, event.get("newValue"))
        ui_state.persist_tasks()


def _build_grid_options(df: pd.DataFrame) -> dict:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True, editable=True)
    gb.configure_column("id", hide=True)
    gb.configure_column("name", headerName="Task", autoHeight=True, wrapText=True, checkboxSelection=True, width=400)
    gb.configure_column("frequency", headerName="Frequency", cellEditor=frequency_cell_editor(), cellEditorPopup=True)
    gb.configure_column("priority", headerName="Priority", cellDataType="number")
    gb.configure_column("initial_priority", headerName="Initial Priority", cellDataType="number")
    gb.configure_column("duration", headerName="Duration (min)", cellDataType="number")
    gb.configure_column("selected", headerName="Selected", hide=True)
    gb.configure_column("due_date", headerName="Due date", cellDataType="dateString")
    gb.configure_column("done_date", headerName="Done date", cellDataType="dateString", editable=False)
    gb.configure_selection("multiple", use_checkbox=True,
                            rowMultiSelectWithClick=False, 
                            suppressRowClickSelection=False, 
                            suppressRowDeselection=False)
    gb.configure_grid_options(domLayout="autoHeight")
    return gb.build()


def render() -> None:
    st.markdown("### Edit tasks", anchors=False)

    with st.container(horizontal=True, width="content"):
        if st.button("➕ Add task"):
            add_task_dialog()

        if st.button("🗑️ Remove selection"):
            _on_remove_selection_click()

        # if st.button("🔄️ Load backup"):
        #     st.session_state.tasks = load_tasks_backup()
        #     ui_state.reload_manage_grid()
        if st.button("⭯ Discard changes"): 
            ui_state.restore_tasks(st.session_state.today_tasks)
            ui_state.reload_today_grid()


    df = tasks_to_dataframe(st.session_state.tasks)
    if df.empty:
        st.info("No tasks yet — use \u201cAdd task\u201d to create your first one.")
        return

    grid_response = AgGrid(
        df,
        gridOptions=_build_grid_options(df),
        height=630,
        key=st.session_state.manage_grid_key,
        update_on=["cellValueChanged", "selectionChanged"],
        callback=_on_grid_event,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )

