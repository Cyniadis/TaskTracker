"""Domain model for a recurring task.

This module has no dependency on Streamlit, pandas, or any storage
mechanism — it only knows about the shape and behaviour of a `Task`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
from .consts import DATE_FORMAT, PRIORITY_INCREMENT

class Period(str, Enum):
    """The recurrence unit of a task, e.g. 'twice a WEEK'."""

    DAY = "jour"
    WEEK = "semaine"
    MONTH = "mois"
    YEAR = "an"

    @property
    def length_in_days(self) -> float:
        return {
            Period.DAY: 1.0,
            Period.WEEK: 7.0,
            Period.MONTH: 30.4,
            Period.YEAR: 365.0,
        }[self]


@dataclass(frozen=True)
class Frequency:
    """How often a task recurs, e.g. '2xsemaine' -> twice a week."""

    count: int = 1
    period: Period = Period.DAY

    @classmethod
    def parse(cls, text: str | None) -> "Frequency":
        """Parse strings like '3xmois'. Falls back to the default (1xjour) on bad input."""
        if text:
            try:
                count_str, period_str = text.lower().split("x", 1)
                return cls(count=int(count_str), period=Period(period_str))
            except (ValueError, KeyError):
                pass
        return cls()

    @property
    def days(self) -> float:
        """Average number of days between two occurrences."""
        return self.period.length_in_days / self.count

    def __str__(self) -> str:
        return f"{self.count}x{self.period.value}"


def normalize_date(value: Any) -> date | None:
    """Coerce assorted date-like inputs (str, datetime, pandas NaT...) into a plain `date`."""
    if value is None or value == "":
        return None

    try:
        if value != value:  # NaN / NaT are the only values that aren't equal to themselves
            return None
    except Exception:
        pass

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() == "nan":
            return None
        if "/" in value:
            return datetime.strptime(value, DATE_FORMAT).date()
        return datetime.fromisoformat(value).date()
    if hasattr(value, "item"):  # numpy / pandas scalar
        return normalize_date(value.item())

    raise TypeError(f"Unsupported date value: {value!r}")


_DATE_FIELDS = ("due_date", "done_date")


@dataclass
class Task:
    """A recurring chore, with everything needed to schedule and track it."""

    id: int
    name: str
    frequency: str = "1xjour"
    priority: float = 0.0
    initial_priority: float = 0.0
    duration: int = 0
    due_date: date | None = None
    done_date: date | None = None

    orig_frequency: str = "1xjour"
    orig_priority: float = 0.0
    orig_initial_priority: float = 0.0
    orig_duration: int = 0
    orig_due_date: date | None = None
    orig_done_date: date | None = None


    def __post_init__(self) -> None:
        for field_name in _DATE_FIELDS:
            setattr(self, field_name, normalize_date(getattr(self, field_name)))
        self.orig_frequency = self.frequency
        self.orig_priority = self.priority
        self.orig_initial_priority = self.initial_priority
        self.orig_duration = self.duration
        self.orig_due_date = self.due_date
        self.orig_done_date = self.done_date

    # -- (de)serialization -------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        known_fields = {f.name for f in fields(cls) if not f.name.startswith("orig_")}
        return cls(**{key: value for key, value in data.items() if key in known_fields})

    def to_dict(self) -> dict:
        payload = {k: v for k,v in asdict(self).items()  if not k.startswith("orig_") }
        for field_name in _DATE_FIELDS:
            value = payload[field_name]
            payload[field_name] = value.isoformat() if value else None
        return payload

    # -- frequency helpers ---------------------------------------------------
    @property
    def frequency_obj(self) -> Frequency:
        return Frequency.parse(self.frequency)

    def compute_next_due_date(self, current_date: date) -> date:
        return current_date + timedelta(days=self.frequency_obj.days)

    # -- priority helpers ---------------------------------------------------
    
    def increment_priority(self):
        self.priority += PRIORITY_INCREMENT

    # -- lifecycle -----------------------------------------------------------
    def complete(self, completion_date: date) -> None:
        self.done_date = completion_date
        self.priority = self.initial_priority

    def uncomplete(self) -> None:
        self.done_date = self.orig_done_date
        self.priority = self.orig_priority
        pass

    def is_completed_on(self, current_date: date) -> bool:
        return self.done_date is not None and self.done_date == current_date

    def schedule_for(self, current_date: date) -> None:
        """Mark this task as picked for `current_date` and roll its next occurrence forward."""
        self.due_date = current_date

    def set_field(self, field_name: str, value: Any) -> None:
        """Generic setter used by grid-edit callbacks (keeps date fields normalized)."""
        if field_name not in {f.name for f in fields(self)}:
            raise AttributeError(f"Unknown task field: {field_name!r}")
        if field_name in _DATE_FIELDS:
            value = normalize_date(value)
        setattr(self, field_name, value)

    def restore(self): 
        self.frequency = self.orig_frequency
        self.priority = self.orig_priority
        self.initial_priority = self.orig_initial_priority
        self.duration = self.orig_duration
        self.due_date = self.orig_due_date
        self.done_date = self.orig_done_date
