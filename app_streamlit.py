import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from st_aggrid.shared import JsCode
from TT_json_utils import read_tasks, write_tasks
from TT_task import complete_task, clone_task, uncomplete_task
from TT_task_selector import TT_TaskSelector
from TT_utils import date_to_string

TASKFILE = os.path.join(os.path.dirname(__file__), 'tasklist.json')
FREQUENCY_OPTIONS = ['1xjour', '2xjour', '1xsemaine', '2xsemaine', '1xmois', '2xmois', '1xan']
SORT_OPTIONS = ['Task', 'Frequency', 'Priority', 'Duration', 'Due date', 'Completed']
GENERAL_SORT_OPTIONS = ['Name', 'Priority', 'Duration', 'Due date', 'Frequency']

st.set_page_config(page_title='TaskTracker', layout='wide')


def load_tasks():
    tasks = read_tasks(TASKFILE)
    for task in tasks:
        if 'completed' not in task:
            task['completed'] = False
    return tasks


def frequency_to_days(frequency):
    try:
        number, period = frequency.lower().split('x')
        number = int(number)
        if period == 'jour':
            return 1.0 / number
        if period == 'semaine':
            return 7.0 / number
        if period == 'mois':
            return 30.4 / number
        if period in ('an', 'ans'):
            return 365.0 / number
    except Exception:
        pass
    return 1.0


def task_frequency_label(frequency_value):
    if isinstance(frequency_value, str):
        return frequency_value
    return next((opt for opt in FREQUENCY_OPTIONS if abs(frequency_to_days(opt) - frequency_value) < 0.001), '1xjour')


def sort_tasks(tasks, sort_key, descending=True):
    key_map = {
        'Task': lambda task: task.get('name', '').lower(),
        'Name': lambda task: task.get('name', '').lower(),
        'Frequency': lambda task: float(task.get('frequency', 0)),
        'Priority': lambda task: task.get('priority', 0),
        'Duration': lambda task: task.get('duration', 0),
        'Due date': lambda task: task.get('due_date') or datetime.max.date(),
        'Completed': lambda task: task.get('completed', False),
    }
    return sorted(tasks, key=key_map.get(sort_key, lambda task: task.get('name', '').lower()), reverse=descending)


def get_today_tasks(tasks, limit_minutes):
    task_clones = [clone_task(task) for task in tasks]
    selector = TT_TaskSelector(daily_time_limit=limit_minutes)
    return selector.get_daily_tasks(task_clones, datetime.now().date())


def create_new_task(tasks, name, frequency, priority, duration, due_date):
    next_id = max((task.get('id', -1) for task in tasks), default=-1) + 1
    due_date_parsed = None if due_date is None else due_date
    return {
        'id': next_id,
        'name': name,
        'frequency': frequency_to_days(frequency),
        'initial_priority': float(priority),
        'priority': float(priority),
        'duration': int(duration),
        'due_date': due_date_parsed,
        'completed': False,
        'last_done_date': None,
    }


def save_tasks():
    write_tasks(TASKFILE, st.session_state.tasks)
    st.session_state.last_saved = datetime.now().strftime('%H:%M:%S')


def build_today_grid(today_sorted, key=None):
    df = pd.DataFrame(
        [
            {
                'id': task.get('id'),
                'Task': task.get('name', ''),
                'Frequency': task_frequency_label(task.get('frequency', 0)),
                'Priority': int(task.get('priority', 0)),
                'Duration': f"{int(task.get('duration', 0))} min",
                'Due date': date_to_string(task.get('due_date')) if task.get('due_date') else '—',
            }
            for task in today_sorted
        ]
    )
    if df.empty:
        return None

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    gb.configure_column('id', hide=True)
    gb.configure_column('Task', autoHeight=True, wrapText=True, checkboxSelection=True)
    gb.configure_column('Frequency', width=120)
    gb.configure_column('Priority', width=90)
    gb.configure_column('Duration', width=110)
    gb.configure_column('Due date', width=120)
    gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False)
    # gb.configure_column('Task', checkboxSelection=True)
    gb.configure_grid_options(domLayout='autoHeight', suppressMovableColumns=True, getRowId=JsCode('function(data) { return data.id; }'),)

    grid_options = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=500,
        key=key,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )

    return grid_response


def sync_today_grid(grid_response):
    if grid_response is None:
        return

    selected_rows = None
    if hasattr(grid_response, 'selected_rows'):
        selected_rows = grid_response.selected_rows
        if isinstance(selected_rows, pd.DataFrame):
            selected_rows = selected_rows.to_dict('records')

    if not selected_rows and hasattr(grid_response, 'selected_data'):
        selected_rows = grid_response.selected_data

    print(f"Selected rows: {selected_rows}")
    selected_ids = {
        int(row.get('id'))
        for row in selected_rows
        if isinstance(row, dict) and row.get('id') is not None
    } if selected_rows else set()

    for task in st.session_state.tasks:
        if task.get('id') in selected_ids:
            complete_task(task, datetime.now().date())
        else:
            uncomplete_task(task)
    save_tasks()


def skip_task(task_id):
    task = next(task for task in st.session_state.tasks if task.get('id') == task_id)
    task['due_date'] = datetime.now().date() + timedelta(days=1)
    save_tasks()


def move_task(task_id):
    date_key = f'move_date-{task_id}'
    move_date = st.session_state.get(date_key, datetime.now().date())
    task = next(task for task in st.session_state.tasks if task.get('id') == task_id)
    task['due_date'] = move_date
    save_tasks()


def set_selected_task(task_id):
    st.session_state.selected_task_id = task_id


def init_session_state():
    if 'tasks' not in st.session_state:
        st.session_state.tasks = load_tasks()
    if 'selected_task_id' not in st.session_state:
        st.session_state.selected_task_id = None
    if 'daily_limit' not in st.session_state:
        st.session_state.daily_limit = 240
    if 'today_sort' not in st.session_state:
        st.session_state.today_sort = 'Priority'
    if 'today_order' not in st.session_state:
        st.session_state.today_order = 'Descending'
    if 'general_sort' not in st.session_state:
        st.session_state.general_sort = 'Name'
    if 'general_order' not in st.session_state:
        st.session_state.general_order = 'Descending'
    if 'last_saved' not in st.session_state:
        st.session_state.last_saved = None


def main():
    st.title('TaskTracker')
    st.markdown('Manage your task library and generate today\'s list using the existing priority scheduler.')

    init_session_state()

    top_cols = st.columns([1, 1, 1])
    if top_cols[0].button('Reload JSON'):
        st.session_state.tasks = load_tasks()
        st.session_state.selected_task_id = None
    if top_cols[1].button('Save JSON'):
        save_tasks()
        st.success('tasklist.json updated')
    if st.session_state.last_saved:
        top_cols[2].markdown(f'Last saved: {st.session_state.last_saved}')

    tabs = st.tabs(['Today', 'General'])

    with tabs[0]:
        st.markdown('### Today')
        st.number_input(
            'Daily duration limit (minutes)',
            min_value=30,
            max_value=720,
            step=15,
            value=st.session_state.daily_limit,
            key='daily_limit',
        )
        today_tasks = get_today_tasks(st.session_state.tasks, st.session_state.daily_limit)

        controls = st.columns([1, 1, 2])
        if controls[0].button('Regenerate list'):
            st.session_state.tasks = st.session_state.tasks
        controls[1].markdown('')
        controls[2].markdown('')

        today_sorted = today_tasks
        active_tasks = [task for task in today_sorted if not task.get('completed', False)]
        completed_tasks = [task for task in today_sorted if task.get('completed', False)]

        st.write(f"**Active duration:** {sum(task.get('duration', 0) for task in active_tasks)} min")

        if not active_tasks and not completed_tasks:
            st.info('No tasks were selected for today. Add or edit tasks in the General tab.')
        else:
            if active_tasks:
                st.subheader('Today')
                grid_response = build_today_grid(active_tasks, key='today_active_grid')
                sync_today_grid(grid_response)

                selected_id = st.selectbox(
                    'Select task for action',
                    options=[task.get('id') for task in active_tasks],
                    format_func=lambda x: next((task.get('name', '') for task in active_tasks if task.get('id') == x), ''),
                    key='today_select_task',
                )
                selected_row = next((task for task in active_tasks if task.get('id') == selected_id), None)

                if selected_row is not None:
                    row_actions = st.columns([1, 1])
                    if row_actions[0].button('Move task', key=f"move-today-{selected_row.get('id')}"):
                        move_task(selected_row.get('id'))
                    if row_actions[1].button('Skip to tomorrow', key=f"skip-today-{selected_row.get('id')}"):
                        skip_task(selected_row.get('id'))
            else:
                st.info('No active tasks for today.')

            if completed_tasks:
                st.subheader('Completed tasks')
                for task in completed_tasks:
                    due_date = task.get('due_date')
                    frequency = task.get('frequency', 0)
                    if due_date:
                        next_due = due_date + timedelta(days=frequency)
                        due_text = f"{date_to_string(due_date)} -> <span style='color:red'>{date_to_string(next_due)}</span>"
                    else:
                        due_text = '—'

                    st.markdown(
                        f"**{task.get('name', '')}**  \
                        {task_frequency_label(frequency)} · P{int(task.get('priority', 0))} · {int(task.get('duration', 0))} min  \
                        Due: {due_text}",
                        unsafe_allow_html=True,
                    )

    with tabs[1]:
        st.markdown('### General Tasks')
        st.caption('Sort by:')
        sort_cols = st.columns([2, 1])
        sort_cols[0].selectbox('Sort by', GENERAL_SORT_OPTIONS, key='general_sort', label_visibility='collapsed')
        sort_cols[1].radio('Order', ['Descending', 'Ascending'], key='general_order', label_visibility='collapsed')

        task_ids = [None] + [task.get('id') for task in st.session_state.tasks]
        selected_id = st.selectbox(
            'Select task to edit',
            options=task_ids,
            index=task_ids.index(st.session_state.selected_task_id) if st.session_state.selected_task_id in task_ids else 0,
            format_func=lambda x: 'New task' if x is None else next(
                (task.get('name', '') for task in st.session_state.tasks if task.get('id') == x), str(x)
            ),
        )
        st.session_state.selected_task_id = selected_id

        with st.form('general_task_form'):
            if selected_id is not None:
                task = next(task for task in st.session_state.tasks if task.get('id') == selected_id)
                name = st.text_input('Name', value=task.get('name', ''))
                frequency = st.selectbox(
                    'Frequency',
                    FREQUENCY_OPTIONS,
                    index=FREQUENCY_OPTIONS.index(task_frequency_label(task.get('frequency', 0))),
                )
                priority = st.number_input('Priority', min_value=1, max_value=10, value=int(task.get('priority', 0)))
                duration = st.number_input('Duration (min)', min_value=1, value=int(task.get('duration', 0)))
                due_date_enabled = st.checkbox('Has due date', value=task.get('due_date') is not None)
                due_date = task.get('due_date') if task.get('due_date') else datetime.now().date()
                if due_date_enabled:
                    due_date = st.date_input('Due date', value=due_date)
                else:
                    due_date = None
                submitted = st.form_submit_button('Save task')
                delete_clicked = st.form_submit_button('Delete task')
                if submitted:
                    task['name'] = name
                    task['frequency'] = frequency_to_days(frequency)
                    task['initial_priority'] = float(priority)
                    task['priority'] = float(priority)
                    task['duration'] = int(duration)
                    task['due_date'] = due_date
                    save_tasks()
                    st.success('Task updated')
                if delete_clicked:
                    st.session_state.tasks = [t for t in st.session_state.tasks if t.get('id') != selected_id]
                    st.session_state.selected_task_id = None
                    save_tasks()
                    st.success('Task deleted')
            else:
                name = st.text_input('Name', value='')
                frequency = st.selectbox('Frequency', FREQUENCY_OPTIONS, index=0)
                priority = st.number_input('Priority', min_value=1, max_value=10, value=3)
                duration = st.number_input('Duration (min)', min_value=1, value=15)
                due_date_enabled = st.checkbox('Has due date', value=False)
                due_date = None
                if due_date_enabled:
                    due_date = st.date_input('Due date', value=datetime.now().date())
                submitted = st.form_submit_button('Add task')
                if submitted:
                    new_task = create_new_task(
                        st.session_state.tasks,
                        name,
                        frequency,
                        priority,
                        duration,
                        due_date,
                    )
                    st.session_state.tasks.append(new_task)
                    save_tasks()
                    st.success('Task added')

        st.markdown('<hr style="margin:6px 0">', unsafe_allow_html=True)
        st.subheader('Task list')
        general_tasks = sort_tasks(
            st.session_state.tasks,
            st.session_state.general_sort,
            st.session_state.general_order == 'Descending',
        )
        if not general_tasks:
            st.info('No tasks in the library.')
        else:
            header = st.columns([3, 1, 1, 1, 1, 1])
            header[0].markdown('Task')
            header[1].markdown('Frequency')
            header[2].markdown('Priority')
            header[3].markdown('Duration')
            header[4].markdown('Due date')
            header[5].markdown('')
            for task in general_tasks:
                cols = st.columns([3, 1, 1, 1, 1, 1])
                cols[0].markdown(f"**{task.get('name', '')}**")
                cols[1].markdown(task_frequency_label(task.get('frequency', 0)))
                cols[2].markdown(int(task.get('priority', 0)))
                cols[3].markdown(f"{int(task.get('duration', 0))} min")
                cols[4].markdown(date_to_string(task.get('due_date')) if task.get('due_date') else '—')
                cols[5].button('Edit', key=f"edit-{task.get('id')}", on_click=set_selected_task, args=(task.get('id'),))


if __name__ == '__main__':
    main()
