"""Datasheet theme — denser type, fact-blue primary (not a customer brand)."""
from artifact_engine.model.theme import Theme

DATASHEET = Theme(
    name="datasheet",
    primary_color="#1450B4",
    secondary_color="#16181D",
    text_color="#16181D",
    muted_color="#5A6472",
    border_color="#DCD9D0",
    background="#FFFFFF",
    page_chrome="#E9E7E0",
    font_sans="Arial, Helvetica, sans-serif",
    font_mono="'IBM Plex Mono', Consolas, monospace",
    h1=24,
    h2=13,
    h3=11,
    body=9.5,
    caption=8,
    table=8.5,
    footer=7.5,
    page_margin_mm=14,
    gutter_mm=5,
    baseline_pt=12,
    column_count=12,
    accent="#F5C400",
)
