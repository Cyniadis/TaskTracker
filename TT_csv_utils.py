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
                    id=int(row["ID"]),
                    name=row['Nom'],
                    frequency=frequency,
                    priority=float(row['Priorité']),
                    duration=int(row['Durée (min)']),
                    due_date=None if row['Date prévue'] == "" else string_to_date(row['Date prévue']),
                )
                tasks.append(task)

    except FileNotFoundError:
        print(f"Error: File {file_name} not found.")
    except Exception as e:
        print(f"Error: {e}")

    if not tasks:
        print("No tasks were loaded from the file. Please check the input.")

    return tasks

def write_schedule(file_name, scheduler):
    """Writes the schedueler  to a CSV file."""
    with open(file_name, "w", encoding="utf-8", newline="") as file:
        fieldnames = ["Date", "IDs"]
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for date_str, task_list in scheduler.items():
            writer.writerow({
                "Date": date_str,
                "IDs": [task.id for task in task_list]
            })

# def write_tasks(file_name, tasks):
#     """Writes the updated tasks back to a CSV file."""
#     with open(file_name, "w", encoding="utf-8", newline="") as file:
#         fieldnames = ["Nom", "Fréquence", "Priorité", "Durée (min)", "Date prévue", "Date achevée", "Achevée?"]
#         writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
#         writer.writeheader()

#         for task in tasks:
#             writer.writerow({
#                 "ID": task.id,
#                 "Nom": task.name,
#                 "Fréquence": f"{int(1 / task.frequency)}xjour" if task.frequency <= 1 else f"{int(task.frequency / 7)}xsemaine" if task.frequency <= 7 else f"{int(task.frequency / 30.4)}xmois" if task.frequency <= 30.4 else f"{int(task.frequency / 365)}xan",
#                 "Priorité": int(task.priority),
#                 "Durée (min)": task.duration,
#                 "Date prévue": task.due_date.strftime("%d/%m/%Y") if task.due_date else "",
#             })