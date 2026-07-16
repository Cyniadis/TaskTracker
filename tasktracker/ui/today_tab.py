"""The 'Today' tab: check off and reschedule today's tasks."""
from __future__ import annotations

import streamlit as st
import pandas as pd 

from . import ui_state
from .grid_utils import find_task_by_id, tasks_to_dataframe
from ..json_utils import save_daily_limit


_COLUMN_ORDER = ["name", "frequency", "priority", "duration", "due_date", "done_date"]


@st.dialog("Rechedule task")
def edit_due_date(row: int):
    current = st.session_state.df.iloc[row]["due_date"]
    new_date = st.date_input(
        f"**{st.session_state.df.iloc[row]['name']}**",
        value=pd.to_datetime(current).date(),
    )
    if st.button("Save"):
        task = find_task_by_id(st.session_state.today_tasks, st.session_state.df.at[row, 'id'])
        task.due_date = new_date
        # st.session_state.df.at[row, "due_date"] = str(new_dae)
        
        st.rerun()

def _on_reschedule_click():
    click = st.session_state.reschedule_button
    edit_due_date(click["row"])


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
            on_change=lambda: save_daily_limit(daily_limit=st.session_state.daily_limit),
            width=100,
        )

        if st.button("🔄 Regenerate"):
            ui_state.regenerate_today_tasks()
            st.rerun()
        if st.button("🗑 Discard completed tasks"):
            ui_state.discard_completed_tasks()
            st.rerun()

    st.write(
        f"**Active duration:** {sum(t.duration for t in st.session_state.today_tasks)} min - "
        f"**Number of tasks:** {len(st.session_state.today_tasks)}"
    )


def _column_config() -> dict:
    return {
        "id": None,
        "frequency_count": None,
        "frequency_period": None,
        "initial_priority": None,
        "name": st.column_config.TextColumn("Task", width="large"),
        "frequency": st.column_config.TextColumn("Frequency", width="small"),
        "priority": st.column_config.NumberColumn("Priority", format="%.1f", width="small"),
        "duration": st.column_config.NumberColumn("Duration", width="small"),
        "due_date": st.column_config.DateColumn("Due date", format="localized"),
        "done_date": st.column_config.DateColumn("Done date", format="localized"),
        "reschedule": st.column_config.ButtonColumn("Reschedule", on_click=_on_reschedule_click, key="reschedule_button", alignment="left")
    }

def _on_row_selected() -> None:
    selected_rows = st.session_state[st.session_state.grid_key]["selection"]["rows"]
    filtered_df = st.session_state.df.iloc[selected_rows]
    selected_ids = filtered_df["id"].values
    for task in st.session_state.today_tasks:
        if len(selected_ids) > 0 and task.id in selected_ids:
            task.complete(ui_state.TODAY)
        else:
            task.uncomplete()
    ui_state.persist_tasks()




# def _sync_edits(df, edited_rows: dict) -> None:
#     reset_grid = False

#     for row_pos, changes in edited_rows.items():
#         task = find_task_by_id(st.session_state.tasks, int(df.iloc[row_pos]["id"]))

#         if "done" in changes:
#             if changes["done"]:
#                 task.complete(ui_state.TODAY)
#             else:
#                 task.uncomplete()

#         if "due_date" in changes:
#             new_due_date = changes["due_date"]
#             if new_due_date is None or new_due_date < ui_state.TODAY:
#                 st.toast("Chosen due date is in the past", icon="⚠️")
#                 reset_grid = True  # discard the invalid edit visually
#             else:
#                 task.due_date = new_due_date
#                 ui_state.reload_manage_grid()

#     if edited_rows:
#         ui_state.persist_tasks()
#     if reset_grid:
#         ui_state.reload_today_grid()


def render() -> None:
    _render_today_header()

    df = tasks_to_dataframe(st.session_state.today_tasks)
    st.session_state.df = df
    if df is None:
        st.info("No tasks were selected for today. Add or edit tasks in the General tab.")
        return

    df["frequency"] = df["frequency_count"].astype(str) + "x" + df["frequency_period"]
    key = st.session_state.grid_key
    event = st.dataframe(
        df,
        column_config=_column_config(),
        # column_order=_COLUMN_ORDER,
        hide_index=True,
        width="stretch",
        height=500,
        key=key,
        on_select=_on_row_selected,
        selection_mode=["multi-row"]
    )


    # _sync_edits(df, st.session_state[key]["edited_rows"])