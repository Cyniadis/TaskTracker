"""Streamlit session-state wiring.

This is the only module allowed to touch `st.session_state` directly for
task data — UI modules call these functions instead of poking at state
themselves, which keeps the "what happens when I click this" logic in
one place.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from ..json_utils import load_daily_limit, load_tasks, save_tasks, save_daily_limit, create_tasks_backup, load_tasks_backup
from ..selector import compute_daily_tasks, initialize_tasks
from ..consts import TODAY
from ..task import Task


@st.cache_resource(show_spinner=False)
def _init_task_lists(include_completed_today: bool = False) -> tuple[list[Task], list[Task], int]:
    print("Initialize tasks lists")
    daily_limit = load_daily_limit()
    tasks = load_tasks()
    initialize_tasks(tasks)
    today_tasks = compute_daily_tasks(tasks, TODAY, daily_limit, include_completed_today)
    save_tasks(tasks)
    return tasks, today_tasks, daily_limit


def init_session_state() -> None:
    """Populate `st.session_state` on first run; a no-op on later reruns."""
    if "tasks" in st.session_state:
        return

    print("Initialize session state")
    tasks, today_tasks, daily_limit = _init_task_lists()
    st.session_state.update(
        tasks=tasks,
        today_tasks=today_tasks,
        daily_limit=daily_limit,
        grid_key="TodayGrid1",
        manage_grid_key="ManageGrid1",
        timer_running=False,
        timer_start_time=None,
        elapsed_accum=0.0,
        selected_rows=[]
    )
    create_tasks_backup(tasks)


def persist_tasks() -> None:
    save_tasks(st.session_state.tasks)


def regenerate_today_tasks() -> None:
    """Recompute today's task selection from scratch, keeping already-completed ones."""
    _init_task_lists.clear()
    st.session_state.tasks, st.session_state.today_tasks, st.session_state.daily_limit = (
        _init_task_lists(True)
    )

def restore_tasks(tasks: list[Task]) -> None: 
    for task in tasks: 
        task.restore()

def discard_completed_tasks() -> None:
    completed = [t for t in st.session_state.today_tasks if t.is_completed_on(TODAY)]
    if not completed:
        return

    for task in completed:
        task.reset_and_advance()

    completed_ids = {t.id for t in completed}
    st.session_state.today_tasks = [
        t for t in st.session_state.today_tasks if t.id not in completed_ids
    ]
    persist_tasks()
    reload_today_grid()


def reload_today_grid() -> None:
    st.session_state.grid_key = f"TodayGrid{datetime.now().timestamp()}"


def reload_manage_grid() -> None:
    st.session_state.manage_grid_key = f"ManageGrid{datetime.now().timestamp()}"


def reset_app() -> None:
    st.cache_resource.clear()
    st.session_state.clear()


def next_task_id() -> int:
    tasks = st.session_state.tasks
    return max((t.id for t in tasks), default=-1) + 1


def add_task(task: Task) -> None:
    st.session_state.tasks.append(task)
    persist_tasks()
    reload_manage_grid()


def schedule_task_for_today(task: Task) -> None:
    """Manually add a task to today's list, ignoring the daily time budget."""
    task.schedule_for(TODAY)
    if task not in st.session_state.today_tasks:
        st.session_state.today_tasks.append(task)
    persist_tasks()
    reload_today_grid()
