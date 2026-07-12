"""TaskTracker — Streamlit entry point.

Run with: streamlit run app_streamlit.py
"""
from __future__ import annotations

import streamlit as st

from tasktracker.ui import ui_state
from tasktracker.json_utils import save_daily_limit
from tasktracker.ui import general_tab, timer_tab, today_tab

import locale
locale.setlocale(locale.LC_ALL, 'fr_FR')

# import pdb
# pdb.set_trace()

def _render_today_header() -> None:
    st.markdown("### Tâches du " + ui_state.TODAY.strftime("%A %d %B %Y"), anchors=False)

    with st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", height="stretch"):
        st.markdown("Daily duration limit (minutes) : ", anchors=False)
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
        st.button("Discard completed tasks", on_click=ui_state.discard_completed_tasks)
        st.button("Regenerate", on_click=ui_state.regenerate_today_tasks)
        st.button("Reload", on_click=ui_state.reset_app)

    st.write(
        f"**Active duration:** {sum(t.duration for t in st.session_state.today_tasks)} min - "
        f"**Number of tasks:** {len(st.session_state.today_tasks)}"
    )


def main() -> None:
    print("Starting Streamlit App")

    st.set_page_config(page_title="TaskTracker", layout="wide")
    st.title("TaskTracker", anchor=False)

    ui_state.init_session_state()

    today_tab_ui, general_tab_ui, timer_tab_ui = st.tabs(["📝 Today", "⚙️ General", "⏱️ Timer"])

    with today_tab_ui:
        _render_today_header()
        today_tab.render()

    with general_tab_ui:
        general_tab.render()

    with timer_tab_ui:
        st.markdown("### Timer", anchors=False)
        timer_tab.render()


if __name__ == "__main__":
    main()
