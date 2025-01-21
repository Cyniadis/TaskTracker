import os
from TT_task import *
from TT_csv_utils import *
from TT_utils import *

def serialize_all_tasks(folder : str, task_list : list[TT_Task]) -> None:
    os.makedirs(folder, exist_ok=True)
    for task in task_list:
        task.serialize(folder)
        
def deserialize_all_tasks(folder: str) -> list[TT_Task]:
    tasks = []
    for filename in os.listdir(folder):
        if filename.endswith('.yaml'):
            file_path = os.path.join(folder, filename)
            try:
                task = TT_Task()
                task.deserialize(file_path)
                tasks.append(task)
            except Exception as e:
                print(f"Failed to deserialize {filename}: {e}")
    
    return tasks


if __name__ == "__main__":
    task_list = read_tasks(TASKLIST_FILE_NAME)
    serialize_all_tasks(TASKS_YAML_FOLDER, task_list)