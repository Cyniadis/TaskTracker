"""The 'Today' tab: check off and reschedule today's tasks."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, JsCode

from . import ui_state
from ..task import normalize_date
from .grid_utils import due_date_cell_style, find_task_by_id, tasks_to_dataframe
from ..json_utils import save_daily_limit


_DOUBLE_CLICK_DUE_DATE_JS = r"""function (params) {
    if (params.column.colId == "due_date") {
        params.node.setDataValue('doubleClicked', params.data.id);
    }
}"""

def _render_today_header() -> None:
    st.markdown("### Tâches du " + ui_state.TODAY.strftime("%A %d %B %Y"), anchors=False)

    with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", height="stretch"):
        st.markdown("Daily duration limit (minutes) : ", anchors=False)
        st.number_input(
            label="Daily duration limit",
            label_visibility="collapsed",
            min_value=5,
            max_value=720,
            step=15,
            key="daily_limit",
            on_change=lambda: save_daily_limit(daily_limit=st.session_state.daily_limit),
            width=100,
        )
        st.button("Discard completed tasks", on_click=ui_state.discard_completed_tasks)
        st.button("Regenerate", on_click=ui_state.regenerate_today_tasks)
        st.button("Reload", on_click=ui_state.reset_app)

    st.write(
        f"**Active duration:** {sum(t.duration for t in st.session_state.today_tasks)} min - "
        f"**Number of tasks:** {len(st.session_state.today_tasks)}"
    )


def _apply_selection(selected_ids: set[int]) -> None:
    for task in st.session_state.today_tasks:
        if selected_ids and task.id in selected_ids:
            task.complete(ui_state.TODAY)
        else:
            task.uncomplete()
    ui_state.persist_tasks()


def _apply_due_date_edit(task_id: int, new_value) -> None:
    new_due_date = normalize_date(new_value)
    if new_due_date < ui_state.TODAY:
        st.toast("Chosen due date is in the past", icon="⚠️")
        ui_state.reload_today_grid()
        return

    task = find_task_by_id(st.session_state.tasks, task_id)
    task.due_date = new_due_date
    ui_state.persist_tasks()


def _on_grid_event(grid_response) -> None:
    event = grid_response.event_data
    event_type = event.get("type")

    if event_type == "selectionChanged":
        selected_rows = grid_response.selected_rows
        selected_ids: set[int] = set()
        if selected_rows is not None and len(selected_rows) > 0:
            selected_ids = {int(row["id"]) for row in selected_rows.to_dict(orient="records")}
        _apply_selection(selected_ids)

    elif event_type == "cellValueChanged":
        task_data = event.get("data")
        _apply_due_date_edit(task_data["id"], event.get("newValue"))


def _build_grid_options(df: pd.DataFrame) -> dict:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    gb.configure_column("id", hide=True)
    gb.configure_column("name", headerName="Task", autoHeight=True, wrapText=True, checkboxSelection=True)
    gb.configure_column("frequency", headerName="Frequency", width=120)
    gb.configure_column("priority", headerName="Priority", width=90)
    gb.configure_column("initial_priority", hide=True)
    gb.configure_column("duration", headerName="Duration", width=110)
    gb.configure_column(
        "due_date", headerName="Due date", width=120,
        cellStyle=due_date_cell_style(ui_state.TODAY.isoformat()),
        cellDataType="dateString", editable=True,
    )
    gb.configure_column("next_due_date", headerName="Next Due Date", width=120, cellDataType="dateString")
    gb.configure_column("done_date", headerName="Done date", width=120, cellDataType="dateString")
    gb.configure_column("last_done_date", headerName="Last Done Date", width=150, cellDataType="dateString")
    gb.configure_column("selected", headerName="Selected", hide=True)

    pre_selected = [
        str(idx) for idx, task in enumerate(st.session_state.today_tasks)
        if task.is_completed_on(ui_state.TODAY)
    ]
    gb.configure_selection(
        "multiple", use_checkbox=True, rowMultiSelectWithClick=True,
        suppressRowClickSelection=False, pre_selected_rows=pre_selected,
    )
    gb.configure_grid_options(domLayout="autoHeight", onCellDoubleClicked=JsCode(_DOUBLE_CLICK_DUE_DATE_JS))
    return gb.build()


def render() -> None:
    _render_today_header()

    df = tasks_to_dataframe(st.session_state.today_tasks)
    if df.empty:
        st.info("No tasks were selected for today. Add or edit tasks in the General tab.")
        return

    AgGrid(
        df,
        gridOptions=_build_grid_options(df),
        height=500,
        key=st.session_state.grid_key,
        update_on=["selectionChanged", "cellValueChanged"],
        callback=_on_grid_event,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )
