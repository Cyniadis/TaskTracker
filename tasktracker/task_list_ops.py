"""Pure operations on lists of Task objects — no Streamlit, no I/O.

Anything that just needs a `list[Task]` (and maybe an id) to do its job
belongs here, as opposed to `selector.py` (which is specifically about
picking which tasks belong on "today") or the `ui/` package (which owns
Streamlit session state and widgets).
"""
from __future__ import annotations

from .task import Task


def find_task_by_id(tasks: list[Task], task_id: int) -> Task:
    """Return the task with `id == task_id`, or raise KeyError if not found."""
    for task in tasks:
        if task.id == task_id:
            return task
    raise KeyError(f"No task with id={task_id}")


def next_task_id(tasks: list[Task]) -> int:
    """Return the next unused task id (max existing id + 1, or 0 if no tasks)."""
    return max((t.id for t in tasks), default=-1) + 1


def remove_tasks_by_id(tasks: list[Task], task_ids: list[int]) -> list[Task]:
    """Return a new list with every task whose id is in `task_ids` filtered out."""
    ids_to_remove = set(task_ids)
    return [t for t in tasks if t.id not in ids_to_remove]


def restore_tasks(tasks: list[Task]) -> None:
    """Revert every task in `tasks` to its last-persisted (orig_*) state, in place."""
    for task in tasks:
        task.restore()
