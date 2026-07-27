from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    primary_color: str
    secondary_color: str
    text_color: str
    muted_color: str
    border_color: str
    background: str
    page_chrome: str  # screen backdrop behind the sheet
    font_sans: str
    font_mono: str
    h1: float
    h2: float
    h3: float
    body: float
    caption: float
    table: float
    footer: float
    page_margin_mm: float
    gutter_mm: float
    baseline_pt: float
    column_count: int
    accent: str  # signal bar / brand underline
