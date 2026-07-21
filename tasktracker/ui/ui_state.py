"""Streamlit session-state wiring.

This is the only module allowed to touch `st.session_state` directly for
task data — UI modules call these functions instead of poking at state
themselves, which keeps the "what happens when I click this" logic in
one place.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from ..consts import today
from ..json_utils import (
    cache_tasks,
    load_allow_future_tasks,
    load_cached_daily_limit,
    load_cached_task_ids,
    load_show_completed,
    load_show_rescheduled,
    load_tasks,
    save_tasks,
)
from ..selector import compute_daily_tasks
from ..task import Task, normalize_date
from ..task_list_ops import next_task_id as _next_task_id
from ..task_list_ops import remove_tasks_by_id, update_tasks_priority_and_due_date
from ..task_list_ops import restore_tasks as _restore_tasks

@st.cache_resource(show_spinner=False)
def _init_general_task_list() -> list[Task]:
    """Load tasks from disk once per app session and run the daily housekeeping pass.

    Cached with `st.cache_resource` so a Streamlit rerun (which happens on
    every widget interaction) doesn't re-read/re-process the file each time —
    only a fresh process (or an explicit `reset_app()`) does.
    """
    tasks = load_tasks()
    update_tasks_priority_and_due_date(tasks)
    save_tasks(tasks)
    return tasks


def load_today_tasks(
    tasks: list[Task],
    daily_limit: int,
    show_completed: bool = False,
    show_rescheduled: bool = False,
    force_regeneration: bool = False,
    allow_future_tasks: bool = False,
) -> list[Task]:
    """Compute (or reuse) the list of tasks to show in the 'Today' tab.

    If today's selection was already cached (same day, `force_regeneration`
    not set), reuse those task ids as the "pre-selected" set so the picks
    stay stable across reruns instead of being recomputed from scratch.
    Otherwise it and updates `active_duration` / `nb_today_task` in session
    state for the header display.
    Optionally appends already-completed and/or rescheduled tasks so they
    remain visible even if they'd no longer be picked by the selector.
    """
    cache_date, cached_task_ids = load_cached_task_ids()
    current_date = today()

    completed_tasks = [t for t in tasks if t.is_completed_on(current_date)] if show_completed else []
    rescheduled_tasks = (
        [t for t in tasks if any(diff[0] == "Due date" for diff in t.get_changes())]
        if show_rescheduled else []
    )

    if force_regeneration or normalize_date(cache_date) != current_date:
        today_tasks = compute_daily_tasks(tasks, current_date, daily_limit, allow_future_tasks=allow_future_tasks)
    else:
        cached_tasks = [t for t in tasks if t.id in cached_task_ids]
        today_tasks = compute_daily_tasks(tasks, current_date, daily_limit, cached_tasks, allow_future_tasks=allow_future_tasks)

    st.session_state.active_duration = sum(t.duration for t in today_tasks)
    st.session_state.nb_today_task = len(today_tasks)

    # Compare against ids (not the Task objects themselves) to correctly
    # dedup tasks that are both selected by compute_daily_tasks() and
    # already-completed / rescheduled.
    existing_ids = {t.id for t in today_tasks}
    today_tasks += [t for t in completed_tasks if t.id not in existing_ids]

    existing_ids = {t.id for t in today_tasks}
    today_tasks += [t for t in rescheduled_tasks if t.id not in existing_ids]

    return today_tasks


def init_session_state(force_regeneration: bool = False) -> None:
    """Set up (or reset) all Streamlit session state the app depends on.

    Called once at app startup, and again (with `force_regeneration=True`)
    whenever the user clicks "Regenerate" or imports a new task file.
    """
    tasks = _init_general_task_list()
    daily_limit = load_cached_daily_limit()
    show_completed = load_show_completed()
    show_rescheduled = load_show_rescheduled()
    allow_future_tasks = load_allow_future_tasks()
    today_tasks = load_today_tasks(
        tasks, daily_limit, show_completed, show_rescheduled,
        force_regeneration, allow_future_tasks,
    )

    st.session_state.update(
        tasks=tasks,
        today_tasks=today_tasks,
        daily_limit=daily_limit,
        today_grid_key="TodayGrid1",
        general_grid_key="GeneralGrid1",
        timer_running=False,
        timer_start_time=None,
        elapsed_accum=0.0,
        show_completed=show_completed,
        allow_future_tasks=allow_future_tasks,
    )
    persist_tasks()


def cache_today_tasks() -> None:
    """Remember today's task selection in cache.json, keyed by today's date."""
    cache_tasks(st.session_state.today_tasks)


def persist_tasks() -> None:
    """Write the full task list back to tasklist.json."""
    save_tasks(st.session_state.tasks)


def regenerate_today_tasks() -> None:
    """Recompute today's task selection from scratch, keeping already-completed ones.

    Deliberately narrower than `init_session_state`: it only touches
    `today_tasks` (and the counters `load_today_tasks` sets alongside it),
    so it doesn't reset unrelated state like the Timer tab or grid
    selections.
    """
    tasks = st.session_state.tasks
    daily_limit = st.session_state.daily_limit
    show_completed = load_show_completed()
    show_rescheduled = load_show_rescheduled()
    allow_future_tasks = load_allow_future_tasks()

    st.session_state.today_tasks = load_today_tasks(
        tasks, daily_limit, show_completed, show_rescheduled,
        force_regeneration=True, allow_future_tasks=allow_future_tasks,
    )
    persist_tasks()


def restore_tasks(tasks: list[Task]) -> None:
    """Revert every task in `tasks` to its last-persisted (orig_*) state."""
    _restore_tasks(tasks)


def reload_today_grid() -> None:
    """Force the 'Today' data grid to remount by giving it a fresh widget key."""
    st.session_state.today_grid_key = f"TodayGrid{datetime.now().timestamp()}"


def reload_general_grid() -> None:
    """Force the 'General' data grid to remount by giving it a fresh widget key."""
    st.session_state.general_grid_key = f"GeneralGrid{datetime.now().timestamp()}"


def reset_app() -> None:
    """Clear all cached resources and session state (used after importing a new task file)."""
    st.cache_resource.clear()
    st.session_state.clear()


def next_task_id() -> int:
    """Return the next unused task id (max existing id + 1, or 0 if no tasks)."""
    return _next_task_id(st.session_state.tasks)


def add_task(task: Task) -> None:
    """Append a new task, persist it, and refresh the 'General' grid."""
    st.session_state.tasks.append(task)
    persist_tasks()
    reload_general_grid()


def schedule_task_for_today(task: Task) -> None:
    """Manually add a task to today's list, ignoring the daily time budget."""
    task.schedule_for(today())
    if task not in st.session_state.today_tasks:
        st.session_state.today_tasks.append(task)
    persist_tasks()
    reload_today_grid()


def remove_tasks(task_ids: list[int]) -> None:
    """Remove tasks by id from both the full list and today's list, then persist."""
    st.session_state.tasks = remove_tasks_by_id(st.session_state.tasks, task_ids)
    st.session_state.today_tasks = remove_tasks_by_id(st.session_state.today_tasks, task_ids)
    persist_tasks()
    reload_today_grid()
