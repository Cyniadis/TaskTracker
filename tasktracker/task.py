"""Domain model for a recurring task.

This module has no dependency on Streamlit, pandas, or any storage
mechanism — it only knows about the shape and behaviour of a `Task`.

`due_date` and `done_date` are intentionally read-only from outside this
module (exposed as properties backed by private `_due_date`/`_done_date`
fields). Every way of changing them goes through a named method
(`set_due_date`, `set_done_date`, `cancel`, `manually_reschedule`,
`compute_next_due_date`, `schedule_for`, `complete`/`uncomplete`)
so the due-date-state invariants below can't be bypassed by a stray
`task.due_date = ...` somewhere in the UI layer.

Due-date-state invariants
--------------------------
`cancelled` and `manually_rescheduled_on` are mutually
exclusive *for the same day* — a task can't simultaneously be cancelled,
force-scheduled for today, and rescheduled out of today. Every transition
method that sets one of these explicitly clears the other two. This is
enforced at the transition-method level rather than trusted to callers.

`completed` (from `is_completed_on`/`status()`) is independent of the
above — a task can be both manually-scheduled for today and completed
today, for instance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, field
from datetime import date, timedelta
from enum import Enum
from typing import Any
from common.consts import PRIORITY_INCREMENT, today
from common.common_utils import generate_unique_id, normalize_date

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


class TaskDueDateState(str, Enum):
    """Mutually-exclusive due-date-related states a task can be in on a given day."""

    NORMAL = "normal"
    CANCELLED = "cancelled"
    MANUALLY_RESCHEDULED = "rescheduled"


@dataclass
class TaskState:
    """A task's status as of a given date.

    `completed` is independent of `due_date_state` — see the module
    docstring for why these aren't folded into one combined enum.
    """

    completed: bool = False
    due_date_state: TaskDueDateState = TaskDueDateState.NORMAL
    
    def __str__(self) -> str:
        return f"{'🗹' if self.completed else '☐'} {self.due_date_state.value}"
    
    @classmethod
    def from_dict(cls, data: dict) -> "TaskState":
        return cls(
            completed=data.get("completed", False),
            due_date_state=TaskDueDateState(data.get("due_date_state", TaskDueDateState.NORMAL.value))
        )
        

    
@dataclass
class Task:
    """A recurring chore, with everything needed to schedule and track it."""

    name: str
    frequency: str = "1xjour"
    priority: float = 0.0
    initial_priority: float = 0.0
    duration: int = 0

    
    # Private — see module docstring. Exposed read-only via properties below.
    _id: str = field(default_factory=lambda: generate_unique_id())
    _state : TaskState = field(default_factory=lambda: TaskState(completed=False, due_date_state=TaskDueDateState.NORMAL))
    _due_date: date | None = None
    _done_date: date | None = None

    def __post_init__(self) -> None:
        self._due_date = normalize_date(self._due_date)
        self._done_date = normalize_date(self._done_date)

        # Stashed pre-completion state, used by uncomplete() to undo the most
        # recent complete() call exactly (not a dataclass field: deliberately
        # excluded from to_dict()/persistence — it's session-only).
        self._pre_complete_priority: float | None = self.priority
        self._pre_complete_done_date: date | None = self._done_date

    # -- read-onlydate access ------------------------------------------------
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def due_date(self) -> date | None:
        return self._due_date

    @property
    def done_date(self) -> date | None:
        return self._done_date

    @property
    def state(self) -> TaskState:
        """Return the task's status as of today, including both completion and due date state."""
        return self._state
        # if self.cancelled:
        #     due_date_state = TaskDueDateState.CANCELLED
        # elif self.manually_rescheduled_on == today():
        #     due_date_state = TaskDueDateState.MANUALLY_RESCHEDULED
        # else:
        #     due_date_state = TaskDueDateState.NORMAL

        # return TaskState(completed=self.is_completed_on(today()), due_date_state=due_date_state)

    # -- (de)serialization -------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Build a Task from a JSON-shaped dict.

        Legacy files may still have `due_date` set to the old date.max
        sentinel that used to mean "cancelled" — migrated here into the
        explicit `cancelled` flag instead.
        """
        known_fields = {f.name for f in fields(cls) if not f.name.startswith("_")}
        kwargs = {
            key: value for key, value in data.items()
            if key in known_fields 
        }
        kwargs["_due_date"] = data.get("due_date")
        kwargs["_done_date"] = data.get("done_date")
        kwargs["_id"] = data.get("id")
        kwargs["_state"] = TaskState.from_dict(data.get("state", {"completed": False, "due_date_state": TaskDueDateState.NORMAL.value}))
        return cls(**kwargs)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["id"] = payload.pop("_id")
        payload["due_date"] = payload.pop("_due_date")
        payload["done_date"] = payload.pop("_done_date")
        payload["state"] =  payload.pop("_state")
        for field_name in ("due_date", "done_date"):
            value = payload[field_name]
            payload[field_name] = value.isoformat() if value else None
        return payload

    # -- frequency helpers ---------------------------------------------------
    @property
    def frequency_obj(self) -> Frequency:
        return Frequency.parse(self.frequency)

    def get_next_due_date(self, current_date: date) -> date:
        return current_date + timedelta(days=self.frequency_obj.days)

    # -- priority helpers ---------------------------------------------------
    def increment_priority(self):
        self.priority += PRIORITY_INCREMENT

    # -- due-date transitions -------------------------------------------------
    #
    # Every method below is a deliberate, named transition.
    
    def set_due_date(self, new_date: date | None) -> None:
        """Direct due-date edits (grid, dialog's custom-date save).

        Just a plain date change — clears cancellation (setting a real date
        is incompatible with being cancelled) but is NOT by itself a
        "reschedule"; callers doing an actual reschedule action should also
        call manually_reschedule() right after this.
        """
        self._due_date = normalize_date(new_date)
        if self._state.due_date_state == TaskDueDateState.CANCELLED:
            self._state.due_date_state = TaskDueDateState.NORMAL

    def set_done_date(self, new_date: date | None) -> None:
        """Direct done-date edits (grid, 'Completed on' dialog save)."""
        self._done_date = normalize_date(new_date)

    def cancel(self) -> None:
        """Mark this task as having no active due date, deliberately."""
        self._state.due_date_state = TaskDueDateState.CANCELLED
        self._due_date = None

    def manually_reschedule(self, current_date: date) -> None:
        """Force this task onto `current_date`'s list, bypassing the daily
        time budget. Tasks in this state should always survive a
        regeneration of today's list (see selector.compute_daily_tasks's
        `pre_selected_tasks`)."""
        self._due_date = current_date
        self._state.due_date_state = TaskDueDateState.MANUALLY_RESCHEDULED


    def set_next_due_date(self, from_date: date = None) -> None:
        """Housekeeping's 'completed on time -> advance to next occurrence'
        transition. `from_date` is the due date being rolled forward from."""
        if from_date is None:
            from_date = self._due_date
        self.set_due_date(self.get_next_due_date(from_date))



    # -- lifecycle -----------------------------------------------------------
    def complete(self, completion_date: date) -> None:
        """Mark the task done on `completion_date`, remembering the prior
        priority/done_date so `uncomplete()` can undo this exact change."""
        self._pre_complete_priority = self.priority
        self._pre_complete_done_date = self._done_date
        self._done_date = completion_date
        self.priority = self.initial_priority
        self._state.completed = True

    def uncomplete(self) -> None:
        """Undo the most recent complete() call, restoring priority and
        done_date to what they were right before it."""
        self._done_date = self._pre_complete_done_date
        if self._pre_complete_priority is not None:
            self.priority = self._pre_complete_priority
        self._pre_complete_priority = None
        self._pre_complete_done_date = None
        self._state.completed = False

    def is_completed_on(self, current_date: date) -> bool:
        return self._done_date is not None and self._done_date == current_date

    # -- editing ---------------------------------------------------------
    def set_field(self, field_name: str, value: Any) -> None:
        """Generic setter used by grid-edit callbacks for plain fields.

        due_date/done_date are intentionally NOT settable this way — use
        set_due_date()/set_done_date() (or cancel()/manually_reschedule()) 
        instead, since those enforce the due-date-state
        invariants documented at the top of this module.
        """
        if field_name in ("due_date", "done_date"):
            raise AttributeError(
                f"{field_name!r} must be set via set_due_date()/set_done_date(), "
                "not set_field()."
            )
        known_fields = {f.name for f in fields(self) if not f.name.startswith("_")}
        if field_name not in known_fields:
            raise AttributeError(f"Unknown task field: {field_name!r}")
        setattr(self, field_name, value)

    def apply_snapshot(self, data: dict) -> None:
        """Revert editable fields to a prior snapshot (from the change-tracking
        baseline — see tasktracker/change_tracking.py). Doesn't touch id,
        manually_scheduled_on, or rescheduled_on — those are per-day markers,
        not "edits" a user would want to discard.
        """
        self.name = data["name"]
        self.frequency = data["frequency"]
        self.priority = data["priority"]
        self.initial_priority = data["initial_priority"]
        self.duration = data["duration"]
        self._due_date = normalize_date(data.get("due_date"))
        self._done_date = normalize_date(data.get("done_date"))


    def is_completed(self) -> bool:
        """Return True if this task is completed on any date (not just today)."""
        return self._state.completed
    
    def is_cancelled(self) -> bool:
        """Return True if this task is cancelled on any date (not just today)."""
        return self._state.due_date_state == TaskDueDateState.CANCELLED

    def is_manually_rescheduled(self) -> bool:
        """Return True if this task is manually rescheduled on any date (not just today)."""
        return self._state.due_date_state == TaskDueDateState.MANUALLY_RESCHEDULED
    
    def is_manually_rescheduled_on_today(self) -> bool:
        return self.is_manually_rescheduled() and self._due_date == today()