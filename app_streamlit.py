import os
from datetime import datetime

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode
from st_aggrid.shared import JsCode
from TT_json_utils import read_tasks, write_tasks
from TT_task import *
from TT_task_selector import TT_TaskSelector
from TT_utils import *

TASKFILE = os.path.join(os.path.dirname(__file__), 'tasklist.json')
DEFAULT_DAILY_LIMIT = 60
TODAY = datetime.now().date()
LAST_CONFIG_FILE_NAME = os.path.join(SOURCE_DIR, "lastConfig.json")


def __load_tasks():
    print(f"Loading tasks from {TASKFILE}")
    return read_tasks(TASKFILE)

def __save_tasks():
    print(f"Saving tasks to {TASKFILE}")
    write_tasks(TASKFILE, st.session_state.tasks)

def __get_today_tasks(tasks, limit_minutes):
    print(f"Getting today's tasks with limit {limit_minutes} minutes")
    selector = TT_TaskSelector(daily_time_limit=limit_minutes)
    today_tasks = selector.get_daily_tasks(tasks, TODAY)
    __save_tasks()
    return today_tasks

def __regenerate_today_tasks():
    print("Regenerating today tasks")
    reset_and_update_tasks(TODAY, st.session_state.tasks)
    st.session_state.key_name = "key2" if st.session_state.key_name == "key1" else "key1"
    st.session_state.today_tasks = __get_today_tasks(st.session_state.tasks, st.session_state.daily_limit)
    
    
def __build_today_grid(today_sorted, key=None):
    print("Building today grid")
    df = pd.DataFrame.from_dict(today_sorted)
    if df.empty:
        return None

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    gb.configure_column('id', hide=True)
    gb.configure_column('name', headerName='Task', autoHeight=True, wrapText=True, checkboxSelection=True)
    gb.configure_column('frequency', headerName='Frequency', width=120, )
    gb.configure_column('priority', headerName='Priority', width=90)
    gb.configure_column('initial_priority', hide=True)
    gb.configure_column('duration', headerName='Duration', width=110)
    gb.configure_column('due_date', headerName='Due date', width=120)
    gb.configure_column('next_due_date', headerName='Next Due Date', width=120)
    gb.configure_column('done_date', header_name="Done date", width=120)
    gb.configure_column('last_done_date', headerName='Last Done Date', width=150)
    gb.configure_column('selected', headerName='Selected', hide=True)

    # Get the row indices of the completed tasks so they are preselected in the grid
    pre_selected_row_indices = [  str(df.index[idx]) for idx, task in enumerate(today_sorted) if is_task_completed(task, TODAY) ]
    gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False,  pre_selected_rows=pre_selected_row_indices)
    gb.configure_grid_options(domLayout='autoHeight')

    grid_options = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=500,
        key=key,
        update_on=['selectionChanged'],
        callback=__sync_today_grid,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )


def __sync_today_grid(grid_response):
    print("Sync today grid")
    selected_rows = grid_response.selected_rows

    selected_ids = set()
    if selected_rows is not None and len(selected_rows) > 0:
        # Get the IDs of the selected tasks and update their completion status
        selected_tasks = selected_rows.to_dict(orient='records')
        selected_ids = { int(row.get('id')) for row in selected_tasks }

    for task in st.session_state.today_tasks:
        if selected_ids and get_id(task) in selected_ids:
            complete_task(task, datetime.now().date())
        else:
            uncomplete_task(task)

    __save_tasks()


def __init_session_state():
    if 'tasks' not in st.session_state:
        st.session_state.tasks = __load_tasks()
    if 'daily_limit' not in st.session_state:
        st.session_state.daily_limit = DEFAULT_DAILY_LIMIT
    if 'today_tasks' not in st.session_state:
        st.session_state.today_tasks = __get_today_tasks(st.session_state.tasks, st.session_state.daily_limit)
    if 'key_name' not in st.session_state:
        st.session_state.key_name = "key1"

def __reset_all():
    st.session_state.tasks = __load_tasks()
    previous_selected = get_all_selected_tasks(st.session_state.tasks)
    update_priorities(tasks, previous_selected)
    st.session_state.daily_limit = DEFAULT_DAILY_LIMIT
    st.session_state.key_name = "key1"
    st.session_state.today_tasks = __get_today_tasks(st.session_state.tasks, st.session_state.daily_limit)

def __init_tasks():
    is_new_day = (read_last_date() == TODAY)
    if is_new_day: 
        save_last_date()
        st.session_state.tasks = __load_tasks()
        __reset_all()



        update_priorities(st.session_state.tasks, st.session_state.)



def main():
    st.set_page_config(page_title='TaskTracker', layout='wide')

    print("Starting TaskTracker Streamlit app")
    st.title('TaskTracker')
    st.markdown('Manage your task library and generate today\'s list using the existing priority scheduler.')



    __init_session_state()
    tabs = st.tabs(['Today', 'General'])

    with tabs[0]:
        st.markdown('### Tasks of ' + TODAY.strftime(' %B, %d %Y'))
        flex_container = st.container(horizontal=True, horizontal_alignment='left', vertical_alignment='center', height="stretch")
        flex_container.markdown('Daily duration limit (minutes) : ')
        flex_container.number_input(
            label='Daily duration limit',
            label_visibility='collapsed',
            min_value=30,
            max_value=720,
            step=15,
            key='daily_limit',
            width=100
        )
        flex_container.button('Regenerate', on_click=__regenerate_today_tasks)

        st.write(f"**Active duration:** {sum(get_duration(task) for task in st.session_state.today_tasks)} min - **Number of tasks:** {len(st.session_state.today_tasks)}")

        if not st.session_state.today_tasks:
            st.info('No tasks were selected for today. Add or edit tasks in the General tab.')
        else:
            __build_today_grid(st.session_state.today_tasks, key=st.session_state.key_name)

if __name__ == '__main__':
    main()
