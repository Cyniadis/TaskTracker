"""The 'Today' tab: check off and reschedule today's tasks."""
from __future__ import annotations

import streamlit as st
import pandas as pd 

from . import ui_state
from .grid_utils import find_task_by_id, tasks_to_today_dataframe, get_theme_color
from ..json_utils import save_daily_limit
from ..consts import TODAY


_COLUMN_ORDER = ["name", "frequency", "priority", "duration", "due_date", "done_date"]


@st.dialog("Rechedule task")
def edit_due_date(row: int):
    row_date = st.session_state.today_df.iloc[row]["due_date"]  
    current = row_date if  row_date is not None else TODAY
    task = find_task_by_id(st.session_state.tasks, st.session_state.today_df.at[row, 'id'])
    with st.container(horizontal=True, vertical_alignment="bottom"):
        new_date = st.date_input(
            f"**{st.session_state.today_df.iloc[row]['name']}**",
            value=pd.to_datetime(current).date(),
            width=200
        )
        if st.button("Save"):
            task.due_date = new_date
            ui_state.persist_tasks
            st.rerun()
            
    if st.button("Skip this time"):
        task.due_date = task.compute_next_due_date(task.due_date)
        ui_state.persist_tasks()
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

        st.button("🔄 Regenerate", on_click=ui_state.regenerate_today_tasks)

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
        "reschedule": st.column_config.ButtonColumn("", on_click=_on_reschedule_click, key="reschedule_button", alignment="left")
    }

def _on_row_selected() -> None:
    selected_rows = st.session_state[st.session_state.grid_key]["selection"]["rows"]
    filtered_df = st.session_state.today_df.iloc[selected_rows]
    selected_ids = filtered_df["id"].values
    for task in st.session_state.today_tasks:
        if len(selected_ids) > 0 and task.id in selected_ids:
            task.complete(TODAY)
        elif task.is_completed_on(TODAY) and task.id not in selected_ids:
            print(task.name)
            task.uncomplete()
            
    ui_state.cache_today_tasks()
    ui_state.persist_tasks()
    ui_state.reload_today_grid()


def color_by_due_date(row):
    color = get_theme_color("textColor")
    if TODAY == row['done_date']: 
        color = get_theme_color("doneTextColor") 
    elif row['due_date'] != TODAY:
        color = get_theme_color("hiddenTextColor")
    return [f"color: {color}"] * len(row)


def pre_select_rows(df: pd.DataFrame) -> dict:
    completed_tasks = [ task for task in st.session_state.tasks if task.is_completed_on(TODAY) ]
    rows_to_select = { "rows": [] }
    for task in completed_tasks:
        completed_row = df.index[df["id"] == task.id]
        if not completed_row.empty:
            rows_to_select["rows"].append(completed_row[0])
    return {"selection": rows_to_select}

def render() -> None:
    _render_today_header()

    df = tasks_to_today_dataframe(st.session_state.today_tasks)
    st.session_state.today_df = df
    if df is None:
        st.info("No tasks were selected for today. Add or edit tasks in the General tab.")
        return

    styled_df = df.style.apply(color_by_due_date, axis=1)

    key = st.session_state.grid_key
    event = st.dataframe(
        styled_df,
        column_config=_column_config(),
        # column_order=_COLUMN_ORDER,
        hide_index=True,
        width="content",
        height="content",
        key=key,
        on_select=_on_row_selected,
        selection_mode=["multi-row"],
        selection_default=pre_select_rows(df)
    )