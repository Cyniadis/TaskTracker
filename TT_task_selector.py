from datetime import datetime, date
from enum import Enum
from TT_task import *

class _Eligibility(Enum):
    NOT_ELIGIBLE = 0
    MAYBE_ELIGIBLE = 2
    ELIGIBLE = 1

# Determine if a task is eligible for selection based on its due date, last done date, and frequency
def _is_task_eligible(task: TT_Task, current_date: datetime.date) -> _Eligibility:
    due_date = task.get_due_date()
    last_done_date = task.get_last_done_date()
    frequency = frequency_to_days(task.get_frequency())

    if due_date and due_date == current_date:
        return _Eligibility.ELIGIBLE
    
    if not due_date or due_date < current_date:  # undefined or in the past
        if last_done_date:
            print(current_date - last_done_date)
            if (current_date - last_done_date).days >= frequency:
                return _Eligibility.ELIGIBLE
            return _Eligibility.NOT_ELIGIBLE
        return _Eligibility.MAYBE_ELIGIBLE
    return _Eligibility.NOT_ELIGIBLE


# Use a dynamic programming approach to select tasks that maximize priority while staying within the daily time limit
def _knapsack(tasks: list[TT_Task], max_time: int) -> list[TT_Task]:
    n = len(tasks)
    tasks = sorted(
        tasks,
        key=lambda t: (-t.get_priority(), t.get_due_date() if t.get_due_date() else date(9999, 12, 31)),
    )
    dp = [[0] * (max_time + 1) for _ in range(n + 1)]
    selected_tasks = []

    for i in range(1, n + 1):
        task = tasks[i - 1]
        duration = task.get_duration()
        for w in range(max_time + 1):
            if duration <= w:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - duration] + duration)
            else:
                dp[i][w] = dp[i - 1][w]

    w = max_time
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected_tasks.append(tasks[i - 1])
            w -= int(tasks[i - 1].get_duration())

    # unselected_tasks = [task for task in tasks if task not in selected_tasks]
    return selected_tasks
    # return selected_tasks, unselected_tasks


# Compute the daily tasks based on eligibility and the knapsack algorithm
def compute_daily_tasks(tasks: list[TT_Task], current_date: datetime.date, daily_time_limit: int, include_completed_today: bool = False) -> list[TT_Task]:
    print(f"Computing daily tasks for {current_date} with daily limit {daily_time_limit} and include_completed_today={include_completed_today}")
    # Update the last done date for each task before checking eligibility
    # for task in tasks:
    #     task.set_last_done_date(task.get_done_date())

    # Filter tasks based on eligibility
    eligible_tasks = [
        task for task in tasks
        if _is_task_eligible(task, current_date) != _Eligibility.NOT_ELIGIBLE
    ]

    # If the user wants to always include already completed today tasks, reserve them first
    completed_today = [t for t in eligible_tasks if t.is_task_completed(current_date)]
    if include_completed_today and completed_today:
        # mark completed tasks as selected and reserve their durations
        for t in completed_today:
            t.set_selected(True)
            t.set_due_date(current_date)
            t.set_next_due_date(t.compute_next_due_date(current_date))

        reserved_time = sum(int(t.get_duration()) for t in completed_today)
        remaining_time = daily_time_limit - reserved_time
        # If reserved tasks already exceed or meet the limit, return them (always include completed)
        if remaining_time <= 0:
            return completed_today

        # Consider other eligible tasks (excluding the already completed ones)
        candidate_tasks = [t for t in eligible_tasks if t not in completed_today]

        total_candidate_duration = sum(int(task.get_duration()) for task in candidate_tasks)
        if total_candidate_duration <= remaining_time:
            # select all candidates
            for task in candidate_tasks:
                task.set_selected(True)
                task.set_due_date(current_date)
                task.set_next_due_date(task.compute_next_due_date(current_date))
            return completed_today + candidate_tasks

        # otherwise fill remaining time with knapsack from candidates
        selected_from_candidates = _knapsack(candidate_tasks, remaining_time)
        for task in selected_from_candidates:
            task.set_selected(True)
            task.set_due_date(current_date)
            task.set_next_due_date(task.compute_next_due_date(current_date))

        return completed_today + selected_from_candidates

    # Default behaviour when not forcing completed tasks
    total_duration = sum(int(task.get_duration()) for task in eligible_tasks)
    if total_duration <= daily_time_limit:
        for task in eligible_tasks:
            task.set_selected(True)
            task.set_due_date(current_date)
            task.set_next_due_date(task.compute_next_due_date(current_date))
        return [task for task in eligible_tasks]

    # If the total duration exceeds the daily limit, use the knapsack algorithm to select tasks
    selected_tasks = _knapsack(eligible_tasks, daily_time_limit)

    # Set the due date and next due date for selected tasks
    for task in selected_tasks:
        task.set_due_date(current_date)
        task.set_next_due_date(task.compute_next_due_date(current_date))
        task.set_selected(True)
    return selected_tasks
