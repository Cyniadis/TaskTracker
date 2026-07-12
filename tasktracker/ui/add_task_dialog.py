"""Modal form used to create a brand-new task."""
from __future__ import annotations

import streamlit as st

from . import ui_state
from ..task import Period, Task


@st.dialog("Add a new task")
def add_task_dialog() -> None:
    name = st.text_input("Name*", placeholder="e.g. 🍴 Nettoyer la table")

    freq_col, period_col = st.columns(2)
    frequency_count = freq_col.number_input("Frequency*", min_value=1, step=1, value=1)
    period = period_col.selectbox("Every*", list(Period), format_func=lambda p: p.value)

    initial_priority = st.number_input("Initial priority*", min_value=0.0, step=0.5, value=1.0)
    duration = st.number_input("Duration (min)*", min_value=1, step=5, value=10)
    due_date = st.date_input("Due date (optional)", value=None)

    st.caption("* Mandatory fields")

    submit_col, cancel_col = st.columns(2)
    submitted = submit_col.button("Add task", type="primary", use_container_width=True)
    cancelled = cancel_col.button("Cancel", use_container_width=True)

    if cancelled:
        st.rerun()

    if not submitted:
        return

    if not name.strip():
        st.error("Task name is required.")
        return

    task = Task(
        id=ui_state.next_task_id(),
        name=name.strip(),
        frequency=f"{int(frequency_count)}x{period.value}",
        priority=initial_priority,
        initial_priority=initial_priority,
        duration=int(duration),
        due_date=due_date,
    )
    ui_state.add_task(task)
    st.rerun()
