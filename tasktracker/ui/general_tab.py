"""The 'General' tab: manage the full task library."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from . import ui_state
from .common import PERIOD_OPTIONS
from ..json_utils import import_tasks_from_json_bytes, save_tasks, task_list_to_json
from ..task import Task
from ..task_list_ops import find_task_by_id


def _tasks_to_general_dataframe(tasks: list[Task]) -> pd.DataFrame | None:
    """Build the dataframe shown in the 'General' (edit-all-tasks) tab.

    Frequency is split into `frequency_count` / `frequency_period` so each
    half gets its own widget (number input / dropdown) in the editor —
    this replaces the old combined JS cell editor. Dates are kept as real
    `date` objects so `st.column_config.DateColumn` can format/parse them.
    Returns None if `tasks` is empty.
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
            "changes": ":material/edit_note: Changes" if task.get_changes() else None,
        })
    return pd.DataFrame.from_records(records)


def _column_config() -> dict:
    """Column layout/behavior for the 'General' data grid."""
    return {
        "id": None,
        "name": st.column_config.TextColumn("Task", width="large", required=True),
        "frequency_count": st.column_config.NumberColumn(
            "Every", min_value=1, step=1, format="%d", width="small", required=True,
        ),
        "frequency_period": st.column_config.SelectboxColumn(
            "Period", options=PERIOD_OPTIONS, width="small", required=True,
        ),
        "priority": st.column_config.NumberColumn("Priority", step=0.5, format="%.1f"),
        "initial_priority": st.column_config.NumberColumn("Initial Priority", step=0.5, format="%.1f", required=True),
        "duration": st.column_config.NumberColumn("Duration (min)", min_value=1, step=5, required=True),
        "due_date": st.column_config.DateColumn("Due date", format="DD/MM/YYYY"),
        "done_date": st.column_config.DateColumn("Done date", format="DD/MM/YYYY", disabled=True),
        "schedule_today": st.column_config.ButtonColumn(
            "", on_click=_on_schedule_today_click, key="schedule_today_button", alignment="center",
        ),
        "changes": st.column_config.ButtonColumn(
            "", on_click=_on_show_changes_click, key="show_changes_button", alignment="center", width="small",
        ),
    }


def _apply_added_row(new_row: dict) -> None:
    """Turn a single new-row dict from the data editor into a persisted Task."""
    task = Task(
        id=ui_state.next_task_id(),
        name=new_row["name"].strip(),
        frequency=f"{int(new_row['frequency_count'])}x{new_row['frequency_period']}",
        priority=new_row["initial_priority"],
        initial_priority=new_row["initial_priority"],
        duration=int(new_row["duration"]),
        due_date=None,
        done_date=None,
    )
    ui_state.add_task(task)


def _apply_edited_rows(edited_rows: dict, df: pd.DataFrame) -> None:
    """Apply each column change from the data editor onto the matching Task.

    `frequency_count`/`frequency_period` are recombined into the single
    `frequency` field the Task model actually stores.
    """
    for row_pos, changes in edited_rows.items():
        task = find_task_by_id(st.session_state.tasks, int(df.iloc[row_pos]["id"]))

        for column_name in changes:
            if column_name in ("frequency_count", "frequency_period"):
                count = changes.get("frequency_count", df.iloc[row_pos]["frequency_count"])
                period = changes.get("frequency_period", df.iloc[row_pos]["frequency_period"])
                task.set_field("frequency", f"{int(count)}x{period}")
            else:
                task.set_field(column_name, changes[column_name])


def _on_data_change() -> None:
    """Callback fired on any add/edit/delete in the 'General' data editor."""
    key = st.session_state.general_grid_key
    editor_state = st.session_state[key]
    df = st.session_state.general_df

    if editor_state["added_rows"]:
        # Only the last added row is new; earlier ones were already handled
        # on a previous rerun.
        _apply_added_row(editor_state["added_rows"][-1])

    if editor_state["edited_rows"]:
        _apply_edited_rows(editor_state["edited_rows"], df)

    if editor_state["deleted_rows"]:
        deleted_ids = [int(df.iloc[row_pos]["id"]) for row_pos in editor_state["deleted_rows"]]
        ui_state.remove_tasks(deleted_ids)

    ui_state.persist_tasks()


def _export_json_bytes() -> bytes:
    """Serialize the full task list as JSON bytes, for the download button."""
    payload = task_list_to_json(st.session_state.tasks)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _on_schedule_today_click() -> None:
    """Callback for the 'schedule_today' button column."""
    click = st.session_state.schedule_today_button
    row = click["row"]
    task_id = int(st.session_state.general_df.iloc[row]["id"])
    task = find_task_by_id(st.session_state.tasks, task_id)
    ui_state.schedule_task_for_today(task)


@st.dialog("Changes")
def _show_changes_dialog(row: int) -> None:
    """Dialog listing pending (unpersisted) field changes for one task, with a discard option."""
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
    """Callback for the 'changes' button column: opens the changes dialog for the clicked row."""
    click = st.session_state.show_changes_button
    _show_changes_dialog(click["row"])


@st.dialog("Import tasks")
def _import_tasks_dialog() -> None:
    """Dialog to upload a JSON file and, after validation, replace the entire task list."""
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


def _toggle_sort() -> None:
    """Flip the ascending/descending sort direction for the 'General' grid."""
    st.session_state.ascending = not st.session_state.ascending


def _reset_priorities() -> None:
    """Reset every task's priority back to its initial_priority."""
    for task in st.session_state.tasks:
        task.priority = task.initial_priority
    ui_state.persist_tasks()


def render() -> None:
    """Render the 'General' tab: toolbar (discard/export/import/sort/reset) + the full task grid."""
    st.markdown("### Edit tasks", anchors=False)

    if "ascending" not in st.session_state:
        st.session_state.ascending = True

    toolbar = st.container(horizontal=True, width="content", vertical_alignment="bottom")
    if toolbar.button("⭯ Discard all changes"):
        ui_state.restore_tasks(st.session_state.tasks)
        ui_state.reload_today_grid()
        ui_state.reload_general_grid()
        st.rerun()

    toolbar.download_button(
        "⭳ Export tasks", data=_export_json_bytes(), file_name="tasklist.json", mime="application/json",
    )

    if toolbar.button("⭱ Import tasks"):
        _import_tasks_dialog()

    df = _tasks_to_general_dataframe(st.session_state.tasks)
    if df is None:
        st.info("No tasks yet — use \u201cAdd task\u201d to create your first one.")
        return

    sort_column = toolbar.selectbox("Sort by", options=df.columns, width=150)
    toolbar.button(
        label="▲ Ascending" if st.session_state.ascending else "▼ Descending",
        on_click=_toggle_sort, width="content", type="tertiary",
    )
    toolbar.button(label="Reset priorities", on_click=_reset_priorities)

    sorted_df = df.sort_values(by=sort_column, ascending=st.session_state.ascending).reset_index(drop=True)
    st.session_state.general_df = sorted_df

    key = st.session_state.general_grid_key
    st.data_editor(
        sorted_df,
        column_config=_column_config(),
        hide_index=True,
        width="content",
        height="content",
        key=key,
        num_rows="dynamic",
        on_change=_on_data_change,
    )
