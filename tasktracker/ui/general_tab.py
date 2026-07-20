"""The 'General' tab: manage the full task library."""
from __future__ import annotations

import json

import streamlit as st

from .grid_utils import find_task_by_id, tasks_to_general_dataframe, PERIOD_OPTIONS
from . import ui_state
from ..task import Task
from ..json_utils import task_list_to_json, save_tasks, import_tasks_from_json_bytes


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
        "schedule_today": st.column_config.ButtonColumn(
            "",
            on_click=_on_schedule_today_click,
            key="schedule_today_button",
            alignment="center",
        ),
        "changes": st.column_config.ButtonColumn(
            "",
            on_click=_on_show_changes_click,
            key="show_changes_button",
            alignment="center",
            width="small",
        ),
    }


def _on_data_change():
    key = st.session_state.general_grid_key
    added_rows = st.session_state[key]["added_rows"]
    edited_rows = st.session_state[key]["edited_rows"]
    deleted_rows = st.session_state[key]["deleted_rows"]
    df = st.session_state.general_df

    if added_rows:
        added_rows = st.session_state[key]["added_rows"]
        new_row = added_rows[-1]
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

    if edited_rows:
        for row_pos, changes in edited_rows.items():
            task = find_task_by_id(st.session_state.tasks, int(df.iloc[row_pos]["id"]))
            
            for column_name in changes.keys():
                if column_name in ["frequency_count", "frequency_period" ]: 
                    count = changes.get("frequency_count", df.iloc[row_pos]["frequency_count"])
                    period = changes.get("frequency_period", df.iloc[row_pos]["frequency_period"])
                    task.set_field("frequency", f"{int(count)}x{period}")

                else:
                    task.set_field(column_name, changes[column_name])
    
    if deleted_rows:
        deleted_ids = [int(df.iloc[row_pos]["id"]) for row_pos in deleted_rows]
        ui_state.remove_tasks(deleted_ids)

    ui_state.persist_tasks()


def _export_json_bytes() -> bytes:
    payload = task_list_to_json(st.session_state.tasks)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    
def _on_schedule_today_click() -> None:
    click = st.session_state.schedule_today_button
    row = click["row"]
    task_id = int(st.session_state.general_df.iloc[row]["id"])
    task = find_task_by_id(st.session_state.tasks, task_id)
    ui_state.schedule_task_for_today(task)

@st.dialog("Changes")
def _show_changes_dialog(row: int) -> None:
    df = st.session_state.general_df
    task_id = int(df.iloc[row]["id"])
    task = find_task_by_id(st.session_state.tasks, task_id)

    st.markdown(f"**{task.name}**")

    diffs = task.get_changes()
    if not diffs:
        st.info("No changes on this task.")
        return

    for label, old, new in diffs:
        st.markdown(f"**{label}:** ~~{old}~~ → {new}")

    if st.button("Discard changes"): 
        task.restore()
        st.rerun()

def _on_show_changes_click() -> None:
    click = st.session_state.show_changes_button
    _show_changes_dialog(click["row"])


@st.dialog("Import tasks")
def _import_tasks_dialog() -> None:
    st.warning(
        "⚠️ Importing a file will **replace your entire task list** "
        "(priorities, due dates, done dates — everything) and cannot be undone."
    )

    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"], key="import_file_uploader")

    if uploaded_file is None:
        return

    try:
        new_tasks = import_tasks_from_json_bytes(uploaded_file.getvalue())
    except ValueError as exc:
        st.error(f"Could not import this file:\n\n{exc}")
        return

    st.success(f"File looks valid — {len(new_tasks)} tasks found.")
    st.caption("Click confirm below to replace your current tasks and reload the app.")

    if st.button("✅ Replace all tasks and reload", type="primary"):
        save_tasks(new_tasks)
        ui_state.reset_app()
        st.rerun()

def _toggle_sort():
    st.session_state.ascending = not st.session_state.ascending

def _reset_priorities():
    for task in st.session_state.tasks: 
        task.priority = task.initial_priority
    ui_state.persist_tasks()

def render() -> None:
    st.markdown("### Edit tasks", anchors=False)

    if "ascending" not in st.session_state:
        st.session_state.ascending = True

    container = st.container(horizontal=True, width="content", vertical_alignment="bottom")
    if container.button("⭯ Discard all changes"):
        ui_state.restore_tasks(st.session_state.tasks)
        ui_state.reload_today_grid()
        ui_state.reload_general_grid()
        st.rerun()

    container.download_button("⭳ Export tasks",data=_export_json_bytes(),file_name="tasklist.json",mime="application/json",)

    if container.button("⭱ Import tasks"):
        _import_tasks_dialog()
        
    df = tasks_to_general_dataframe(st.session_state.tasks)
    if df.empty:
        st.info("No tasks yet — use \u201cAdd task\u201d to create your first one.")
        return
 
    col = container.selectbox("Sort by", options=df.columns)
    container.button(label="▲ Ascending" if st.session_state.ascending else "▼ Descending", on_click=_toggle_sort, width="content")

    container.button(label="Reset priorities", on_click=_reset_priorities)

    sorted_df = df.sort_values(by=col, ascending=st.session_state.ascending).reset_index(drop=True)
    st.session_state.general_df = sorted_df

    key = st.session_state.general_grid_key
    edited_df = st.data_editor(
        sorted_df,
        column_config=_column_config(),
        hide_index=True,
        width="content",
        height="content",
        key=key,
        num_rows="dynamic",
        on_change=_on_data_change
    )

    