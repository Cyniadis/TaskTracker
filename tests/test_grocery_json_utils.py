"""Persistence + import-validation tests for groceries.json_utils.

Mirrors tests/test_json_utils.py's TestTaskListRoundTrip conventions —
every round-trip test uses a tmp_path so the real groceries.json is never
touched.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from groceries import json_utils as grocery_json_utils
from groceries.grocery import GroceryItem, GroceryState


@pytest.fixture
def groceries_file(tmp_path):
    return tmp_path / "groceries.json"


class TestGroceryListRoundTrip:
    def test_a_bought_item_stays_bought_after_save_and_load(self, groceries_file):
        item = GroceryItem(id=1, name="Lait", state=GroceryState.BOUGHT.value, last_bought_date=date(2026, 7, 26))

        grocery_json_utils.save_groceries([item], path=groceries_file)
        reloaded = grocery_json_utils.load_groceries(path=groceries_file)

        assert len(reloaded) == 1
        assert reloaded[0].state == GroceryState.BOUGHT.value
        assert reloaded[0].last_bought_date == date(2026, 7, 26)

    def test_an_item_with_no_last_bought_date_survives(self, groceries_file):
        item = GroceryItem(id=1, name="Pain")

        grocery_json_utils.save_groceries([item], path=groceries_file)
        reloaded = grocery_json_utils.load_groceries(path=groceries_file)[0]

        assert reloaded.last_bought_date is None
        assert reloaded.state == GroceryState.TO_BUY.value

    def test_loading_a_missing_file_returns_an_empty_list(self, tmp_path):
        missing = tmp_path / "does_not_exist.json"
        assert grocery_json_utils.load_groceries(path=missing) == []

    def test_saving_overwrites_the_previous_contents_entirely(self, groceries_file):
        grocery_json_utils.save_groceries(
            [GroceryItem(id=1, name="First"), GroceryItem(id=2, name="Second")], path=groceries_file,
        )
        grocery_json_utils.save_groceries([GroceryItem(id=3, name="Only this one now")], path=groceries_file)

        reloaded = grocery_json_utils.load_groceries(path=groceries_file)

        assert len(reloaded) == 1
        assert reloaded[0].name == "Only this one now"

    def test_reloaded_items_have_a_fresh_orig_snapshot(self, groceries_file):
        item = GroceryItem(id=1, name="Lait")
        item.name = "Lait edited before save"

        grocery_json_utils.save_groceries([item], path=groceries_file)
        reloaded = grocery_json_utils.load_groceries(path=groceries_file)[0]

        assert reloaded.get_changes() == []


class TestNextGroceryId:
    def test_returns_zero_for_an_empty_list(self):
        assert grocery_json_utils.next_grocery_id([]) == 0

    def test_returns_one_past_the_highest_existing_id(self):
        items = [GroceryItem(id=1, name="A"), GroceryItem(id=5, name="B")]
        assert grocery_json_utils.next_grocery_id(items) == 6


# ---------------------------------------------------------------------------
# import validation — mirrors test_json_utils.py's coverage of
# validate_and_parse_tasks / import_tasks_from_json_bytes.
# ---------------------------------------------------------------------------

class TestImportValidation:
    def test_valid_payload_is_parsed_into_grocery_items(self):
        raw = [{"id": 1, "name": "Lait", "state": "achete", "last_bought_date": "2026-07-26"}]
        items = grocery_json_utils.validate_and_parse_groceries(raw)

        assert len(items) == 1
        assert items[0].name == "Lait"
        assert items[0].state == GroceryState.BOUGHT.value
        assert items[0].last_bought_date == date(2026, 7, 26)

    def test_minimal_payload_with_only_id_and_name_is_valid(self):
        items = grocery_json_utils.validate_and_parse_groceries([{"id": 1, "name": "Pain"}])
        assert items[0].state == GroceryState.TO_BUY.value

    def test_rejects_non_list_payload(self):
        with pytest.raises(ValueError, match="JSON array"):
            grocery_json_utils.validate_and_parse_groceries({"id": 1, "name": "Lait"})

    def test_rejects_empty_list(self):
        with pytest.raises(ValueError, match="empty"):
            grocery_json_utils.validate_and_parse_groceries([])

    def test_rejects_missing_id(self):
        with pytest.raises(ValueError, match="missing required field 'id'"):
            grocery_json_utils.validate_and_parse_groceries([{"name": "Lait"}])

    def test_rejects_duplicate_ids(self):
        raw = [{"id": 1, "name": "Lait"}, {"id": 1, "name": "Pain"}]
        with pytest.raises(ValueError, match="duplicate id"):
            grocery_json_utils.validate_and_parse_groceries(raw)

    def test_rejects_missing_name(self):
        with pytest.raises(ValueError, match="missing or empty required field 'name'"):
            grocery_json_utils.validate_and_parse_groceries([{"id": 1, "name": ""}])

    def test_rejects_invalid_state(self):
        raw = [{"id": 1, "name": "Lait", "state": "bogus"}]
        with pytest.raises(ValueError, match="invalid 'state' value"):
            grocery_json_utils.validate_and_parse_groceries(raw)

    def test_rejects_invalid_last_bought_date(self):
        raw = [{"id": 1, "name": "Lait", "last_bought_date": "not-a-date"}]
        with pytest.raises(ValueError, match="invalid 'last_bought_date' value"):
            grocery_json_utils.validate_and_parse_groceries(raw)

    def test_import_from_bytes_round_trips_a_valid_file(self):
        raw = [{"id": 1, "name": "Lait", "state": "a_acheter"}]
        raw_bytes = json.dumps(raw).encode("utf-8")

        items = grocery_json_utils.import_groceries_from_json_bytes(raw_bytes)

        assert len(items) == 1
        assert items[0].name == "Lait"

    def test_import_from_bytes_rejects_malformed_json(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            grocery_json_utils.import_groceries_from_json_bytes(b"{not json")

    def test_import_from_bytes_rejects_bad_utf8(self):
        with pytest.raises(ValueError, match="not valid UTF-8"):
            grocery_json_utils.import_groceries_from_json_bytes(b"\xff\xfe\x00\x00")
