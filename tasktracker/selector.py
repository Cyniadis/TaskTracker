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

from .task import Task


class Eligibility(Enum):
    NOT_ELIGIBLE = auto()
    MAYBE_ELIGIBLE = auto()
    ELIGIBLE = auto()


def _eligibility(task: Task, current_date: date) -> Eligibility:
    if task.due_date == current_date:
        return Eligibility.ELIGIBLE

    if not task.due_date or task.due_date < current_date:
        if task.last_done_date:
            days_since_done = (current_date - task.last_done_date).days
            return (
                Eligibility.ELIGIBLE
                if days_since_done >= task.frequency_obj.days
                else Eligibility.NOT_ELIGIBLE
            )
        return Eligibility.MAYBE_ELIGIBLE

    return Eligibility.NOT_ELIGIBLE


def _select_by_priority(tasks: list[Task], time_budget: int) -> list[Task]:
    """0/1 knapsack over `tasks`, maximizing time used while favouring higher priority."""
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

    selected: list[Task] = []
    capacity = time_budget
    for i in range(n, 0, -1):
        if dp[i][capacity] != dp[i - 1][capacity]:
            task = ordered[i - 1]
            selected.append(task)
            capacity -= task.duration
    return selected


def compute_daily_tasks(
    tasks: list[Task],
    current_date: date,
    daily_time_limit: int,
    include_completed_today: bool = False,
) -> list[Task]:
    """Return the subset of `tasks` scheduled for `current_date`.

    Tasks already completed today are optionally always kept (and their
    time reserved first) when `include_completed_today` is set.
    """
    eligible = [t for t in tasks if _eligibility(t, current_date) is not Eligibility.NOT_ELIGIBLE]
    completed_today = [t for t in eligible if t.is_completed_on(current_date)]

    if include_completed_today and completed_today:
        for task in completed_today:
            task.schedule_for(current_date)

        remaining_time = daily_time_limit - sum(t.duration for t in completed_today)
        if remaining_time <= 0:
            return completed_today

        completed_ids = {t.id for t in completed_today}
        candidates = [t for t in eligible if t.id not in completed_ids]

        if sum(t.duration for t in candidates) <= remaining_time:
            for task in candidates:
                task.schedule_for(current_date)
            return completed_today + candidates

        extra = _select_by_priority(candidates, remaining_time)
        for task in extra:
            task.schedule_for(current_date)
        return completed_today + extra

    if sum(t.duration for t in eligible) <= daily_time_limit:
        for task in eligible:
            task.schedule_for(current_date)
        return eligible

    selected = _select_by_priority(eligible, daily_time_limit)
    for task in selected:
        task.schedule_for(current_date)
    return selected
