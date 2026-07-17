"""Shared helpers for turning Task lists into st.data_editor tables."""
from __future__ import annotations

import pandas as pd

from ..task import Task, Period

PERIOD_OPTIONS = [p.value for p in Period]


def tasks_to_toady_dataframe(tasks: list[Task]) -> pd.DataFrame:
    """Convert tasks into a display-ready dataframe.

    Frequency is split into `frequency_count` / `frequency_period` so each
    half gets its own widget (number input / dropdown) in the editor —
    this replaces the old combined JS cell editor. Dates are kept as real
    `date` objects so `st.column_config.DateColumn` can format/parse them.
    """
    if not tasks:
        return None


    records = []
    for task in tasks:
        freq = task.frequency_obj
        records.append({
            "id": task.id,
            "name": task.name,
            "frequency": task.frequency,
            "priority": task.priority,
            "initial_priority": task.initial_priority,
            "duration": task.duration,
            "due_date": task.due_date,
            "done_date": task.done_date,
            "reschedule": ":material/edit: Reschedule"
        })
    return pd.DataFrame.from_records(records)



def tasks_to_general_dataframe(tasks: list[Task]) -> pd.DataFrame:
    """Convert tasks into a display-ready dataframe.

    Frequency is split into `frequency_count` / `frequency_period` so each
    half gets its own widget (number input / dropdown) in the editor —
    this replaces the old combined JS cell editor. Dates are kept as real
    `date` objects so `st.column_config.DateColumn` can format/parse them.
    """
    if not tasks:
        return None


    records = []
    for task in tasks:
        freq = task.frequency_obj
        records.append({
            "id": task.id,
            "name": task.name,
            "frequency_count": freq.count,
            "frequency_period": freq.period.value,
            "priority": task.priority,
            "initial_priority": task.initial_priority,
            "duration": task.duration,
            "due_date": task.due_date,
            "done_date": task.done_date,
        })
    return pd.DataFrame.from_records(records)


def find_task_by_id(tasks: list[Task], task_id: int) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise KeyError(f"No task with id={task_id}")
