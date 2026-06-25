from datetime import datetime, timedelta


def is_task_due(task: dict, current_date: datetime.date) -> bool:
    if not task.get('last_done_date'):
        return False
    days_since_completion = (current_date - task['last_done_date']).days
    return days_since_completion >= task.get('frequency', 0)


def complete_task(task: dict, completion_date: datetime.date) -> None:
    task['completed'] = True
    task['last_done_date'] = completion_date
    task['due_date'] = completion_date + timedelta(days=task.get('frequency', 0))
    task['priority'] = task.get('initial_priority', task.get('priority', 0))


def uncomplete_task(task: dict) -> None:
    task['completed'] = False


def clone_task(task: dict) -> dict:
    return task.copy()

