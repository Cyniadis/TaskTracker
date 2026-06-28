from datetime import datetime
import os
import re

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKLIST_FILE_NAME = os.path.join(SOURCE_DIR, "tasklist.json")

def date_to_string(date: datetime) -> str:
    if date is None: 
        return None
    return datetime.strftime(date, "%d/%m/%Y")

def string_to_date(string):
    if string is None or string == "":
        return None
    if "-" in string:
        return datetime.fromisoformat(string).date()
    return datetime.strptime(string, "%d/%m/%Y").date()

def frequency_to_days(frequency : str) -> float:
    try:
        number, period = frequency.lower().split('x')
        number = int(number)
        if period == 'jour':
            return 1.0 / number
        if period == 'semaine':
            return 7.0 / number
        if period == 'mois':
            return 30.4 / number
        if period in ('an', 'ans'):
            return 365.0 / number
    except Exception:
        pass
    return 1.0