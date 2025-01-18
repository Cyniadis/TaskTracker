from datetime import datetime
from dataclasses import dataclass

@dataclass
class Task:
    id: int
    name: str
    duration: int  # in minutes
    priority: int  # higher value = higher priority
    frequency: float  # in days
    due_date: datetime = None  # Optional: If task is time-bound
    last_done_date: datetime = None
    completed: bool = False


    def __repr__(self):
        return f"Task({self.name} ({self.duration}m, P{self.priority}, every {int(self.frequency)} days)"


def date_to_string(date):
    return  datetime.strftime(date, "%d/%m/%Y")


def string_to_date(string):
    return datetime.strptime(string, "%d/%m/%Y")