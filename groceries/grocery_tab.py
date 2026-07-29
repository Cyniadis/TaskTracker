"""The 'Groceries' tab: one data-editor tracking a tri-state shopping list.

Unlike the tasks feature (split across Today/General), groceries get a
single tab and a single grid — there's no "today's subset" concept, just
the full list with an editable state per row.
"""
from __future__ import annotations

import datetime as _dt
import json

import pandas as pd
import streamlit as st

from common.consts import today
from tasktracker.ui.ui_state import persist_tasks
from .grocery import LABEL_TO_STATE, STATE_TO_LABEL, GroceryItem, GroceryState
from .json_utils import (
    grocery_list_to_json,
    import_groceries_from_json_bytes,
    load_groceries,
    next_grocery_id,
    save_groceries,
)
from common.ui_common import get_theme_color


def persist_groceries():
    save_groceries(st.session_state.groceries)

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
            "completed": "🗹" if item.state == GroceryState.BOUGHT else "☐",
            "name": item.name,
            "state": item.state_label,
            "last_bought_date": item.last_bought_date,
        }
        for item in items
    ]
    return pd.DataFrame.from_records(records)


def _on_bought_button_click() -> None:
    clicked_row = st.session_state.bought_button["row"]
    row_id = st.session_state.groceries_df.at[clicked_row, "id"]
    item = _find_by_id(row_id)
    
    was_uncompleted = st.session_state.groceries_df.at[clicked_row, "completed"] != "☐"
    if was_uncompleted:
        item.state = GroceryState.TO_BUY
    else:
        item.state = GroceryState.BOUGHT
    print(item)
    persist_groceries()


def _column_config() -> dict:
    return {
        "id": None,
        "completed": None,
        "name": st.column_config.TextColumn("Article", width="medium", required=True),
        "state": st.column_config.SelectboxColumn("État", options=list(STATE_TO_LABEL.values()), width=125, required=True),
        "last_bought_date": st.column_config.DateColumn("Dernier achat", format="localized", disabled=True),
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


def _export_json_bytes() -> bytes:
    """Serialize the full grocery list as JSON bytes, for the download button."""
    payload = grocery_list_to_json(st.session_state.groceries)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


@st.dialog("Import groceries")
def _import_groceries_dialog() -> None:
    """Dialog to upload a JSON file and, after validation, replace the entire grocery list."""
    st.warning(
        "⚠️ Importing a file will **replace your entire grocery list** "
        "(states, last-bought dates — everything) and cannot be undone."
    )

    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"], key="import_groceries_file_uploader")
    if uploaded_file is None:
        return

    try:
        new_items = import_groceries_from_json_bytes(uploaded_file.getvalue())
    except ValueError as exc:
        st.error(f"Could not import this file:\n\n{exc}")
        return

    st.success(f"File looks valid — {len(new_items)} items found.")
    st.caption("Click confirm below to replace your current grocery list.")

    if st.button("✅ Replace all items and reload", type="primary"):
        save_groceries(new_items)
        # Only the groceries resource cache needs clearing here — tasks,
        # cache.json settings, etc. are untouched, so there's no need for
        # the app-wide reset_app() that the General tab's task import uses.
        _init_grocery_list.clear()
        st.session_state.groceries = new_items
        _reload_grid()
        st.rerun()


def _color_by_state(row: pd.Series) -> list[str]:
    """Row-styling: highlight tasks done today, dim tasks not due today."""
    state = LABEL_TO_STATE[row["state"]]
    color = get_theme_color("textColor")
    if state == GroceryState.BOUGHT:
        color = get_theme_color("doneTextColor")
    elif state == GroceryState.NOT_TO_BUY:
        color = get_theme_color("cancelledTextColor")
    # elif state == GroceryState.TO_BUY:
    #     color = get_theme_color("hiddenTextColor")
    return [f"color: {color}"] * len(row)


def _toggle_grocery_mode(df: pd.DataFrame):
    df = df[df["state"] != STATE_TO_LABEL[GroceryState.NOT_TO_BUY]].reset_index(drop=True)
    column_config = _column_config()
    column_config["completed"] = st.column_config.ButtonColumn("", width="30", key="bought_button", on_click=_on_bought_button_click, type="tertiary")
    column_config["last_bought_date"] = None 
    column_config["name"]["disabled"] = True
    return df, column_config

def render() -> None:
    """Render the 'Groceries' tab: toolbar (export/import) + the shopping-list grid."""
    st.markdown("### Liste de courses", anchors=False)

    toolbar = st.container(horizontal=True, width="content", vertical_alignment="center")
    toolbar.download_button(
        "⭳ Export list", data=_export_json_bytes(), file_name="groceries.json", mime="application/json",
    )
    if toolbar.button("⭱ Import list"):
        _import_groceries_dialog()

        
    column_config = _column_config()
    df = _to_dataframe(st.session_state.groceries)
    if toolbar.toggle("🛒 Grocery mode"): 
        df, column_config = _toggle_grocery_mode(df)


    if df is None:
        st.info("No grocery items yet — use \u201cAdd item\u201d to create your first one.")
        return
    

    st.session_state.groceries_df = df

    styled_df = df.style.apply(_color_by_state, axis=1)

    key = st.session_state.groceries_grid_key
    st.data_editor(
        styled_df,
        column_config=column_config,
        hide_index=True,
        width="content",
        height="content",
        key=key,
        num_rows="fixed",
        on_change=_on_data_change,
    )
