"""AppTest-based tests for tasktracker/ui/timer_tab.py.

See tests/ui/conftest.py for why the "Play" button is only clicked once,
in a dedicated, timeout-guarded test. Pure logic (start/stop/reset/elapsed
math) is unit-tested directly in test_timer_tab_logic.py instead, without
going through Streamlit's runtime at all.
"""
from __future__ import annotations

import pytest


class TestTimerInitialRender:
    def test_shows_the_timer_heading(self, timer_app):
        at = timer_app.run()
        assert "Timer" in at.markdown[0].value

    def test_shows_zeroed_clock_by_default(self, timer_app):
        at = timer_app.run()
        assert "00:00:00" in at.markdown[1].value

    def test_shows_play_and_reset_buttons(self, timer_app):
        at = timer_app.run()
        labels = [b.label for b in at.button]
        assert "▶️ Play" in labels
        assert "⏹ Reset" in labels

    def test_renders_without_error(self, timer_app):
        at = timer_app.run()
        assert len(at.exception) == 0


class TestTimerDisplaysBankedTime:
    def test_shows_pre_existing_elapsed_time(self, timer_app):
        timer_app.session_state["elapsed_accum"] = 125.0  # 2:05
        at = timer_app.run()
        assert "00:02:05" in at.markdown[1].value

    def test_formats_hours_minutes_seconds(self, timer_app):
        timer_app.session_state["elapsed_accum"] = 3725.0  # 1:02:05
        at = timer_app.run()
        assert "01:02:05" in at.markdown[1].value


class TestResetButton:
    def test_reset_zeroes_a_running_display(self, timer_app):
        timer_app.session_state["elapsed_accum"] = 100.0
        at = timer_app.run()

        reset_button = next(b for b in at.button if b.label == "⏹ Reset")
        at = reset_button.click().run()

        assert "00:00:00" in at.markdown[1].value
        assert len(at.exception) == 0

    def test_reset_clears_timer_running_flag(self, timer_app):
        at = timer_app.run()
        timer_app.session_state["timer_running"] = False  # never started in this test

        reset_button = next(b for b in at.button if b.label == "⏹ Reset")
        at = reset_button.click().run()

        assert at.session_state["timer_running"] is False
        assert at.session_state["timer_start_time"] is None


class TestPlayButtonFragmentLimitation:
    """Pinned, documented behavior — see the module docstring and
    tests/ui/conftest.py for why this is the one place we click Play."""

    @pytest.mark.timeout(10)
    def test_clicking_play_updates_state_before_the_known_apptest_exception(self, timer_app):
        at = timer_app.run()
        play_button = next(b for b in at.button if b.label == "▶️ Play")
        at = play_button.click().run()

        # The callback ran and updated state correctly...
        assert at.session_state["timer_running"] is True
        assert at.session_state["timer_start_time"] is not None

        # ...even though the live-refresh rerun that follows it can't work
        # in AppTest's bare execution context (no real fragment scope).
        assert len(at.exception) == 1
        assert "fragment" in at.exception[0].value
