import copy
import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from st_aggrid.shared import JsCode
from TT_json_utils import read_tasks, write_tasks
from TT_task import *
from TT_task_selector import TT_TaskSelector
from TT_utils import *

TASKFILE = os.path.join(os.path.dirname(__file__), 'tasklist.json')
SORT_OPTIONS = ['Task', 'Frequency', 'Priority', 'Duration', 'Due date', 'Completed']
GENERAL_SORT_OPTIONS = ['Name', 'Priority', 'Duration', 'Due date', 'Frequency']
DEFAULT_DAILY_LIMIT = 240

st.set_page_config(page_title='TaskTracker', layout='wide')


def __load_tasks():
    return read_tasks(TASKFILE)

def __get_today_tasks(tasks, limit_minutes):
    selector = TT_TaskSelector(daily_time_limit=limit_minutes)
    return selector.get_daily_tasks(tasks, datetime.now().date())

def __save_tasks():
    write_tasks(TASKFILE, st.session_state.tasks)

def __build_today_grid(today_sorted, key=None):
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
    gb.configure_column('due_date', headerName='Due date', width=120, cellDataType='dateTime', hide=True)
    gb.configure_column('completed', hide=True)
    gb.configure_column('last_done_date', headerName='Last Done Date', width=150, cellDataType='dateTimeString')
    
    gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False)
    gb.configure_grid_options(domLayout='autoHeight', suppressMovableColumns=True, getRowId=JsCode('function(data) { return data.id; }'),)

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

    return grid_response


def __sync_today_grid(grid_response):
    selected_rows = grid_response.selected_rows
    
    # Reset tasks to uncompleted before updating the selected ones
    st.session_state.tasks = copy.deepcopy(st.session_state.init_tasks)
    
    if selected_rows is not None and len(selected_rows) > 0:
        # Get the IDs of the selected tasks and update their completion status
        selected_tasks = selected_rows.to_dict(orient='records') 
        selected_ids = { int(row.get('id')) for row in selected_tasks }

        for task in st.session_state.tasks:
            if get_id(task) in selected_ids:
                complete_task(task, datetime.now().date())
            
    __save_tasks()


def __skip_task(task_id):
    task = next(task for task in st.session_state.tasks if get_id(task) == task_id)
    task['due_date'] = datetime.now().date() + timedelta(days=1)
    __save_tasks()


def __move_task(task_id):
    date_key = f'move_date-{task_id}'
    move_date = st.session_state.get(date_key, datetime.now().date())
    task = next(task for task in st.session_state.tasks if get_id(task) == task_id)
    task['due_date'] = move_date
    __save_tasks()


def __init_session_state():
    if 'tasks' not in st.session_state:
        st.session_state.tasks = __load_tasks()
    if 'daily_limit' not in st.session_state:
        st.session_state.daily_limit = DEFAULT_DAILY_LIMIT
    if 'today_tasks' not in st.session_state:
        st.session_state.today_tasks = __get_today_tasks(st.session_state.tasks, st.session_state.daily_limit)
    if 'init_tasks' not in st.session_state:
        st.session_state.init_tasks = copy.deepcopy(st.session_state.tasks)

def main():
    print("Starting TaskTracker Streamlit app")
    st.title('TaskTracker')
    st.markdown('Manage your task library and generate today\'s list using the existing priority scheduler.')

    __init_session_state()
    tabs = st.tabs(['Today', 'General'])

    with tabs[0]:
        st.markdown('### Tasks of ' + datetime.now().strftime(' %B, %d %Y'))
        flex_container = st.container(horizontal=True, horizontal_alignment='left', vertical_alignment='bottom', height="stretch")
        flex_container.markdown('Daily duration limit (minutes) : ')
        flex_container.number_input(
            label='Daily duration limit',
            label_visibility='hidden',
            min_value=30,
            max_value=720,
            step=15,
            key='daily_limit',
            width=100
        )

        st.write(f"**Active duration:** {sum(get_duration(task) for task in st.session_state.today_tasks)} min")

        if not st.session_state.today_tasks:
            st.info('No tasks were selected for today. Add or edit tasks in the General tab.')
        else:
            grid_response = __build_today_grid(st.session_state.today_tasks, key='today_active_grid')

    return 0

if __name__ == '__main__':
    main()
