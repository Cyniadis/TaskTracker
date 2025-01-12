from TT_structs import *
import csv


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

def read_tasks(file_name):
    """Reads tasks from a CSV file and returns a list of Task objects."""
    tasks = []
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            csv_reader = csv.DictReader(file, delimiter=';')

            for row in csv_reader:
                frequency = parse_frequency(row['Fréquence'])
                if frequency is None:
                    print(f"Skipping task due to invalid frequency: {row['Nom']}")
                    continue

                task = Task(
                    name=row['Nom'],
                    frequency=frequency,
                    priority=float(row['Priorité']),
                    duration=int(row['Durée (min)']),
                    due_date=None if row['Date prévue'] == "" else datetime.strptime(row['Date prévue'], "%d/%m/%Y").date(),
                    last_done_date=None if row['Date achevée'] == "" else datetime.strptime(row['Date achevée'], "%d/%m/%Y").date(),
                    completed=row['Achevée?'] == "1"
                )
                tasks.append(task)

    except FileNotFoundError:
        print(f"Error: File {file_name} not found.")
    except Exception as e:
        print(f"Error: {e}")

    if not tasks:
        print("No tasks were loaded from the file. Please check the input.")

    return tasks

def write_tasks(file_name, tasks):
    """Writes the updated tasks back to a CSV file."""
    with open(file_name, "w", encoding="utf-8", newline="") as file:
        fieldnames = ["Nom", "Fréquence", "Priorité", "Durée (min)", "Date prévue", "Date achevée", "Achevée?"]
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for task in tasks:
            writer.writerow({
                "Nom": task.name,
                "Fréquence": f"{int(1 / task.frequency)}xjour" if task.frequency <= 1 else f"{int(task.frequency / 7)}xsemaine" if task.frequency <= 7 else f"{int(task.frequency / 30.4)}xmois" if task.frequency <= 30.4 else f"{int(task.frequency / 365)}xan",
                "Priorité": int(task.priority),
                "Durée (min)": task.duration,
                "Date prévue": task.due_date.strftime("%d/%m/%Y") if task.due_date else "",
                "Date achevée": task.last_done_date.strftime("%d/%m/%Y") if task.last_done_date else "",
                "Achevée?": "1" if task.completed else "0"
            })