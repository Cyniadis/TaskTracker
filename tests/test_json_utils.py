"""Persistence tests for tasktracker.json_utils — the real, cross-process
persistence layer (write tasklist.json/cache.json to disk, read them back),
as opposed to tests/ui/test_persistence.py which covers same-session
Streamlit reruns. Every test here uses a tmp_path so the real project
files are never touched.
"""
from __future__ import annotations

from datetime import date

import pytest

from tasktracker import json_utils
from tasktracker.task import Task


@pytest.fixture
def tasks_file(tmp_path):
    return tmp_path / "tasklist.json"


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    """Redirect the cache.json helpers (which have no `path=` parameter,
    unlike load/save_tasks) at a throwaway file for this test."""
    path = tmp_path / "cache.json"
    monkeypatch.setattr(json_utils, "CACHE_FILE", path)
    return path


# ---------------------------------------------------------------------------
# tasklist.json round trip
# ---------------------------------------------------------------------------

class TestTaskListRoundTrip:
    def test_a_completed_task_stays_completed_after_save_and_load(self, tasks_file):
        task = Task(id=1, name="Task A", duration=10, priority=2.0, initial_priority=2.0)
        task.complete(date(2026, 7, 21))

        json_utils.save_tasks([task], path=tasks_file)
        reloaded = json_utils.load_tasks(path=tasks_file)

        assert len(reloaded) == 1
        assert reloaded[0].done_date == date(2026, 7, 21)
        assert reloaded[0].priority == 2.0

    def test_an_incomplete_task_stays_incomplete_after_save_and_load(self, tasks_file):
        task = Task(id=1, name="Task A", duration=10, due_date=date(2026, 7, 22), done_date=None)

        json_utils.save_tasks([task], path=tasks_file)
        reloaded = json_utils.load_tasks(path=tasks_file)

        assert reloaded[0].done_date is None
        assert reloaded[0].due_date == date(2026, 7, 22)

    def test_multiple_tasks_with_mixed_completion_states_all_survive(self, tasks_file):
        done = Task(id=1, name="Done", done_date=date(2026, 7, 20))
        pending = Task(id=2, name="Pending", done_date=None)
        overdue = Task(id=3, name="Overdue", due_date=date(2026, 7, 1), done_date=None)

        json_utils.save_tasks([done, pending, overdue], path=tasks_file)
        reloaded = {t.id: t for t in json_utils.load_tasks(path=tasks_file)}

        assert reloaded[1].done_date == date(2026, 7, 20)
        assert reloaded[2].done_date is None
        assert reloaded[3].due_date == date(2026, 7, 1)

    def test_priority_and_frequency_survive_the_round_trip(self, tasks_file):
        task = Task(id=1, name="Task A", frequency="3xsemaine", priority=4.5, initial_priority=1.5)

        json_utils.save_tasks([task], path=tasks_file)
        reloaded = json_utils.load_tasks(path=tasks_file)[0]

        assert reloaded.frequency == "3xsemaine"
        assert reloaded.priority == 4.5
        assert reloaded.initial_priority == 1.5

    def test_a_task_with_no_dates_at_all_survives(self, tasks_file):
        task = Task(id=1, name="Never scheduled", due_date=None, done_date=None)

        json_utils.save_tasks([task], path=tasks_file)
        reloaded = json_utils.load_tasks(path=tasks_file)[0]

        assert reloaded.due_date is None
        assert reloaded.done_date is None

    def test_reloaded_tasks_have_a_fresh_orig_snapshot_matching_the_saved_state(self, tasks_file):
        # Reloading from disk is meant to represent the new "last persisted"
        # baseline — get_changes() should report no pending changes right
        # after a fresh load, even for a task that had in-memory edits
        # before it was saved.
        task = Task(id=1, name="Task A", priority=1.0)
        task.name = "Edited before save"
        task.priority = 9.0

        json_utils.save_tasks([task], path=tasks_file)
        reloaded = json_utils.load_tasks(path=tasks_file)[0]

        assert reloaded.get_changes() == []

    def test_saving_overwrites_the_previous_contents_entirely(self, tasks_file):
        json_utils.save_tasks([Task(id=1, name="First"), Task(id=2, name="Second")], path=tasks_file)
        json_utils.save_tasks([Task(id=3, name="Only this one now")], path=tasks_file)

        reloaded = json_utils.load_tasks(path=tasks_file)

        assert len(reloaded) == 1
        assert reloaded[0].name == "Only this one now"

    def test_loading_a_missing_file_returns_an_empty_list(self, tmp_path):
        missing = tmp_path / "does_not_exist.json"
        assert json_utils.load_tasks(path=missing) == []

    def test_empty_task_list_round_trips_to_an_empty_list(self, tasks_file):
        json_utils.save_tasks([], path=tasks_file)
        assert json_utils.load_tasks(path=tasks_file) == []

    def test_unicode_task_names_survive_the_round_trip(self, tasks_file):
        task = Task(id=1, name="🍴 Nettoyer la vaisselle à la main")

        json_utils.save_tasks([task], path=tasks_file)
        reloaded = json_utils.load_tasks(path=tasks_file)[0]

        assert reloaded.name == "🍴 Nettoyer la vaisselle à la main"


# ---------------------------------------------------------------------------
# cache.json round trip — the values that back the 'Today' tab's checkboxes
# and daily-limit input across a real page reload / process restart.
# ---------------------------------------------------------------------------

class TestCacheRoundTrip:
    def test_show_completed_checkbox_state_survives(self, cache_file):
        json_utils.cache_show_completed(False)
        assert json_utils.load_show_completed() is False

        json_utils.cache_show_completed(True)
        assert json_utils.load_show_completed() is True

    def test_show_rescheduled_checkbox_state_survives(self, cache_file):
        json_utils.cache_show_rescheduled(False)
        assert json_utils.load_show_rescheduled() is False

    def test_allow_future_tasks_checkbox_state_survives(self, cache_file):
        json_utils.cache_allow_future_tasks(True)
        assert json_utils.load_allow_future_tasks() is True

    def test_daily_limit_survives(self, cache_file):
        json_utils.cache_daily_limit(90)
        assert json_utils.load_cached_daily_limit() == 90

    def test_defaults_when_cache_file_does_not_exist_yet(self, cache_file):
        # cache_file fixture points at a path that hasn't been written to.
        assert json_utils.load_show_completed() is True
        assert json_utils.load_show_rescheduled() is True
        assert json_utils.load_allow_future_tasks() is False
        assert json_utils.load_cached_daily_limit() == json_utils.DEFAULT_DAILY_LIMIT_MINUTES

    def test_caching_one_value_does_not_clobber_the_others(self, cache_file):
        json_utils.cache_show_completed(False)
        json_utils.cache_daily_limit(45)
        json_utils.cache_show_rescheduled(False)

        assert json_utils.load_show_completed() is False
        assert json_utils.load_cached_daily_limit() == 45
        assert json_utils.load_show_rescheduled() is False

    def test_todays_selected_task_ids_survive_for_reuse_on_a_later_render(self, cache_file):
        tasks = [Task(id=1, name="A"), Task(id=2, name="B")]
        json_utils.cache_tasks(tasks)

        cache_date, cached_ids = json_utils.load_cached_task_ids()

        assert cached_ids == [1, 2]
        assert cache_date is not None

    def test_delete_cached_value_removes_only_that_key(self, cache_file):
        json_utils.cache_daily_limit(90)
        json_utils.cache_show_completed(False)

        json_utils.delete_cached_value("daily_limit")

        assert json_utils.load_cached_daily_limit() == json_utils.DEFAULT_DAILY_LIMIT_MINUTES
        assert json_utils.load_show_completed() is False  # untouched

    def test_deleting_a_missing_key_is_a_no_op(self, cache_file):
        json_utils.delete_cached_value("nonexistent")  # should not raise
