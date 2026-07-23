"""Unit tests for tasktracker.task_list_ops."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from tasktracker import task_list_ops
from tasktracker.task_list_ops import (
    find_task_by_id,
    next_task_id,
    remove_tasks_by_id,
    restore_tasks,
    update_tasks_priority_and_due_date,
)

TODAY = date(2026, 7, 21)


class TestFindTaskById:
    def test_finds_existing_task(self, make_task):
        tasks = [make_task(id=1), make_task(id=2), make_task(id=3)]
        found = find_task_by_id(tasks, 2)
        assert found.id == 2

    def test_raises_key_error_when_not_found(self, make_task):
        tasks = [make_task(id=1)]
        with pytest.raises(KeyError):
            find_task_by_id(tasks, 999)

    def test_raises_key_error_on_empty_list(self):
        with pytest.raises(KeyError):
            find_task_by_id([], 0)


class TestNextTaskId:
    def test_returns_max_plus_one(self, make_task):
        tasks = [make_task(id=0), make_task(id=5), make_task(id=2)]
        assert next_task_id(tasks) == 6

    def test_returns_zero_for_empty_list(self):
        assert next_task_id([]) == 0

    def test_handles_single_task(self, make_task):
        assert next_task_id([make_task(id=10)]) == 11

    def test_ignores_gaps_in_ids(self, make_task):
        tasks = [make_task(id=0), make_task(id=100)]
        assert next_task_id(tasks) == 101


class TestRemoveTasksById:
    def test_removes_matching_ids(self, make_task):
        tasks = [make_task(id=1), make_task(id=2), make_task(id=3)]
        result = remove_tasks_by_id(tasks, [2])
        assert [t.id for t in result] == [1, 3]

    def test_removes_multiple_ids(self, make_task):
        tasks = [make_task(id=1), make_task(id=2), make_task(id=3)]
        result = remove_tasks_by_id(tasks, [1, 3])
        assert [t.id for t in result] == [2]

    def test_no_matching_ids_returns_full_list_unchanged(self, make_task):
        tasks = [make_task(id=1), make_task(id=2)]
        result = remove_tasks_by_id(tasks, [999])
        assert [t.id for t in result] == [1, 2]

    def test_returns_new_list_does_not_mutate_original(self, make_task):
        tasks = [make_task(id=1), make_task(id=2)]
        result = remove_tasks_by_id(tasks, [1])
        assert len(tasks) == 2  # original untouched
        assert len(result) == 1

    def test_empty_task_ids_list_removes_nothing(self, make_task):
        tasks = [make_task(id=1), make_task(id=2)]
        result = remove_tasks_by_id(tasks, [])
        assert len(result) == 2


class TestRestoreTasks:
    def test_restores_every_task_in_place(self, make_task):
        t1 = make_task(id=1, name="Old1")
        t2 = make_task(id=2, name="Old2")
        t1.name = "New1"
        t2.name = "New2"

        restore_tasks([t1, t2])

        assert t1.name == "Old1"
        assert t2.name == "Old2"

    def test_empty_list_is_a_no_op(self):
        restore_tasks([])  # should not raise


# ---------------------------------------------------------------------------
# update_tasks_priority_and_due_date
# ---------------------------------------------------------------------------

class TestUpdateTasksPriorityAndDueDate:
    """Covers the housekeeping pass: for any task whose due date has already
    passed, either bump its priority (missed) or roll its due date forward
    (completed on time). Uses `today()` internally, so it's monkeypatched
    for determinism."""

    @pytest.fixture(autouse=True)
    def _freeze_today(self, monkeypatch):
        monkeypatch.setattr(task_list_ops, "today", lambda: TODAY)

    def test_overdue_and_never_completed_gets_priority_bumped(self, make_task):
        task = make_task(due_date=TODAY - timedelta(days=1), done_date=None, priority=2.0)
        update_tasks_priority_and_due_date([task])
        assert task.priority == 2.5

    def test_overdue_and_completed_on_a_different_day_gets_priority_bumped(self, make_task):
        task = make_task(due_date=TODAY - timedelta(days=1), done_date=TODAY - timedelta(days=5), priority=2.0)
        update_tasks_priority_and_due_date([task])
        assert task.priority == 2.5

    def test_completed_exactly_on_its_due_date_rolls_due_date_forward(self, make_task):
        due = TODAY - timedelta(days=1)
        task = make_task(frequency="1xsemaine", due_date=due, done_date=due, priority=2.0)
        update_tasks_priority_and_due_date([task])
        assert task.due_date == task.compute_next_due_date(due)
        assert task.priority == 2.0  # unchanged

    def test_due_date_rolls_forward_from_the_due_date_not_from_today(self, make_task):
        # compute_next_due_date is based on the *due date*, not today() —
        # this pins that behavior since it's easy to accidentally flip.
        due = TODAY - timedelta(days=10)
        task = make_task(frequency="1xsemaine", due_date=due, done_date=due)
        update_tasks_priority_and_due_date([task])
        assert task.due_date == due + timedelta(days=7)

    def test_task_due_today_is_left_untouched(self, make_task):
        task = make_task(due_date=TODAY, done_date=None, priority=3.0)
        update_tasks_priority_and_due_date([task])
        assert task.priority == 3.0
        assert task.due_date == TODAY

    def test_task_due_in_the_future_is_left_untouched(self, make_task):
        task = make_task(due_date=TODAY + timedelta(days=3), done_date=None, priority=3.0)
        update_tasks_priority_and_due_date([task])
        assert task.priority == 3.0

    def test_task_without_a_due_date_is_left_untouched(self, make_task):
        task = make_task(due_date=None, done_date=TODAY, priority=3.0)
        update_tasks_priority_and_due_date([task])
        assert task.priority == 3.0
        assert task.due_date is None

    def test_never_completed_overdue_task_is_treated_as_missed(self, make_task):
        # done_date is None entirely (not just "not on due date") — still counts as missed.
        task = make_task(due_date=TODAY - timedelta(days=30), done_date=None, priority=1.0)
        update_tasks_priority_and_due_date([task])
        assert task.priority == 1.5

    def test_empty_list_is_a_no_op(self):
        update_tasks_priority_and_due_date([])  # should not raise

    def test_processes_multiple_tasks_independently(self, make_task):
        missed = make_task(id=1, due_date=TODAY - timedelta(days=1), done_date=None, priority=1.0)
        on_time = make_task(id=2, due_date=TODAY - timedelta(days=1), done_date=TODAY - timedelta(days=1), priority=1.0)
        untouched = make_task(id=3, due_date=TODAY + timedelta(days=1), done_date=None, priority=1.0)

        update_tasks_priority_and_due_date([missed, on_time, untouched])

        assert missed.priority == 1.5
        assert on_time.priority == 1.0
        assert on_time.due_date == on_time.compute_next_due_date(TODAY - timedelta(days=1))
        assert untouched.priority == 1.0
        assert untouched.due_date == TODAY + timedelta(days=1)
