from datetime import datetime, timedelta
from TT_structs import *
            
def schedule_tasks(tasks, start_date, end_date, daily_limit):
    """
    Schedules tasks between start_date and end_date respecting durations, priorities, and frequencies.

    :param tasks: List of Task objects.
    :param start_date: Start date for scheduling (datetime).
    :param end_date: End date for scheduling (datetime).
    :param daily_limit: Maximum time available per day (in minutes).
    :return: A dictionary mapping dates to lists of tasks.
    """
    if not tasks:
        print("No tasks to schedule.")
        return {}

    # Sort tasks by priority (descending)
    tasks.sort(key=lambda t: t.priority, reverse=True)

    # Initialize schedule
    schedule = {}
    current_date = start_date

    while current_date <= end_date:
        schedule[current_date] = []
        current_date += timedelta(days=1)

    # Schedule tasks
    for task in tasks:
        next_date = start_date
        while next_date <= end_date:
            if next_date not in schedule:
                schedule[next_date] = []

            if task.due_date and next_date > task.due_date:
                break

            if sum(t.duration for t in schedule[next_date]) + task.duration <= daily_limit:
                schedule[next_date].append(task)
                next_date += timedelta(days=task.frequency)  # Respect task frequency
                task.due_date = next_date
            else:
                next_date += timedelta(days=1)

    return schedule

def print_schedule(task_schedule):
    """Prints the task schedule in a readable format."""
    print("\nTask Schedule:\n")
    for date, day_tasks in task_schedule.items():
        total_time = sum(task.duration for task in day_tasks)
        if day_tasks:
            print(f"{date.strftime('%Y-%m-%d')} (Total time: {total_time} minutes):\n  " + "\n  ".join(f"- {task}" for task in day_tasks))
        else:
            print(f"{date.strftime('%Y-%m-%d')} (Total time: {total_time} minutes): No tasks scheduled")
        print()
  