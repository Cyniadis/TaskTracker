"""Change-tracking for tasks: a thin, Task-specific layer over
common.change_tracking's generic baseline/diff machinery.

Powers the General tab's 'Changes' dialog and 'Discard all changes' button.
"""
from __future__ import annotations

from common.consts import TASK_BASELINE_FILE
from common.change_tracking import ensure_baseline, get_baseline_entry, get_changes, snapshot
from .task import Task

# Fields worth showing in the "Changes" diff / reverting on "Discard changes".
# `id` is the lookup key, not a diffable field. `state` (due_date_state /
# completed) is deliberately excluded too — but note that cancel() and
# manually_reschedule() both change `due_date` itself as a side effect, and
# `due_date` *is* diffable, so those actions still show up here as a
# "Due date" change (and get reverted by discard_task_changes(), via
# Task.apply_snapshot() — see its docstring for what it does and doesn't
# touch).
_LABELS = {
    "name": "Name",
    "frequency": "Frequency",
    "priority": "Priority",
    "initial_priority": "Initial priority",
    "duration": "Duration",
    "due_date": "Due date",
    "done_date": "Done date"
}


def snapshot_tasks(tasks: list[Task]) -> None:
    """Persist the current task list as the new change-tracking baseline.

    Call this whenever tasks are freshly loaded from tasklist.json (process
    start, reset_app(), import) — see ui_state._init_general_task_list().
    """
    snapshot(tasks, TASK_BASELINE_FILE, Task.to_dict)


def load_task_baseline(tasks: list[Task]) -> dict[int, dict]:
    """Load the baseline, creating it from `tasks` first if this is the very
    first run (no baseline file yet)."""
    return ensure_baseline(tasks, TASK_BASELINE_FILE, Task.to_dict)


def task_changes(task: Task, baseline: dict[int, dict]) -> list[tuple[str, str, str]]:
    """(label, old, new) for every field of `task` that differs from its
    baseline snapshot. Empty if nothing changed, or if `task` didn't exist
    yet at the last snapshot."""
    return get_changes(task.to_dict(), baseline, _LABELS)


def discard_task_changes(task: Task, baseline: dict[int, dict]) -> bool:
    """Revert `task` in place to its baseline snapshot.

    Returns False (no-op) if `task` has no baseline entry — e.g. it was
    added after the last snapshot, so there's nothing to discard to.
    """
    entry = get_baseline_entry(task.to_dict(), baseline)
    if entry is None:
        return False
    task.apply_snapshot(entry)
    return True
