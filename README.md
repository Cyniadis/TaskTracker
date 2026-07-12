# TaskTracker

A small Streamlit app that schedules recurring chores into a daily plan,
subject to a time budget.

## Running

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project layout

```
app.py                         Streamlit entry point (page setup, tabs)
tasklist.json                  Task data (persisted)
cache.json                     App settings (persisted, e.g. daily time limit)

tasktracker/
    config.py                  Paths & constants
    models.py                  Task, Frequency, Period — pure domain logic, no I/O
    storage.py                 JSON read/write for tasks and settings
    scheduler.py                Eligibility + knapsack: picks today's tasks
    state.py                   Streamlit session-state glue ("controller")

    ui/
        today_tab.py            "Today" tab: check off / reschedule tasks
        general_tab.py          "General" tab: manage the full task library
        add_task_dialog.py      Modal form to create a new task
        timer_tab.py            Stopwatch tab
        grid_utils.py           Shared AgGrid helpers
        assets/
            FrequencyCellEditor.js

tests/
    test_scheduler.py          Manual smoke test that simulates 30 days
```

## Design notes

- **`models.py`** has no dependency on Streamlit, pandas, or the filesystem.
  `Task` is a `dataclass` with plain attributes (`task.name`, `task.due_date`, ...)
  instead of `get_x()`/`set_x()` boilerplate, plus a couple of small behavioural
  methods (`complete`, `uncomplete`, `schedule_for`, ...).
- **`scheduler.py`** is pure functions over `Task` objects — easy to unit test
  without touching Streamlit or disk.
- **`storage.py`** is the only place that reads/writes JSON.
- **`state.py`** is the only place that touches `st.session_state` for task
  data; UI modules call its functions (`state.persist_tasks()`,
  `state.discard_completed_tasks()`, ...) instead of mutating state directly.
- **`ui/`** has one module per tab/dialog, each exposing a single `render()`
  (or, for the dialog, a callable) — no business logic lives here, only
  widget wiring and callbacks that delegate to `state`/`scheduler`.
