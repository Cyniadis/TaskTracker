from datetime import datetime
import os

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKLIST_FILE_NAME = os.path.join(SOURCE_DIR, "tasklist.csv")
SCHEDULE_FILE_NAME = os.path.join(SOURCE_DIR, "schedule.csv")
TASKS_YAML_FOLDER = os.path.join(SOURCE_DIR, "tasks_yaml")

def date_to_string(date):
    return datetime.strftime(date, "%d/%m/%Y")

def string_to_date(string):
    return datetime.strptime(string, "%d/%m/%Y").date()