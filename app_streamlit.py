import os
from datetime import datetime

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode
from TT_json_utils import *
from TT_task import *
from TT_utils import *
from TT_task_selector import compute_daily_tasks

TASKFILE = os.path.join(os.path.dirname(__file__), 'tasklist.json')
TODAY = datetime.now().date()


@st.cache_resource(show_spinner=False)
def _init_task_list(include_completed_today: bool = False):
    print("Initializing task lists")
    daily_limit = load_daily_limit()
    tasks = read_tasks(TASKFILE)
    today_tasks = compute_daily_tasks(tasks, TODAY, daily_limit, include_completed_today)
    _save_tasks(tasks)  # Save the updated tasks after computing today's tasks
    return tasks, today_tasks, daily_limit

def _save_tasks(tasks: list[TT_Task]):
    print(f"Saving tasks to {TASKFILE}")
    write_tasks(TASKFILE, tasks)

def _add_more_tasks():
    print("Addding more tasks")
    _init_task_list.clear()
    st.session_state.tasks, st.session_state.today_tasks, st.session_state.daily_limit = _init_task_list(True)

def _force_grid_reload():
    print("Forcing grid reload")
    st.session_state.grid_key = f'TodayGrid{datetime.now().timestamp()}'  # Change the key to force a re-render of the grid

def _discard_completed_tasks():
    print("Discarding completed tasks")
    completed_tasks = [task for task in st.session_state.today_tasks if task.is_task_completed(TODAY)]
    if not completed_tasks:
        return
    
    for task in completed_tasks:
        task.reset_and_update(TODAY)
    st.session_state.today_tasks = [task for task in st.session_state.today_tasks if task not in completed_tasks]
    _save_tasks(st.session_state.tasks)
    _force_grid_reload()
    
def _on_selection_changed(grid_response, today_tasks: list[TT_Task], tasks: list[TT_Task]):
    print("On Selection Changed")
    selected_rows = grid_response.selected_rows

    selected_ids = set()
    if selected_rows is not None and len(selected_rows) > 0:
        # Get the IDs of the selected tasks and update their completion status
        selected_tasks = selected_rows.to_dict(orient='records')
        selected_ids = { int(row.get('id')) for row in selected_tasks }

    for task in today_tasks:
        if selected_ids and task.get_id() in selected_ids:
            task.complete(TODAY)
        else:
            task.uncomplete()
    _save_tasks(tasks)

def _on_clean_cache_clicked():
    print("Clearing cache")
    st.cache_resource.clear()
    st.session_state.clear()
    

# =================== TODAY TASKS GRID =================
def _build_today_grid():
    print("Building today grid")
    today_tasks_dict = [task.task for task in st.session_state.today_tasks]
    df = pd.DataFrame.from_dict(today_tasks_dict)
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
    gb.configure_column('done_date', headerName='Done date', width=120)
    gb.configure_column('last_done_date', headerName='Last Done Date', width=150)
    gb.configure_column('selected', headerName='Selected', hide=True)

    # Get the row indices of the completed tasks so they are preselected in the grid
    pre_selected_row_indices = [  str(df.index[idx]) for idx, task in enumerate(st.session_state.today_tasks) if task.is_task_completed(TODAY) ]
    gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False,  pre_selected_rows=pre_selected_row_indices)

    gb.configure_grid_options(domLayout='autoHeight')

    grid_options = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=500,
        key=st.session_state.grid_key,
        update_on=['selectionChanged'],
        callback=lambda gr: _on_selection_changed(gr, st.session_state.today_tasks, st.session_state.tasks),
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )




# =================== STREAMLIT MAIN =================

def main():
    st.set_page_config(page_title='TaskTracker', layout='wide')

    print("Starting TaskTracker Streamlit app")
    st.title('TaskTracker')
    # st.markdown('Manage your task library and generate today\'s list using the existing priority scheduler.')

    tasks, today_tasks, daily_limit = _init_task_list()

    if 'tasks' not in st.session_state:
        st.session_state.tasks = tasks
    if 'today_tasks' not in st.session_state:
        st.session_state.today_tasks = today_tasks
    if 'daily_limit' not in st.session_state:
        st.session_state.daily_limit = daily_limit
    if 'grid_key' not in st.session_state:
        st.session_state.grid_key = 'TodayGrid1'

    # tabs = st.tabs(['Today', 'General'])
    tabs = st.tabs(['Today'])

    with tabs[0]:
        st.markdown('### Tasks of ' + TODAY.strftime('%a, %B %d, %Y'))
        flex_container = st.container(horizontal=True, horizontal_alignment='left', vertical_alignment='center', height="stretch")
        flex_container.markdown('Daily duration limit (minutes) : ')
        flex_container.number_input(
            label='Daily duration limit',
            label_visibility='collapsed',
            min_value=5,
            max_value=720,
            step=15,
            key='daily_limit',
            on_change=lambda: save_daily_limit(st.session_state.daily_limit),
            width=100
        )
        flex_container.button('Discard completed tasks', on_click=_discard_completed_tasks)
        flex_container.button('Regenerate', on_click=_add_more_tasks)
        flex_container.button('Reset all', on_click=_on_clean_cache_clicked)

        st.write(f"**Active duration:** {sum(task.get_duration() for task in st.session_state.today_tasks)} min - **Number of tasks:** {len(st.session_state.today_tasks)}")
        

        if not tasks:
            st.info('No tasks were selected for today. Add or edit tasks in the General tab.')
        else:
            _build_today_grid()

if __name__ == '__main__':
    main()
