"""Provenance colors + sheet tokens — contract with 0.24/0.26.

Sheet ink / paper / accent can follow ArtifactEngine Theme; provenance
colors stay fixed (extracted / user / reference contract).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from artifact_engine.model.theme import Theme

INK = "#16181D"
PAPER = "#F2F0EA"
SHEET = "#FFFFFF"
SIGNAL = "#F5C400"
STEEL = "#5A6472"
LINE = "#DCD9D0"
PROV = {
    "extracted": ("#1450B4", None),
    "user": ("#1E7A46", None),
    "verified_by_user": ("#1E7A46", None),
    "reference": ("#C74E19", "6,4"),
}

BOX_W, BOX_H_BASE, PIN_H, COL_GAP, ROW_GAP, PAD = 190, 46, 16, 110, 34, 28


def tokens_from_theme(theme: "Theme | None" = None) -> dict:
    """Map ArtifactEngine Theme → diagram sheet tokens. PROV unchanged."""
    if theme is None:
        return {
            "ink": INK,
            "paper": PAPER,
            "sheet": SHEET,
            "signal": SIGNAL,
            "steel": STEEL,
            "line": LINE,
            "font": "Arial,Helvetica,sans-serif",
        }
    return {
        "ink": theme.primary_color or INK,
        "paper": theme.page_chrome or PAPER,
        "sheet": theme.background or SHEET,
        "signal": theme.accent or SIGNAL,
        "steel": theme.muted_color or STEEL,
        "line": theme.border_color or LINE,
        "font": theme.font_sans or "Arial,Helvetica,sans-serif",
    }
