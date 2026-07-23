"""Persistence regression tests: does state survive a rerun?

Streamlit reruns and re-renders *every* tab's content on every widget
interaction, regardless of which tab is visually active — that's just how
`st.tabs` works. A whole class of real bugs comes from code that
accidentally resets or recomputes state on a rerun it wasn't "supposed to"
affect (e.g. rebuilding a dataframe from scratch instead of reading
session_state, or a widget quietly reverting to its default because its
key wasn't wired up). These tests interact with one tab and then trigger a
rerun *from a different tab*, to check that a completed task, a checked
box, an edited row, or a running timer isn't silently lost in the crossfire.

See tests/ui/apps/full_app.py for the harness (mirrors app_streamlit.py's
tab layout) and tests/ui/conftest.py for the disk-I/O safety net.
"""
from __future__ import annotations

from datetime import date

import pytest

from tasktracker.task import Task
from tasktracker.ui import today_tab as tt

FROZEN_TODAY = date(2026, 7, 21)


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    monkeypatch.setattr(tt, "today", lambda: FROZEN_TODAY)


def _label(at, kind: str, needle: str):
    return next(w for w in getattr(at, kind) if needle in w.label)


class TestCrossTabPersistence:
    """Interact with one tab, rerun via a button in a *different* tab,
    then check the first tab's state is still intact."""

    def test_completed_task_survives_a_rerun_triggered_from_the_timer_tab(self, full_app):
        task = Task(id=1, name="Task A", duration=10, due_date=FROZEN_TODAY, done_date=FROZEN_TODAY)
        full_app.session_state["tasks"] = [task]
        full_app.session_state["today_tasks"] = [task]
        at = full_app.run()

        assert at.dataframe[0].value["completed"].iloc[0] == "🗹"

        reset_button = _label(at, "button", "⏹ Reset")
        at = reset_button.click().run()

        assert at.dataframe[0].value["completed"].iloc[0] == "🗹"
        assert task.done_date == FROZEN_TODAY

    def test_checkbox_state_survives_a_rerun_triggered_from_the_general_tab(self, full_app):
        full_app.session_state["tasks"] = [Task(id=1, name="Task A")]
        at = full_app.run()

        show_completed = _label(at, "checkbox", "Show completed tasks")
        at = show_completed.check().run()
        assert at.checkbox[0].value is True

        toggle_sort = _label(at, "button", "scending")
        at = toggle_sort.click().run()

        assert _label(at, "checkbox", "Show completed tasks").value is True

    def test_daily_limit_survives_a_rerun_triggered_from_the_general_tab(self, full_app):
        full_app.session_state["tasks"] = [Task(id=1, name="Task A")]
        at = full_app.run()

        at = at.number_input[0].set_value(90).run()
        assert at.session_state["daily_limit"] == 90

        reset_priorities = _label(at, "button", "Reset priorities")
        at = reset_priorities.click().run()

        assert at.number_input[0].value == 90
        assert at.session_state["daily_limit"] == 90

    def test_edited_task_name_survives_a_rerun_triggered_from_the_timer_tab(self, full_app):
        task = Task(id=1, name="Original name", duration=10)
        full_app.session_state["tasks"] = [task]
        at = full_app.run()

        # Simulate an edit already applied by the (untestable-via-AppTest)
        # data_editor grid — see test_general_tab_grid_logic.py for the
        # editing path itself. Here we only care whether it survives.
        task.name = "Edited name"
        at = full_app.run()
        assert at.session_state["tasks"][0].name == "Edited name"

        reset_button = _label(at, "button", "⏹ Reset")
        at = reset_button.click().run()

        assert at.session_state["tasks"][0].name == "Edited name"

    def test_reset_priorities_survives_a_rerun_triggered_from_the_today_tab(self, full_app):
        task = Task(id=1, name="Task A", priority=99.0, initial_priority=2.0)
        full_app.session_state["tasks"] = [task]
        full_app.session_state["today_tasks"] = []
        at = full_app.run()

        reset_priorities = _label(at, "button", "Reset priorities")
        at = reset_priorities.click().run()
        assert task.priority == 2.0

        regenerate = _label(at, "button", "Regenerate")
        at = regenerate.click().run()

        assert task.priority == 2.0

    def test_sort_direction_survives_a_rerun_triggered_from_the_today_tab(self, full_app):
        full_app.session_state["tasks"] = [Task(id=1, name="Task A")]
        at = full_app.run()

        toggle_sort = _label(at, "button", "scending")
        at = toggle_sort.click().run()
        assert at.session_state["ascending"] is False

        regenerate = _label(at, "button", "Regenerate")
        at = regenerate.click().run()

        assert at.session_state["ascending"] is False
        assert any(b.label == "▼ Descending" for b in at.button)

    def test_running_timer_elapsed_time_survives_a_rerun_triggered_from_the_today_tab(self, full_app):
        full_app.session_state["elapsed_accum"] = 305.0  # 5:05
        at = full_app.run()

        assert "00:05:05" in at.markdown[-1].value

        regenerate = _label(at, "button", "Regenerate")
        at = regenerate.click().run()

        assert "00:05:05" in at.markdown[-1].value

    def test_full_task_list_is_stable_across_an_unrelated_rerun(self, full_app):
        tasks = [Task(id=i, name=f"Task {i}") for i in range(5)]
        full_app.session_state["tasks"] = tasks
        at = full_app.run()

        reset_button = _label(at, "button", "⏹ Reset")
        at = reset_button.click().run()

        assert len(at.session_state["tasks"]) == 5
        assert {t.name for t in at.session_state["tasks"]} == {f"Task {i}" for i in range(5)}


class TestSameTabMultiRerunStability:
    """Simpler sanity check: rerunning a single tab repeatedly with no new
    interaction shouldn't drift or reset anything on its own."""

    def test_today_tab_is_stable_across_repeated_reruns(self, today_app):
        task = Task(id=1, name="Task A", duration=10, due_date=FROZEN_TODAY, done_date=FROZEN_TODAY)
        today_app.session_state["today_tasks"] = [task]
        at = today_app.run()

        for _ in range(3):
            at = at.run()

        assert len(at.dataframe[0].value) == 1
        assert at.dataframe[0].value["completed"].iloc[0] == "🗹"
        assert len(at.exception) == 0

    def test_general_tab_is_stable_across_repeated_reruns(self, general_app):
        tasks = [Task(id=1, name="Task A", priority=3.0, initial_priority=3.0)]
        general_app.session_state["tasks"] = tasks
        at = general_app.run()

        for _ in range(3):
            at = at.run()

        assert at.session_state["tasks"][0].name == "Task A"
        assert at.session_state["tasks"][0].priority == 3.0
        assert len(at.exception) == 0

    def test_timer_tab_elapsed_time_is_stable_across_repeated_reruns_when_stopped(self, timer_app):
        timer_app.session_state["elapsed_accum"] = 42.0
        at = timer_app.run()

        for _ in range(3):
            at = at.run()

        assert "00:00:42" in at.markdown[1].value
        assert len(at.exception) == 0
