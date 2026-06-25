from datetime import datetime
import os
import re

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKLIST_FILE_NAME = os.path.join(SOURCE_DIR, "tasklist.json")

def date_to_string(date):
    return datetime.strftime(date, "%d/%m/%Y")

def date_to_iso_string(date):
    return date.isoformat()

def string_to_date(string):
    if string is None or string == "":
        return None
    if "-" in string:
        return datetime.fromisoformat(string).date()
    return datetime.strptime(string, "%d/%m/%Y").date()

