"""Fixtures shared by the Streamlit UI tests.

These tests drive real tab-render functions through Streamlit's AppTest
harness (see https://docs.streamlit.io/develop/concepts/app-testing/cheat-sheet).
A few things are deliberately out of scope, with the reasoning left here
rather than scattered across test files:

- `st.data_editor` (the 'General' tab's main grid) and button-column clicks
  inside `st.dataframe` (the 'Today' tab's complete/reschedule buttons)
  have no AppTest query object — the cheat sheet's Limitations section
  lists `st.data_editor` explicitly, and button columns aren't mentioned
  as interactive anywhere either. We can't assert on their rendered rows
  or trigger their on_click callbacks through `at.data_editor`/`at.dataframe`.
  Instead, `general_grid_logic_app.py` / `today_tab_logic_app.py` wire the
  same private callback functions to plain buttons, so the callback logic
  still runs inside a real AppTest ScriptRunContext (calling them from a
  bare pytest function would rely on `st.session_state` "bare mode", which
  Streamlit's own runtime explicitly warns doesn't reliably function).

- `st.dialog` bodies (Import tasks, Changes) aren't driven here. AppTest
  doesn't expose a way to open a dialog and interact with the widgets
  inside it, so `_import_tasks_dialog` / `_show_changes_dialog` aren't
  covered by these tests.

- The Timer tab's "Play" button is clicked exactly once, in a dedicated
  test that expects (and pins) the resulting exception: `render()` uses
  `time.sleep()` + `st.rerun(scope="fragment")` to redraw the clock every
  250ms, which is exactly right in a live browser tab but has no real
  fragment-rerun context in AppTest's bare execution, so it raises
  `StreamlitAPIException` instead of looping. A `pytest.mark.timeout` is
  kept on that test anyway as a safety net, since `requirements.txt` pins
  `streamlit>=1.31` with no upper bound and a future version could handle
  this differently.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APPS_DIR = Path(__file__).parent / "apps"


@pytest.fixture(autouse=True)
def _no_disk_io(monkeypatch):
    """Never let a UI test read or write the real tasklist.json / cache.json.

    Patches every disk-touching function these tabs can reach, at the
    module namespace each one was imported into (they're plain `from x
    import y` bindings, so patching json_utils itself wouldn't reach them).
    """
    from tasktracker.ui import general_tab, today_tab, ui_state

    monkeypatch.setattr(ui_state, "save_tasks", lambda *a, **k: None)
    monkeypatch.setattr(ui_state, "cache_tasks", lambda *a, **k: None)
    monkeypatch.setattr(general_tab, "save_tasks", lambda *a, **k: None)

    monkeypatch.setattr(today_tab, "load_show_completed", lambda: False)
    monkeypatch.setattr(today_tab, "load_show_rescheduled", lambda: False)
    monkeypatch.setattr(today_tab, "load_allow_future_tasks", lambda: False)
    monkeypatch.setattr(today_tab, "cache_daily_limit", lambda *a, **k: None)
    monkeypatch.setattr(today_tab, "cache_show_completed", lambda *a, **k: None)
    monkeypatch.setattr(today_tab, "cache_show_rescheduled", lambda *a, **k: None)
    monkeypatch.setattr(today_tab, "cache_allow_future_tasks", lambda *a, **k: None)


def _app(name: str) -> AppTest:
    return AppTest.from_file(str(APPS_DIR / name))


@pytest.fixture
def timer_app():
    return _app("timer_app.py")


@pytest.fixture
def today_app():
    return _app("today_app.py")


@pytest.fixture
def today_tab_logic_app():
    return _app("today_tab_logic_app.py")


@pytest.fixture
def general_app():
    return _app("general_app.py")


@pytest.fixture
def general_grid_logic_app():
    return _app("general_grid_logic_app.py")
