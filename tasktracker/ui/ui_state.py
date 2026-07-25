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


def _sync_today_tasks(
    tasks: list[Task], show_completed: bool, show_rescheduled: bool,
) -> tuple[list[Task], bool]:
    """Derive today's task list purely from what's persisted in cache.json.

    Never invokes the selector — just reads cache.json and filters `tasks`
    against the cached ids. Cheap enough to call on every rerun, from any
    session, so correctness never depends on `st.session_state` having
    survived a refresh, a new tab, or a process restart. If cache.json's
    date doesn't match today (never generated yet, or day rolled over),
    returns ([], False).
    """
    cache_date, cached_task_ids = load_cached_task_ids()
    current_date = today()

    if normalize_date(cache_date) != current_date:
        return [], False

    cached_ids = set(cached_task_ids or [])
    today_tasks = [t for t in tasks if t.id in cached_ids]

    completed_tasks = [t for t in tasks if t.is_completed_on(current_date)] if show_completed else []
    rescheduled_tasks = (
        [t for t in tasks if any(diff[0] == "Due date" for diff in t.get_changes())]
        if show_rescheduled else []
    )

    existing_ids = {t.id for t in today_tasks}
    today_tasks += [t for t in completed_tasks if t.id not in existing_ids]

    existing_ids = {t.id for t in today_tasks}
    today_tasks += [t for t in rescheduled_tasks if t.id not in existing_ids]

    return today_tasks, True


def load_today_tasks(
    tasks: list[Task],
    daily_limit: int,
    show_completed: bool = False,
    show_rescheduled: bool = False,
    allow_future_tasks: bool = False,
) -> list[Task]:
    """Actually *compute* today's task list by running the selector.

    This is the only function allowed to call `compute_daily_tasks`. It's
    used exclusively by `regenerate_today_tasks` — never at plain session
    init, which instead uses `_sync_today_tasks` to re-derive from
    cache.json without recomputing anything.

    Reuses whatever is currently cached as `today` as the "pre-selected"
    set (if any) so the picks stay stable around already-chosen tasks
    instead of being recomputed from scratch, then also appends
    already-completed and/or rescheduled tasks so they remain visible
    even if they'd no longer be picked by the selector.
    """
    current_date = today()
    _, cached_task_ids = load_cached_task_ids()
    cached_task_ids = cached_task_ids or []

    pre_selected = [t for t in tasks if t.id in cached_task_ids]
    today_tasks = compute_daily_tasks(
        tasks, current_date, daily_limit, pre_selected, allow_future_tasks=allow_future_tasks,
    )

    completed_tasks = [t for t in tasks if t.is_completed_on(current_date)] if show_completed else []
    rescheduled_tasks = (
        [t for t in tasks if any(diff[0] == "Due date" for diff in t.get_changes())]
        if show_rescheduled else []
    )

    existing_ids = {t.id for t in today_tasks}
    today_tasks += [t for t in completed_tasks if t.id not in existing_ids]

    existing_ids = {t.id for t in today_tasks}
    today_tasks += [t for t in rescheduled_tasks if t.id not in existing_ids]

    return today_tasks


def init_session_state() -> None:
    """Set up (or refresh) all Streamlit session state the app depends on.

    Runs on every rerun — no "already initialized" guard. Today's task
    list is always re-derived from cache.json via `_sync_today_tasks`,
    never recomputed here, so this stays cheap regardless of how often
    it's called and regardless of what session/tab/process is calling it.
    """
    tasks = _init_general_task_list()
    daily_limit = load_cached_daily_limit()
    show_completed = load_show_completed()
    show_rescheduled = load_show_rescheduled()
    allow_future_tasks = load_allow_future_tasks()

    today_tasks, today_generated = _sync_today_tasks(tasks, show_completed, show_rescheduled)

    st.session_state.tasks = tasks
    st.session_state.today_tasks = today_tasks
    st.session_state.today_generated = today_generated
    st.session_state.active_duration = sum(t.duration for t in today_tasks)
    st.session_state.nb_today_task = len(today_tasks)
    st.session_state.daily_limit = daily_limit
    st.session_state.show_completed = show_completed
    st.session_state.allow_future_tasks = allow_future_tasks

    # Pure session-local UI state — setdefault so mid-session values (timer
    # running, grid keys) survive reruns, but a genuinely fresh session
    # still gets sane defaults.
    st.session_state.setdefault("today_grid_key", "TodayGrid1")
    st.session_state.setdefault("general_grid_key", "GeneralGrid1")
    st.session_state.setdefault("timer_running", False)
    st.session_state.setdefault("timer_start_time", None)
    st.session_state.setdefault("elapsed_accum", 0.0)

    persist_tasks()


def cache_today_tasks() -> None:
    """Remember today's task selection in cache.json, keyed by today's date."""
    cache_tasks(st.session_state.today_tasks)


def persist_tasks() -> None:
    """Write the full task list back to tasklist.json."""
    save_tasks(st.session_state.tasks)


def regenerate_today_tasks() -> None:
    """Compute today's task selection from scratch, keeping already-completed ones.

    This is the ONLY place the selector (`compute_daily_tasks`, via
    `load_today_tasks`) is ever invoked — bound to the "Regenerate" /
    "Generate today's list" button, never triggered implicitly by a
    rerun. Writes the result to cache.json via `cache_today_tasks()`,
    which is what lets every other session/tab pick up the change on
    their next rerun via `_sync_today_tasks` without recomputing anything
    themselves.
    """
    tasks = st.session_state.tasks
    daily_limit = st.session_state.daily_limit
    show_completed = load_show_completed()
    show_rescheduled = load_show_rescheduled()
    allow_future_tasks = load_allow_future_tasks()

    today_tasks = load_today_tasks(
        tasks, daily_limit, show_completed, show_rescheduled,
        allow_future_tasks=allow_future_tasks,
    )

    st.session_state.today_tasks = today_tasks
    st.session_state.today_generated = True
    st.session_state.active_duration = sum(t.duration for t in today_tasks)
    st.session_state.nb_today_task = len(today_tasks)

    cache_today_tasks()
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
    cache_today_tasks()
    persist_tasks()
    reload_today_grid()


def remove_tasks(task_ids: list[int]) -> None:
    """Remove tasks by id from both the full list and today's list, then persist."""
    st.session_state.tasks = remove_tasks_by_id(st.session_state.tasks, task_ids)
    st.session_state.today_tasks = remove_tasks_by_id(st.session_state.today_tasks, task_ids)
    cache_today_tasks()
    persist_tasks()
    reload_today_grid()