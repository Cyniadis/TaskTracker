"""Generic change-tracking against a durable, file-backed baseline snapshot.

Replaces the old orig_*/restore()/get_changes() fields that used to live
directly on Task and GroceryItem. Domain objects no longer know anything
about change-tracking — this module owns that concern entirely, working
off each object's own to_dict()/id.

The baseline is just the domain list's own JSON serialization, written to
its own file (not folded into cache.json, which holds small scalar
settings — a whole task list is a different kind of thing) via the same
read_json/write_json helpers cache.json uses. It's refreshed whenever the
domain list is freshly loaded from disk (process start, reset_app(),
import) — the same "since the last full reload" reference point orig_*
had, just durable across process restarts and shared across workers,
instead of living in a per-process st.cache_resource.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar

from .common_json_utils import read_json, write_json

T = TypeVar("T")


def snapshot(items: list[T], path: Path, to_dict: Callable[[T], dict]) -> None:
    """Persist the current state of `items` as the new baseline.

    Call this whenever `items` is freshly (re)loaded from its own source of
    truth — that's what makes this "since the last full reload", matching
    the old orig_* semantics.
    """
    write_json(path, [to_dict(item) for item in items])


def load_baseline(path: Path) -> dict[int, dict]:
    """Load the baseline as a dict keyed by id, for O(1) per-item lookup."""
    raw = read_json(path) or []
    return {entry["id"]: entry for entry in raw}


def ensure_baseline(items: list[T], path: Path, to_dict: Callable[[T], dict]) -> dict[int, dict]:
    """Load the baseline, creating it from `items` first if the file doesn't exist yet."""
    if not path.exists():
        snapshot(items, path, to_dict)
    return load_baseline(path)


def get_changes(
    item_dict: dict,
    baseline: dict[int, dict],
    labels: dict[str, str],
    formatters: dict[str, Callable[[Any], str]] | None = None,
) -> list[tuple[str, str, str]]:
    """Diff `item_dict` (an already-serialized item, e.g. task.to_dict())
    against its baseline entry.

    Only fields present in `labels` are compared — that's how callers
    exclude fields that shouldn't count as "edits" (e.g. id, or per-day
    markers like manually_scheduled_on/rescheduled_on).

    Returns [] if the item has no baseline entry (e.g. it was added after
    the last snapshot — nothing to diff against).
    """
    base = baseline.get(item_dict["id"])
    if base is None:
        return []

    formatters = formatters or {}

    def _format(field_name: str, value: Any) -> str:
        if field_name in formatters:
            return formatters[field_name](value)
        return "—" if value is None else str(value)

    diffs = []
    for field_name, label in labels.items():
        old, new = base.get(field_name), item_dict.get(field_name)
        if old != new:
            diffs.append((label, _format(field_name, old), _format(field_name, new)))
    return diffs


def get_baseline_entry(item_dict: dict, baseline: dict[int, dict]) -> dict | None:
    """Return the raw baseline dict for this item's id, or None if it predates
    the baseline (e.g. added after the last snapshot — nothing to discard to)."""
    return baseline.get(item_dict["id"])
