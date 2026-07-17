"""The 'General' tab: manage the full task library."""
from __future__ import annotations

import streamlit as st

from .grid_utils import find_task_by_id, tasks_to_general_dataframe, PERIOD_OPTIONS
from . import ui_state
from ..task import Task

# _COLUMN_ORDER = [
#     "name", "frequency_count", "frequency_period",
#     "priority", "initial_priority", "duration", "due_date", "done_date",
# ]


def _column_config() -> dict:
    return {
        "id": None,
        "name": st.column_config.TextColumn("Task", width="large", required=True),
        "frequency_count": st.column_config.NumberColumn("Every", min_value=1, step=1, format="%d", width="small", required=True),
        "frequency_period": st.column_config.SelectboxColumn("Period", options=PERIOD_OPTIONS, width="small", required=True),
        "priority": st.column_config.NumberColumn("Priority", step=0.5, format="%.1f"),
        "initial_priority": st.column_config.NumberColumn("Initial Priority", step=0.5, format="%.1f", required=True),
        "duration": st.column_config.NumberColumn("Duration (min)", min_value=1, step=5, required=True),
        "due_date": st.column_config.DateColumn("Due date", format="DD/MM/YYYY"),
        "done_date": st.column_config.DateColumn("Done date", format="DD/MM/YYYY", disabled=True),
    }


def _sync_edits(df, edited_rows: dict) -> None:
    """Push cell-level diffs from the editor back onto the real Task objects."""
    for row_pos, changes in edited_rows.items():
        task = find_task_by_id(st.session_state.tasks, int(df.iloc[row_pos]["id"]))

        if "frequency_count" in changes or "frequency_period" in changes:
            count = changes.get("frequency_count", df.iloc[row_pos]["frequency_count"])
            period = changes.get("frequency_period", df.iloc[row_pos]["frequency_period"])
            task.set_field("frequency", f"{int(count)}x{period}")

        for field_name in ("name", "priority", "initial_priority", "duration", "due_date"):
            if field_name in changes:
                task.set_field(field_name, changes[field_name])

    if edited_rows:
        ui_state.persist_tasks()



def on_data_change():
    key = st.session_state.manage_grid_key
    added_rows = st.session_state[key]["added_rows"]
    if not added_rows:
        return
    
    added_rows = st.session_state[key]["added_rows"]
    new_row = [-1]
    task = Task(
        id=ui_state.next_task_id(),
        name=new_row['name'].strip(),
        frequency=f"{int(new_row['frequency_count'])}x{new_row['frequency_period']}",
        priority=new_row['initial_priority'],
        initial_priority=new_row['initial_priority'],
        duration=int(new_row['duration']),
        due_date=None,
        done_date=None
    )
    ui_state.add_task(task)
    ui_state.persist_tasks()


def render() -> None:
    st.markdown("### Edit tasks", anchors=False)
    df = tasks_to_general_dataframe(st.session_state.tasks)
    if df.empty:
        st.info("No tasks yet — use \u201cAdd task\u201d to create your first one.")
        return

    key = st.session_state.manage_grid_key
    edited_df = st.data_editor(
        df,
        column_config=_column_config(),
        # column_order=_COLUMN_ORDER,
        hide_index=True,
        width="stretch",
        height="auto",
        key=key,
        num_rows="dynamic",
        on_change=on_data_change
    )

    _sync_edits(df, st.session_state[key]["edited_rows"])

    with st.container(horizontal=True, width="content"):
        if st.button("⭯ Discard changes"):
            ui_state.restore_tasks(st.session_state.today_tasks)
            ui_state.reload_today_grid()
            ui_state.reload_manage_grid()
            st.rerun()