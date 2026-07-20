"""Streamlit session-state wiring.

This is the only module allowed to touch `st.session_state` directly for
task data — UI modules call these functions instead of poking at state
themselves, which keeps the "what happens when I click this" logic in
one place.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from ..json_utils import load_cached_daily_limit, load_tasks, save_tasks, cache_tasks, load_cached_task_ids, load_show_completed, load_show_rescheduled
from ..selector import compute_daily_tasks, update_tasks_priority_and_due_date
from ..consts import TODAY
from ..task import Task, normalize_date, schedule_task_list

@st.cache_resource(show_spinner=False)
def _init_general_task_list() -> tuple[list[Task], list[Task], int]:
    print("Initialize tasks lists")
    tasks = load_tasks()
    update_tasks_priority_and_due_date(tasks)
    save_tasks(tasks)
    return tasks


def load_today_tasks(tasks: list[Task], daily_limit: int, show_completed=False, show_rescheduled=False, force_regeneration=False) -> list[Task]: 
    cache_date, cached_task_ids = load_cached_task_ids()
    
    today_tasks = []
    completed_tasks = [t for t in tasks if t.is_completed_on(TODAY)] if show_completed else []
    rescheduled_tasks = [ t for t in tasks if any(diff[0] == "Due date" for diff in t.get_changes()) ] if show_rescheduled else []
    
    if force_regeneration or normalize_date(cache_date) != TODAY: 
        today_tasks = compute_daily_tasks(tasks, TODAY, daily_limit)
    else: 
        cached_tasks = [t for t in tasks if t.id in cached_task_ids ] 
        today_tasks = compute_daily_tasks(tasks, TODAY, daily_limit, cached_tasks)
    
    today_tasks += [ t for t in completed_tasks if t.id not in today_tasks ]
    today_tasks += [ t for t in rescheduled_tasks if t.id not in today_tasks ]
    return today_tasks
        

def init_session_state(force_regeneration=False) -> None:
    """Populate `st.session_state` on first run; a no-op on later reruns."""
    # if "tasks" in st.session_state:
    #     return

    print("Initialize session state")
    tasks = _init_general_task_list()
    daily_limit = load_cached_daily_limit()
    show_completed = load_show_completed()
    show_rescheduled = load_show_rescheduled()
    today_tasks = load_today_tasks(tasks, daily_limit, show_completed, show_rescheduled, force_regeneration)

    st.session_state.update(
        tasks=tasks,
        today_tasks=today_tasks,
        daily_limit=daily_limit,
        today_grid_key="TodayGrid1",
        general_grid_key="GeneralGrid1",
        timer_running=False,
        timer_start_time=None,
        elapsed_accum=0.0,
        selected_rows=[],
        show_completed=show_completed
    )
    # cache_today_tasks()
    persist_tasks()

def cache_today_tasks():
    cache_tasks(st.session_state.today_tasks)
    

def persist_tasks() -> None:
    print("Save tasks")
    save_tasks(st.session_state.tasks)


def regenerate_today_tasks() -> None: 
    """Recompute today's task selection from scratch, keeping already-completed ones."""
    # _init_task_lists.clear()
    st.session_state[st.session_state.today_grid_key] =  {'selection': {'rows': []}}
    init_session_state(True)

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
    st.session_state.today_grid_key = f"TodayGrid{datetime.now().timestamp()}"


def reload_general_grid() -> None:
    st.session_state.general_grid_key = f"GeneralGrid{datetime.now().timestamp()}"


def reset_app() -> None:
    st.cache_resource.clear()
    st.session_state.clear()


def next_task_id() -> int:
    tasks = st.session_state.tasks
    return max((t.id for t in tasks), default=-1) + 1


def add_task(task: Task) -> None:
    st.session_state.tasks.append(task)
    persist_tasks()
    reload_general_grid()


def schedule_task_for_today(task: Task) -> None:
    """Manually add a task to today's list, ignoring the daily time budget."""
    task.schedule_for(TODAY)
    if task not in st.session_state.today_tasks:
        st.session_state.today_tasks.append(task)
    persist_tasks()
    reload_today_grid()

def remove_tasks(task_ids: list[int]) -> None:
    """Remove tasks by id from both the full list and today's list, then persist."""
    ids_to_remove = set(task_ids)
    st.session_state.tasks = [t for t in st.session_state.tasks if t.id not in ids_to_remove]
    st.session_state.today_tasks = [t for t in st.session_state.today_tasks if t.id not in ids_to_remove]
    persist_tasks()
    reload_today_grid()


