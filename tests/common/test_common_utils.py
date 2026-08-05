""" Unit tests for common/common_utils.py
"""
from __future__ import annotations

import pytest

from groceries.grocery import GroceryItem
from tasktracker.task import Task


class TestUniqueId:
    def test_no_task_id_collision(self):
        """Generate a bunch of tasks and ensure that all ids are unique."""
        sample_size = 1000
        ids = set()
        for i in range(sample_size):
            task = Task(name=f"Task {i}")
            ids.add(task.id)
        assert len(ids) == sample_size
    
    def test_no_grocery_id_collision(self):
        """Generate a bunch of grocery items and ensure that all ids are unique."""
        sample_size = 1000
        ids = set()
        for i in range(sample_size):
            grocery_item = GroceryItem(name=f"Grocery Item {i}")
            ids.add(grocery_item.id)
        assert len(ids) == sample_size
