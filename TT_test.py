from TT_task_selector import TT_TaskSelector
from TT_yaml import deserialize_all_tasks, serialize_all_tasks
from TT_utils import TASKS_YAML_FOLDER, TASKLIST_FILE_NAME
from TT_csv_utils import read_tasks
from datetime import datetime, timedelta
import random
import shutil
import os

def random_selection(items, min_items: int = 1, max_items: int = None):
    """Select random number of elements from list"""
    if not items:
        return []
    
    if max_items is None:
        max_items = len(items)
    
    num_items = random.randint(min_items, min(max_items, len(items)))
    return random.sample(items, num_items)


if __name__ == "__main__":
    daily_time_limit = 2*60
    selector = TT_TaskSelector(daily_time_limit)
    
    if os.path.exists(TASKS_YAML_FOLDER):
        shutil.rmtree(TASKS_YAML_FOLDER) 



    for d in range(0, 5) :
        current_date = datetime.today().date() + timedelta(weeks=d)
        tasks = selector.initialize(TASKS_YAML_FOLDER, TASKLIST_FILE_NAME, current_date)

        if len(tasks) == 0: 
            print("Erreur dans l'initialisation")
            exit(1)
        
        print(f"Weekly tasks for {current_date}:")
        prioIncr = []
        for task in tasks:
            if task.priority > task.initial_priority:
                prioIncr.append("*") 
            else :
                prioIncr.append("")


        rdn_tasks_to_complete = random_selection(tasks)
        for task in rdn_tasks_to_complete:                
            task.complete_task(current_date)
            task.serialize(TASKS_YAML_FOLDER)
            
        for i, task in enumerate(tasks):
            prefix = "✅" if task in rdn_tasks_to_complete else "❌"
            print(f"{prioIncr[i]}{prefix} {task}")
           
            
        total_time = sum([task.duration for task in tasks])
        print(f"Total time: {total_time} minutes")
        if (total_time > daily_time_limit):
            print(f"❌ ERROR: Total time exceeds daily limit of {daily_time_limit} minutes")
        else:
            print(f"✅ PASS")
        print()