"""Foldok engineering theme — ink / signal / paper (matches form/diagram engines)."""
from artifact_engine.model.theme import Theme

ENGINEERING = Theme(
    name="engineering",
    primary_color="#16181D",
    secondary_color="#5A6472",
    text_color="#16181D",
    muted_color="#5A6472",
    border_color="#DCD9D0",
    background="#FFFFFF",
    page_chrome="#E9E7E0",
    font_sans="Arial, Helvetica, sans-serif",
    font_mono="'IBM Plex Mono', Consolas, monospace",
    h1=26,
    h2=14,
    h3=12,
    body=10.5,
    caption=9,
    table=9,
    footer=8,
    page_margin_mm=16,
    gutter_mm=6,
    baseline_pt=14,
    column_count=12,
    accent="#F5C400",
)
