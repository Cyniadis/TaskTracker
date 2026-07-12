import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, JsCode

from TT_task import TT_Task
from TT_utils import normalize_date
from TT_app_state import TODAY, force_grid_reload, save_tasks

from datetime import datetime, timedelta
import time

# ======================= TODAY TAB =======================

def _due_date_cell_style():
    today_value = normalize_date(TODAY).isoformat()
    return JsCode(f"""function(params) {{
    if (!params.value) {{ return {{ color: 'primary' }}; }}
    const valueDate = new Date(params.value);
    const isToday = !isNaN(valueDate.getTime()) && valueDate.toISOString().slice(0, 10) === '{today_value}';
    if (!isToday) {{ return {{ color: '#d32f2f', fontWeight: 'bold' }}; }}
    return {{ color: 'primary' }};}}""")


def _on_today_selection_changed(grid_response, today_tasks: list[TT_Task], tasks: list[TT_Task]):
    print('On Selection Changed')
    selected_rows = grid_response.selected_rows
    selected_ids = set()
    if selected_rows is not None and len(selected_rows) > 0:
        selected_tasks = selected_rows.to_dict(orient='records')
        selected_ids = {int(row.get('id')) for row in selected_tasks}

    for task in today_tasks:
        if selected_ids and task.get_id() in selected_ids:
            task.complete(TODAY)
        else:
            task.uncomplete()
    save_tasks(tasks)


def _on_today_cell_value_changed(grid_response):
    event_data = grid_response.event_data
    cell_value = normalize_date(event_data.get('newValue'))
    task_data = event_data.get('data')
    updated_task = [task for task in st.session_state.tasks if task.get_id() == task_data['id']][0]

    if cell_value < TODAY:
        st.toast('Chosen due date is in the past', icon='⚠️')
        force_grid_reload()
    else:
        updated_task.set_due_date(cell_value)
        save_tasks(st.session_state.tasks)


def _on_today_grid_event(grid_response):
    event_type = grid_response.event_data.get('type')
    print(event_type)
    if event_type == 'selectionChanged':
        _on_today_selection_changed(grid_response, st.session_state.today_tasks, st.session_state.tasks)
    elif event_type == 'cellValueChanged':
        _on_today_cell_value_changed(grid_response)


def build_today_grid():
    print('Building today grid')
    today_tasks_dict = [task.task for task in st.session_state.today_tasks]
    df = pd.DataFrame.from_dict(today_tasks_dict)
    if df.empty:
        return None

    for date_field in ('due_date', 'next_due_date', 'done_date', 'last_done_date'):
        if date_field in df.columns:
            df[date_field] = pd.to_datetime(df[date_field], errors='coerce', dayfirst=True).dt.strftime('%Y-%m-%d')

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True)
    gb.configure_column('id', hide=True)
    gb.configure_column('name', headerName='Task', autoHeight=True, wrapText=True, checkboxSelection=True)
    gb.configure_column('frequency', headerName='Frequency', width=120)
    gb.configure_column('priority', headerName='Priority', width=90)
    gb.configure_column('initial_priority', hide=True)
    gb.configure_column('duration', headerName='Duration', width=110)
    gb.configure_column('due_date', headerName='Due date', width=120, cellStyle=_due_date_cell_style(), cellDataType='dateString', editable=True)
    gb.configure_column('next_due_date', headerName='Next Due Date', width=120, cellDataType='dateString')
    gb.configure_column('done_date', headerName='Done date', width=120, cellDataType='dateString')
    gb.configure_column('last_done_date', headerName='Last Done Date', width=150, cellDataType='dateString')
    gb.configure_column('selected', headerName='Selected', hide=True)

    pre_selected_row_indices = [str(df.index[idx]) for idx, task in enumerate(st.session_state.today_tasks) if task.is_task_completed(TODAY)]
    gb.configure_selection('multiple', use_checkbox=True, rowMultiSelectWithClick=True, suppressRowClickSelection=False, pre_selected_rows=pre_selected_row_indices)

    doubleClickedFunc = r'''function (params){ if (params.column.colId == "due_date") { params.node.setDataValue('doubleClicked', params.data.id); } }'''
    gb.configure_grid_options(domLayout='autoHeight', onCellDoubleClicked=JsCode(doubleClickedFunc))

    grid_options = gb.build()
    return AgGrid(
        df,
        gridOptions=grid_options,
        height=500,
        key=st.session_state.grid_key,
        update_on=['selectionChanged', 'cellValueChanged'],
        callback=_on_today_grid_event,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )

# ======================= GENERAL TAB =======================

@st.cache_resource(show_spinner=False)
def _load_frequency_cell_editor():
    return JsCode(open("FrequencyCellEditor.js").read())

def _on_manage_tasks_grid_event(grid_response):
    event_data = grid_response.event_data
    cell_value = event_data.get('newValue')
    task_param = event_data.get('column').get('colId')
    task_data = event_data.get('data')
    updated_task = [task for task in st.session_state.tasks if task.get_id() == task_data['id']][0]
    updated_task.set_value(task_param, cell_value)
    save_tasks(st.session_state.tasks)

def _build_task_parameters_df(tasks: list[TT_Task]) -> pd.DataFrame:
    if not tasks:
        return pd.DataFrame()
    task_records = [task.clone() for task in tasks]
    df = pd.DataFrame.from_records(task_records)
    for date_field in ('due_date', 'next_due_date', 'done_date', 'last_done_date'):
        if date_field in df.columns:
            df[date_field] = pd.to_datetime(df[date_field], errors='coerce', dayfirst=True).dt.strftime('%Y-%m-%d')
    return df

def build_manage_tasks_grid():
    print('Building manage tasks grid')
    df = _build_task_parameters_df(st.session_state.tasks)
    if df.empty:
        return None

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filter=True, resizable=True, editable=True)
    gb.configure_column('id', hide=True)
    gb.configure_column('name', headerName='Task', autoHeight=True, wrapText=True)
    gb.configure_column('frequency', headerName='Frequency', cellEditor=_load_frequency_cell_editor(), cellEditorPopup=True)
    gb.configure_column('priority', headerName='Priority', cellDataType='number')
    gb.configure_column('initial_priority', headerName='Initial Priority', cellDataType='number')
    gb.configure_column('duration', headerName='Duration (min)',  cellDataType='number')
    gb.configure_column('selected', headerName='Selected', hide=True)
    gb.configure_column('due_date', headerName='Due date',  cellDataType='dateString')
    gb.configure_column('next_due_date', headerName='Next Due Date', cellDataType='dateString', editable=False)
    gb.configure_column('done_date', headerName='Done date', cellDataType='dateString', editable=False)
    gb.configure_column('last_done_date', headerName='Last Done Date', cellDataType='dateString', editable=False)
    gb.configure_grid_options(domLayout='autoHeight')

    grid_options = gb.build()
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=630,
        key=st.session_state.manage_grid_key,
        update_on=['cellValueChanged'],
        callback=_on_manage_tasks_grid_event,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
    )
    return grid_response

# ======================= TIMER TAB =======================


def toggle_play_pause():
    if st.session_state.timer_running:
        # Pause: accumulate elapsed time
        elapsed = (datetime.now() - st.session_state.timer_start_time).total_seconds()
        st.session_state.elapsed_accum += elapsed
        st.session_state.timer_start_time = None
        st.session_state.timer_running = False
    else:
        # Play
        st.session_state.timer_start_time = datetime.now()
        st.session_state.timer_running = True

def reset_timer():
    st.session_state.timer_running = False
    st.session_state.timer_start_time = None
    st.session_state.elapsed_accum = 0.0


@st.fragment
def build_timer_tab():
    # --- Compute current elapsed ---
    if st.session_state.timer_running and st.session_state.timer_start_time:
        current_elapsed = st.session_state.elapsed_accum + (
            datetime.now() - st.session_state.timer_start_time
        ).total_seconds()
    else:
        current_elapsed = st.session_state.elapsed_accum

    total_seconds = int(current_elapsed)
    h, m, s = total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60

    # --- Display ---
    # flex_container = st.container(horizontal=True, horizontal_alignment='left', vertical_alignment='center', height='stretch', width="content", border=True)
    # Big elapsed time
    with st.container(horizontal_alignment="center", border=True, width="content"):
        st.markdown(
            f"<h1 style='text-align:center; font-size: 5rem;'>"
            f"{h:02d}:{m:02d}:{s:02d}"
            f"</h1>",
            unsafe_allow_html=True,
            anchors=False
        )

        # Buttons row
        with st.container(horizontal=True, horizontal_alignment="center", width="content"):
            play_label = "⏸ Pause" if st.session_state.timer_running else "▶️ Play"
            st.button(play_label, on_click=toggle_play_pause, use_container_width=True)
            st.button("⏹ Reset", on_click=reset_timer, use_container_width=True)

    # Auto-rerun every second while running
    if st.session_state.timer_running:
        time.sleep(0.25)
        st.rerun(scope="fragment")


