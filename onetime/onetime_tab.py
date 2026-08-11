"""The 'One-time' tab: manage tasks that don't recur.

One-time tasks reuse the Task model (tasktracker/task.py) but are never fed
into the daily selector/eligibility logic — the only way one gets onto the
Today list is the '📅 Schedule for today' button here (see
ui_state.schedule_onetime_task_for). Once scheduled, a task stays flagged
as manually-rescheduled indefinitely — there's no daily housekeeping pass
resetting it the way there is for recurring tasks — so it keeps showing on
Today, green once completed, until its row is deleted from this grid.
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from tasktracker import ui_state
from tasktracker.task import Task
from tasktracker.task_list_ops import find_task_by_id
from common.consts import today
from common.common_utils import get_theme_color

from .onetime_json_utils import (
    import_onetime_tasks_from_json_bytes,
    save_onetime_tasks,
    task_list_to_json,
)


def _on_schedule_click() -> None:
    click = st.session_state.onetime_schedule_button
    row = click["row"]
    task_id = st.session_state.onetime_df.at[row, "id"]
    task = find_task_by_id(st.session_state.onetime_tasks, task_id)
    ui_state.schedule_onetime_task_for(task, today())


def _tasks_to_onetime_dataframe(tasks: list[Task]) -> pd.DataFrame | None:
    if not tasks:
        return None
    records = []
    for task in tasks:
        records.append({
            "id": task.id,
            "name": task.name,
            "duration": task.duration,
            "done_date": task.done_date,
            "state": str(task.state),
            "schedule": (
                ":material/event_available: On today's list"
                if task.is_manually_rescheduled()
                else ":material/event: Add to today"
            ),
        })
    return pd.DataFrame.from_records(records)


def _column_config() -> dict:
    return {
        "id": None,
        "name": st.column_config.TextColumn("Task", width="large", required=True),
        "duration": st.column_config.NumberColumn("Duration (min)", min_value=1, step=5, required=True),
        "done_date": st.column_config.DateColumn("Done date", format="DD/MM/YYYY", disabled=True),
        "state": st.column_config.TextColumn("State", disabled=True),
        "schedule": st.column_config.ButtonColumn(
            "", on_click=_on_schedule_click, key="onetime_schedule_button",
            alignment="center", width="medium",
        ),
    }


def _apply_added_row(new_row: dict) -> None:
    """Turn a new-row dict from the data editor into a persisted one-time Task.

    frequency/priority are set to inert defaults — one-time tasks never
    read them for anything (see onetime/__init__.py).
    """
    task = Task(
        name=new_row["name"].strip(),
        frequency="ponctuel",
        priority=0,
        initial_priority=0,
        duration=int(new_row["duration"]),
    )
    ui_state.add_onetime_task(task)


def _apply_edited_rows(edited_rows: dict, df: pd.DataFrame) -> None:
    for row_pos, changes in edited_rows.items():
        task = find_task_by_id(st.session_state.onetime_tasks, df.iloc[row_pos]["id"])
        for column_name in ("name", "duration"):
            if column_name in changes:
                task.set_field(column_name, changes[column_name])


def _on_data_change() -> None:
    """Callback fired on any add/edit/delete in the One-time data editor."""
    key = st.session_state.onetime_grid_key
    editor_state = st.session_state[key]
    df = st.session_state.onetime_df

    if editor_state["added_rows"]:
        _apply_added_row(editor_state["added_rows"][-1])

    if editor_state["edited_rows"]:
        _apply_edited_rows(editor_state["edited_rows"], df)

    if editor_state["deleted_rows"]:
        deleted_ids = [df.iloc[row_pos]["id"] for row_pos in editor_state["deleted_rows"]]
        ui_state.remove_onetime_tasks(deleted_ids)

    ui_state.persist_onetime_tasks()


def _export_json_bytes() -> bytes:
    payload = task_list_to_json(st.session_state.onetime_tasks)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


@st.dialog("Import one-time tasks")
def _import_onetime_dialog() -> None:
    st.warning(
        "⚠️ Importing a file will **replace your entire one-time task list** "
        "and cannot be undone."
    )
    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"], key="import_onetime_file_uploader")
    if uploaded_file is None:
        return

    try:
        new_tasks = import_onetime_tasks_from_json_bytes(uploaded_file.getvalue())
    except ValueError as exc:
        st.error(f"Could not import this file:\n\n{exc}")
        return

    st.success(f"File looks valid — {len(new_tasks)} tasks found.")
    st.caption("Click confirm below to replace your current one-time tasks and reload.")

    if st.button("✅ Replace all one-time tasks and reload", type="primary"):
        save_onetime_tasks(new_tasks)
        ui_state.reset_app()
        st.rerun()


def _colorize_rows(row: pd.Series) -> list[str]:
    """Row-styling: green once completed, an 'eligible'-style highlight while
    scheduled-but-not-done, default otherwise."""
    color = get_theme_color("textColor")
    task = find_task_by_id(st.session_state.onetime_tasks, row["id"])
    if task.is_completed():
        color = get_theme_color("doneTextColor")
    elif task.is_manually_rescheduled():
        color = get_theme_color("eligibleTextColor")
    return [f"color: {color}"] * len(row)


def render() -> None:
    """Render the 'One-time' tab: toolbar (export/import) + the task grid."""
    st.markdown("### One-time tasks", anchors=False)

    toolbar = st.container(horizontal=True, width="content", vertical_alignment="bottom")
    toolbar.download_button(
        "⭳ Export", data=_export_json_bytes(), file_name="onetime_tasks.json", mime="application/json",
    )
    if toolbar.button("⭱ Import"):
        _import_onetime_dialog()

    df = _tasks_to_onetime_dataframe(st.session_state.onetime_tasks)
    if df is None:
        st.info("No one-time tasks yet — use \u201cAdd task\u201d to create your first one.")
        return

    st.session_state.onetime_df = df
    styled_df = df.style.apply(_colorize_rows, axis=1)

    key = st.session_state.onetime_grid_key
    st.data_editor(
        styled_df,
        column_config=_column_config(),
        hide_index=True,
        width="content",
        height="content",
        key=key,
        num_rows="dynamic",
        on_change=_on_data_change,
    )
