"""Unit tests for common.change_tracking (generic baseline/diff machinery)
and tasktracker.change_tracking_task (the Task-specific wrapper around it).

This replaces the old Task.restore()/get_changes() tests that used to live
directly in test_task.py — those methods moved off Task entirely and into
this generic, file-backed module (see change_tracking.py's docstring for
why), but nothing tested the new module directly until now.
"""
from __future__ import annotations

from datetime import date

import pytest

from common import change_tracking
from tasktracker import change_tracking_task
from tasktracker.change_tracking_task import (
    discard_task_changes,
    load_task_baseline,
    snapshot_tasks,
    task_changes,
)


@pytest.fixture
def task_baseline_file(tmp_path, monkeypatch):
    """Redirect TASK_BASELINE_FILE at a throwaway file for this test.

    TASK_BASELINE_FILE is imported by name into change_tracking_task.py
    (`from common.consts import TASK_BASELINE_FILE`), so that's the binding
    that has to be patched — patching common.consts.TASK_BASELINE_FILE
    itself would have no effect on the already-bound name in
    change_tracking_task's own namespace.
    """
    path = tmp_path / "task_baseline.json"
    monkeypatch.setattr(change_tracking_task, "TASK_BASELINE_FILE", path)
    return path


# ---------------------------------------------------------------------------
# tasktracker.change_tracking_task: task_changes / snapshot_tasks
# ---------------------------------------------------------------------------

class TestTaskChanges:
    def test_no_baseline_entry_returns_empty_list(self, make_task):
        """A task added after the last snapshot has nothing to diff against."""
        task = make_task()
        baseline = {}
        assert task_changes(task, baseline) == []

    def test_no_changes_returns_empty_list(self, make_task, task_baseline_file):
        task = make_task(name="Same")
        snapshot_tasks([task])
        baseline = load_task_baseline([task])
        assert task_changes(task, baseline) == []

    def test_name_change_is_reported(self, make_task, task_baseline_file):
        task = make_task(name="Old")
        snapshot_tasks([task])
        baseline = load_task_baseline([task])

        task.name = "New"
        diffs = task_changes(task, baseline)
        assert ("Name", "Old", "New") in diffs

    def test_priority_change_reports_formatted_numbers(self, make_task, task_baseline_file):
        task = make_task(priority=1.0)
        snapshot_tasks([task])
        baseline = load_task_baseline([task])

        task.priority = 2.5
        diffs = task_changes(task, baseline)
        assert ("Priority", "1.0", "2.5") in diffs

    def test_none_due_date_is_formatted_as_em_dash(self, make_task, task_baseline_file):
        task = make_task(due_date=None)
        snapshot_tasks([task])
        baseline = load_task_baseline([task])

        task.set_due_date(date(2026, 7, 21))
        diffs = dict((label, (old, new)) for label, old, new in task_changes(task, baseline))
        assert diffs["Due date"][0] == "—"

    def test_multiple_changed_fields_all_reported(self, make_task, task_baseline_file):
        task = make_task(name="Old", duration=10)
        snapshot_tasks([task])
        baseline = load_task_baseline([task])

        task.name = "New"
        task.duration = 20
        labels = {label for label, _, _ in task_changes(task, baseline)}
        assert labels == {"Name", "Duration"}

    def test_manually_reschedule_is_reported_as_a_due_date_change(self, make_task, task_baseline_file):
        """due_date_state itself isn't in _LABELS, but manually_reschedule()
        changes due_date as a side effect, and due_date IS diffable — so
        this legitimately shows up as a 'Due date' change (and reverting it
        via discard_task_changes() puts due_date back, though not the
        due_date_state flag — see Task.apply_snapshot()'s docstring)."""
        task = make_task(due_date=None)
        snapshot_tasks([task])
        baseline = load_task_baseline([task])

        task.manually_reschedule(date(2026, 7, 21))
        diffs = dict((label, (old, new)) for label, old, new in task_changes(task, baseline))
        assert diffs["Due date"] == ("—", "2026-07-21")


class TestDiscardTaskChanges:
    def test_reverts_edited_fields_to_the_baseline(self, make_task, task_baseline_file):
        task = make_task(name="Old", duration=10, priority=1.0)
        snapshot_tasks([task])
        baseline = load_task_baseline([task])

        task.name = "New"
        task.duration = 99
        task.priority = 9.0

        assert discard_task_changes(task, baseline) is True
        assert task.name == "Old"
        assert task.duration == 10
        assert task.priority == 1.0

    def test_returns_false_when_task_has_no_baseline_entry(self, make_task):
        """A task added after the last snapshot has nothing to discard to."""
        task = make_task(name="Brand new")
        assert discard_task_changes(task, {}) is False
        assert task.name == "Brand new"  # left untouched

    def test_discard_after_cancel_restores_due_date_but_not_due_date_state(self, make_task, task_baseline_file):
        """Known edge case, not a bug fix: Task.apply_snapshot() explicitly
        documents that it doesn't touch due_date_state ('per-day markers,
        not edits a user would want to discard'). That means discarding
        after a cancel() can leave a task with due_date_state=CANCELLED but
        a restored, non-null due_date — worth knowing about since
        task_list_ops assumes cancelled tasks always have due_date is None."""
        task = make_task(due_date=date(2026, 7, 21))
        snapshot_tasks([task])
        baseline = load_task_baseline([task])

        task.cancel()
        discard_task_changes(task, baseline)

        assert task.due_date == date(2026, 7, 21)  # restored
        assert task.is_cancelled() is True  # ...but the flag survived the discard


class TestSnapshotAndLoadBaseline:
    def test_ensure_baseline_creates_the_file_on_first_run(self, make_task, task_baseline_file):
        task = make_task(name="First run")
        assert not task_baseline_file.exists()

        baseline = load_task_baseline([task])

        assert task_baseline_file.exists()
        assert baseline[task.id]["name"] == "First run"

    def test_snapshot_overwrites_the_previous_baseline(self, make_task, task_baseline_file):
        task = make_task(name="Old")
        snapshot_tasks([task])

        task.name = "New"
        snapshot_tasks([task])  # simulates a fresh reload

        baseline = change_tracking.load_baseline(task_baseline_file)
        assert baseline[task.id]["name"] == "New"
        assert task_changes(task, baseline) == []
