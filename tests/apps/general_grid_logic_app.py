"""Harness to exercise the 'General' tab's data-editor callback logic
(`_apply_added_row` / `_apply_edited_rows`) through a real AppTest session.

`st.data_editor` itself has no AppTest query object (see the cheat sheet's
Limitations section: https://docs.streamlit.io/develop/concepts/app-testing/cheat-sheet),
so we can't drive an actual add/edit/delete through the grid widget. Instead,
this harness wires plain buttons that call the same private callback
functions the real grid's `on_change` handler would call, using session
state a test sets up beforehand — that's enough to exercise the logic
inside a genuine ScriptRunContext (unlike calling them directly from a bare
pytest function, which Streamlit explicitly warns doesn't reliably support
`st.session_state`).
"""
import streamlit as st

from tasktracker.ui import general_tab as gt

st.session_state.setdefault("tasks", [])

if st.button("apply_added_row"):
    gt._apply_added_row(st.session_state["new_row"])

if st.button("apply_edited_rows"):
    gt._apply_edited_rows(st.session_state["edited_rows"], st.session_state["edit_df"])
