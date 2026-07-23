"""AppTest-based tests for tasktracker/ui/general_tab.py's toolbar and
rendering. The grid itself (`st.data_editor`) has no AppTest query object
— see test_general_tab_grid_logic.py and tests/ui/conftest.py for how its
add/edit callbacks are covered instead. Dialogs (Import, Changes) aren't
covered here either, for the same reason.
"""
from __future__ import annotations

from tasktracker.task import Task


class TestEmptyState:
    def test_shows_no_tasks_message(self, general_app):
        at = general_app.run()
        assert any("No tasks yet" in i.value for i in at.info)

    def test_still_shows_discard_and_import_buttons(self, general_app):
        at = general_app.run()
        labels = [b.label for b in at.button]
        assert "⭯ Discard all changes" in labels
        assert "⭱ Import tasks" in labels

    def test_renders_without_error(self, general_app):
        at = general_app.run()
        assert len(at.exception) == 0


class TestPopulatedToolbar:
    def _seed(self, general_app):
        t1 = Task(id=1, name="Task A", duration=10, priority=2.0, initial_priority=2.0)
        t2 = Task(id=2, name="Task B", duration=5, priority=1.0, initial_priority=1.0)
        general_app.session_state["tasks"] = [t1, t2]
        return t1, t2

    def test_shows_the_edit_tasks_heading(self, general_app):
        self._seed(general_app)
        at = general_app.run()
        assert "Edit tasks" in at.markdown[0].value

    def test_shows_export_download_button(self, general_app):
        self._seed(general_app)
        at = general_app.run()
        assert any("Export tasks" in d.label for d in at.download_button)

    def test_shows_sort_by_selectbox_with_all_columns(self, general_app):
        self._seed(general_app)
        at = general_app.run()
        assert len(at.selectbox) == 1
        assert at.selectbox[0].label == "Sort by"
        assert "priority" in at.selectbox[0].options

    def test_default_sort_direction_is_ascending(self, general_app):
        self._seed(general_app)
        at = general_app.run()
        assert at.session_state["ascending"] is True
        assert any(b.label == "▲ Ascending" for b in at.button)

    def test_toggle_sort_flips_direction_and_button_label(self, general_app):
        self._seed(general_app)
        at = general_app.run()

        toggle = next(b for b in at.button if "scending" in b.label)
        at = toggle.click().run()

        assert at.session_state["ascending"] is False
        assert any(b.label == "▼ Descending" for b in at.button)

    def test_reset_priorities_restores_initial_priority(self, general_app):
        t1, t2 = self._seed(general_app)
        t1.priority = 99.0
        t2.priority = 42.0
        at = general_app.run()

        reset = next(b for b in at.button if b.label == "Reset priorities")
        at = reset.click().run()

        assert t1.priority == t1.initial_priority
        assert t2.priority == t2.initial_priority

    def test_renders_without_error(self, general_app):
        self._seed(general_app)
        at = general_app.run()
        assert len(at.exception) == 0
