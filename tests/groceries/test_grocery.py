"""Pure-domain tests for groceries.grocery — no Streamlit, no I/O."""
from datetime import date

from groceries.grocery import GroceryItem, GroceryState, STATE_TO_LABEL


def test_new_item_defaults_to_to_buy():
    item = GroceryItem(id=0, name="Lait")
    assert item.state == GroceryState.TO_BUY.value
    assert item.last_bought_date is None
    assert item.state_label == STATE_TO_LABEL[GroceryState.TO_BUY]


def test_set_state_from_label_to_bought_stamps_last_bought_date():
    item = GroceryItem(id=0, name="Lait")
    today = date(2026, 7, 27)

    item.set_state_from_label(STATE_TO_LABEL[GroceryState.BOUGHT], today)

    assert item.state == GroceryState.BOUGHT.value
    assert item.last_bought_date == today


def test_set_state_from_label_to_not_to_buy_leaves_last_bought_date_untouched():
    item = GroceryItem(id=0, name="Lait")
    bought_date = date(2026, 7, 20)
    item.set_state_from_label(STATE_TO_LABEL[GroceryState.BOUGHT], bought_date)

    item.set_state_from_label(STATE_TO_LABEL[GroceryState.NOT_TO_BUY], date(2026, 7, 27))

    assert item.state == GroceryState.NOT_TO_BUY.value
    assert item.last_bought_date == bought_date


def test_set_field_updates_name():
    item = GroceryItem(id=0, name="Lait")
    item.set_field("name", "Lait demi-écrémé")
    assert item.name == "Lait demi-écrémé"


def test_set_field_rejects_unknown_field():
    item = GroceryItem(id=0, name="Lait")
    try:
        item.set_field("bogus", "x")
        assert False, "expected AttributeError"
    except AttributeError:
        pass


def test_to_dict_and_from_dict_round_trip():
    item = GroceryItem(id=3, name="Pommes", state=GroceryState.BOUGHT.value, last_bought_date=date(2026, 7, 26))
    payload = item.to_dict()

    assert payload["last_bought_date"] == "2026-07-26"

    rebuilt = GroceryItem.from_dict(payload)
    assert rebuilt.id == 3
    assert rebuilt.name == "Pommes"
    assert rebuilt.state == GroceryState.BOUGHT.value
    assert rebuilt.last_bought_date == date(2026, 7, 26)
