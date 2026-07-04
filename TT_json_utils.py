import json
import os

from TT_task import *

DEFAULT_DAILY_LIMIT = 60
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'cache.json')

def read_json_file(file_name: str):
    """Reads a JSON file and returns its content or an empty dictionary when absent."""
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File {file_name} not found.")
    except Exception as exc:
        print(f"Error: {exc}")
    return {}


def write_json_file(file_name: str, payload):
    """Writes a JSON payload to disk."""
    directory = os.path.dirname(file_name)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, default=str)


def read_tasks(file_name: str) -> list[TT_Task]:
    """Reads tasks from a JSON file and returns a list of Task objects."""
    print(f"Reading tasks from {file_name}")
    tasks = read_json_file(file_name)
    if not tasks:
        print("No tasks were loaded from the file. Please check the input.")
    return [TT_Task(task) for task in tasks]


def write_tasks(file_name: str, tasks: list[TT_Task]):
    """Writes the updated tasks back to a JSON file."""
    write_json_file(file_name, [task.task for task in tasks])


def save_daily_limit(daily_limit: int, cache_file: str = CACHE_FILE):
    print(f"Saving daily limit: {daily_limit}")
    cache = {'daily_limit': daily_limit}
    write_json_file(cache_file, cache)
    

def load_daily_limit(cache_file: str = CACHE_FILE):
   return read_json_file(cache_file).get('daily_limit', DEFAULT_DAILY_LIMIT)