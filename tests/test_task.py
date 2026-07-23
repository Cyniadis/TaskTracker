"""Unit tests for tasktracker.task (Period, Frequency, normalize_date, Task)."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from tasktracker.task import Frequency, Period, Task, normalize_date, schedule_task_list


# ---------------------------------------------------------------------------
# Period
# ---------------------------------------------------------------------------

class TestPeriod:
    @pytest.mark.parametrize("period, expected_days", [
        (Period.DAY, 1.0),
        (Period.WEEK, 7.0),
        (Period.MONTH, 30.4),
        (Period.YEAR, 365.0),
    ])
    def test_length_in_days(self, period, expected_days):
        assert period.length_in_days == expected_days

    def test_period_is_str_enum_valued_by_french_word(self):
        assert Period("semaine") is Period.WEEK
        assert Period.DAY.value == "jour"


# ---------------------------------------------------------------------------
# Frequency
# ---------------------------------------------------------------------------

class TestFrequencyParse:
    def test_parses_count_and_period(self):
        freq = Frequency.parse("2xsemaine")
        assert freq.count == 2
        assert freq.period is Period.WEEK

    def test_parse_is_case_insensitive(self):
        freq = Frequency.parse("3XMOIS")
        assert freq.count == 3
        assert freq.period is Period.MONTH

    @pytest.mark.parametrize("bad_text", [None, "", "garbage", "2x", "xsemaine", "2xnotaperiod", "twoxsemaine"])
    def test_falls_back_to_default_on_bad_input(self, bad_text):
        freq = Frequency.parse(bad_text)
        assert freq == Frequency(count=1, period=Period.DAY)

    def test_str_roundtrips_through_parse(self):
        freq = Frequency(count=5, period=Period.MONTH)
        assert Frequency.parse(str(freq)) == freq

    def test_str_format(self):
        assert str(Frequency(count=2, period=Period.WEEK)) == "2xsemaine"

    def test_frequency_is_frozen(self):
        freq = Frequency()
        with pytest.raises(Exception):
            freq.count = 5


class TestFrequencyDays:
    def test_days_is_period_length_divided_by_count(self):
        assert Frequency(count=2, period=Period.WEEK).days == pytest.approx(3.5)

    def test_daily_task_days_is_one(self):
        assert Frequency(count=1, period=Period.DAY).days == 1.0

    def test_higher_count_means_fewer_days_between_occurrences(self):
        assert Frequency(count=4, period=Period.MONTH).days < Frequency(count=1, period=Period.MONTH).days


# ---------------------------------------------------------------------------
# normalize_date
# ---------------------------------------------------------------------------

class TestNormalizeDate:
    @pytest.mark.parametrize("value", [None, ""])
    def test_none_and_empty_string_become_none(self, value):
        assert normalize_date(value) is None

    def test_nan_becomes_none(self):
        nan = float("nan")
        assert normalize_date(nan) is None

    def test_date_passthrough(self):
        d = date(2026, 1, 15)
        assert normalize_date(d) is d

    def test_datetime_is_truncated_to_date(self):
        dt = datetime(2026, 1, 15, 13, 30)
        assert normalize_date(dt) == date(2026, 1, 15)

    def test_slash_format_string(self):
        assert normalize_date("15/01/2026") == date(2026, 1, 15)

    def test_iso_format_string(self):
        assert normalize_date("2026-01-15") == date(2026, 1, 15)

    def test_string_is_stripped(self):
        assert normalize_date("  2026-01-15  ") == date(2026, 1, 15)

    def test_literal_nan_string_becomes_none(self):
        assert normalize_date("NaN") is None
        assert normalize_date("nan") is None

    def test_blank_string_becomes_none(self):
        assert normalize_date("   ") is None

    def test_numpy_like_scalar_with_item_method(self):
        class FakeScalar:
            def __init__(self, value):
                self._value = value

            def item(self):
                return self._value

        assert normalize_date(FakeScalar("2026-01-15")) == date(2026, 1, 15)

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            normalize_date(12345)

    def test_bad_string_raises(self):
        with pytest.raises(ValueError):
            normalize_date("not-a-date")


# ---------------------------------------------------------------------------
# Task: construction / normalization
# ---------------------------------------------------------------------------

class TestTaskConstruction:
    def test_default_frequency_is_one_per_day(self, make_task):
        task = make_task()
        assert task.frequency == "1xjour"

    def test_date_fields_are_normalized_on_construction(self):
        task = Task(id=1, name="x", due_date="15/01/2026", done_date="2026-01-14")
        assert task.due_date == date(2026, 1, 15)
        assert task.done_date == date(2026, 1, 14)

    def test_orig_snapshot_matches_initial_values(self, make_task):
        task = make_task(name="Water plants", priority=3.0)
        assert task.orig_name == "Water plants"
        assert task.orig_priority == 3.0
        assert task.orig_due_date == task.due_date
        assert task.orig_done_date == task.done_date


# ---------------------------------------------------------------------------
# Task: (de)serialization
# ---------------------------------------------------------------------------

class TestTaskSerialization:
    def test_from_dict_ignores_unknown_and_orig_fields(self):
        data = {
            "id": 5, "name": "Test", "frequency": "1xjour",
            "orig_name": "should be ignored", "some_extra_field": "ignored too",
        }
        task = Task.from_dict(data)
        assert task.id == 5
        assert task.name == "Test"
        assert task.orig_name == "Test"  # set by __post_init__, not from input

    def test_to_dict_excludes_orig_fields(self):
        task = Task(id=1, name="Test")
        payload = task.to_dict()
        assert all(not key.startswith("orig_") for key in payload)

    def test_to_dict_serializes_dates_as_iso_strings(self):
        task = Task(id=1, name="Test", due_date=date(2026, 7, 21), done_date=None)
        payload = task.to_dict()
        assert payload["due_date"] == "2026-07-21"
        assert payload["done_date"] is None

    def test_roundtrip_from_dict_to_dict(self):
        original = {
            "id": 3, "name": "Roundtrip", "frequency": "2xsemaine",
            "priority": 4.5, "initial_priority": 2.0, "duration": 15,
            "due_date": "2026-07-21", "done_date": None,
        }
        task = Task.from_dict(original)
        assert task.to_dict() == original


# ---------------------------------------------------------------------------
# Task: frequency helpers
# ---------------------------------------------------------------------------

class TestTaskFrequencyHelpers:
    def test_frequency_obj_parses_the_frequency_string(self, make_task):
        task = make_task(frequency="3xmois")
        assert task.frequency_obj == Frequency(count=3, period=Period.MONTH)

    def test_compute_next_due_date_adds_frequency_days(self, make_task):
        task = make_task(frequency="1xsemaine")
        next_due = task.compute_next_due_date(date(2026, 7, 21))
        assert next_due == date(2026, 7, 28)

    def test_compute_next_due_date_for_daily_task(self, make_task):
        task = make_task(frequency="1xjour")
        assert task.compute_next_due_date(date(2026, 7, 21)) == date(2026, 7, 22)


# ---------------------------------------------------------------------------
# Task: priority
# ---------------------------------------------------------------------------

class TestTaskPriority:
    def test_increment_priority_adds_the_configured_increment(self, make_task):
        task = make_task(priority=2.0)
        task.increment_priority()
        assert task.priority == 2.5

    def test_increment_priority_can_be_called_repeatedly(self, make_task):
        task = make_task(priority=0.0)
        task.increment_priority()
        task.increment_priority()
        assert task.priority == 1.0


# ---------------------------------------------------------------------------
# Task: lifecycle (complete / uncomplete)
# ---------------------------------------------------------------------------

class TestTaskLifecycle:
    def test_complete_sets_done_date_and_resets_priority(self, make_task):
        task = make_task(priority=5.0, initial_priority=2.0)
        task.complete(date(2026, 7, 21))
        assert task.done_date == date(2026, 7, 21)
        assert task.priority == 2.0

    def test_uncomplete_restores_priority_and_done_date_from_before_complete(self, make_task):
        task = make_task(priority=5.0, initial_priority=2.0, done_date=date(2026, 7, 1))
        task.complete(date(2026, 7, 21))
        task.uncomplete()
        assert task.done_date == date(2026, 7, 1)
        assert task.priority == 5.0

    def test_uncomplete_without_prior_complete_falls_back_to_orig_priority(self, make_task):
        task = make_task(priority=3.0)
        task.priority = 9.0  # simulate an edit with no complete() call yet
        task.uncomplete()
        assert task.priority == 3.0
        assert task.done_date is None

    def test_uncomplete_clears_the_stashed_pre_complete_state(self, make_task):
        task = make_task()
        task.complete(date(2026, 7, 21))
        task.uncomplete()
        assert task._pre_complete_priority is None
        assert task._pre_complete_done_date is None

    def test_double_complete_then_uncomplete_only_undoes_the_last_call(self, make_task):
        task = make_task(priority=1.0, initial_priority=1.0)
        task.complete(date(2026, 7, 1))    # priority -> 1.0 (initial), done_date -> 7/1
        task.priority = 6.0                # simulate priority bumped by housekeeping
        task.complete(date(2026, 7, 21))   # priority -> 1.0 (initial), done_date -> 7/21
        task.uncomplete()
        assert task.done_date == date(2026, 7, 1)
        assert task.priority == 6.0

    def test_is_completed_on_true_when_done_date_matches(self, make_task):
        task = make_task(done_date=date(2026, 7, 21))
        assert task.is_completed_on(date(2026, 7, 21)) is True

    def test_is_completed_on_false_when_done_date_is_none(self, make_task):
        task = make_task(done_date=None)
        assert task.is_completed_on(date(2026, 7, 21)) is False

    def test_is_completed_on_false_for_a_different_date(self, make_task):
        task = make_task(done_date=date(2026, 7, 20))
        assert task.is_completed_on(date(2026, 7, 21)) is False

    def test_schedule_for_sets_due_date(self, make_task):
        task = make_task(due_date=None)
        task.schedule_for(date(2026, 7, 21))
        assert task.due_date == date(2026, 7, 21)


class TestScheduleTaskList:
    def test_sets_due_date_on_every_task_in_the_list(self, make_task):
        tasks = [make_task(id=1), make_task(id=2), make_task(id=3)]
        schedule_task_list(tasks, date(2026, 7, 21))
        assert all(t.due_date == date(2026, 7, 21) for t in tasks)

    def test_empty_list_is_a_no_op(self):
        schedule_task_list([], date(2026, 7, 21))  # should not raise


# ---------------------------------------------------------------------------
# Task: set_field
# ---------------------------------------------------------------------------

class TestSetField:
    def test_sets_a_plain_field(self, make_task):
        task = make_task(name="Old")
        task.set_field("name", "New")
        assert task.name == "New"

    def test_normalizes_date_fields(self, make_task):
        task = make_task(due_date=None)
        task.set_field("due_date", "21/07/2026")
        assert task.due_date == date(2026, 7, 21)

    def test_unknown_field_raises_attribute_error(self, make_task):
        task = make_task()
        with pytest.raises(AttributeError):
            task.set_field("not_a_real_field", 123)

    def test_set_field_does_not_touch_orig_snapshot(self, make_task):
        task = make_task(name="Old")
        task.set_field("name", "New")
        assert task.orig_name == "Old"


# ---------------------------------------------------------------------------
# Task: restore
# ---------------------------------------------------------------------------

class TestRestore:
    def test_restore_reverts_every_editable_field(self, make_task):
        task = make_task(
            name="Old", frequency="1xjour", priority=1.0, initial_priority=1.0,
            duration=10, due_date=date(2026, 7, 1), done_date=None,
        )
        task.name = "New"
        task.frequency = "2xsemaine"
        task.priority = 9.0
        task.initial_priority = 9.0
        task.duration = 99
        task.due_date = date(2026, 8, 1)
        task.done_date = date(2026, 8, 1)

        task.restore()

        assert task.name == "Old"
        assert task.frequency == "1xjour"
        assert task.priority == 1.0
        assert task.initial_priority == 1.0
        assert task.duration == 10
        assert task.due_date == date(2026, 7, 1)
        assert task.done_date is None

    def test_restore_is_idempotent(self, make_task):
        task = make_task(name="Old")
        task.name = "New"
        task.restore()
        task.restore()
        assert task.name == "Old"


# ---------------------------------------------------------------------------
# Task: get_changes
# ---------------------------------------------------------------------------

class TestGetChanges:
    def test_no_changes_returns_empty_list(self, make_task):
        task = make_task()
        assert task.get_changes() == []

    def test_name_change_is_reported(self, make_task):
        task = make_task(name="Old")
        task.name = "New"
        diffs = task.get_changes()
        assert ("Name", "Old", "New") in diffs

    def test_priority_change_reports_formatted_numbers(self, make_task):
        task = make_task(priority=1.0)
        task.priority = 2.5
        diffs = task.get_changes()
        assert ("Priority", "1.0", "2.5") in diffs

    def test_none_values_are_formatted_as_em_dash(self, make_task):
        task = make_task(due_date=None)
        task.due_date = date(2026, 7, 21)
        diffs = dict((label, (old, new)) for label, old, new in task.get_changes())
        assert diffs["Due date"][0] == "—"

    def test_multiple_changed_fields_all_reported(self, make_task):
        task = make_task(name="Old", duration=10)
        task.name = "New"
        task.duration = 20
        labels = {label for label, _, _ in task.get_changes()}
        assert labels == {"Name", "Duration"}

    def test_get_changes_does_not_mutate_state(self, make_task):
        task = make_task(name="Old")
        task.name = "New"
        task.get_changes()
        task.get_changes()
        assert task.name == "New"
        assert task.orig_name == "Old"
