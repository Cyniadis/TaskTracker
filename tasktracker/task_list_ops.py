"""Pure operations on lists of Task objects — no Streamlit, no I/O.

Anything that just needs a `list[Task]` (and maybe an id) to do its job
belongs here, as opposed to `selector.py` (which is specifically about
picking which tasks belong on "today") or the `ui/` package (which owns
Streamlit session state and widgets).
"""
from __future__ import annotations

from .task import Period, Task, TaskDueDateState, TaskState
from common.consts import today

from datetime import datetime

def find_task_by_id(tasks: list[Task], task_id: str) -> Task:
    """Return the task with `id == task_id`, or raise KeyError if not found."""
    for task in tasks:
        if task.id == task_id:
            return task
    raise KeyError(f"No task with id={task_id}")


def remove_tasks_by_id(tasks: list[Task], task_ids: list[str]) -> list[Task]:
    """Return a new list with every task whose id is in `task_ids` filtered out."""
    ids_to_remove = set(task_ids)
    return [t for t in tasks if t.id not in ids_to_remove]


def initialize_tasks(tasks: list[Task]) -> None:
    """Housekeeping pass, meant to be called once before `compute_daily_tasks`.

    For every task whose due date has already passed:
    - if it was *not* completed on that due date (including tasks that have
      never been completed at all — `done_date` may be `None`), bump its
      priority so it surfaces sooner next time;
    - if it *was* completed on time, roll its due date forward to the next
      occurrence.

    Tasks with no due date, or a due date that's today or in the future,
    are left untouched — they haven't missed their window yet. Cancelled
    tasks always have `due_date is None` (see Task.cancel()), so they're
    naturally skipped here too — no special-casing needed.
    """
    current_date = today()
    for task in tasks:
        if not task.due_date or task.due_date >= current_date:
            continue
        if task.is_completed_on(task.due_date):
            task.set_next_due_date()
        else:
            task.increment_priority()

def set_due_date_task_list(tasks: list[Task], date: datetime.date):
    for task in tasks:
        task.set_due_date(date)


def get_daily_task_list(tasks: list[Task]):
    return [ task for task in tasks if task.frequency_obj.period == Period.DAY ]

def get_manually_rescheduled_task_list(tasks: list[Task]):  
    return [ task for task in tasks if task.is_manually_rescheduled_on_today() ]


def get_scheduled_task_list(tasks: list[Task]) -> list[Task]:
    """Tasks flagged manually-rescheduled, regardless of which day they were
    scheduled for. Used for one-time tasks: unlike recurring tasks, they have
    no daily housekeeping pass to reset this flag, so once scheduled they
    stay on the Today list until the task itself is deleted (see
    onetime/onetime_tab.py and tasktracker/ui_state.py)."""
    return [task for task in tasks if task.is_manually_rescheduled()]
