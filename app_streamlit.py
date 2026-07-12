"""TaskTracker — Streamlit entry point.

Run with: streamlit run app_streamlit.py
"""
from __future__ import annotations

import streamlit as st

from tasktracker import state
from tasktracker.storage import save_daily_limit
from tasktracker.ui import general_tab, timer_tab, today_tab


def _render_today_header() -> None:
    st.markdown("### Tasks of " + state.TODAY.strftime("%a, %B %d, %Y"))

    with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", height="stretch"):
        st.markdown("Daily duration limit (minutes) : ")
        st.number_input(
            label="Daily duration limit",
            label_visibility="collapsed",
            min_value=5,
            max_value=720,
            step=15,
            key="daily_limit",
            on_change=lambda: save_daily_limit(st.session_state.daily_limit),
            width=100,
        )
        st.button("Discard completed tasks", on_click=state.discard_completed_tasks)
        st.button("Regenerate", on_click=state.regenerate_today_tasks)
        st.button("Reload", on_click=state.reset_app)

    st.write(
        f"**Active duration:** {sum(t.duration for t in st.session_state.today_tasks)} min - "
        f"**Number of tasks:** {len(st.session_state.today_tasks)}"
    )


def main() -> None:
    print("Starting Streamlit App")

    st.set_page_config(page_title="TaskTracker", layout="wide")
    st.title("TaskTracker")

    state.init_session_state()

    today_tab_ui, general_tab_ui, timer_tab_ui = st.tabs(["📝 Today", "⚙️ General", "⏱️ Timer"])

    with today_tab_ui:
        _render_today_header()
        today_tab.render()

    with general_tab_ui:
        general_tab.render()

    with timer_tab_ui:
        st.markdown("### Timer")
        timer_tab.render()


if __name__ == "__main__":
    main()
