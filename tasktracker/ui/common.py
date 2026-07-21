"""UI helpers shared by both the 'Today' and 'General' tabs."""
from __future__ import annotations

import streamlit as st

from ..task import Period

PERIOD_OPTIONS = [p.value for p in Period]


# -- theme colors ------------------------------------------------------------
#
# Streamlit doesn't expose named semantic colors (e.g. "the green Streamlit
# uses for success states") directly, so we hardcode the palette for both
# light and dark theme here and pick the right one based on the active theme.

_THEME_COLORS = {
    "light": {
        "primaryColor": "#ff4b4b",
        "backgroundColor": "#ffffff",
        "secondaryBackgroundColor": "#f0f2f6",
        "textColor": "#31333f",
        "redColor": "#ff4b4b",
        "orangeColor": "#ffa421",
        "yellowColor": "#faca2b",
        "blueColor": "#1c83e1",
        "greenColor": "#21c354",
        "violetColor": "#803df5",
        "grayColor": "#a3a8b8",
        # Text colors (light theme)
        "redTextColor": "#bd4043",
        "orangeTextColor": "#e2660c",
        "yellowTextColor": "#926c05",
        "blueTextColor": "#0054a3",
        "greenTextColor": "#158237",
        "violetTextColor": "#583f84",
        "grayTextColor": "#31333f",
        "hiddenTextColor": "#31333f36",
        "doneTextColor": "#15823755",
    },
    "dark": {
        "primaryColor": "#ff4b4b",
        "backgroundColor": "#0e1117",
        "secondaryBackgroundColor": "#262730",
        "textColor": "#fafafa",
        "redColor": "#ff2b2b",
        "orangeColor": "#ff8700",
        "yellowColor": "#ffe312",
        "blueColor": "#0068c9",
        "greenColor": "#09ab3b",
        "violetColor": "#803df5",
        "grayColor": "#555867",
        # Text colors (dark theme)
        "redTextColor": "#ff6c6c",
        "orangeTextColor": "#ffbd45",
        "yellowTextColor": "#ffffc2",
        "blueTextColor": "#3d9df3",
        "greenTextColor": "#5ce488",
        "violetTextColor": "#b27eff",
        "grayTextColor": "#d5dae5",
        "hiddenTextColor": "#fafafa36",
        "doneTextColor": "#09ab3c55",
    },
}


def get_theme_color(name: str) -> str:
    """Look up a named color for whichever theme (light/dark) is active."""
    theme_type = st.context.theme.type  # "light" or "dark"
    colors = _THEME_COLORS.get(theme_type, _THEME_COLORS["dark"])
    return colors[name]
