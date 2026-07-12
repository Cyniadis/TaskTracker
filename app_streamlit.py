import streamlit as st

from TT_json_utils import save_daily_limit
from TT_utils import normalize_date
from TT_app_state import TODAY, add_more_tasks, clean_cache, discard_completed_tasks, ensure_session_state, init_task_list
from TT_app_ui import build_manage_tasks_grid, build_today_grid, build_timer_tab

from datetime import datetime, timedelta
import time

def main():
    st.set_page_config(page_title='TaskTracker', layout='wide')
    st.title('TaskTracker')

    tasks, today_tasks, daily_limit = init_task_list()
    ensure_session_state(tasks, today_tasks, daily_limit)

    tabs = st.tabs(['📝 Today', '⚙️ General', '⏱️ Timer'])

    with tabs[0]:
        today_display = normalize_date(TODAY)
        st.markdown('### Tasks of ' + today_display.strftime('%a, %B %d, %Y'), anchors=False)

        with st.container(horizontal=True, horizontal_alignment='left', vertical_alignment='center', height='stretch'):
            st.markdown('Daily duration limit (minutes) : ', anchors=False)
            st.number_input(
                label='Daily duration limit',
                label_visibility='collapsed',
                min_value=5,
                max_value=720,
                step=15,
                key='daily_limit',
                on_change=lambda: save_daily_limit(st.session_state.daily_limit),
                width=100,
            )
            st.button('Discard completed tasks', on_click=discard_completed_tasks)
            st.button('Regenerate', on_click=add_more_tasks)
            st.button('Reload', on_click=clean_cache)

        st.write(
            f"**Active duration:** {sum(task.get_duration() for task in st.session_state.today_tasks)} min - "
            f"**Number of tasks:** {len(st.session_state.today_tasks)}"
        )

        if not tasks:
            st.info('No tasks were selected for today. Add or edit tasks in the General tab.')
        else:
            build_today_grid()

    with tabs[1]:
        st.markdown('### Edit tasks', anchors=False)
        # st.caption('Update the task library here. The fields for Done date and Last Done Date stay read-only.')
        build_manage_tasks_grid()

    with tabs[2]:
        st.markdown('### Timer', anchors=False)
        build_timer_tab()
        


if __name__ == '__main__':
    main()
