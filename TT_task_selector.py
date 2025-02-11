from datetime import datetime, timedelta, date
from TT_task import TT_Task
from typing import List, Tuple
from enum import Enum
import os
from TT_csv_utils import read_tasks
from TT_utils import id_to_yaml_filename, yaml_filename_to_id
from TT_yaml import deserialize_all_tasks, serialize_all_tasks

class TT_TaskSelector:

    class Eligibility(Enum):
        NOT_ELIGIBLE = 0
        MAYBE_ELIGIBLE = 2
        ELIGIBLE = 1
    
    def __init__(self, daily_time_limit: int, priority_increment: float = 0.5):
        self.daily_time_limit = daily_time_limit
        self.priority_increment = priority_increment

    def _is_task_eligible(self, task: TT_Task, current_date: datetime.date) -> Eligibility:
        if task.due_date and task.due_date == current_date:
            return self.Eligibility.ELIGIBLE
        
        if not task.due_date or task.due_date < current_date: # undefined or in the past
            if task.last_done_date: 
                if (current_date - task.last_done_date).days >= task.frequency :
                     return self.Eligibility.ELIGIBLE
                else:
                    return self.Eligibility.NOT_ELIGIBLE 

            return self.Eligibility.MAYBE_ELIGIBLE
        return self.Eligibility.NOT_ELIGIBLE

    def _knapsack(self, tasks: List[Tuple[TT_Task, float]], max_time: int) -> Tuple[List[TT_Task], List[TT_Task]]:
        n = len(tasks)
        tasks = sorted(tasks, key=lambda t: (-t.priority, t.due_date if t.due_date else date(9999, 12, 31)))  # Sort by initial priority, then due date
        dp = [[0] * (max_time + 1) for _ in range(n + 1)]
        selected_tasks = []

        # Build the DP table
        for i in range(1, n + 1):
            for w in range(max_time + 1):
                if tasks[i - 1].duration <= w:
                    dp[i][w] = max(dp[i - 1][w], 
                                dp[i - 1][w - tasks[i - 1].duration] + tasks[i - 1].duration)
                else:
                    dp[i][w] = dp[i - 1][w]

        # Backtrack to find selected tasks
        w = max_time
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                selected_tasks.append(tasks[i - 1])
                w -= tasks[i - 1].duration

        unselected_tasks = [task for task in tasks if task not in selected_tasks]   
        return selected_tasks, unselected_tasks
    
    def initialize(self, folder: str, task_filename: str, current_date: datetime) -> List[TT_Task]:
        if not os.path.exists(folder):
            all_tasks = read_tasks(task_filename)
            serialize_all_tasks(folder, all_tasks)
            
        self.update_tasks_serialized(task_filename, folder)

        # Load tasks from the CSV file
        task_list = deserialize_all_tasks(folder)
        if task_list == None or len(task_list) == 0: 
            print("Erreur: liste de tâches vide")
            return []
        
        self.reset_and_update_task(current_date, task_list)
        
        today_tasks = self.get_task_list(task_list, current_date)
        if today_tasks == None or len(today_tasks) == 0: 
            print("Erreur: liste de tâches du jour vide")
            return []
                                    
        return today_tasks

    def get_task_list(self, tasks: List[TT_Task], current_date: datetime) -> List[TT_Task]:
        # Filter eligible tasks
        eligible_tasks = [task for task in tasks 
                         if self._is_task_eligible(task, current_date) != self.Eligibility.NOT_ELIGIBLE] 

        total_duration = sum(task.duration for task in eligible_tasks)
        
        if total_duration <= self.daily_time_limit:
            return [task for task in eligible_tasks]

        # Apply knapsack optimization
        selected_tasks, unselected_tasks = self._knapsack(
            eligible_tasks, self.daily_time_limit)

        unselected_tasks = [task for task in unselected_tasks if self._is_task_eligible(task, current_date) != self.Eligibility.MAYBE_ELIGIBLE]

        for task in selected_tasks:
            if task.due_date is None:
                task.due_date = current_date

        # Increase priority of unselected tasks
        for task in unselected_tasks:
            task.priority += self.priority_increment

        return selected_tasks
    

    def update_tasks_serialized(self, filename: str, folder: str):
        task_list = read_tasks(filename)
        task_ids = set([task.id for task in task_list])
        file_ids = set()

        for fname in os.listdir(folder):
            tid = yaml_filename_to_id(fname)
            if tid != -1: 
                file_ids.add(tid)

        # Add missing serialized tasks
        missing_files = task_ids - file_ids  # IDs without corresponding files
        for task in task_list: 
            if task.id in missing_files:
                task.serialize(folder)

        # Remove deleted tasks
        extra_files = file_ids - task_ids    # Files without corresponding IDs
        for tid in extra_files: 
            os.remove(os.path.join(folder, id_to_yaml_filename(tid)))


    def reset_and_update_task(self, current_date: datetime.date, tasks: List[TT_Task]):
        for task in tasks:
            if task.due_date:
                if task.due_date < current_date and not task.completed:
                    task.priority += 1.0
            elif task.completed:
                task.due_date += timedelta(days=task.frequency)
            task.completed = False