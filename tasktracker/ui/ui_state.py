"""Streamlit session-state wiring.

This is the only module allowed to touch `st.session_state` directly for
task data — UI modules call these functions instead of poking at state
themselves, which keeps the "what happens when I click this" logic in
one place.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from .. import json_utils
from ..task import Task, normalize_date
from ..selector import compute_daily_tasks

TODAY = normalize_date(datetime.now())

@st.cache_resource(show_spinner=False)
def _load_task_lists(include_completed_today: bool = False) -> tuple[list[Task], list[Task], int]:
    daily_limit = json_utils.load_daily_limit()
    tasks = json_utils.load_tasks()
    today_tasks = compute_daily_tasks(tasks, TODAY, daily_limit, include_completed_today)
    json_utils.save_tasks(tasks)
    json_utils.create_tasks_backup(tasks)
    return tasks, today_tasks, daily_limit


def init_session_state() -> None:
    """Populate `st.session_state` on first run; a no-op on later reruns."""
    if "tasks" in st.session_state:
        return
    tasks, today_tasks, daily_limit = _load_task_lists()
    st.session_state.update(
        tasks=tasks,
        today_tasks=today_tasks,
        daily_limit=daily_limit,
        grid_key="TodayGrid1",
        manage_grid_key="ManageGrid1",
        timer_running=False,
        timer_start_time=None,
        elapsed_accum=0.0,
    )



def persist_tasks() -> None:
    json_utils.save_tasks(st.session_state.tasks)


def regenerate_today_tasks() -> None:
    """Recompute today's task selection from scratch, keeping already-completed ones."""
    _load_task_lists.clear()
    st.session_state.tasks, st.session_state.today_tasks, st.session_state.daily_limit = (
        _load_task_lists(True)
    )


def discard_completed_tasks() -> None:
    completed = [t for t in st.session_state.today_tasks if t.is_completed_on(TODAY)]
    if not completed:
        return

    for task in completed:
        task.reset_and_advance(TODAY)

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
