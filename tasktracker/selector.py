"""Decides which tasks belong on today's plate.

Pure business logic: no Streamlit, no I/O. Two steps:

1. Filter tasks down to the ones that are *eligible* today (due, overdue,
   or never scheduled).
2. If they don't all fit in the daily time budget, pick the best subset
   with a 0/1 knapsack, favouring higher-priority tasks.
"""
from __future__ import annotations

from datetime import date
from enum import Enum, auto

from .consts import today
from .task import Task, schedule_task_list


class Eligibility(Enum):
    """Whether a task can be picked for a given day."""
    NOT_ELIGIBLE = auto()    # already done today, or not due yet and never done
    MAYBE_ELIGIBLE = auto()  # never scheduled/done before — can be used as a filler
    ELIGIBLE = auto()        # due today, overdue, or its recurrence window has elapsed


def _eligibility(task: Task, current_date: date) -> Eligibility:
    """Classify whether `task` can be scheduled on `current_date`."""
    if task.done_date == current_date:
        return Eligibility.NOT_ELIGIBLE

    if task.due_date == current_date:
        return Eligibility.ELIGIBLE

    if not task.due_date or task.due_date < current_date:
        if task.done_date:
            days_since_done = (current_date - task.done_date).days
            if days_since_done >= task.frequency_obj.days:
                return Eligibility.NOT_ELIGIBLE
            return Eligibility.ELIGIBLE
        return Eligibility.MAYBE_ELIGIBLE

    return Eligibility.NOT_ELIGIBLE


def _select_by_priority(tasks: list[Task], time_budget: int) -> list[Task]:
    """0/1 knapsack over `tasks`, maximizing time used while favouring higher priority.

    Tasks are pre-sorted by priority (descending) before the knapsack DP so that,
    among equally-good-duration combinations, ties are naturally broken in favour
    of higher-priority tasks during backtracking.
    """
    ordered = sorted(tasks, key=lambda t: (-t.priority, t.due_date or date.max))
    n = len(ordered)

    # dp[i][w] = best total duration achievable using the first i tasks within budget w
    dp = [[0] * (time_budget + 1) for _ in range(n + 1)]
    for i, task in enumerate(ordered, start=1):
        duration = task.duration
        for capacity in range(time_budget + 1):
            if duration <= capacity:
                dp[i][capacity] = max(dp[i - 1][capacity], dp[i - 1][capacity - duration] + duration)
            else:
                dp[i][capacity] = dp[i - 1][capacity]

    # Backtrack through the DP table to recover which tasks were chosen.
    selected: list[Task] = []
    capacity = time_budget
    for i in range(n, 0, -1):
        if dp[i][capacity] != dp[i - 1][capacity]:
            task = ordered[i - 1]
            selected.append(task)
            capacity -= task.duration
    return selected

def _fill_with_future_tasks(
    tasks: list[Task],
    selected: list[Task],
    current_date: date,
    daily_time_limit: int,
) -> list[Task]:
    """Top up `selected` with tasks whose due date is in the future, closest due
    date first, as long as there's leftover room in the daily budget."""
    remaining_time = daily_time_limit - sum(t.duration for t in selected)
    if remaining_time <= 0:
        return selected

    selected_ids = {t.id for t in selected}
    future_candidates = [
        t for t in tasks
        if t.id not in selected_ids
        and t.due_date is not None
        and t.due_date > current_date
        and t.done_date != current_date
    ]
    future_candidates.sort(key=lambda t: (t.due_date, -t.priority))

    extra: list[Task] = []
    for task in future_candidates:
        if task.duration <= remaining_time:
            extra.append(task)
            remaining_time -= task.duration

    schedule_task_list(extra, current_date)
    return selected + extra


def compute_daily_tasks(
    tasks: list[Task],
    current_date: date,
    daily_time_limit: int,
    pre_selected_tasks: list[Task] | None = None,
    allow_future_tasks: bool = False,
) -> list[Task]:
    """Return the subset of `tasks` scheduled for `current_date`.

    If `pre_selected_tasks` is given (e.g. tasks already picked in a previous
    render, or manually added), they're kept as-is and the remaining budget is
    filled around them. Otherwise the full eligible pool is considered.

    If `allow_future_tasks` is set and the normally-eligible tasks don't
    fill the daily budget, future-dated tasks are pulled forward to fill
    the remaining time.
    """
    pre_selected_tasks = pre_selected_tasks or []

    eligible = [t for t in tasks if _eligibility(t, current_date) is not Eligibility.NOT_ELIGIBLE]
    pre_selected_tasks = [t for t in pre_selected_tasks if _eligibility(t, current_date) is not Eligibility.NOT_ELIGIBLE]

    if pre_selected_tasks:
        schedule_task_list(pre_selected_tasks, current_date)

        remaining_time = daily_time_limit - sum(t.duration for t in pre_selected_tasks)
        if remaining_time <= 0:
            return pre_selected_tasks

        pre_selected_ids = {t.id for t in pre_selected_tasks}
        candidates = [t for t in eligible if t.id not in pre_selected_ids]

        if sum(t.duration for t in candidates) <= remaining_time:
            schedule_task_list(candidates, current_date)
            result = pre_selected_tasks + candidates
            if allow_future_tasks:
                result = _fill_with_future_tasks(tasks, result, current_date, daily_time_limit)
            return result

        extra = _select_by_priority(candidates, remaining_time)
        schedule_task_list(extra, current_date)
        return pre_selected_tasks + extra

    if sum(t.duration for t in eligible) <= daily_time_limit:
        schedule_task_list(eligible, current_date)
        result = eligible
        if allow_future_tasks:
            result = _fill_with_future_tasks(tasks, result, current_date, daily_time_limit)
        return result

    selected = _select_by_priority(eligible, daily_time_limit)
    schedule_task_list(selected, current_date)
    return selected
