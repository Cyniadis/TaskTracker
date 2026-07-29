"""Domain model for a grocery list item.

Mirrors task.py's shape (orig_* snapshot fields for change tracking, a
set_field()/restore()/get_changes() trio) but carries a tri-state `state`
field instead of a schedule, and a single `last_bought_date` field to
remember when the item was last bought — the "track when I last bought
something" equivalent of a Task's `done_date`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date
from enum import Enum
from typing import Any

from common.ui_common import normalize_date


class GroceryState(str, Enum):
    """Whether a grocery item is something to buy, already bought, or paused."""

    TO_BUY = "to_buy"
    BOUGHT = "bought"
    NOT_TO_BUY = "not_to_buy"


# Display labels used in the 'État' dropdown. The emoji circle doubles as
# the color cue the state is meant to convey — Styler doesn't apply to
# editable st.data_editor columns (see the General tab), so an actual
# colored row isn't an option here; the emoji in the dropdown value itself
# is the workaround.
STATE_TO_LABEL: dict[GroceryState, str] = {
    GroceryState.TO_BUY: "⚪ À acheter",
    GroceryState.BOUGHT: "🟢 Acheté",
    GroceryState.NOT_TO_BUY: "⚫ Ne pas acheter",
}
LABEL_TO_STATE: dict[str, GroceryState] = {label: state for state, label in STATE_TO_LABEL.items()}


@dataclass
class GroceryItem:
    """A single item on the grocery list."""

    id: int
    name: str
    state: str = GroceryState.TO_BUY.value
    last_bought_date: date | None = None

    orig_name: str = ""
    orig_state: str = GroceryState.TO_BUY.value
    orig_last_bought_date: date | None = None

    def __post_init__(self) -> None:
        self.last_bought_date = normalize_date(self.last_bought_date)
        self.orig_name = self.name
        self.orig_state = self.state
        self.orig_last_bought_date = self.last_bought_date

    # -- (de)serialization ----------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "GroceryItem":
        known_fields = {f.name for f in fields(cls) if not f.name.startswith("orig_")}
        return cls(**{key: value for key, value in data.items() if key in known_fields})

    def to_dict(self) -> dict:
        payload = {k: v for k, v in asdict(self).items() if not k.startswith("orig_")}
        payload["last_bought_date"] = (
            payload["last_bought_date"].isoformat() if payload["last_bought_date"] else None
        )
        return payload

    # -- state helpers ----------------------------------------------------------
    @property
    def state_label(self) -> str:
        return STATE_TO_LABEL[GroceryState(self.state)]

    def set_state_from_label(self, label: str, today_date: date) -> None:
        """Apply a state change coming from the dropdown's display label.

        Moving to BOUGHT stamps `last_bought_date` with `today_date` — the
        one state transition with a side effect, so it gets its own method
        rather than going through the generic set_field() below.
        """
        new_state = LABEL_TO_STATE[label]
        self.state = new_state.value
        if new_state is GroceryState.BOUGHT:
            self.last_bought_date = today_date

    def set_field(self, field_name: str, value: Any) -> None:
        """Generic setter used by plain (non-state) column edits, e.g. 'name'."""
        if field_name not in {f.name for f in fields(self)}:
            raise AttributeError(f"Unknown grocery field: {field_name!r}")
        setattr(self, field_name, value)

    def restore(self) -> None:
        """Revert to the last-persisted (orig_*) snapshot."""
        self.name = self.orig_name
        self.state = self.orig_state
        self.last_bought_date = self.orig_last_bought_date

    def get_changes(self) -> list[tuple[str, str, str]]:
        """Return (field_label, old_value, new_value) for every field that
        differs from the item's original (orig_*) snapshot. Empty if nothing changed."""
        def _format_value(value: Any) -> str:
            return "—" if value is None else str(value)

        diffs: list[tuple[str, str, str]] = []
        if self.name != self.orig_name:
            diffs.append(("Name", self.orig_name, self.name))
        if self.state != self.orig_state:
            diffs.append((
                "État",
                STATE_TO_LABEL[GroceryState(self.orig_state)],
                STATE_TO_LABEL[GroceryState(self.state)],
            ))
        if self.last_bought_date != self.orig_last_bought_date:
            diffs.append((
                "Last bought",
                _format_value(self.orig_last_bought_date),
                _format_value(self.last_bought_date),
            ))
        return diffs
