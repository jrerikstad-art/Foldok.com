"""Diagram style — tokens only.  No one-off styling anywhere in layout/render.

Two rules that the previous style spec got wrong:

*  Colour may not be the only carrier of meaning.  An inspector photocopies the
   manual in mono.  Every conductor class therefore has (colour, dash,
   width) and a printed designation.
*  Stroke widths are specified at the drawing's own scale, then floored at
   render time against the target figure width, so a 0.9 pt wire does not
   vanish when the figure is placed in a 180 pt column.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class Encoding:
    """How one conductor / medium class is drawn."""

    color: str = "#374151"
    dash: tuple[float, ...] | None = None   # dash pattern in units, None = solid
    width: float = 0.9
    stripe: str | None = None        # second colour, drawn as overlay dashes (PE)


@dataclass
class DiagramStyle:
    id: str = "foldok.diagram.v1"

    # geometry ---------------------------------------------------------
    unit: str = "pt"
    grid: float = 8.0
    column_gap: float = 104.0
    row_gap: float = 72.0
    stub: float = 18.0
    min_component_gap: float = 24.0
    padding: float = 16.0
    crossing_gap: float = 4.5
    corner_radius: float = 0.0
    lane_step: float = 8.0
    lane_count: int = 5

    # ink --------------------------------------------------------------
    background: str = "#FFFFFF"
    symbol_stroke: str = "#111827"
    symbol_fill: str = "#FFFFFF"
    equipment_width: float = 1.25
    min_stroke_pt: float = 0.5       # floor after figure scaling

    # type -------------------------------------------------------------
    font: str = "Inter, Helvetica Neue, Arial, sans-serif"   # from DesignSystem
    mono_font: str = "IBM Plex Mono, Menlo, monospace"
    tag_size: float = 9.0
    tag_weight: int = 600
    label_size: float = 8.0
    port_label_size: float = 7.0
    designation_size: float = 7.5
    caption_size: float = 9.0
    legend_size: float = 8.0
    text_color: str = "#111827"
    muted_text_color: str = "#4B5563"

    # encodings --------------------------------------------------------
    encodings: dict[str, Encoding] = field(default_factory=dict)
    default_encoding: Encoding = field(default_factory=Encoding)

    show_legend: bool = True
    legend_position: str = "bottom_left"
    show_port_labels: bool = True

    def __post_init__(self) -> None:
        if not self.encodings:
            self.encodings = default_encodings()

    def encoding(self, designation: str | None, medium: str) -> Encoding:
        if designation and designation in self.encodings:
            return self.encodings[designation]
        if medium in self.encodings:
            return self.encodings[medium]
        return self.default_encoding

    def scale_for(self, content_width: float, target_width_pt: float | None) -> float:
        if not target_width_pt or content_width <= 0:
            return 1.0
        return target_width_pt / content_width

    def floored(self, width: float, scale: float) -> float:
        """Stroke width in drawing units that survives ``scale``."""
        if scale <= 0:
            return width
        return max(width, self.min_stroke_pt / scale)

    def with_overrides(self, tokens: dict[str, Any]) -> "DiagramStyle":
        known = {k: v for k, v in tokens.items() if k in self.__dataclass_fields__}
        return replace(self, **known)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "DiagramStyle":
        enc = {}
        for key, val in (d.get("encodings") or {}).items():
            enc[key] = Encoding(**val) if isinstance(val, dict) else Encoding(color=str(val))
        base = {k: v for k, v in d.items() if k in DiagramStyle.__dataclass_fields__ and k != "encodings"}
        style = DiagramStyle(**base)
        if enc:
            merged = default_encodings()
            merged.update(enc)
            style.encodings = merged
        return style


def default_encodings() -> dict[str, Encoding]:
    """IEC / NEK-flavoured defaults.  Dash carries the meaning in mono."""
    return {
        # electrical
        "L1": Encoding("#8B5A2B", None, 1.0),
        "L2": Encoding("#111827", None, 1.0),
        "L3": Encoding("#6B7280", (2.0, 1.5), 1.0),
        "N": Encoding("#2563EB", (5.0, 2.0), 0.9),
        "PE": Encoding("#16A34A", (4.0, 3.0), 1.0, stripe="#EAB308"),
        "signal": Encoding("#7C3AED", (1.5, 1.5), 0.75),
        "wire": Encoding("#374151", None, 0.9),
        # piping
        "cold": Encoding("#0EA5E9", None, 1.5),
        "hot": Encoding("#DC2626", None, 1.5),
        "circulation": Encoding("#DC2626", (6.0, 3.0), 1.25),
        "drain": Encoding("#78716C", (8.0, 3.0, 2.0, 3.0), 1.75),
        "vent": Encoding("#78716C", (2.0, 3.0), 1.0),
        "process": Encoding("#111827", None, 1.5),
        "pipe": Encoding("#111827", None, 1.5),
        # mechanical
        "shaft": Encoding("#111827", (10.0, 3.0), 1.75),
        "duct": Encoding("#0F766E", (6.0, 4.0), 1.5),
    }


def dasharray(enc: Encoding, scale: float = 1.0) -> str | None:
    if not enc.dash:
        return None
    return " ".join(f"{round(v, 2):g}" for v in enc.dash)
