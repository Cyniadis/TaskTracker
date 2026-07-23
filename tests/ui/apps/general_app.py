"""Harness script for AppTest: renders the 'General' tab against whatever
session_state a test injects beforehand via `at.session_state[...] = ...`.

Note: the tab's main grid (`st.data_editor`) has no AppTest query object,
so this harness is only useful for the toolbar (discard/export/import/
sort/reset) — see tests/ui/test_general_tab.py for what's covered, and
tests/test_json_utils.py / a dedicated logic test module for the grid's
row-add/row-edit callbacks, tested directly as plain functions instead.
"""
import streamlit as st

from tasktracker.ui import general_tab

st.session_state.setdefault("tasks", [])
st.session_state.setdefault("general_grid_key", "GeneralGrid1")

general_tab.render()
