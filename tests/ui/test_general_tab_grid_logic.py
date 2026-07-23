"""Tests for general_tab's `_apply_added_row` / `_apply_edited_rows`
callbacks (the 'General' tab's grid add/edit logic), driven through
general_grid_logic_app.py since AppTest can't drive `st.data_editor`
directly. See tests/ui/conftest.py for why.
"""
from __future__ import annotations

import pandas as pd
import pytest

from tasktracker.task import Task


class TestApplyAddedRow:
    def test_appends_a_new_task_with_a_fresh_id(self, general_grid_logic_app):
        existing = Task(id=0, name="Existing", duration=5)
        general_grid_logic_app.session_state["tasks"] = [existing]
        at = general_grid_logic_app.run()

        at.session_state["new_row"] = {
            "name": "New Task",
            "frequency_count": 2,
            "frequency_period": "semaine",
            "initial_priority": 3.0,
            "duration": 15,
        }
        add_button = next(b for b in at.button if b.label == "apply_added_row")
        at = add_button.click().run()

        assert len(at.exception) == 0
        tasks = at.session_state["tasks"]
        assert len(tasks) == 2
        new_task = tasks[-1]
        assert new_task.id == 1  # next after id=0
        assert new_task.name == "New Task"
        assert new_task.frequency == "2xsemaine"
        assert new_task.priority == 3.0  # priority starts equal to initial_priority
        assert new_task.initial_priority == 3.0
        assert new_task.duration == 15
        assert new_task.due_date is None
        assert new_task.done_date is None

    def test_strips_whitespace_from_the_name(self, general_grid_logic_app):
        general_grid_logic_app.session_state["tasks"] = []
        at = general_grid_logic_app.run()

        at.session_state["new_row"] = {
            "name": "  Padded name  ",
            "frequency_count": 1,
            "frequency_period": "jour",
            "initial_priority": 1.0,
            "duration": 5,
        }
        add_button = next(b for b in at.button if b.label == "apply_added_row")
        at = add_button.click().run()

        assert at.session_state["tasks"][0].name == "Padded name"

    def test_first_task_gets_id_zero(self, general_grid_logic_app):
        general_grid_logic_app.session_state["tasks"] = []
        at = general_grid_logic_app.run()

        at.session_state["new_row"] = {
            "name": "First", "frequency_count": 1, "frequency_period": "jour",
            "initial_priority": 1.0, "duration": 5,
        }
        add_button = next(b for b in at.button if b.label == "apply_added_row")
        at = add_button.click().run()

        assert at.session_state["tasks"][0].id == 0


class TestApplyEditedRows:
    def _edit_df_for(self, task: Task) -> pd.DataFrame:
        freq = task.frequency_obj
        return pd.DataFrame.from_records([{
            "id": task.id, "name": task.name,
            "frequency_count": freq.count, "frequency_period": freq.period.value,
            "priority": task.priority, "initial_priority": task.initial_priority,
            "duration": task.duration,
        }])

    def test_edits_a_plain_field(self, general_grid_logic_app):
        task = Task(id=5, name="Old name", duration=10)
        general_grid_logic_app.session_state["tasks"] = [task]
        at = general_grid_logic_app.run()

        at.session_state["edit_df"] = self._edit_df_for(task)
        at.session_state["edited_rows"] = {0: {"name": "New name"}}
        edit_button = next(b for b in at.button if b.label == "apply_edited_rows")
        at = edit_button.click().run()

        assert len(at.exception) == 0
        assert task.name == "New name"

    def test_recombines_frequency_count_and_period_into_frequency(self, general_grid_logic_app):
        task = Task(id=5, name="Task", frequency="1xjour")
        general_grid_logic_app.session_state["tasks"] = [task]
        at = general_grid_logic_app.run()

        at.session_state["edit_df"] = self._edit_df_for(task)
        at.session_state["edited_rows"] = {0: {"frequency_count": 3, "frequency_period": "mois"}}
        edit_button = next(b for b in at.button if b.label == "apply_edited_rows")
        at = edit_button.click().run()

        assert task.frequency == "3xmois"

    def test_editing_only_frequency_count_keeps_the_existing_period(self, general_grid_logic_app):
        task = Task(id=5, name="Task", frequency="2xsemaine")
        general_grid_logic_app.session_state["tasks"] = [task]
        at = general_grid_logic_app.run()

        at.session_state["edit_df"] = self._edit_df_for(task)
        at.session_state["edited_rows"] = {0: {"frequency_count": 5}}
        edit_button = next(b for b in at.button if b.label == "apply_edited_rows")
        at = edit_button.click().run()

        assert task.frequency == "5xsemaine"

    def test_edits_multiple_fields_in_the_same_row(self, general_grid_logic_app):
        task = Task(id=5, name="Task", duration=10, priority=1.0)
        general_grid_logic_app.session_state["tasks"] = [task]
        at = general_grid_logic_app.run()

        at.session_state["edit_df"] = self._edit_df_for(task)
        at.session_state["edited_rows"] = {0: {"duration": 25, "priority": 4.5}}
        edit_button = next(b for b in at.button if b.label == "apply_edited_rows")
        at = edit_button.click().run()

        assert task.duration == 25
        assert task.priority == 4.5

    def test_edits_the_correct_row_among_several(self, general_grid_logic_app):
        t1 = Task(id=1, name="First")
        t2 = Task(id=2, name="Second")
        general_grid_logic_app.session_state["tasks"] = [t1, t2]
        at = general_grid_logic_app.run()

        edit_df = pd.concat([self._edit_df_for(t1), self._edit_df_for(t2)], ignore_index=True)
        at.session_state["edit_df"] = edit_df
        at.session_state["edited_rows"] = {1: {"name": "Second, edited"}}
        edit_button = next(b for b in at.button if b.label == "apply_edited_rows")
        at = edit_button.click().run()

        assert t1.name == "First"
        assert t2.name == "Second, edited"
