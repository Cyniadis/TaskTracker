"""Unit tests for tasktracker.selector."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from tasktracker import selector
from tasktracker.selector import (
    Eligibility,
    _eligibility,
    _select_by_priority,
    compute_daily_tasks,
)


TODAY = date(2026, 7, 21)


# ---------------------------------------------------------------------------
# _eligibility
# ---------------------------------------------------------------------------

class TestEligibility:
    def test_done_today_is_not_eligible(self, make_task):
        task = make_task(done_date=TODAY, due_date=TODAY)
        assert _eligibility(task, TODAY) is Eligibility.NOT_ELIGIBLE

    def test_due_today_is_eligible(self, make_task):
        task = make_task(due_date=TODAY, done_date=None)
        assert _eligibility(task, TODAY) is Eligibility.ELIGIBLE

    def test_never_scheduled_or_done_is_maybe_eligible(self, make_task):
        task = make_task(due_date=None, done_date=None)
        assert _eligibility(task, TODAY) is Eligibility.MAYBE_ELIGIBLE

    def test_overdue_and_never_done_is_maybe_eligible(self, make_task):
        task = make_task(due_date=TODAY - timedelta(days=5), done_date=None)
        assert _eligibility(task, TODAY) is Eligibility.MAYBE_ELIGIBLE

    def test_due_in_future_and_never_done_is_not_eligible(self, make_task):
        task = make_task(due_date=TODAY + timedelta(days=1), done_date=None)
        assert _eligibility(task, TODAY) is Eligibility.NOT_ELIGIBLE

    def test_cancelled_task_is_not_eligible_even_if_overdue(self, make_task):
        task = make_task(due_date=TODAY - timedelta(days=5), done_date=None)
        task.cancel()
        assert _eligibility(task, TODAY) is Eligibility.NOT_ELIGIBLE

    def test_cancelled_task_is_excluded_from_compute_daily_tasks(self, make_task):
        cancelled = make_task(due_date=TODAY, done_date=None, duration=10)
        cancelled.cancel()
        kept = make_task(due_date=TODAY, done_date=None, duration=10)

        result = compute_daily_tasks([cancelled, kept], TODAY, daily_time_limit=60)

        assert cancelled not in result
        assert kept in result

    def test_overdue_but_recently_done_within_recurrence_window_is_eligible(self, make_task):
        # 1xsemaine (7 days) task done 3 days ago and due date in the past -> still within window
        task = make_task(frequency="1xsemaine", due_date=TODAY - timedelta(days=1), done_date=TODAY - timedelta(days=3))
        assert _eligibility(task, TODAY) is Eligibility.ELIGIBLE

    def test_overdue_and_done_outside_recurrence_window_is_not_eligible(self, make_task):
        # 1xjour (1 day) task done 10 days ago -> window elapsed, so become eligible instead?
        # Actually per logic: days_since_done >= frequency.days -> NOT_ELIGIBLE
        task = make_task(frequency="1xjour", due_date=TODAY - timedelta(days=10), done_date=TODAY - timedelta(days=10))
        assert _eligibility(task, TODAY) is Eligibility.NOT_ELIGIBLE

    def test_due_date_in_past_no_done_date_at_all_is_maybe_eligible(self, make_task):
        task = make_task(due_date=TODAY - timedelta(days=100), done_date=None)
        assert _eligibility(task, TODAY) is Eligibility.MAYBE_ELIGIBLE


# ---------------------------------------------------------------------------
# _select_by_priority (0/1 knapsack)
# ---------------------------------------------------------------------------

class TestSelectByPriority:
    def test_selects_all_tasks_that_fit(self, make_task):
        tasks = [make_task(duration=10, priority=1), make_task(duration=10, priority=2)]
        selected = _select_by_priority(tasks, time_budget=30)
        assert {t.id for t in selected} == {'0', '1'}

    def test_prefers_higher_priority_when_budget_is_tight(self, make_task):
        tasks = [
            make_task(duration=10, priority=1.0),
            make_task(duration=10, priority=5.0),
        ]
        selected = _select_by_priority(tasks, time_budget=10)
        assert [t.id for t in selected] == ['1']

    def test_maximizes_total_duration_within_budget(self, make_task):
        # Two low-priority tasks (10+10=20) fit better than one high-priority task (15)
        # within a 20-minute budget, but the knapsack favors total duration used.
        tasks = [
            make_task(duration=10, priority=1.0),
            make_task(duration=10, priority=1.0),
            make_task(duration=15, priority=10.0),
        ]
        selected = _select_by_priority(tasks, time_budget=20)
        total_duration = sum(t.duration for t in selected)
        assert total_duration == 20
        assert {t.id for t in selected} == {'0', '1'}

    def test_empty_task_list_returns_empty(self):
        assert _select_by_priority([], time_budget=60) == []

    def test_zero_budget_selects_nothing(self, make_task):
        tasks = [make_task(duration=5)]
        assert _select_by_priority(tasks, time_budget=0) == []

    def test_task_larger_than_budget_is_excluded(self, make_task):
        tasks = [make_task(duration=100, priority=10)]
        assert _select_by_priority(tasks, time_budget=10) == []

    def test_result_never_exceeds_budget(self, make_task):
        tasks = [make_task(duration=7, priority=i) for i in range(1, 10)]
        selected = _select_by_priority(tasks, time_budget=22)
        assert sum(t.duration for t in selected) <= 22

# ---------------------------------------------------------------------------
# compute_daily_tasks (integration of the above)
# ---------------------------------------------------------------------------

class TestComputeDailyTasks:
    def test_all_eligible_tasks_fit_within_budget(self, make_task):
        tasks = [make_task(duration=10, due_date=TODAY), make_task(duration=10, due_date=TODAY)]
        result = compute_daily_tasks(tasks, TODAY, daily_time_limit=60)
        assert {t.id for t in result} == {'0', '1'}

    def test_knapsack_kicks_in_when_over_budget(self, make_task):
        tasks = [
            make_task(duration=30, due_date=TODAY, priority=5.0),
            make_task(duration=30, due_date=TODAY, priority=1.0),
        ]
        result = compute_daily_tasks(tasks, TODAY, daily_time_limit=30)
        assert [t.id for t in result] == ['0']

    def test_pre_selected_tasks_are_kept_and_budget_filled_around_them(self, make_task):
        pre_selected = [make_task(duration=10, due_date=TODAY)]
        other = make_task(duration=10, due_date=TODAY)
        result = compute_daily_tasks([pre_selected[0], other], TODAY, daily_time_limit=20, pre_selected_tasks=pre_selected)
        assert {t.id for t in result} == {'0', '1'}

    def test_pre_selected_tasks_that_are_no_longer_eligible_are_dropped(self, make_task):
        # done today -> no longer eligible even though pre-selected
        pre_selected_task = make_task(duration=10, due_date=TODAY, done_date=TODAY)
        result = compute_daily_tasks([pre_selected_task], TODAY, daily_time_limit=60, pre_selected_tasks=[pre_selected_task])
        assert result == []

    def test_pre_selected_over_budget_returns_only_pre_selected(self, make_task):
        pre_selected = [make_task(duration=50, due_date=TODAY)]
        other = make_task(duration=10, due_date=TODAY)
        result = compute_daily_tasks([pre_selected[0], other], TODAY, daily_time_limit=50, pre_selected_tasks=pre_selected)
        assert [t.id for t in result] == ['0']

    def test_no_eligible_tasks_returns_empty_list(self, make_task):
        task = make_task(due_date=TODAY + timedelta(days=5))
        result = compute_daily_tasks([task], TODAY, daily_time_limit=60)
        assert result == []

    def test_scheduling_sets_due_date_to_current_date_for_selected_tasks(self, make_task):
        task = make_task(duration=10, due_date=None)  # MAYBE_ELIGIBLE
        result = compute_daily_tasks([task], TODAY, daily_time_limit=60)
        assert result[0].due_date == TODAY
