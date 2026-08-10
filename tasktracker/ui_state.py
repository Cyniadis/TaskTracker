"""Streamlit session-state wiring.

This is the only module allowed to touch `st.session_state` directly for
task data — UI modules call these functions instead of poking at state
themselves, which keeps the "what happens when I click this" logic in
one place.
"""
from __future__ import annotations

from datetime import datetime
from datetime import date

import streamlit as st

from common.consts import today
from onetime.onetime_json_utils import load_onetime_tasks, save_onetime_tasks
from .tt_json_utils import (
    cache_tasks,
    load_cached_daily_limit,
    load_cached_task_ids,
    load_show_completed,
    load_show_rescheduled,
    load_tasks,
    save_tasks
)
from tasktracker.change_tracking_task import snapshot_tasks, load_task_baseline
from .selector import compute_daily_tasks
from common.common_utils import normalize_date
from .task_list_ops import (
    get_daily_task_list,
    get_manually_rescheduled_task_list,
    get_scheduled_task_list,
    initialize_tasks,
)
from .task import Task

@st.cache_resource(show_spinner=False)
def _init_general_task_list() -> list[Task]:
    """Load tasks from disk once per app session and run the daily housekeeping pass.

    Cached with `st.cache_resource` so a Streamlit rerun (which happens on
    every widget interaction) doesn't re-read/re-process the file each time —
    only a fresh process (or an explicit `reset_app()`) does.
    """
    tasks = load_tasks()
    initialize_tasks(tasks)
    save_tasks(tasks)
    # Refresh the change-tracking baseline to match this fresh load — this is
    # the "since the last full reload" reference point the old orig_* fields
    # used to capture, now living in its own durable file instead of on the
    # Task objects themselves. See tasktracker/change_tracking.py.
    snapshot_tasks(tasks)
    return tasks


@st.cache_resource(show_spinner=False)
def _init_onetime_task_list() -> list[Task]:
    """Load one-time (no-frequency) tasks from disk once per app session.

    No housekeeping pass here, unlike `_init_general_task_list` — one-time
    tasks have no frequency, so there's nothing to roll over. See
    onetime/onetime_tab.py and get_scheduled_task_list() for how they reach
    the Today list.
    """
    return load_onetime_tasks()


def _sync_today_tasks(
    tasks: list[Task], onetime_tasks: list[Task], show_completed: bool, show_rescheduled: bool,
) -> tuple[list[Task], bool]:
    """Derive today's task list purely from what's persisted on disk.

    Recurring tasks come from cache.json (never invokes the selector — just
    reads cache.json and filters `tasks` against the cached ids). One-time
    tasks are handled separately: they're never written to cache.json, so
    they're always re-derived fresh from `onetime_tasks` via
    get_scheduled_task_list() — a one-time task stays on Today from the
    moment it's scheduled until its row is deleted, with no daily-date
    gating (see task_list_ops.get_scheduled_task_list's docstring).

    If cache.json's date doesn't match today (never generated yet, or day
    rolled over), the recurring list resets, but a still-scheduled one-time
    task is unaffected — it's not tied to cache.json's date at all.
    """
    cache_date, cached_task_ids = load_cached_task_ids()
    current_date = today()
    onetime_scheduled = get_scheduled_task_list(onetime_tasks)

    if normalize_date(cache_date) != current_date:
        for task in tasks: 
            task.reset_state()
        today_tasks = filter_today_tasks(tasks, onetime_scheduled, show_completed, show_rescheduled)
        return today_tasks, bool(onetime_scheduled)

    cached_ids = set(cached_task_ids or [])
    today_tasks = [t for t in tasks if t.id in cached_ids] + onetime_scheduled
    today_tasks = filter_today_tasks(tasks, today_tasks, show_completed, show_rescheduled)
    
    return today_tasks, True


def filter_today_tasks(tasks: list[Task], today_tasks: list[Task], show_completed: bool = False, show_rescheduled: bool = False):
    completed_tasks = [t for t in tasks if t.is_completed()]
    rescheduled_tasks = [ t for t in tasks if t.is_manually_rescheduled() ]

    filtered_today_tasks = [ t for t in today_tasks if t not in completed_tasks and t not in rescheduled_tasks ]
    
    st.session_state.active_duration = sum([t.duration for t in filtered_today_tasks])
    st.session_state.nb_today_task = len(filtered_today_tasks)
    
    if show_completed: 
        filtered_today_tasks += completed_tasks
    if show_rescheduled:
        filtered_today_tasks += [ t for t in rescheduled_tasks if t not in filtered_today_tasks ]
    return filtered_today_tasks
    
def init_session_state() -> None:
    """Set up (or refresh) all Streamlit session state the app depends on.

    Runs on every rerun — no "already initialized" guard. Today's task
    list is always re-derived from cache.json/onetime_tasks via
    `_sync_today_tasks`, never recomputed here, so this stays cheap
    regardless of how often it's called and regardless of what
    session/tab/process is calling it.
    """
    tasks = _init_general_task_list()
    onetime_tasks = _init_onetime_task_list()
    daily_limit = load_cached_daily_limit()
    show_completed = load_show_completed()
    show_rescheduled = load_show_rescheduled()

    st.session_state.active_duration = 0
    st.session_state.nb_today_task = 0
    
    today_tasks, today_generated = _sync_today_tasks(tasks, onetime_tasks, show_completed, show_rescheduled)

    st.session_state.tasks = tasks
    st.session_state.onetime_tasks = onetime_tasks
    st.session_state.today_tasks = today_tasks
    st.session_state.today_generated = today_generated
    st.session_state.task_baseline = load_task_baseline(tasks)
    
    st.session_state.daily_limit = daily_limit
    st.session_state.show_completed = show_completed

    # Pure session-local UI state — setdefault so mid-session values (timer
    # running, grid keys) survive reruns, but a genuinely fresh session
    # still gets sane defaults.
    st.session_state.setdefault("today_grid_key", "TodayGrid1")
    st.session_state.setdefault("general_grid_key", "GeneralGrid1")
    st.session_state.setdefault("onetime_grid_key", "OnetimeGrid1")
    st.session_state.setdefault("timer_running", False)
    st.session_state.setdefault("timer_start_time", None)
    st.session_state.setdefault("timer_elapsed_accum", 0.0)

    persist_tasks()


def cache_today_tasks() -> None:
    """Remember today's task selection in cache.json, keyed by today's date."""
    cache_tasks(st.session_state.today_tasks)


def persist_tasks() -> None:
    """Write the full task list back to tasklist.json."""
    save_tasks(st.session_state.tasks)


def persist_onetime_tasks() -> None:
    """Write the full one-time task list back to onetime_tasks.json."""
    save_onetime_tasks(st.session_state.onetime_tasks)


def regenerate_today_tasks() -> None:
    """Compute today's task selection from scratch, keeping already-completed ones.

    This is the ONLY place the selector (`compute_daily_tasks`, via
    `load_today_tasks`) is ever invoked — bound to the "Regenerate" /
    "Generate today's list" button, never triggered implicitly by a
    rerun. Writes the result to cache.json via `cache_today_tasks()`,
    which is what lets every other session/tab pick up the change on
    their next rerun via `_sync_today_tasks` without recomputing anything
    themselves.

    Tasks manually scheduled for today are always passed in as
    `pre_selected_tasks`, so they survive regeneration regardless of the
    daily time budget (see Task.manually_reschedule). One-time tasks that
    have been scheduled (via onetime/onetime_tab.py) are folded in the same
    way, so their duration also eats into the remaining budget for
    recurring tasks — see task_list_ops.get_scheduled_task_list.
    """
    tasks = st.session_state.tasks
    onetime_tasks = st.session_state.onetime_tasks
    daily_limit = st.session_state.daily_limit
    current_date = today()

    daily_tasks = get_daily_task_list(tasks)
    manually_scheduled = get_manually_rescheduled_task_list(tasks)
    onetime_scheduled = get_scheduled_task_list(onetime_tasks)
    pre_selected_tasks = list(set(daily_tasks + manually_scheduled)) + onetime_scheduled
    
    today_tasks = compute_daily_tasks(
        tasks, current_date, daily_limit,
        pre_selected_tasks=pre_selected_tasks
    )

    st.session_state.today_tasks = today_tasks
    st.session_state.today_generated = True

    cache_today_tasks()
    persist_tasks()
    persist_onetime_tasks()


def reload_today_grid() -> None:
    """Force the 'Today' data grid to remount by giving it a fresh widget key."""
    st.session_state.today_grid_key = f"TodayGrid{datetime.now().timestamp()}"


def reload_general_grid() -> None:
    """Force the 'General' data grid to remount by giving it a fresh widget key."""
    st.session_state.general_grid_key = f"GeneralGrid{datetime.now().timestamp()}"


def reload_onetime_grid() -> None:
    """Force the 'One-time' data grid to remount by giving it a fresh widget key."""
    st.session_state.onetime_grid_key = f"OnetimeGrid{datetime.now().timestamp()}"


def reset_app() -> None:
    """Clear all cached resources and session state (used after importing a new task file)."""
    st.cache_resource.clear()
    st.session_state.clear()


def add_task(task: Task) -> None:
    """Append a new task, persist it, and refresh the 'General' grid."""
    st.session_state.tasks.append(task)
    persist_tasks()
    # reload_general_grid()


def add_onetime_task(task: Task) -> None:
    """Append a new one-time task and persist it."""
    st.session_state.onetime_tasks.append(task)
    persist_onetime_tasks()


def schedule_task_for(task: Task, date: datetime.date) -> None:
    """Manually add a task to today's list, ignoring the daily time budget."""
    task.manually_reschedule(date)
    if task not in st.session_state.today_tasks:
        st.session_state.today_tasks.append(task)
    cache_today_tasks()
    persist_tasks()
    persist_onetime_tasks()
    reload_today_grid()


def schedule_onetime_task_for(task: Task, date: datetime.date) -> None:
    """Flag a one-time task as scheduled for today.

    This is the ONLY way a one-time task ever reaches the Today list —
    unlike recurring tasks, it never becomes "eligible" on its own. Once
    scheduled it stays flagged (see task.manually_reschedule /
    task_list_ops.get_scheduled_task_list) until its row is deleted via
    remove_onetime_tasks().
    """
    task.manually_reschedule(date)
    if task not in st.session_state.today_tasks:
        st.session_state.today_tasks.append(task)
    persist_onetime_tasks()
    reload_today_grid()
    

def update_done_date(task: Task, date: datetime.date) -> None:
    """Manually add a task to today's list, ignoring the daily time budget."""
    task.set_done_date(date)
    task.set_next_due_date(date)
    cache_today_tasks()
    persist_tasks()
    persist_onetime_tasks()


def remove_tasks(task_ids: list[str]) -> None:
    """Remove tasks by id from both the full list and today's list, then persist."""
    if len(task_ids) == 0:
        return
    # Mutate inplace to bypass the cache from _init_general_task_list()
    st.session_state.tasks[:] = [t for t in st.session_state.tasks if t.id not in task_ids]
    st.session_state.today_tasks[:] = [t for t in st.session_state.today_tasks if t.id not in task_ids]
    cache_today_tasks()
    persist_tasks()
    reload_today_grid()


def remove_onetime_tasks(task_ids: list[str]) -> None:
    """Remove one-time tasks by id from both the library and today's list.

    This is the only thing that makes a one-time task disappear from
    Today once it's been scheduled — see schedule_onetime_task_for's
    docstring.
    """
    if len(task_ids) == 0:
        return
    st.session_state.onetime_tasks[:] = [t for t in st.session_state.onetime_tasks if t.id not in task_ids]
    st.session_state.today_tasks[:] = [t for t in st.session_state.today_tasks if t.id not in task_ids]
    persist_onetime_tasks()
    reload_today_grid()


def cancel_task(task: Task) -> None:
    """Cancel a task (remove its due date, so it won't be selected for today)."""
    task.cancel()
    cache_today_tasks()
    persist_tasks()
    persist_onetime_tasks()
