"""TaskTracker — Streamlit entry point.

Run with: streamlit run app_streamlit.py
"""
from __future__ import annotations

import streamlit as st

from tasktracker.ui import ui_state
from tasktracker.ui import general_tab, timer_tab, today_tab

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')

def main() -> None:
    print("Starting Streamlit App")
    
    st.set_page_config(page_title="TaskTracker", layout="wide")
    st.title("TaskTracker", anchor=False)

    ui_state.init_session_state()

    today_tab_ui, general_tab_ui, timer_tab_ui = st.tabs(["📝 Today", "⚙️ General", "⏱️ Timer"])

    with today_tab_ui:
        print("Render Today tab")
        today_tab.render()

    with general_tab_ui:
        print("Render General tab")
        general_tab.render()

    with timer_tab_ui:
        print("Render Timer tab")
        timer_tab.render()


if __name__ == "__main__":
    main()
