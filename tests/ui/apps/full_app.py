"""Harness mirroring app_streamlit.py's tab layout (minus locale/page-config,
which aren't relevant to state), so tests can check that a rerun triggered
by *any* tab doesn't lose or reset another tab's state — exactly what
happens in the real app, since Streamlit reruns and re-renders every tab's
content on every interaction, regardless of which tab is visually active.

Deliberately does NOT call ui_state.init_session_state() (that reads real
tasks/cache files from disk) — tests inject whatever state they need via
`at.session_state[...] = ...` before the first `.run()`, same as the
single-tab harnesses.
"""
import streamlit as st

from tasktracker.ui import general_tab, timer_tab, today_tab

st.session_state.setdefault("tasks", [])
st.session_state.setdefault("today_tasks", [])
st.session_state.setdefault("daily_limit", 60)
st.session_state.setdefault("active_duration", 0)
st.session_state.setdefault("nb_today_task", 0)
st.session_state.setdefault("today_grid_key", "TodayGrid1")
st.session_state.setdefault("general_grid_key", "GeneralGrid1")
st.session_state.setdefault("ascending", True)
st.session_state.setdefault("timer_running", False)
st.session_state.setdefault("timer_start_time", None)
st.session_state.setdefault("elapsed_accum", 0.0)

today_tab_ui, general_tab_ui, timer_tab_ui = st.tabs(["📝 Today", "⚙️ General", "⏱️ Timer"])

with today_tab_ui:
    today_tab.render()

with general_tab_ui:
    general_tab.render()

with timer_tab_ui:
    timer_tab.render()
