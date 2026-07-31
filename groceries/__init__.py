"""Grocery list feature: domain model, persistence, and the Streamlit tab.

Kept as its own subpackage (mirroring tasktracker/ui/ being the only place
that owns task-related Streamlit session state) so the shopping list stays
self-contained and doesn't need to touch the existing task.py / json_utils.py
/ ui/ modules.
"""
