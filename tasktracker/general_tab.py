"""The 'General' tab: manage the full task library."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from datetime import date, timedelta

from tasktracker.today_tab import get_theme_color


from . import ui_state
from .tt_json_utils import import_tasks_from_json_bytes, save_tasks, task_list_to_json
from tasktracker.change_tracking_task import task_changes, discard_task_changes
from .task import Task, Period
from .task_list_ops import find_task_by_id

from common.consts import today

def _on_update_dates_click():
    click = st.session_state.update_dates_button
    _update_dates(click["row"])
    

@st.dialog("Completed on", width="medium")
def _update_dates(row: int) -> None:
    """Dialog to change, cancel, or advance a task's due date."""
    
    st.markdown(f"**{st.session_state.general_df.iloc[row]['name']}**")
    task = find_task_by_id(st.session_state.tasks, st.session_state.general_df.at[row, "id"])
    init_due_date = task.due_date if task.due_date is not None else today()
    init_done_date = task.done_date if task.done_date is not None else today()

    # UI to update the done date and compute next due date
    with st.container(horizontal=True, vertical_alignment="bottom"):
        new_done_date = st.date_input(
            "Update done date and set next due date",
            value=pd.to_datetime(init_done_date).date(),
            width="stretch",
        )
        if st.button("Save", key="save_done_date_button"):
            ui_state.update_done_date(task, new_done_date)
            st.rerun()
    with st.container(horizontal=True, vertical_alignment="bottom"):
        new_due_date = st.date_input(
            "Update due date",
            value=pd.to_datetime(init_due_date).date(),
            width="stretch",
        )
        if st.button("Save", key="save_due_date_button"):
            ui_state.schedule_task_for(task, new_due_date)
            st.rerun()
            
    with st.container(horizontal=True, vertical_alignment="bottom", width="stretch" ):
        if st.button("Cancel task"):
            ui_state.cancel_task(task)
            st.rerun()
        if st.button("To next due date"):
            ui_state.schedule_task_for(task, task.get_next_due_date(task.due_date))
            st.rerun()
        if st.button("To this weekend"):
            days_until_saturday = (5 - today().weekday()) % 7
            ui_state.schedule_task_for(task, today() + timedelta(days=days_until_saturday))
            st.rerun()
        if st.button("To today"):
            ui_state.schedule_task_for(task, today())
            st.rerun()
    

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
            "state": str(task.state),
            "update_dates": ":material/edit_note: Update dates",
            "changes": ":material/edit_note: Changes" if task_changes(task, st.session_state.task_baseline) else None,
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
            "Period", options=[p.value for p in Period], width="small", required=True,
        ),
        "priority": st.column_config.NumberColumn("Priority", step=0.5, format="%.1f"),
        "initial_priority": st.column_config.NumberColumn("Initial Priority", step=0.5, format="%.1f", required=True),
        "duration": st.column_config.NumberColumn("Duration (min)", min_value=1, step=5, required=True),
        "due_date": st.column_config.DateColumn("Due date", format="DD/MM/YYYY", disabled=True), 
        "done_date": st.column_config.DateColumn("Done date", format="DD/MM/YYYY", disabled=True),
        "state": st.column_config.TextColumn("State", disabled=True),
        "update_dates": st.column_config.ButtonColumn("", on_click=_on_update_dates_click, key="update_dates_button", alignment="center"),
        "changes": st.column_config.ButtonColumn("", on_click=_on_show_changes_click, key="show_changes_button", alignment="center", width='medium'),
    }


def _apply_added_row(new_row: dict) -> None:
    """Turn a single new-row dict from the data editor into a persisted Task."""
    task = Task(
        name=new_row["name"].strip(),
        frequency=f"{int(new_row['frequency_count'])}x{new_row['frequency_period']}",
        priority=new_row["initial_priority"],
        initial_priority=new_row["initial_priority"],
        duration=int(new_row["duration"]),
    )
    ui_state.add_task(task)


def _apply_edited_rows(edited_rows: dict, df: pd.DataFrame) -> None:
    """Apply each column change from the data editor onto the matching Task.

    `frequency_count`/`frequency_period` are recombined into the single
    `frequency` field the Task model actually stores. `due_date`/`done_date`
    are routed through their dedicated setter methods rather than
    `set_field()`, since Task no longer allows those two fields to be set
    generically (see Task.set_field's docstring).
    """
    for row_pos, changes in edited_rows.items():
        task = find_task_by_id(st.session_state.tasks, df.iloc[row_pos]["id"])

        for column_name in changes:
            if column_name in ("frequency_count", "frequency_period"):
                count = changes.get("frequency_count", df.iloc[row_pos]["frequency_count"])
                period = changes.get("frequency_period", df.iloc[row_pos]["frequency_period"])
                task.set_field("frequency", f"{int(count)}x{period}")
            elif column_name == "due_date":
                task.set_due_date(changes["due_date"])
            elif column_name == "done_date":
                task.set_done_date(changes["done_date"])
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
        deleted_ids = [df.iloc[row_pos]["id"] for row_pos in editor_state["deleted_rows"]]
        ui_state.remove_tasks(deleted_ids)

    ui_state.persist_tasks()


def _export_json_bytes() -> bytes:
    """Serialize the full task list as JSON bytes, for the download button."""
    payload = task_list_to_json(st.session_state.tasks)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


@st.dialog("Changes")
def _show_changes_dialog(row: int) -> None:
    """Dialog listing pending (unpersisted-since-baseline) field changes for
    one task, with a discard option."""
    df = st.session_state.general_df
    task_id = df.iloc[row]["id"]
    task = find_task_by_id(st.session_state.tasks, task_id)

    st.markdown(f"**{task.name}**")

    diffs = task_changes(task, st.session_state.task_baseline)
    if not diffs:
        st.info("No changes on this task.")
        return

    for label, old, new in diffs:
        st.markdown(f"**{label}:** ~~{old}~~ → {new}")

    if st.button("Discard changes"):
        discard_task_changes(task, st.session_state.task_baseline)
        ui_state.persist_tasks()
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


def _colorize_rows(row: pd.Series) -> list[str]:
    """Row-styling: highlight tasks done today, dim tasks not due today, mark
    cancelled tasks — reading the explicit `cancelled` flag instead of the
    old date.max sentinel."""

    color = get_theme_color("textColor")
    colIdx = row.index.get_loc("state")
    colors = [f"color: {color}"] * len(row)
    
    task = find_task_by_id(st.session_state.tasks, row["id"])
    if task.is_completed():
        color = get_theme_color("doneTextColor")
    elif task.is_cancelled():
        color = get_theme_color("cancelledTextColor")
    elif task.is_manually_rescheduled() and task.due_date != today():
        color = get_theme_color("hiddenTextColor")
    elif task.is_eligible():
        color = get_theme_color("eligibleTextColor")
    colors[colIdx] = f"color: {color}"
    return colors


def render() -> None:
    """Render the 'General' tab: toolbar (discard/export/import/sort/reset) + the full task grid."""
    st.markdown("### Edit tasks", anchors=False)

    if "ascending" not in st.session_state:
        st.session_state.ascending = True

    toolbar = st.container(horizontal=True, width="content", vertical_alignment="bottom")

    toolbar.download_button(
        "⭳ Export tasks", data=_export_json_bytes(), file_name="tasklist.json", mime="application/json",
    )

    if toolbar.button("⭱ Import tasks"):
        _import_tasks_dialog()

    df = _tasks_to_general_dataframe(st.session_state.tasks)
    if df is None:
        st.info("No tasks yet — use \u201cAdd task\u201d to create your first one.")
        return

    sort_column = toolbar.selectbox("Sort by", options=df.columns, width=150, index=1)
    toolbar.button(
        label="▲ Ascending" if st.session_state.ascending else "▼ Descending",
        on_click=_toggle_sort, width="content", type="tertiary",
    )

    sorted_df = df.sort_values(by=sort_column, ascending=st.session_state.ascending).reset_index(drop=True)
    st.session_state.general_df = sorted_df

    styled_df = sorted_df.style.apply(_colorize_rows, axis=1)

    key = st.session_state.general_grid_key
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
