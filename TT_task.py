from datetime import datetime, timedelta
from dataclasses import dataclass
from TT_utils import *
import yaml
import os 


@dataclass
class TT_Task:
    id: int = 0
    name: str = ""
    duration: int = 0 # in minutes
    initial_priority: float = 0  # higher value = higher priority
    priority: float = 0 # higher value = higher priority
    frequency: float = 0 # in days
    due_date: datetime.date = None  # Optional: If task is time-bound
    last_done_date: datetime.date = None
    completed: bool = False

    def __repr__(self):
        return f"\033[1m{self.name}\033[0m ({self.duration}m, P{self.priority}, every {float(self.frequency)} days) - \
due on {date_to_string(self.due_date) if self.due_date else 'None'}, \
done on {date_to_string(self.last_done_date) if self.last_done_date else 'None'}"
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, TT_Task):
            return False
        return self.id == other.id

    def serialize(self, folder : str) -> None:
        """
        Serializes a Task object and writes it to a YAML file.
        """
        task_dict = {
            'id': self.id,
            'name': self.name,
            'duration': self.duration,
            'initial_priority': self.initial_priority,
            'priority': self.priority,
            'frequency': self.frequency,
            'due_date': date_to_string(self.due_date) if self.due_date else None,
            'last_done_date': date_to_string(self.last_done_date) if self.last_done_date else None,
            'completed': self.completed
        }

        f = os.path.join(folder, self.get_yaml_filename())
        with open(f, 'w') as file:
            yaml.dump(task_dict, file, default_flow_style=False, sort_keys=False)


    def deserialize(self, filename: str) -> None:
        """
        Deserializes a YAML file into a Task object.
        """
        with open(filename, 'r') as file:
            task_dict = yaml.safe_load(file)

        self.id=task_dict['id']
        self.name=task_dict['name']
        self.duration=task_dict['duration']
        self.priority=task_dict['priority']
        self.initial_priority=task_dict['initial_priority']
        self.frequency=task_dict['frequency']
        self.due_date=string_to_date(task_dict['due_date']) if task_dict['due_date'] else None
        self.last_done_date=string_to_date(task_dict['last_done_date']) if task_dict['last_done_date'] else None
        self.completed=task_dict['completed']
        
    def get_yaml_filename(self):
        return id_to_yaml_filename(self.id)
        
    def is_task_due(self, current_date: datetime.date) -> bool:
        days_since_completion = (current_date - self.last_done_date).days
        return days_since_completion >= self.frequency

    def complete_task(self, completion_date: datetime.date) -> None:
        """Complete task and adjust priority"""
        self.completed = True
        self.last_done_date = completion_date
        self.due_date = completion_date + timedelta(days=self.frequency)
        self.priority = self.initial_priority
        
    def update_serialized(self, folder: str) -> None:
        f = os.path.join(folder, self.get_yaml_filename())
        if not os.path.exists(f): 
            self.serialize(folder)
        else :
            task_tmp = TT_Task()
            task_tmp.deserialize(f) 
            if task_tmp.name != self.name  or \
               task_tmp.initial_priority != self.initial_priority or \
               task_tmp.duration != self.duration or \
               task_tmp.frequency != self.frequency: 
                self.serialize(folder)
            

