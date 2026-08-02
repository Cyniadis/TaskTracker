"""Harness to exercise the 'Groceries' tab's data-editor callback logic
(`_apply_added_row` / `_apply_edited_rows` / `_on_data_change`) through a
real AppTest session — same rationale as general_grid_logic_app.py:
`st.data_editor` has no AppTest query object, so plain buttons wire the
same private callbacks the real grid's `on_change` handler would call.
"""
import streamlit as st

from groceries import grocery_tab as gt

st.session_state.setdefault("groceries", [])
st.session_state.setdefault("groceries_grid_key", "GroceriesGrid1")

if st.button("apply_added_row"):
    gt._apply_added_row(st.session_state["new_row"])

if st.button("apply_edited_rows"):
    gt._apply_edited_rows(st.session_state["edited_rows"], st.session_state["edit_df"])

if st.button("on_data_change"):
    st.session_state.groceries_df = st.session_state["edit_df"]
    st.session_state[st.session_state.groceries_grid_key] = st.session_state["editor_state"]
    gt._on_data_change()
