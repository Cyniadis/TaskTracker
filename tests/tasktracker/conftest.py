"""Shared fixtures for the TaskTracker test suite."""
from __future__ import annotations

from datetime import date

import pytest

from tasktracker.task import Task


@pytest.fixture
def make_task():
    """Factory fixture: build a Task with sane defaults, overridable per-test."""
    def _make(
        id: int = 1,
        name: str = "Test task",
        frequency: str = "1xjour",
        priority: float = 1.0,
        initial_priority: float = 1.0,
        duration: int = 10,
        due_date=None,
        done_date=None,
    ) -> Task:
        return Task(
            id=id,
            name=name,
            frequency=frequency,
            priority=priority,
            initial_priority=initial_priority,
            duration=duration,
            due_date=due_date,
            done_date=done_date,
        )
    return _make


@pytest.fixture
def fixed_today():
    """A stable 'today' used across tests instead of datetime.now()."""
    return date(2026, 7, 21)
