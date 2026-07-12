import json
from copy import deepcopy
from datetime import datetime, timedelta

from TT_utils import date_to_string, frequency_to_days, normalize_date

PRIORITY_INCREMENT = 0.5

# ================= SINGLE TASK FUNCTIONS =================

class TT_Task:
    _DATE_FIELDS = {'due_date', 'next_due_date', 'done_date', 'last_done_date'}

    def __init__(self, task: dict):
        self.task = deepcopy(task)
        for field in self._DATE_FIELDS:
            if field in self.task:
                self.task[field] = normalize_date(self.task[field])

    def __str__(self):
        return json.dumps(self.task)
        # return json.dumps(self.task, default=date_to_string)

    def is_due(self, current_date: datetime.date) -> bool:
        last_done_date = self.get_last_done_date()
        if not last_done_date:
            return False
        days_since_completion = (current_date - last_done_date).days
        return days_since_completion >= self.get_frequency()

    def compute_next_due_date(self, current_date: datetime.date) -> datetime.date:
        frequency = self.get_frequency()
        return current_date + timedelta(days=frequency_to_days(frequency))

    def complete(self, completion_date: datetime.date) -> None:
        self.set_done_date(completion_date)
        self.set_priority(self.get_initial_priority())

    def uncomplete(self) -> None:
        self.set_done_date(self.get_last_done_date())

    def clone(self) -> dict:
        return self.task.copy()

    def set_value(self, param: str, value):
        if param == "name": 
            self.set_name(value)
        elif param == "frequency": 
            self.set_frequency(value)
        elif param == "priority":
            self.set_priority(value)
        elif param == "initial_priority":
            self.set_initial_priority(value)
        elif param == "duration": 
            self.set_duration(value)
        elif param == "due_date":
            self.set_due_date(value)
        elif param == "next_due_date":
            self.set_next_due_date(value)


    def get_id(self) -> int:
        return self.task.get('id', -1)

    def get_name(self) -> str:
        return self.task.get('name', '')
    def set_name(self, name: str):
        self.task["name"] = name

    def get_frequency(self) -> str:
        return self.task.get('frequency', '')
    def set_frequency(self, freq: str): 
        self.task['frequency'] = freq

    def get_priority(self) -> float:
        return self.task.get('priority', 0.0)
    def set_priority(self, priority: float):
        self.task['priority'] = priority

    def get_duration(self) -> int:
        return self.task.get('duration', 0)
    def set_duration(self, duration: int) -> int:
        self.task['duration'] = duration

    def get_due_date(self) -> datetime.date:
        return normalize_date(self.task.get('due_date'))
    def set_due_date(self, date_value: datetime.date):
        self.task['due_date'] = normalize_date(date_value)

    def get_done_date(self) -> datetime.date:
        return normalize_date(self.task.get('done_date'))
    def set_done_date(self, date_value: datetime.date):
        self.task['done_date'] = normalize_date(date_value)

    def get_last_done_date(self) -> datetime.date:
        return normalize_date(self.task.get('last_done_date'))

    def get_initial_priority(self) -> float:
        return self.task.get('initial_priority', 0.0)
    def set_initial_priority(self, priority: int):
        self.task['initial_priority'] = priority

    def get_next_due_date(self, current_date: datetime.date) -> datetime.date:
        return normalize_date(self.task.get('next_due_date'))

    def get_selected(self) -> bool:
        return self.task.get('selected', False)
    def set_selected(self, selected: bool):
        self.task['selected'] = selected

    def set_last_done_date(self, date_value: datetime.date):
        self.task['last_done_date'] = normalize_date(date_value)

    def set_next_due_date(self, date_value: datetime.date):
        self.task['next_due_date'] = normalize_date(date_value)

    def is_task_completed(self, current_date: datetime.date) -> bool:
        if self.task.get('done_date') is None:
            return False
        return self.get_done_date() == current_date

    def reset_and_update(self, current_date: datetime.date):
        self.set_selected(False)
        self.set_last_done_date(self.get_done_date())
        self.set_due_date(self.get_next_due_date(current_date))
        self.set_done_date(None)
        self.set_next_due_date(None)


# ================= TASK LIST FUNCTIONS =================

def sort_tasks(tasks: list[TT_Task], sort_key: str, descending=True) -> list[TT_Task]:
    key_map = {
        'Task': lambda task: task.get_name(),
        'Name': lambda task: task.get_name(),
        'Frequency': lambda task: task.get_frequency(),
        'Priority': lambda task: task.get_priority(),
        'Duration': lambda task: task.get_duration(),
        'Due date': lambda task: task.get_due_date() ,
        'Done date': lambda task: task.get_done_date(),
    }
    return sorted(tasks, key=key_map.get(sort_key, lambda task: task.get_name()), reverse=descending)


def update_priorities(tasks: list[TT_Task], today_tasks: list[TT_Task], priority_increment = PRIORITY_INCREMENT):
    unselected_tasks = [task for task in tasks if task not in today_tasks]
    for task in unselected_tasks:
        task.set_priority(task.get_priority() + priority_increment)

def get_all_selected_tasks(tasks: list[TT_Task]) -> list[TT_Task]:
    return [ t for t in tasks if t.get_selected() ]

