"""Tests for grocery_tab's `_apply_added_row` / `_apply_edited_rows` /
`_on_data_change` callbacks (the 'Groceries' tab's grid add/edit/delete
logic), driven through grocery_grid_logic_app.py — same rationale as
tests/tasktracker/test_general_tab_grid_logic.py: `st.data_editor` has no
AppTest query object.

This file didn't exist before: the 'General' tab's grid callbacks had
coverage, but the 'Groceries' tab's never did, which is exactly how the
id-type bugs here (GroceryItem(id=...) TypeError, int(uuid) ValueError on
edit/delete) went unnoticed after ids switched from int to uuid string.
"""
from __future__ import annotations

import pandas as pd
import pytest

from groceries.grocery import GroceryItem, GroceryState


class TestApplyAddedRow:
    def test_appends_a_new_item_with_a_fresh_id(self, grocery_grid_logic_app):
        existing = GroceryItem(name="Existing")
        grocery_grid_logic_app.session_state["groceries"] = [existing]
        at = grocery_grid_logic_app.run()

        at.session_state["new_row"] = {"name": "New Item"}
        add_button = next(b for b in at.button if b.label == "apply_added_row")
        at = add_button.click().run()

        assert len(at.exception) == 0
        items = at.session_state["groceries"]
        assert len(items) == 2
        new_item = items[-1]
        assert new_item.id == "1"  # next after id=0, via the sequential-id test fixture
        assert new_item.name == "New Item"
        assert new_item.state == GroceryState.TO_BUY.value

    def test_strips_whitespace_from_the_name(self, grocery_grid_logic_app):
        grocery_grid_logic_app.session_state["groceries"] = []
        at = grocery_grid_logic_app.run()

        at.session_state["new_row"] = {"name": "  Padded  "}
        add_button = next(b for b in at.button if b.label == "apply_added_row")
        at = add_button.click().run()

        assert len(at.exception) == 0
        assert at.session_state["groceries"][0].name == "Padded"


class TestApplyEditedRows:
    def _edit_df_for(self, *items: GroceryItem) -> pd.DataFrame:
        return pd.DataFrame.from_records([{"id": i.id, "name": i.name} for i in items])

    def test_edits_a_plain_field(self, grocery_grid_logic_app):
        item = GroceryItem(name="Old name")
        grocery_grid_logic_app.session_state["groceries"] = [item]
        at = grocery_grid_logic_app.run()

        at.session_state["edit_df"] = self._edit_df_for(item)
        at.session_state["edited_rows"] = {0: {"name": "New name"}}
        edit_button = next(b for b in at.button if b.label == "apply_edited_rows")
        at = edit_button.click().run()

        assert len(at.exception) == 0
        assert item.name == "New name"

    def test_edits_the_correct_row_among_several(self, grocery_grid_logic_app):
        i1 = GroceryItem(name="First")
        i2 = GroceryItem(name="Second")
        grocery_grid_logic_app.session_state["groceries"] = [i1, i2]
        at = grocery_grid_logic_app.run()

        at.session_state["edit_df"] = self._edit_df_for(i1, i2)
        at.session_state["edited_rows"] = {1: {"name": "Second, edited"}}
        edit_button = next(b for b in at.button if b.label == "apply_edited_rows")
        at = edit_button.click().run()

        assert len(at.exception) == 0
        assert i1.name == "First"
        assert i2.name == "Second, edited"


class TestOnDataChangeDeletedRows:
    """Regression coverage: ids are uuid strings now, and a stray
    `int(df.iloc[row_pos]["id"])` cast used to raise ValueError here."""

    def _grid_df_for(self, *items: GroceryItem) -> pd.DataFrame:
        return pd.DataFrame.from_records([{"id": i.id, "name": i.name} for i in items])

    def test_deleting_a_row_removes_the_matching_item(self, grocery_grid_logic_app):
        i1 = GroceryItem(name="Keep")
        i2 = GroceryItem(name="Delete me")
        grocery_grid_logic_app.session_state["groceries"] = [i1, i2]
        at = grocery_grid_logic_app.run()

        at.session_state["edit_df"] = self._grid_df_for(i1, i2)
        at.session_state["editor_state"] = {
            "added_rows": [], "edited_rows": {}, "deleted_rows": [1],
        }
        button = next(b for b in at.button if b.label == "on_data_change")
        at = button.click().run()

        assert len(at.exception) == 0
        remaining = at.session_state["groceries"]
        assert [i.name for i in remaining] == ["Keep"]
