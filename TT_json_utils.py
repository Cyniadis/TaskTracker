import json

from TT_task import *

def parse_frequency(frequency: str) -> float:
    """Parses frequency strings like '1xjour', '2xsemaine', etc."""
    try:
        number, period = frequency.lower().split('x')
        number = int(number)

        if period == "jour":
            return 1.0 / number
        elif period == "semaine":
            return 7.0 / number
        elif period == "mois":
            return 30.4 / number
        elif period == "an":
            return 365.0 / number
        raise ValueError(f"Unknown period: {period}")
    except ValueError:
        print(f"Invalid frequency format: {frequency}")
        return None

def _frequency_to_string(frequency: float) -> str:
    """Converts a frequency in days to a string representation."""
    if frequency <= 1:
        return f"{int(1 / frequency)}xjour"
    if frequency <= 7:
        return f"{int(7 / frequency)}xsemaine"
    if frequency <= 30.4:
        return f"{int(30.4 / frequency)}xmois"
    return f"{int(365 / frequency)}xan"


def __parse_datetime(task: dict) -> dict:
    if 'due_date' in task and task['due_date'] is not None:
        task["due_date"] = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
    if 'last_done_date' in task and task['last_done_date'] is not None:
        task["last_done_date"] = datetime.strptime(task["last_done_date"], "%Y-%m-%d").date()
    return task
    
def read_tasks(file_name : str) -> dict:
    """Reads tasks from a JSON file and returns a list of Task objects."""
    tasks = []
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            tasks = json.load(file, object_hook=__parse_datetime)
    except FileNotFoundError:
        print(f"Error: File {file_name} not found.")
    except Exception as e:
        print(f"Error: {e}")

    if not tasks:
        print("No tasks were loaded from the file. Please check the input.")

    return tasks


def write_tasks(file_name: str, tasks: dict):
    """Writes the updated tasks back to a JSON file."""
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2, default=str)



