"""User-manual theme — denser body type, chapter-friendly margins.

Not a customer brand. theme=\"akva\" aliases here for legacy AST samples
without shipping real-brand tokens.
"""
from artifact_engine.model.theme import Theme

MANUAL = Theme(
    name="manual",
    primary_color="#1B2A4A",
    secondary_color="#3D4F6F",
    text_color="#1A1A1A",
    muted_color="#5A6472",
    border_color="#C8CDD5",
    background="#FFFFFF",
    page_chrome="#E8EAED",
    font_sans="Arial, Helvetica, sans-serif",
    font_mono="'IBM Plex Mono', Consolas, monospace",
    h1=24,
    h2=13,
    h3=11,
    body=10,
    caption=7.5,
    table=8.5,
    footer=8,
    page_margin_mm=18,
    gutter_mm=5,
    baseline_pt=13,
    column_count=12,
    accent="#C45C26",
)
