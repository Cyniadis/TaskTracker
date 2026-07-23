"""Harness script for AppTest: renders the 'Today' tab against whatever
session_state a test injects beforehand via `at.session_state[...] = ...`,
mirroring the keys ui_state.init_session_state()/load_today_tasks() would
normally set up before the real app renders this tab.
"""
import streamlit as st

from tasktracker.ui import today_tab

st.session_state.setdefault("today_tasks", [])
st.session_state.setdefault("daily_limit", 60)
st.session_state.setdefault("active_duration", 0)
st.session_state.setdefault("nb_today_task", 0)
st.session_state.setdefault("today_grid_key", "TodayGrid1")

today_tab.render()
