"""Minimal harness script so AppTest can drive tasktracker.ui.timer_tab.render()
in isolation, with the same session-state keys ui_state.init_session_state()
would normally set up before the real app renders this tab.
"""
import streamlit as st

from tasktracker.ui import timer_tab

st.session_state.setdefault("timer_running", False)
st.session_state.setdefault("timer_start_time", None)
st.session_state.setdefault("elapsed_accum", 0.0)

timer_tab.render()
