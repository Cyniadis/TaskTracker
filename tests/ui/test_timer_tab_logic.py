"""Unit tests for the pure logic behind tasktracker/ui/timer_tab.py.

`_toggle_play_pause`, `_reset`, and `_current_elapsed_seconds` only ever
touch `st.session_state` — they never call a rendering function — so we
can test them without any Streamlit runtime at all, by swapping out the
module's `st` name for a tiny fake exposing just `.session_state`, and its
`datetime` name for a fake clock we control. This sidesteps two things
covered instead in test_timer_tab.py: real `st.session_state` needing an
AppTest ScriptRunContext, and the risk of driving the fragment's
sleep+rerun loop through a real `render()` call.
"""
from __future__ import annotations

import types
from datetime import datetime, timedelta

import pytest

from tasktracker.ui import timer_tab


class _FakeClock:
    """Stands in for the `datetime` name imported into timer_tab; only `.now()` is used."""

    def __init__(self, fixed_now: datetime):
        self._fixed_now = fixed_now

    def now(self) -> datetime:
        return self._fixed_now


@pytest.fixture
def state(monkeypatch):
    """A plain namespace standing in for st.session_state, wired into timer_tab.st."""
    fake_state = types.SimpleNamespace(
        timer_running=False, timer_start_time=None, elapsed_accum=0.0,
    )
    fake_st = types.SimpleNamespace(session_state=fake_state)
    monkeypatch.setattr(timer_tab, "st", fake_st)
    return fake_state


def _freeze(monkeypatch, when: datetime) -> None:
    monkeypatch.setattr(timer_tab, "datetime", _FakeClock(when))


class TestTogglePlayPause:
    def test_starting_sets_running_flag_and_start_time(self, state, monkeypatch):
        start = datetime(2026, 7, 21, 12, 0, 0)
        _freeze(monkeypatch, start)

        timer_tab._toggle_play_pause()

        assert state.timer_running is True
        assert state.timer_start_time == start

    def test_stopping_banks_the_elapsed_time(self, state, monkeypatch):
        start = datetime(2026, 7, 21, 12, 0, 0)
        state.timer_running = True
        state.timer_start_time = start

        _freeze(monkeypatch, start + timedelta(seconds=5))
        timer_tab._toggle_play_pause()

        assert state.timer_running is False
        assert state.timer_start_time is None
        assert state.elapsed_accum == pytest.approx(5.0)

    def test_multiple_start_stop_cycles_accumulate(self, state, monkeypatch):
        t0 = datetime(2026, 7, 21, 12, 0, 0)

        _freeze(monkeypatch, t0)
        timer_tab._toggle_play_pause()  # start

        _freeze(monkeypatch, t0 + timedelta(seconds=3))
        timer_tab._toggle_play_pause()  # stop: +3s

        _freeze(monkeypatch, t0 + timedelta(seconds=10))
        timer_tab._toggle_play_pause()  # start again

        _freeze(monkeypatch, t0 + timedelta(seconds=17))
        timer_tab._toggle_play_pause()  # stop: +7s

        assert state.elapsed_accum == pytest.approx(10.0)

    def test_starting_does_not_touch_elapsed_accum(self, state, monkeypatch):
        state.elapsed_accum = 42.0
        _freeze(monkeypatch, datetime(2026, 7, 21, 12, 0, 0))
        timer_tab._toggle_play_pause()
        assert state.elapsed_accum == 42.0


class TestReset:
    def test_resets_running_flag_start_time_and_accum(self, state):
        state.timer_running = True
        state.timer_start_time = datetime(2026, 7, 21, 12, 0, 0)
        state.elapsed_accum = 99.0

        timer_tab._reset()

        assert state.timer_running is False
        assert state.timer_start_time is None
        assert state.elapsed_accum == 0.0

    def test_reset_on_an_already_stopped_timer_is_a_no_op_error_wise(self, state):
        timer_tab._reset()  # should not raise
        assert state.elapsed_accum == 0.0


class TestCurrentElapsedSeconds:
    def test_stopped_timer_returns_banked_time_only(self, state):
        state.timer_running = False
        state.elapsed_accum = 42.7
        assert timer_tab._current_elapsed_seconds() == 42

    def test_running_timer_adds_time_since_start(self, state, monkeypatch):
        start = datetime(2026, 7, 21, 12, 0, 0)
        state.timer_running = True
        state.timer_start_time = start
        state.elapsed_accum = 10.0

        _freeze(monkeypatch, start + timedelta(seconds=7))

        assert timer_tab._current_elapsed_seconds() == 17

    def test_truncates_to_whole_seconds(self, state):
        state.timer_running = False
        state.elapsed_accum = 5.9
        assert timer_tab._current_elapsed_seconds() == 5
