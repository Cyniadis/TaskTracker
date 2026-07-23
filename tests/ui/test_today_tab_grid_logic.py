"""Tests for today_tab's `_on_row_selected` callback (the complete/
uncomplete toggle behind the 'Today' tab's ButtonColumn), driven through
today_tab_logic_app.py since AppTest can't click a real ButtonColumn.
See tests/ui/conftest.py for why.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from tasktracker.task import Task

TODAY_ROW = {"id": 1, "completed": "☐"}
DONE_ROW = {"id": 1, "completed": "🗹"}


def _click_toggle(app, df_row: dict):
    app.session_state["today_df"] = pd.DataFrame.from_records([df_row])
    app.session_state["complete_button"] = {"row": 0}
    return app.run().button[0].click().run()


class TestOnRowSelected:
    def test_unchecked_row_marks_the_task_complete(self, today_tab_logic_app):
        task = Task(id=1, name="Task A", priority=5.0, initial_priority=2.0, done_date=None)
        today_tab_logic_app.session_state["tasks"] = [task]
        today_tab_logic_app.session_state["today_tasks"] = [task]

        at = _click_toggle(today_tab_logic_app, TODAY_ROW)

        assert len(at.exception) == 0
        assert task.done_date is not None
        assert task.priority == 2.0  # reset to initial_priority by Task.complete()

    def test_checked_row_marks_the_task_uncomplete(self, today_tab_logic_app):
        task = Task(id=1, name="Task A", priority=2.0, initial_priority=2.0)
        task.complete(date(2026, 7, 21))
        today_tab_logic_app.session_state["tasks"] = [task]
        today_tab_logic_app.session_state["today_tasks"] = [task]

        at = _click_toggle(today_tab_logic_app, DONE_ROW)

        assert len(at.exception) == 0
        assert task.done_date is None

    def test_toggling_twice_returns_to_the_original_state(self, today_tab_logic_app):
        task = Task(id=1, name="Task A", priority=3.0, initial_priority=1.0, done_date=None)
        today_tab_logic_app.session_state["tasks"] = [task]
        today_tab_logic_app.session_state["today_tasks"] = [task]

        at = _click_toggle(today_tab_logic_app, TODAY_ROW)
        assert task.done_date is not None

        at = _click_toggle(today_tab_logic_app, DONE_ROW)
        assert task.done_date is None
        assert task.priority == 3.0
