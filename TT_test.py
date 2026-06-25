from TT_task_selector import TT_TaskSelector
from TT_json_utils import read_tasks
from TT_task import complete_task
from TT_utils import TASKLIST_FILE_NAME
from datetime import datetime, timedelta
import random

def random_selection(items, min_items: int = 1, max_items: int = None):
    """Select random number of elements from list"""
    if not items:
        return []
    
    if max_items is None:
        max_items = len(items)
    
    num_items = random.randint(min_items, min(max_items, len(items)))
    return random.sample(items, num_items)


if __name__ == "__main__":
    daily_time_limit = 3*60
    selector = TT_TaskSelector(daily_time_limit)
    
    for d in range(0, 30) :
        tasks = read_tasks(TASKLIST_FILE_NAME)

        current_date = datetime.today().date() + timedelta(days=d)
        
        selector.reset_and_update_task(current_date, tasks, '')

        daily_tasks = selector.get_daily_tasks(tasks, current_date)
        print(f"Daily tasks for {current_date}:")
        
        prioIncr = []
        for task in daily_tasks:
            if task.get('priority', 0) > task.get('initial_priority', 0):
                prioIncr.append("*") 
            else:
                prioIncr.append("")

        rdn_tasks_to_complete = random_selection(daily_tasks)
        for task in rdn_tasks_to_complete:
            complete_task(task, current_date)

        for i, task in enumerate(daily_tasks):
            prefix = "✅" if task in rdn_tasks_to_complete else "❌"
            print(f"{prioIncr[i]}{prefix} {task}")

        total_time = sum(int(task.get('duration', 0)) for task in daily_tasks)
        print(f"Total time: {total_time} minutes")
        if (total_time > daily_time_limit):
            print(f"❌ ERROR: Total time exceeds daily limit of {daily_time_limit} minutes")
        else:
            print(f"✅ PASS")
        print()