"""The 'Today' tab: check off and reschedule today's tasks."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import ui_state
from .common import get_theme_color
from ..consts import today
from ..json_utils import (
    cache_allow_future_tasks,
    cache_daily_limit,
    cache_show_completed,
    cache_show_rescheduled,
    load_allow_future_tasks,
    load_show_completed,
    load_show_rescheduled,
)
from ..task import Task
from ..task_list_ops import find_task_by_id


def _tasks_to_today_dataframe(tasks: list[Task]) -> pd.DataFrame | None:
    """Build the dataframe shown in the 'Today' tab.

    Frequency stays as a single display string here (read-only column, no
    per-half editing needed) and an extra `completed` / `reschedule` column
    pair drives the row action buttons. Returns None if `tasks` is empty.
    """
    if not tasks:
        return None

    current_date = today()
    records = [
        {
            "id": task.id,
            "completed": "🗹" if task.is_completed_on(current_date) else "☐",
            "name": task.name,
            "frequency": task.frequency,
            "priority": task.priority,
            "initial_priority": task.initial_priority,
            "duration": task.duration,
            "due_date": task.due_date,
            "done_date": task.done_date,
            "reschedule": ":material/edit: Reschedule",
        }
        for task in tasks
    ]
    return pd.DataFrame.from_records(records)


@st.dialog("Rechedule task")
def _edit_due_date(row: int) -> None:
    """Dialog to change, cancel, or advance a task's due date."""
    row_date = st.session_state.today_df.iloc[row]["due_date"]
    current = row_date if row_date is not None else today()
    task = find_task_by_id(st.session_state.tasks, st.session_state.today_df.at[row, "id"])

    with st.container(horizontal=True, vertical_alignment="bottom"):
        new_date = st.date_input(
            f"**{st.session_state.today_df.iloc[row]['name']}**",
            value=pd.to_datetime(current).date(),
            width=200,
        )
        if st.button("Save"):
            task.due_date = new_date
            ui_state.persist_tasks()
            st.rerun()

    with st.container(horizontal=True, vertical_alignment="bottom"):
        if st.button("Cancel task"):
            task.due_date = None
            ui_state.persist_tasks()
            st.rerun()
        if st.button("To next due date"):
            task.due_date = task.compute_next_due_date(task.due_date)
            ui_state.persist_tasks()
            st.rerun()


def _on_reschedule_click() -> None:
    """Callback for the 'reschedule' button column: opens the due-date dialog for the clicked row."""
    click = st.session_state.reschedule_button
    _edit_due_date(click["row"])


def _render_today_header() -> None:
    """Render the date title, daily-limit input, toggles, and the active-duration summary line."""
    st.markdown("### Tâches du " + today().strftime("%A %d %B %Y"), anchors=False)

    with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", height="stretch"):
        st.markdown("Daily duration limit (minutes) : ", anchors=False)
        st.number_input(
            label="Daily duration limit",
            label_visibility="collapsed",
            min_value=5,
            max_value=720,
            step=15,
            key="daily_limit",
            on_change=lambda: cache_daily_limit(daily_limit=st.session_state.daily_limit),
            width=100,
        )

        st.button("🔄 Regenerate", on_click=ui_state.regenerate_today_tasks)
        st.checkbox(
            "Show completed tasks", load_show_completed(),
            on_change=lambda: cache_show_completed(st.session_state.show_completed_checkbox),
            key="show_completed_checkbox",
        )
        st.checkbox(
            "Show rescheduled tasks", load_show_rescheduled(),
            on_change=lambda: cache_show_rescheduled(st.session_state.show_rescheduled_checkbox),
            key="show_rescheduled_checkbox",
        )
        st.checkbox(
            "Allow future tasks", load_allow_future_tasks(),
            on_change=lambda: cache_allow_future_tasks(st.session_state.allow_future_tasks_checkbox),
            key="allow_future_tasks_checkbox",
        )

    st.write(
        f"**Active duration:** {st.session_state.active_duration} min - "
        f"**Number of tasks:** {st.session_state.nb_today_task}"
    )


def _column_config() -> dict:
    """Column layout/behavior for the 'Today' data grid."""
    return {
        "id": None,
        "frequency_count": None,
        "frequency_period": None,
        "initial_priority": None,
        "completed": st.column_config.ButtonColumn(
            "", width=30, key="complete_button", on_click=_on_row_selected, type="tertiary",
        ),
        "name": st.column_config.TextColumn("Task", width="large"),
        "frequency": st.column_config.TextColumn("Frequency", width="small"),
        "priority": st.column_config.NumberColumn("Priority", format="%.1f", width="small"),
        "duration": st.column_config.NumberColumn("Duration", width="small"),
        "due_date": st.column_config.DateColumn("Due date", format="localized"),
        "done_date": st.column_config.DateColumn("Done date", format="localized"),
        "reschedule": st.column_config.ButtonColumn("", on_click=_on_reschedule_click, key="reschedule_button", alignment="left"),
    }


def _on_row_selected() -> None:
    """Callback for the 'completed' button column: toggles a task's completion state."""
    clicked_row = st.session_state.complete_button["row"]
    task = find_task_by_id(st.session_state.tasks, st.session_state.today_df.at[clicked_row, "id"])

    # The dataframe still shows the *pre-click* label, so "☐" means the
    # task is about to be marked done, and "🗹" means it's about to be un-done.
    was_uncompleted = st.session_state.today_df.at[clicked_row, "completed"] == "☐"
    if was_uncompleted:
        task.complete(today())
    else:
        task.uncomplete()

    ui_state.cache_today_tasks()
    ui_state.persist_tasks()


def _color_by_due_date(row: pd.Series) -> list[str]:
    """Row-styling: highlight tasks done today, dim tasks not due today."""
    current_date = today()
    color = get_theme_color("textColor")
    if current_date == row["done_date"]:
        color = get_theme_color("doneTextColor")
    elif row["due_date"] != current_date:
        color = get_theme_color("hiddenTextColor")
    return [f"color: {color}"] * len(row)


def render() -> None:
    """Render the 'Today' tab: header controls + the today-tasks grid."""
    _render_today_header()

    df = _tasks_to_today_dataframe(st.session_state.today_tasks)
    st.session_state.today_df = df
    if df is None:
        st.info("No tasks were selected for today. Add or edit tasks in the General tab.")
        return

    styled_df = df.style.apply(_color_by_due_date, axis=1)

    key = st.session_state.today_grid_key
    st.dataframe(
        styled_df,
        column_config=_column_config(),
        hide_index=True,
        width="content",
        height="content",
        key=key,
        selection_mode=[],
    )
