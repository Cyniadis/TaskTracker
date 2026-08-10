"""One-time task feature: tasks with no recurrence.

Reuses tasktracker.task.Task as-is (it already has everything needed: name,
duration, due_date/done_date, completion state). What makes a task
"one-time" is purely behavioral, not a new field: these tasks are stored in
their own file (onetime_tasks.json) and never fed into the selector's
eligibility/knapsack logic — see tasktracker/ui_state.py's
regenerate_today_tasks and _sync_today_tasks for how they're merged into
the Today list purely through manual scheduling.
"""
