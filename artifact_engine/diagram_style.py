"""DiagramStyle — DesignSystem tokens for deterministic 2D engineering SVG.

Content = project graph. Looks = this spec. Placement = LayoutTree / manual positions.
Wires are always engine-routed from ports; freehand paths are never truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("PyYAML required for DiagramStyle") from e

_YAML = Path(__file__).resolve().parent / "diagram_style.yaml"


@dataclass(frozen=True)
class CanvasStyle:
    background: str = "#FFFFFF"
    frame_stroke: float = 0.5
    frame_color: str = "#E5E7EB"
    padding: float = 12.0


@dataclass(frozen=True)
class GridStyle:
    step: float = 8.0
    snap: bool = True
    # Legacy aliases — prefer GapsStyle
    min_component_gap: float = 28.0
    min_label_gap: float = 8.0


@dataclass(frozen=True)
class GapsStyle:
    min_component: float = 28.0
    min_port_clear: float = 12.0
    min_label: float = 8.0
    wire_to_symbol: float = 4.0
    crossing: float = 6.0


@dataclass(frozen=True)
class StrokeStyle:
    equipment: float = 1.25
    wire_bus: float = 1.5
    wire_L: float = 1.1
    wire_N: float = 1.1
    wire_PE: float = 1.1
    wire_default: float = 0.9
    wire_normal: float = 0.9
    pipe_main: float = 1.5
    pipe_branch: float = 1.0
    shaft: float = 1.25
    guide: float = 0.4
    hidden: float = 0.5


@dataclass(frozen=True)
class ColorStyle:
    wire: dict[str, str] = field(default_factory=dict)
    pipe: dict[str, str] = field(default_factory=dict)
    shaft: str = "#111827"
    emphasis: str = "#B91C1C"
    muted: str = "#9CA3AF"
    ink: str = "#111827"
    symbol_fill: str = "#FFFFFF"
    symbol_stroke: str = "#111827"


@dataclass(frozen=True)
class SymbolStyle:
    default_size: float = 28.0
    port_dot: float = 3.0
    alignment: str = "center"
    width: float = 64.0
    height: float = 48.0


@dataclass(frozen=True)
class LabelStyle:
    font: str = "Arial, Helvetica, sans-serif"
    font_mono: str = "'IBM Plex Mono', Consolas, monospace"
    tag_size: float = 9.0
    tag_weight: int = 600
    annotation_size: float = 8.0
    title_size: float = 14.0
    subtitle_size: float = 9.0
    color: str = "#111827"
    muted_color: str = "#6B7280"
    preferred: str = "above"
    position: str = "above"  # compat
    max_width: float = 64.0
    padding: float = 3.0
    hide_if_overlap: bool = False
    leader_when_offset: bool = True
    leader_stroke: float = 0.4


@dataclass(frozen=True)
class PortStyle:
    hotspot_radius: float = 6.0
    snap_radius: float = 10.0
    show_on_hover: bool = True
    show_when_connecting: bool = True
    dot_size: float = 3.0


@dataclass(frozen=True)
class RoutingStyle:
    orthogonal: bool = True
    corner_radius: float = 0.0
    stub_length: float = 12.0
    bus_align: bool = True
    crossing_gap: float = 6.0
    wire_to_symbol_gap: float = 4.0


@dataclass(frozen=True)
class LegendStyle:
    position: str = "bottom_left"
    swatch: float = 10.0
    font_size: float = 8.0
    gap: float = 6.0
    title_size: float = 10.0


@dataclass(frozen=True)
class FigureChromeStyle:
    caption_size: float = 9.0
    caption_color: str = "#374151"
    number_weight: int = 600
    source_size: float = 8.0
    source_color: str = "#6B7280"


@dataclass(frozen=True)
class DiagramStyle:
    """Single visual system for SLD / wiring / piping / mechanical SVG."""

    id: str = "engineering_default"
    label: str = "Engineering default"
    canvas: CanvasStyle = field(default_factory=CanvasStyle)
    grid: GridStyle = field(default_factory=GridStyle)
    gaps: GapsStyle = field(default_factory=GapsStyle)
    strokes: StrokeStyle = field(default_factory=StrokeStyle)
    colors: ColorStyle = field(default_factory=ColorStyle)
    symbols: SymbolStyle = field(default_factory=SymbolStyle)
    labels: LabelStyle = field(default_factory=LabelStyle)
    ports: PortStyle = field(default_factory=PortStyle)
    routing: RoutingStyle = field(default_factory=RoutingStyle)
    legend: LegendStyle = field(default_factory=LegendStyle)
    figure: FigureChromeStyle = field(default_factory=FigureChromeStyle)

    def wire_hex(self, key: str | None) -> tuple[str, str]:
        raw = (key or "").strip()
        wire = self.colors.wire or {}
        if not raw:
            return wire.get("DEFAULT", self.colors.ink), "Conductor"
        upper = raw.upper().replace("+", "_POS").replace("-", "_NEG").replace(" ", "_")
        aliases = {
            "BROWN": "L1", "BLACK": "L2", "GREY": "L3", "GRAY": "L3",
            "BLUE": "N", "GREEN": "PE", "GREEN_YELLOW": "PE", "GY": "PE",
            "YELLOW_GREEN": "PE", "RED": "DC_POS", "L": "L",
            "DC+": "DC_POS", "DC-": "DC_NEG",
        }
        k = aliases.get(upper, upper)
        if k in wire:
            return wire[k], k
        if k.startswith("L") and "L" in wire:
            return wire["L"], k
        if raw.startswith("#") and len(raw) in (4, 7):
            return raw, raw
        return wire.get("DEFAULT", self.colors.ink), raw or "Conductor"

    def wire_stroke_width(self, key: str | None = None, *, bus: bool = False) -> float:
        if bus:
            return self.strokes.wire_bus
        k = (key or "").upper().replace(" ", "_")
        if k in ("PE", "PEN", "GREEN", "GREEN_YELLOW", "GY"):
            return self.strokes.wire_PE
        if k in ("N", "BLUE"):
            return self.strokes.wire_N
        if k.startswith("L") or k in ("BROWN", "BLACK", "GREY", "GRAY"):
            return self.strokes.wire_L
        return self.strokes.wire_default or self.strokes.wire_normal

    def pipe_hex(self, media: str | None) -> tuple[str, str]:
        key = str(media or "water").lower().replace(" ", "_")
        aliases = {"h2o": "water", "process_water": "water", "compressed_air": "air"}
        key = aliases.get(key, key)
        pipe = self.colors.pipe or {}
        if key in pipe:
            return pipe[key], key.replace("_", " ").title()
        return pipe.get("DEFAULT", self.colors.ink), key

    def pipe_stroke_width(self, size_class: str | None = None, *, branch: bool = False) -> float:
        if branch or size_class == "small":
            return self.strokes.pipe_branch
        return self.strokes.pipe_main

    def label_preferred(self) -> str:
        pref = (self.labels.preferred or self.labels.position or "above").lower()
        if pref == "auto":
            return "above"
        return pref


def _section(cls, data: dict | None, **defaults):
    data = data or {}
    fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    kwargs = {k: v for k, v in {**defaults, **data}.items() if k in fields}
    return cls(**kwargs)


def _from_mapping(data: dict) -> DiagramStyle:
    colors_raw = data.get("colors") or {}
    labels_raw = dict(data.get("labels") or {})
    if "preferred" not in labels_raw and labels_raw.get("position"):
        labels_raw["preferred"] = labels_raw["position"]
    gaps_raw = dict(data.get("gaps") or {})
    grid_raw = dict(data.get("grid") or {})
    if "min_component" not in gaps_raw and "min_component_gap" in grid_raw:
        gaps_raw["min_component"] = grid_raw["min_component_gap"]
    if "min_label" not in gaps_raw and "min_label_gap" in grid_raw:
        gaps_raw["min_label"] = grid_raw["min_label_gap"]
    strokes_raw = dict(data.get("strokes") or {})
    if "wire_default" not in strokes_raw and "wire_normal" in strokes_raw:
        strokes_raw["wire_default"] = strokes_raw["wire_normal"]
    routing_raw = dict(data.get("routing") or {})
    gaps = _section(GapsStyle, gaps_raw)
    grid = _section(
        GridStyle,
        grid_raw,
        min_component_gap=gaps.min_component,
        min_label_gap=gaps.min_label,
    )
    return DiagramStyle(
        id=data.get("id") or "engineering_default",
        label=data.get("label") or "Engineering default",
        canvas=_section(CanvasStyle, data.get("canvas")),
        grid=grid,
        gaps=gaps,
        strokes=_section(StrokeStyle, strokes_raw),
        colors=ColorStyle(
            wire=dict(colors_raw.get("wire") or {}),
            pipe=dict(colors_raw.get("pipe") or {}),
            shaft=colors_raw.get("shaft", "#111827"),
            emphasis=colors_raw.get("emphasis", "#B91C1C"),
            muted=colors_raw.get("muted", "#9CA3AF"),
            ink=colors_raw.get("ink", "#111827"),
            symbol_fill=colors_raw.get("symbol_fill", "#FFFFFF"),
            symbol_stroke=colors_raw.get("symbol_stroke", "#111827"),
        ),
        symbols=_section(SymbolStyle, data.get("symbols")),
        labels=_section(LabelStyle, labels_raw),
        ports=_section(PortStyle, data.get("ports")),
        routing=_section(RoutingStyle, routing_raw),
        legend=_section(LegendStyle, data.get("legend")),
        figure=_section(FigureChromeStyle, data.get("figure")),
    )


@lru_cache(maxsize=8)
def load_diagram_style(style_id: str = "engineering_default") -> DiagramStyle:
    if not _YAML.exists():
        return DiagramStyle(id=style_id)
    raw = yaml.safe_load(_YAML.read_text(encoding="utf-8")) or {}
    style = _from_mapping(raw)
    if style_id and style_id != style.id and style_id != "engineering_default":
        return replace(style, id=style_id)
    return style


def get_diagram_style(style_id: str | None = None) -> DiagramStyle:
    return load_diagram_style(style_id or "engineering_default")


def clear_diagram_style_cache() -> None:
    load_diagram_style.cache_clear()


THEME_DIAGRAM_STYLE = {
    "engineering": "engineering_default",
    "datasheet": "engineering_default",
    "manual": "engineering_default",
    "industrial_report": "engineering_default",
    "akva": "engineering_default",
}


def diagram_style_for_theme(theme_name: str | None) -> DiagramStyle:
    sid = THEME_DIAGRAM_STYLE.get((theme_name or "engineering").lower(), "engineering_default")
    return get_diagram_style(sid)
