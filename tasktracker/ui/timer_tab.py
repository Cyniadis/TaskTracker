"""The 'Timer' tab: a simple play/pause/reset stopwatch."""
from __future__ import annotations

from datetime import datetime

import streamlit as st
from ..tt_json_utils import load_timer_state, cache_timer_state

_TICK_SECONDS = 0.25  # how often the fragment auto-refreshes itself while running


def _toggle_play_pause() -> None:
    """Start the timer if it's stopped, or bank the elapsed time if it's running."""
    if st.session_state.timer_running:
        elapsed = (datetime.now() - st.session_state.timer_start_time).total_seconds()
        st.session_state.timer_elapsed_accum += elapsed
        st.session_state.timer_start_time = None
        st.session_state.timer_running = False
    else:
        st.session_state.timer_start_time = datetime.now()
        st.session_state.timer_running = True
        cache_timer_state(timer_start_time=st.session_state.timer_start_time)
    
    cache_timer_state(timer_elapsed_accum=st.session_state.timer_elapsed_accum, 
                      timer_running=st.session_state.timer_running)


def _reset() -> None:
    """Stop the timer and zero out the accumulated time."""
    st.session_state.timer_running = False
    st.session_state.timer_start_time = None
    st.session_state.timer_elapsed_accum = 0.0
    cache_timer_state(timer_start_time=st.session_state.timer_start_time, 
                      timer_elapsed_accum= st.session_state.timer_elapsed_accum, 
                      timer_running=st.session_state.timer_running)


def _current_elapsed_seconds() -> int:
    """Total elapsed seconds so far: banked time plus the current running segment, if any."""
    accum = st.session_state.timer_elapsed_accum
    if st.session_state.timer_running and st.session_state.timer_start_time:
        accum += (datetime.now() - st.session_state.timer_start_time).total_seconds()
    cache_timer_state(timer_elapsed_accum=accum)
    return int(accum)


def _timer_ui():
    total_seconds = _current_elapsed_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    st.markdown(
        f"<h1 style='text-align:center; font-size: 5rem;'>{hours:02d}:{minutes:02d}:{seconds:02d}</h1>",
        unsafe_allow_html=True,
        anchors=False,
    )

    

@st.fragment(run_every=_TICK_SECONDS)
def _live_clock() -> None:
    """Auto-refreshing fragment: Streamlit reruns *this* fragment on its own
    schedule whenever the timer is running, without us ever calling
    st.rerun() ourselves — which sidesteps the 'rerun(scope=fragment) called
    outside a fragment' error you'd get from a manual sleep()+rerun() loop
    when this code is first reached via a full-page rerun (e.g. a refresh)."""
    if not st.session_state.timer_running:
        return  # run_every still fires the fragment, but nothing to update
    _timer_ui()
    

def render() -> None:
    """Render the stopwatch: static chrome here, the ticking clock in its own fragment."""
    st.markdown("### Timer", anchors=False)
    
    if "timer_start_time" not in st.session_state and \
        "timer_elapsed_accum" not in st.session_state and \
        "timer_running" not in st.session_state:
        st.session_state.timer_start_time, \
        st.session_state.timer_elapsed_accum, \
        st.session_state.timer_running = load_timer_state()
        
    with st.container(horizontal_alignment="center", border=True, width="content"):
        if not st.session_state.timer_running:
            _timer_ui()
        else:
            _live_clock()

        with st.container(horizontal=True, horizontal_alignment="center", width="content"):
            play_label = "⏸ Pause" if st.session_state.timer_running else "▶️ Play"
            st.button(play_label, on_click=_toggle_play_pause, use_container_width=True)
            st.button("⏹ Reset", on_click=_reset, use_container_width=True)