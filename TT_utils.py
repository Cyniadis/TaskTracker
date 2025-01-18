from datetime import datetime

TASKLIST_FILE_NAME = "tasklist.csv"
SCHEDULE_FILE_NAME = "schedule.csv"
TASKS_YAML_FOLDER = "tasks_yaml"

def date_to_string(date):
    return datetime.strftime(date, "%d/%m/%Y")

def string_to_date(string):
    return datetime.strptime(string, "%d/%m/%Y").date()