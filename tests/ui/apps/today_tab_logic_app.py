"""Harness to exercise the 'Today' tab's row-action callback logic
(`_on_row_selected`, the complete/uncomplete toggle) through a real AppTest
session. `st.dataframe`'s ButtonColumn clicks aren't drivable through
AppTest (only plain widget interactions are), so this harness wires a
plain button that calls the same private callback the real button-column
would call, using session state a test sets up beforehand.
"""
import streamlit as st

from tasktracker.ui import today_tab as tt

st.session_state.setdefault("tasks", [])
st.session_state.setdefault("today_tasks", [])

if st.button("toggle_row"):
    tt._on_row_selected()
