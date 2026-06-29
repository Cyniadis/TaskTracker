from asyncio import tasks
from datetime import datetime, timedelta

from TT_utils import date_to_string, frequency_to_days, string_to_date

PRIORITY_INCREMENT = 0.5

def is_task_due(task: dict, current_date: datetime.date) -> bool:
    last_done_date = get_last_done_date(task)
    if not last_done_date:
        return False
    days_since_completion = (current_date - last_done_date).days
    return days_since_completion >= get_frequency(task)

def compute_next_due_date(task: dict, current_date: datetime.date) -> datetime.date:
    frequency = get_frequency(task)
    return current_date + timedelta(days=frequency_to_days(frequency))

def complete_task(task: dict, completion_date: datetime.date) -> None:
    set_done_date(task, completion_date)
    task['priority'] = get_initial_priority(task)

def uncomplete_task(task: dict) -> None:
    set_done_date(task, get_last_done_date(task))

def clone_task(task: dict) -> dict:
    return task.copy()

def sort_tasks(tasks, sort_key, descending=True):
    key_map = {
        'Task': lambda task: get_name(task),
        'Name': lambda task: get_name(task),
        'Frequency': lambda task: get_frequency(task),
        'Priority': lambda task: get_priority(task),
        'Duration': lambda task: get_duration(task),
        'Due date': lambda task: get_due_date(task) or datetime.max.date(),
        'Done date': lambda task: get_done_date(task),
    }
    return sorted(tasks, key=key_map.get(sort_key, lambda task: get_name(task)), reverse=descending)


def reset_and_update_tasks(current_date: datetime.date, tasks: list[dict]):
    for task in tasks:          
        set_due_date(task, get_next_due_date(task, current_date))
        task['selected'] = False  
        set_last_done_date(task, get_done_date(task))
            
        task['done_date'] = None
        task['next_due_date'] = None
            
def update_priorities(tasks: list[dict], today_tasks: list[dict], priority_increment = PRIORITY_INCREMENT): 
    unselected_tasks = tasks - today_tasks
    for task in unselected_tasks:
        task['priority'] = get_priority(task) + priority_increment

def get_all_selected_tasks(tasks: list[dict]) -> list[dict]:  
    return [ t for t in tasks if get_selected(t) ]


"================= GETTERS ================="

def get_id(task: dict) -> int:
    return task.get('id', -1)

def get_name(task: dict) -> str:
    return task.get('name', '')

def get_frequency(task: dict) -> str:
    return task.get('frequency', '')

def get_priority(task: dict) -> float:
    return task.get('priority', 0.0)

def get_duration(task: dict) -> int:
    return task.get('duration', 0)

def get_due_date(task: dict) -> datetime.date:
    date = task.get('due_date')
    if not date or date is None :
        return None
    return string_to_date(date)

def set_due_date(task: dict, date : datetime.date): 
    task['due_date'] = date_to_string(date)

def get_done_date(task: dict) -> bool:
    date = task.get('done_date')
    if not date or date is None :
        return None
    return string_to_date(date)

def set_done_date(task: dict, date : datetime.date): 
    task['done_date'] = date_to_string(date)

def get_last_done_date(task: dict) -> datetime.date:
    date = task.get('last_done_date')
    if not date or date is None :
        return None
    return string_to_date(date)

def set_last_done_date(task: dict, date : datetime.date): 
    task['last_done_date'] = date_to_string(date)

def get_next_due_date(task: dict, current_date: datetime.date) -> datetime.date:
    date = task.get('next_due_date')
    if not date or date is None :
        return None
    return string_to_date(date)

def set_next_due_date(task: dict, date : datetime.date): 
    task['next_due_date'] = date_to_string(date)

def get_initial_priority(task: dict) -> float:
    return task.get('initial_priority', 0.0)

def is_task_completed(task: dict, current_date: datetime.date) -> bool:
    if task.get('done_date') is None:
        return False
    return task.get('done_date') == current_date

def get_selected(task: dict) -> bool:
    return task.get('selected', False)

