import os
from datetime import datetime

import streamlit as st

from TT_json_utils import load_daily_limit, read_tasks, save_daily_limit, write_tasks
from TT_task import TT_Task
from TT_task_selector import compute_daily_tasks
from TT_utils import normalize_date

TASKFILE = os.path.join(os.path.dirname(__file__), 'tasklist.json')
TODAY = normalize_date(datetime.now())


@st.cache_resource(show_spinner=False)
def init_task_list(include_completed_today: bool = False):
    print("Initializing task lists")
    daily_limit = load_daily_limit()
    tasks = read_tasks(TASKFILE)
    today_tasks = compute_daily_tasks(tasks, TODAY, daily_limit, include_completed_today)
    save_tasks(tasks)
    return tasks, today_tasks, daily_limit


def save_tasks(tasks: list[TT_Task]):
    print(f"Saving tasks to {TASKFILE}")
    write_tasks(TASKFILE, tasks)


def add_more_tasks():
    print("Adding more tasks")
    init_task_list.clear()
    st.session_state.tasks, st.session_state.today_tasks, st.session_state.daily_limit = init_task_list(True)


def force_grid_reload():
    print("Forcing grid reload")
    st.session_state.grid_key = f'TodayGrid{datetime.now().timestamp()}'


def discard_completed_tasks():
    print("Discarding completed tasks")
    completed_tasks = [task for task in st.session_state.today_tasks if task.is_task_completed(TODAY)]
    if not completed_tasks:
        return

    for task in completed_tasks:
        task.reset_and_update(TODAY)

    st.session_state.today_tasks = [task for task in st.session_state.today_tasks if task not in completed_tasks]
    save_tasks(st.session_state.tasks)
    force_grid_reload()


def clean_cache():
    print("Clearing cache")
    st.cache_resource.clear()
    st.session_state.clear()


def ensure_session_state(tasks, today_tasks, daily_limit):
    st.session_state.setdefault("tasks", tasks)
    st.session_state.setdefault("today_tasks", today_tasks)
    st.session_state.setdefault("daily_limit", daily_limit)
    st.session_state.setdefault("grid_key", 'TodayGrid1')
    st.session_state.setdefault("manage_grid_key", 'ManageGrid1')
    st.session_state.setdefault("timer_running", False)
    st.session_state.setdefault("timer_start_time", None)
    st.session_state.setdefault("elapsed_accum", 0.0)  # accumulated seconds before pause

__all__ = [
    'TASKFILE',
    'TODAY',
    'add_more_tasks',
    'clean_cache',
    'discard_completed_tasks',
    'ensure_session_state',
    'force_grid_reload',
    'init_task_list',
    'save_daily_limit',
    'save_tasks',
]
