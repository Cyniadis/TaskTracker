from TT_scheduler import *
from TT_csv_utils import *
from TT_ui import *

import argparse
      
if __name__ in {"__main__", "__mp_main__"}:
    # Input CSV file
    task_list_file_name = "tasklist.csv"
    schedule_file_name = "schedule.csv"

    # Define schedule range and daily limit
    start_date = datetime.today().now()
    end_date = start_date + timedelta(days=365)
    daily_limit = 3 * 60  # 3 hours in minutes

    # Read tasks from file
    tasks = read_tasks(task_list_file_name)

    # Generate schedule
    task_schedule = schedule_tasks(tasks, start_date, end_date, daily_limit)

    # Save updated tasks back to the file
    write_schedule(schedule_file_name, task_schedule)

    # print_schedule(task_schedule)
