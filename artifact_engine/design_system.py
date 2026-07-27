"""Shared visual language for every engine — print-first, points only."""
from __future__ import annotations

from dataclasses import dataclass

from artifact_engine.model.theme import Theme

MM_TO_PT = 2.834645339
A4_WIDTH = 595.28
A4_HEIGHT = 841.89


@dataclass(frozen=True)
class DesignSystem:
    """
    Single source of visual truth.
    All measurements in points (print-first).
    """

    name: str = "engineering"

    # Colors — black/white first; accent only for status
    primary: str = "#111827"
    secondary: str = "#4B5563"
    text: str = "#111827"
    muted: str = "#4B5563"
    border: str = "#E5E7EB"
    background: str = "#FFFFFF"
    surface: str = "#FFFFFF"
    page_chrome: str = "#F3F4F6"
    accent: str = "#F5C400"
    danger: str = "#B91C1C"
    warning: str = "#D97706"
    positive: str = "#047857"

    # Typography (pt)
    font_sans: str = "Arial, Helvetica, sans-serif"
    font_mono: str = "'IBM Plex Mono', Consolas, monospace"
    h1: float = 26.0
    h2: float = 14.5
    h3: float = 11.5
    body: float = 9.75
    caption: float = 8.25
    table: float = 8.5
    footer: float = 8.0

    # Grid & spacing (pt) — print-first scale
    page_width: float = A4_WIDTH
    page_height: float = A4_HEIGHT
    margin: float = 45.35  # ~16 mm
    gutter: float = 17.0   # ~6 mm
    columns: int = 12
    baseline: float = 12.0

    space_xs: float = 4.0
    space_sm: float = 8.0
    space_md: float = 12.0
    space_lg: float = 20.0
    space_xl: float = 32.0
    space_2xl: float = 48.0
    space_section: float = 56.0

    # Card / surface tokens (prefer border over shadow for print)
    radius_card: float = 6.0
    radius_button: float = 3.0
    card_padding: float = 16.0
    card_border_width: float = 0.5
    card_border_color: str = "#E5E7EB"
    card_background: str = "#FFFFFF"

    # Rating tokens
    rating_filled: str = "#1F2937"
    rating_empty: str = "#D1D5DB"
    rating_size: float = 11.0

    # Diagram style id (DesignSystem → DiagramStyle bridge)
    diagram_style_id: str = "engineering_default"

    def diagram_style(self):
        """Resolved DiagramStyle tokens for DiagramEngine SVG paint."""
        from artifact_engine.diagram_style import get_diagram_style
        return get_diagram_style(self.diagram_style_id)

    def column_width(self) -> float:
        content = self.page_width - 2 * self.margin
        if self.columns <= 1:
            return content
        return (content - (self.columns - 1) * self.gutter) / self.columns

    def span(self, n: int) -> float:
        n = max(1, n)
        return n * self.column_width() + (n - 1) * self.gutter

    def to_theme(self) -> Theme:
        """Bridge to legacy Theme for CSS / Grid.from_theme callers."""
        return Theme(
            name=self.name,
            primary_color=self.primary,
            secondary_color=self.secondary,
            text_color=self.text,
            muted_color=self.muted,
            border_color=self.border,
            background=self.background,
            page_chrome=self.page_chrome,
            font_sans=self.font_sans,
            font_mono=self.font_mono,
            h1=self.h1,
            h2=self.h2,
            h3=self.h3,
            body=self.body,
            caption=self.caption,
            table=self.table,
            footer=self.footer,
            page_margin_mm=self.margin / MM_TO_PT,
            gutter_mm=self.gutter / MM_TO_PT,
            baseline_pt=self.baseline,
            column_count=self.columns,
            accent=self.accent,
        )

    @classmethod
    def from_theme(cls, theme: Theme, page_size: str = "A4") -> "DesignSystem":
        from artifact_engine.layout.grid import PAGE_SIZES

        w, h = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
        b = float(theme.baseline_pt)
        return cls(
            name=theme.name,
            primary=theme.primary_color,
            secondary=theme.secondary_color,
            text=theme.text_color,
            muted=theme.muted_color,
            border=theme.border_color,
            background=theme.background,
            surface="#FFFFFF",
            page_chrome=theme.page_chrome,
            accent=theme.accent,
            font_sans=theme.font_sans,
            font_mono=theme.font_mono,
            h1=float(theme.h1),
            h2=float(theme.h2),
            h3=float(theme.h3),
            body=float(theme.body),
            caption=float(theme.caption),
            table=float(theme.table),
            footer=float(theme.footer),
            page_width=w,
            page_height=h,
            margin=float(theme.page_margin_mm) * MM_TO_PT,
            gutter=float(theme.gutter_mm) * MM_TO_PT,
            columns=int(theme.column_count),
            baseline=b,
            space_xs=4.0,
            space_sm=8.0,
            space_md=12.0,
            space_lg=20.0,
            space_xl=32.0,
            space_2xl=48.0,
            space_section=56.0,
            diagram_style_id=__import__(
                "artifact_engine.diagram_style", fromlist=["THEME_DIAGRAM_STYLE"]
            ).THEME_DIAGRAM_STYLE.get(theme.name, "engineering_default"),
        )


def _datasheet_ds() -> DesignSystem:
    from artifact_engine.themes.datasheet import DATASHEET
    return DesignSystem.from_theme(DATASHEET)


def _engineering_ds() -> DesignSystem:
    from artifact_engine.themes.engineering import ENGINEERING
    return DesignSystem.from_theme(ENGINEERING)


def _manual_ds() -> DesignSystem:
    from artifact_engine.themes.manual import MANUAL
    return DesignSystem.from_theme(MANUAL)


def _industrial_report_ds() -> DesignSystem:
    """Corporate print profile — matrices, stakeholder cards, comparisons."""
    return DesignSystem(
        name="industrial_report",
        primary="#111827",
        secondary="#4B5563",
        text="#111827",
        muted="#4B5563",
        border="#E5E7EB",
        background="#FFFFFF",
        surface="#FFFFFF",
        page_chrome="#F3F4F6",
        h1=22.0,
        h2=14.5,
        h3=11.5,
        body=9.75,
        caption=8.25,
        table=8.5,
        footer=8.0,
        baseline=12.0,
        space_xs=4.0,
        space_sm=8.0,
        space_md=12.0,
        space_lg=20.0,
        space_xl=32.0,
        space_2xl=48.0,
        space_section=56.0,
        radius_card=6.0,
        card_padding=16.0,
        card_border_width=0.5,
        card_border_color="#E5E7EB",
        card_background="#FFFFFF",
        rating_filled="#1F2937",
        rating_empty="#D1D5DB",
        rating_size=11.0,
    )


ENGINEERING_DS = _engineering_ds()
DATASHEET_DS = _datasheet_ds()
MANUAL_DS = _manual_ds()
INDUSTRIAL_REPORT_DS = _industrial_report_ds()

DESIGN_SYSTEMS = {
    "engineering": ENGINEERING_DS,
    "datasheet": DATASHEET_DS,
    "manual": MANUAL_DS,
    "akva": MANUAL_DS,  # alias only — no customer brand tokens
    "industrial_report": INDUSTRIAL_REPORT_DS,
}


def get_design_system(name: str = "engineering") -> DesignSystem:
    return DESIGN_SYSTEMS.get(name, ENGINEERING_DS)
