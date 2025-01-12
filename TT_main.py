from TT_scheduler import *
from TT_csv_utils import *
      
if __name__ == "__main__":
    # Input CSV file
    file_name = "tasklist.csv"
    file_name_updated = "tasklist_updated.csv"

    # Define schedule range and daily limit
    start_date = datetime.today()
    end_date = start_date + timedelta(weeks=4)
    daily_limit = 3 * 60  # 3 hours in minutes

    # Read tasks from file
    tasks = read_tasks(file_name)

    # Generate schedule
    task_schedule = schedule_tasks(tasks, start_date, end_date, daily_limit)

    # Save updated tasks back to the file
    write_tasks(file_name_updated, tasks)

    # Print schedule
    print_schedule(task_schedule)
