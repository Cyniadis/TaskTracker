"""The 'Timer' tab: a simple play/pause/reset stopwatch."""
from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

_TICK_SECONDS = 0.25  # how often the fragment reruns itself while the timer is running


def _toggle_play_pause() -> None:
    """Start the timer if it's stopped, or bank the elapsed time if it's running."""
    if st.session_state.timer_running:
        elapsed = (datetime.now() - st.session_state.timer_start_time).total_seconds()
        st.session_state.elapsed_accum += elapsed
        st.session_state.timer_start_time = None
        st.session_state.timer_running = False
    else:
        st.session_state.timer_start_time = datetime.now()
        st.session_state.timer_running = True


def _reset() -> None:
    """Stop the timer and zero out the accumulated time."""
    st.session_state.timer_running = False
    st.session_state.timer_start_time = None
    st.session_state.elapsed_accum = 0.0


def _current_elapsed_seconds() -> int:
    """Total elapsed seconds so far: banked time plus the current running segment, if any."""
    accum = st.session_state.elapsed_accum
    if st.session_state.timer_running and st.session_state.timer_start_time:
        accum += (datetime.now() - st.session_state.timer_start_time).total_seconds()
    return int(accum)


@st.fragment
def render() -> None:
    """Render the stopwatch. Runs as its own fragment so the 0.25s tick only
    reruns this widget, not the whole page."""
    total_seconds = _current_elapsed_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    st.markdown("### Timer", anchors=False)

    with st.container(horizontal_alignment="center", border=True, width="content"):
        st.markdown(
            f"<h1 style='text-align:center; font-size: 5rem;'>{hours:02d}:{minutes:02d}:{seconds:02d}</h1>",
            unsafe_allow_html=True,
            anchors=False,
        )
        with st.container(horizontal=True, horizontal_alignment="center", width="content"):
            play_label = "⏸ Pause" if st.session_state.timer_running else "▶️ Play"
            st.button(play_label, on_click=_toggle_play_pause, use_container_width=True)
            st.button("⏹ Reset", on_click=_reset, use_container_width=True)

    if st.session_state.timer_running:
        time.sleep(_TICK_SECONDS)
        st.rerun(scope="fragment")
