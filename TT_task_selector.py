from datetime import datetime, timedelta, date
from typing import List, Tuple
from enum import Enum

class TT_TaskSelector:

    class Eligibility(Enum):
        NOT_ELIGIBLE = 0
        MAYBE_ELIGIBLE = 2
        ELIGIBLE = 1
    
    def __init__(self, daily_time_limit: int, priority_increment: float = 0.25):
        self.daily_time_limit = daily_time_limit
        self.priority_increment = priority_increment

    def _is_task_eligible(self, task: dict, current_date: datetime.date) -> Eligibility:
        due_date = task.get('due_date')
        last_done_date = task.get('last_done_date')
        frequency = task.get('frequency', 0)

        if due_date and due_date == current_date:
            return self.Eligibility.ELIGIBLE
        
        if not due_date or due_date < current_date:  # undefined or in the past
            if last_done_date:
                if (current_date - last_done_date).days >= frequency:
                    return self.Eligibility.ELIGIBLE
                return self.Eligibility.NOT_ELIGIBLE

            return self.Eligibility.MAYBE_ELIGIBLE

        return self.Eligibility.NOT_ELIGIBLE

    def _knapsack(self, tasks: List[dict], max_time: int) -> Tuple[List[dict], List[dict]]:
        n = len(tasks)
        tasks = sorted(
            tasks,
            key=lambda t: (-t.get('priority', 0), t.get('due_date') if t.get('due_date') else date(9999, 12, 31)),
        )
        dp = [[0] * (max_time + 1) for _ in range(n + 1)]
        selected_tasks = []

        for i in range(1, n + 1):
            task = tasks[i - 1]
            duration = int(task.get('duration', 0))
            for w in range(max_time + 1):
                if duration <= w:
                    dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - duration] + duration)
                else:
                    dp[i][w] = dp[i - 1][w]

        w = max_time
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                selected_tasks.append(tasks[i - 1])
                w -= int(tasks[i - 1].get('duration', 0))

        unselected_tasks = [task for task in tasks if task not in selected_tasks]
        return selected_tasks, unselected_tasks

    def get_daily_tasks(self, tasks: List[dict], current_date: datetime.date) -> List[dict]:
        task_clones = [task.copy() for task in tasks]
        eligible_tasks = [
            task for task in task_clones
            if self._is_task_eligible(task, current_date) != self.Eligibility.NOT_ELIGIBLE
        ]

        total_duration = sum(int(task.get('duration', 0)) for task in eligible_tasks)

        if total_duration <= self.daily_time_limit:
            return [task for task in eligible_tasks]

        selected_tasks, unselected_tasks = self._knapsack(eligible_tasks, self.daily_time_limit)

        unselected_tasks = [
            task for task in unselected_tasks
            if self._is_task_eligible(task, current_date) != self.Eligibility.MAYBE_ELIGIBLE
        ]

        for task in selected_tasks:
            if task.get('due_date') is None:
                task['due_date'] = current_date

        for task in unselected_tasks:
            task['priority'] = task.get('priority', 0) + self.priority_increment

        return selected_tasks
    
    def reset_and_update_task(self, current_date: datetime.date, tasks: List[dict], folder: str):
        for task in tasks:
            due_date = task.get('due_date')
            completed = task.get('completed', False)
            frequency = task.get('frequency', 0)

            if due_date:
                if due_date < current_date and not completed:
                    task['priority'] = task.get('priority', 0) + 1.0
            elif completed:
                task['due_date'] = current_date + timedelta(days=frequency)

            task['completed'] = False
