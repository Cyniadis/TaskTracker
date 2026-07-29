"""The 'Groceries' tab: one data-editor tracking a tri-state shopping list.

Unlike the tasks feature (split across Today/General), groceries get a
single tab and a single grid — there's no "today's subset" concept, just
the full list with an editable state per row.
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from ..consts import today
from .grocery import STATE_LABELS, GroceryItem, GroceryState
from .json_utils import load_groceries, next_grocery_id, save_groceries


@st.cache_resource(show_spinner=False)
def _init_grocery_list() -> list[GroceryItem]:
    """Load groceries from disk once per app session, like _init_general_task_list
    does for tasks, so a Streamlit rerun doesn't re-read the file every time."""
    return load_groceries()


def init_session_state() -> None:
    """Set up the session state the Groceries tab depends on.

    Call once from app_streamlit.py's main(), alongside
    tasktracker.ui.ui_state.init_session_state().
    """
    st.session_state.setdefault("groceries", _init_grocery_list())
    st.session_state.setdefault("groceries_grid_key", "GroceriesGrid1")


def _persist() -> None:
    save_groceries(st.session_state.groceries)


def _reload_grid() -> None:
    """Force the data grid to remount by giving it a fresh widget key."""
    st.session_state.groceries_grid_key = f"GroceriesGrid{_dt.datetime.now().timestamp()}"


def _find_by_id(item_id: int) -> GroceryItem:
    for item in st.session_state.groceries:
        if item.id == item_id:
            return item
    raise KeyError(f"No grocery item with id={item_id}")


def _to_dataframe(items: list[GroceryItem]) -> pd.DataFrame | None:
    if not items:
        return None
    records = [
        {
            "id": item.id,
            "name": item.name,
            "state": item.state_label,
            "last_bought_date": item.last_bought_date,
        }
        for item in items
    ]
    return pd.DataFrame.from_records(records)


def _column_config() -> dict:
    return {
        "id": None,
        "name": st.column_config.TextColumn("Article", width="large", required=True),
        "state": st.column_config.SelectboxColumn(
            "État", options=list(STATE_LABELS.values()), width="small", required=True,
        ),
        "last_bought_date": st.column_config.DateColumn(
            "Dernier achat", format="localized", disabled=True,
        ),
    }


def _apply_added_row(new_row: dict) -> None:
    item = GroceryItem(
        id=next_grocery_id(st.session_state.groceries),
        name=new_row["name"].strip(),
        state=GroceryState.TO_BUY.value,
    )
    st.session_state.groceries.append(item)


def _apply_edited_rows(edited_rows: dict, df: pd.DataFrame) -> None:
    for row_pos, changes in edited_rows.items():
        item = _find_by_id(int(df.iloc[row_pos]["id"]))

        if "name" in changes:
            item.set_field("name", changes["name"])
        if "state" in changes:
            item.set_state_from_label(changes["state"], today())


def _on_data_change() -> None:
    """Callback fired on any add/edit/delete in the Groceries data editor."""
    key = st.session_state.groceries_grid_key
    editor_state = st.session_state[key]
    df = st.session_state.groceries_df

    if editor_state["added_rows"]:
        # Only the last added row is new; earlier ones were already handled
        # on a previous rerun.
        _apply_added_row(editor_state["added_rows"][-1])

    if editor_state["edited_rows"]:
        _apply_edited_rows(editor_state["edited_rows"], df)

    if editor_state["deleted_rows"]:
        deleted_ids = {int(df.iloc[row_pos]["id"]) for row_pos in editor_state["deleted_rows"]}
        st.session_state.groceries = [
            item for item in st.session_state.groceries if item.id not in deleted_ids
        ]

    _persist()


def render() -> None:
    """Render the 'Groceries' tab: the shopping-list grid."""
    st.markdown("### Liste de courses", anchors=False)

    df = _to_dataframe(st.session_state.groceries)
    if df is None:
        st.info("No grocery items yet — use \u201cAdd item\u201d to create your first one.")
        return

    st.session_state.groceries_df = df

    key = st.session_state.groceries_grid_key
    st.data_editor(
        df,
        column_config=_column_config(),
        hide_index=True,
        width="content",
        height="content",
        key=key,
        num_rows="dynamic",
        on_change=_on_data_change,
    )
