"""AppTest-based tests for tasktracker/ui/today_tab.py.

Row-action buttons (complete/uncomplete, reschedule) live inside an
`st.dataframe` ButtonColumn, which AppTest can't click — see
test_today_tab_grid_logic.py and tests/ui/conftest.py for how those are
covered instead. The reschedule dialog itself isn't covered here either
(AppTest can't drive `st.dialog` contents).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from tasktracker.task import Task
from tasktracker.ui import today_tab as tt

FROZEN_TODAY = date(2026, 7, 21)


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    monkeypatch.setattr(tt, "today", lambda: FROZEN_TODAY)


class TestHeader:
    def test_shows_the_tasks_du_heading(self, today_app):
        at = today_app.run()
        assert "Tâches du" in at.markdown[0].value

    def test_daily_limit_number_input_reflects_session_state(self, today_app):
        today_app.session_state["daily_limit"] = 45
        at = today_app.run()
        assert at.number_input[0].value == 45

    def test_changing_daily_limit_updates_session_state(self, today_app):
        at = today_app.run()
        at = at.number_input[0].set_value(90).run()
        assert at.session_state["daily_limit"] == 90
        assert len(at.exception) == 0

    def test_shows_the_three_toggle_checkboxes(self, today_app):
        at = today_app.run()
        labels = {c.label for c in at.checkbox}
        assert labels == {"Show completed tasks", "Show rescheduled tasks", "Allow future tasks"}

    def test_shows_active_duration_and_task_count(self, today_app):
        today_app.session_state["active_duration"] = 25
        today_app.session_state["nb_today_task"] = 2
        at = today_app.run()
        body_text = " ".join(m.value for m in at.markdown)
        assert "25" in body_text
        assert "2" in body_text

    def test_renders_without_error(self, today_app):
        at = today_app.run()
        assert len(at.exception) == 0


class TestEmptyState:
    def test_shows_info_message_when_no_tasks_today(self, today_app):
        at = today_app.run()
        assert len(at.dataframe) == 0
        assert any("No tasks were selected for today" in i.value for i in at.info)


class TestTaskTable:
    def test_shows_one_row_per_today_task(self, today_app):
        t1 = Task(id=1, name="Task A", duration=10, priority=2.0, initial_priority=2.0, due_date=FROZEN_TODAY)
        t2 = Task(id=2, name="Task B", duration=5, priority=1.0, initial_priority=1.0, due_date=FROZEN_TODAY)
        today_app.session_state["today_tasks"] = [t1, t2]
        at = today_app.run()

        df = at.dataframe[0].value
        assert len(df) == 2
        assert set(df["name"]) == {"Task A", "Task B"}

    def test_completed_column_reflects_done_state(self, today_app):
        done = Task(id=1, name="Done", duration=5, due_date=FROZEN_TODAY, done_date=FROZEN_TODAY)
        pending = Task(id=2, name="Pending", duration=5, due_date=FROZEN_TODAY, done_date=None)
        today_app.session_state["today_tasks"] = [done, pending]
        at = today_app.run()

        df = at.dataframe[0].value
        completed_by_name = dict(zip(df["name"], df["completed"]))
        assert completed_by_name["Done"] == "🗹"
        assert completed_by_name["Pending"] == "☐"

    def test_renders_without_error_when_populated(self, today_app):
        t1 = Task(id=1, name="Task A", duration=10, due_date=FROZEN_TODAY)
        today_app.session_state["today_tasks"] = [t1]
        at = today_app.run()
        assert len(at.exception) == 0


class TestRegenerateButton:
    def test_click_does_not_error(self, today_app):
        today_app.session_state["tasks"] = []
        today_app.session_state["today_tasks"] = []
        at = today_app.run()

        regenerate = next(b for b in at.button if "Regenerate" in b.label)
        at = regenerate.click().run()

        assert len(at.exception) == 0

    def test_pulls_a_due_today_task_from_the_full_list(self, today_app):
        due_today = Task(id=1, name="Due today", duration=10, due_date=FROZEN_TODAY)
        today_app.session_state["tasks"] = [due_today]
        today_app.session_state["today_tasks"] = []
        at = today_app.run()

        regenerate = next(b for b in at.button if "Regenerate" in b.label)
        at = regenerate.click().run()

        assert any(t.id == 1 for t in at.session_state["today_tasks"])
