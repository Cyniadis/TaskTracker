"""TaskTracker — Streamlit entry point.

Run with: streamlit run app_streamlit.py
"""
from __future__ import annotations

import locale

import streamlit as st

from tasktracker.ui import ui_state
from tasktracker.ui import general_tab, timer_tab, today_tab

try:
    # Used for localized date formatting (e.g. "lundi 20 juillet 2026").
    # Requires the fr_FR.UTF-8 locale to be installed on the host (see
    # packages.txt's "locales-all"); fall back to the system default
    # rather than crashing the whole app if it's missing.
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
except locale.Error:
    print("Warning: fr_FR.UTF-8 locale not available, falling back to system default.")


def main() -> None:
    print()
    print("Starting Streamlit App")

    st.set_page_config(page_title="TaskTracker", layout="wide")
    st.title("TaskTracker", anchor=False)

    ui_state.init_session_state()

    today_tab_ui, general_tab_ui, timer_tab_ui = st.tabs(["📝 Today", "⚙️ General", "⏱️ Timer"])

    with today_tab_ui:
        today_tab.render()

    with general_tab_ui:
        general_tab.render()

    with timer_tab_ui:
        timer_tab.render()


if __name__ == "__main__":
    main()
