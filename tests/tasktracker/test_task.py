"""Unit tests for tasktracker.task (Period, Frequency, normalize_date, Task)."""
from __future__ import annotations

from datetime import date, datetime
import subprocess
import sys

import pytest

from tasktracker.task import Frequency, Period, Task, TaskDueDateState, normalize_date
from tasktracker.task_list_ops import set_due_date_task_list


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

    def test_date_fields_are_normalized_on_construction(self, make_task):
        task = make_task(name="x", due_date="15/01/2026", done_date="2026-01-14")
        assert task.due_date == date(2026, 1, 15)
        assert task.done_date == date(2026, 1, 14)


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

    def test_to_dict_excludes_orig_fields(self):
        task = Task(name="Test")
        payload = task.to_dict()
        assert all(not key.startswith("orig_") for key in payload)

    def test_to_dict_serializes_dates_as_iso_strings(self, make_task):
        task = make_task(name="Test", due_date=date(2026, 7, 21), done_date=None)
        payload = task.to_dict()
        assert payload["due_date"] == "2026-07-21"
        assert payload["done_date"] is None

    def test_roundtrip_from_dict_to_dict(self):
        original = {
            "id": 3, "name": "Roundtrip", "frequency": "2xsemaine",
            "priority": 4.5, "initial_priority": 2.0, "duration": 15,
            "due_date": "2026-07-21", "done_date": None, 
            "state": {'completed': False, 'due_date_state': 'normal'},
        }
        print(original)
        print()
        task = Task.from_dict(original)
        print(task.to_dict())
        assert task.to_dict() == original


# ---------------------------------------------------------------------------
# Task: frequency helpers
# ---------------------------------------------------------------------------

class TestTaskFrequencyHelpers:
    def test_frequency_obj_parses_the_frequency_string(self, make_task):
        task = make_task(frequency="3xmois")
        assert task.frequency_obj == Frequency(count=3, period=Period.MONTH)

    def test_get_next_due_date_adds_frequency_days(self, make_task):
        task = make_task(frequency="1xsemaine")
        next_due = task.get_next_due_date(date(2026, 7, 21))
        assert next_due == date(2026, 7, 28)

    def test_get_next_due_date_for_daily_task(self, make_task):
        task = make_task(frequency="1xjour")
        assert task.get_next_due_date(date(2026, 7, 21)) == date(2026, 7, 22)


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

    def test_complete_sets_is_completed_true(self, make_task):
        task = make_task()
        task.complete(date(2026, 7, 21))
        assert task.is_completed() is True

    def test_uncomplete_sets_is_completed_false(self, make_task):
        task = make_task()
        task.complete(date(2026, 7, 21))
        task.uncomplete()
        assert task.is_completed() is False

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
        task.set_due_date(date(2026, 7, 21))
        assert task.due_date == date(2026, 7, 21)


class TestScheduleTaskList:
    def test_sets_due_date_on_every_task_in_the_list(self, make_task):
        tasks = [make_task(), make_task(), make_task()]
        set_due_date_task_list(tasks, date(2026, 7, 21))
        assert all(t.due_date == date(2026, 7, 21) for t in tasks)

    def test_empty_list_is_a_no_op(self):
        set_due_date_task_list([], date(2026, 7, 21))  # should not raise


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
        with pytest.raises(AttributeError):
            task.set_field("due_date", "21/07/2026")

    def test_unknown_field_raises_attribute_error(self, make_task):
        task = make_task()
        with pytest.raises(AttributeError):
            task.set_field("not_a_real_field", 123)



# ---------------------------------------------------------------------------
# Task: due-date-state machine (cancel / manually_reschedule / set_due_date)
#
# Covers the invariants documented in task.py's module docstring: cancel()
# and manually_reschedule() are mutually exclusive, and a plain set_due_date()
# clears any prior cancellation. There was no coverage at all for this before
# — it's the actual point of the "rework-task-state" branch.
# ---------------------------------------------------------------------------

class TestCancel:
    def test_clears_due_date(self, make_task):
        task = make_task(due_date=date(2026, 7, 21))
        task.cancel()
        assert task.due_date is None

    def test_sets_cancelled_state(self, make_task):
        task = make_task()
        task.cancel()
        assert task.is_cancelled() is True
        assert task.state.due_date_state == TaskDueDateState.CANCELLED

    def test_is_not_manually_rescheduled(self, make_task):
        task = make_task()
        task.cancel()
        assert task.is_manually_rescheduled() is False


class TestManuallyReschedule:
    def test_sets_due_date_to_the_given_date(self, make_task):
        task = make_task(due_date=None)
        task.manually_reschedule(date(2026, 7, 21))
        assert task.due_date == date(2026, 7, 21)

    def test_sets_manually_rescheduled_state(self, make_task):
        task = make_task()
        task.manually_reschedule(date(2026, 7, 21))
        assert task.is_manually_rescheduled() is True
        assert task.state.due_date_state == TaskDueDateState.MANUALLY_RESCHEDULED

    def test_is_not_cancelled(self, make_task):
        task = make_task()
        task.manually_reschedule(date(2026, 7, 21))
        assert task.is_cancelled() is False

    def test_is_manually_rescheduled_on_today_true_when_due_date_is_today(self, make_task, monkeypatch):
        import tasktracker.task as task_module
        monkeypatch.setattr(task_module, "today", lambda: date(2026, 7, 21))
        task = make_task()
        task.manually_reschedule(date(2026, 7, 21))
        assert task.is_manually_rescheduled_on_today() is True

    def test_is_manually_rescheduled_on_today_false_for_a_different_day(self, make_task, monkeypatch):
        import tasktracker.task as task_module
        monkeypatch.setattr(task_module, "today", lambda: date(2026, 7, 22))
        task = make_task()
        task.manually_reschedule(date(2026, 7, 21))
        assert task.is_manually_rescheduled_on_today() is False


class TestDueDateStateTransitions:
    """The three due-date states are mutually exclusive for the same task —
    every transition method must clear the other two."""

    def test_manually_reschedule_after_cancel_clears_cancelled(self, make_task):
        task = make_task()
        task.cancel()
        task.manually_reschedule(date(2026, 7, 21))
        assert task.is_cancelled() is False
        assert task.is_manually_rescheduled() is True

    def test_cancel_after_manually_reschedule_clears_manually_rescheduled(self, make_task):
        task = make_task()
        task.manually_reschedule(date(2026, 7, 21))
        task.cancel()
        assert task.is_manually_rescheduled() is False
        assert task.is_cancelled() is True

    def test_plain_set_due_date_clears_cancelled(self, make_task):
        task = make_task()
        task.cancel()
        task.set_due_date(date(2026, 7, 21))
        assert task.is_cancelled() is False
        assert task.due_date == date(2026, 7, 21)

    def test_completed_is_independent_of_due_date_state(self, make_task):
        """A task can be both manually-scheduled for today and completed
        today at the same time — completed isn't folded into due_date_state."""
        task = make_task()
        task.manually_reschedule(date(2026, 7, 21))
        task.complete(date(2026, 7, 21))
        assert task.is_manually_rescheduled() is True
        assert task.is_completed_on(date(2026, 7, 21)) is True


# ---------------------------------------------------------------------------
# Regression: task.py must be importable standalone
#
# task.py's own docstring promises "no dependency on Streamlit, pandas, or
# any storage mechanism". A stray `from tasktracker import ui_state` briefly
# crept in — unused, and circular (task -> ui_state -> tt_json_utils ->
# task). It didn't fail inside the normal pytest run only because conftest.py
# happens to import general_tab (which imports ui_state) before task.py, so
# ui_state was already sitting in sys.modules by the time task.py's import
# line ran. Importing tasktracker.task fresh, as the very first import in a
# clean interpreter, is what actually exercises the bug.
# ---------------------------------------------------------------------------

class TestModuleIsImportableStandalone:
    def test_import_tasktracker_task_first_in_a_fresh_interpreter(self):
        result = subprocess.run(
            [sys.executable, "-c", "import tasktracker.task"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
