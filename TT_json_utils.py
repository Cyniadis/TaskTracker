import json
from TT_utils import date_to_iso_string, string_to_date

def parse_frequency(frequency):
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

def _frequency_to_string(frequency):
    if frequency <= 1:
        return f"{int(1 / frequency)}xjour"
    if frequency <= 7:
        return f"{int(7 / frequency)}xsemaine"
    if frequency <= 30.4:
        return f"{int(30.4 / frequency)}xmois"
    return f"{int(365 / frequency)}xan"


def read_tasks(file_name):
    """Reads tasks from a JSON file and returns a list of Task objects."""
    tasks = []
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
        for row in data:
            frequency = parse_frequency(row.get('frequency', '1xjour'))
            if frequency is None:
                print(f"Skipping task due to invalid frequency: {row.get('name', '<unknown>')}")
                continue
            task = {
                'id': int(row.get('id', 0)),
                'name': row.get('name', ''),
                'frequency': frequency,
                'priority': float(row.get('priority', 0)) if row.get('priority', 0) not in (None, '') else 0.0,
                'initial_priority': float(row.get('priority', 0)) if row.get('priority', 0) not in (None, '') else 0.0,
                'duration': int(row.get('duration', 0)) if row.get('duration', 0) not in (None, '') else 0,
                'due_date': None if row.get('due_date') in (None, '') else string_to_date(row.get('due_date')),
                'completed': bool(row.get('completed', False)),
                'last_done_date': None if row.get('last_done_date') in (None, '') else string_to_date(row.get('last_done_date')),
            }
            tasks.append(task)
    except FileNotFoundError:
        print(f"Error: File {file_name} not found.")
    except Exception as e:
        print(f"Error: {e}")

    if not tasks:
        print("No tasks were loaded from the file. Please check the input.")

    return tasks


def write_tasks(file_name, tasks):
    """Writes the updated tasks back to a JSON file."""
    json_data = []
    for task in tasks:
        json_data.append({
            'id': task.get('id', 0),
            'name': task.get('name', ''),
            'frequency': _frequency_to_string(task.get('frequency', 0)),
            'priority': int(task.get('priority', 0)),
            'duration': int(task.get('duration', 0)),
            'due_date': date_to_iso_string(task.get('due_date')) if task.get('due_date') else None,
            'completed': bool(task.get('completed', False)),
            'last_done_date': date_to_iso_string(task.get('last_done_date')) if task.get('last_done_date') else None,
        })
    with open(file_name, 'w', encoding='utf-8') as file:
        json.dump(json_data, file, ensure_ascii=False, indent=2)



