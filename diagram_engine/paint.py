"""Paint helpers — DiagramStyle tokens → SVG attributes.

Layout code must not invent hex/fonts; call PaintContext instead.
"""
from __future__ import annotations

import html as html_lib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from artifact_engine.diagram_style import DiagramStyle

from artifact_engine.diagram_style import get_diagram_style


def esc(s: str) -> str:
    return html_lib.escape(s or "", quote=True)


class PaintContext:
    def __init__(self, style: "DiagramStyle | None" = None):
        self.style = style or get_diagram_style()

    @property
    def id(self) -> str:
        return self.style.id

    def wire(self, key: str | None) -> tuple[str, str]:
        return self.style.wire_hex(key)

    def pipe(self, media: str | None, *, size_class: str | None = None,
             dn: str | int | None = None) -> tuple[str, float, str]:
        hex_c, label = self.style.pipe_hex(media)
        branch = False
        sc = size_class
        if not sc and dn is not None:
            digits = "".join(ch for ch in str(dn) if ch.isdigit())
            n = int(digits) if digits else 50
            sc = "small" if n <= 25 else ("large" if n >= 100 else "medium")
            branch = sc == "small"
        width = self.style.pipe_stroke_width(sc, branch=branch)
        if dn:
            label = f"{label} · {dn if str(dn).upper().startswith('DN') else f'DN{dn}' if str(dn).isdigit() else dn}"
        return hex_c, width, label

    def shaft(self) -> tuple[str, float, str]:
        return self.style.colors.shaft, self.style.strokes.shaft, "Shaft / drive"

    def wire_width(self, key: str | None = None, *, bus: bool = False) -> float:
        return self.style.wire_stroke_width(key, bus=bus)

    def title_attrs(self) -> str:
        L = self.style.labels
        return (
            f'font-family="{esc(L.font)}" font-size="{L.title_size}" '
            f'font-weight="600" fill="{esc(L.color)}"'
        )

    def subtitle_attrs(self) -> str:
        L = self.style.labels
        return (
            f'font-family="{esc(L.font_mono)}" font-size="{L.subtitle_size}" '
            f'fill="{esc(L.muted_color)}"'
        )

    def tag_attrs(self) -> str:
        L = self.style.labels
        return (
            f'font-family="{esc(L.font)}" font-size="{L.tag_size}" '
            f'font-weight="{L.tag_weight}" fill="{esc(L.color)}"'
        )

    def annotation_attrs(self, *, color: str | None = None) -> str:
        L = self.style.labels
        c = color or L.muted_color
        return (
            f'font-family="{esc(L.font_mono)}" font-size="{L.annotation_size}" '
            f'fill="{esc(c)}"'
        )

    def wrap_svg(self, body: str, *, width: float, height: float, layout: str) -> str:
        C = self.style.canvas
        pad = C.padding
        # Optional frame inset
        frame = (
            f'<rect x="{pad/2:.1f}" y="{pad/2:.1f}" '
            f'width="{width - pad:.1f}" height="{height - pad:.1f}" '
            f'fill="none" stroke="{esc(C.frame_color)}" '
            f'stroke-width="{C.frame_stroke}"/>'
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
            f'viewBox="0 0 {width:.0f} {height:.0f}" data-foldok="domain_diagram" '
            f'data-layout="{esc(layout)}" data-graph="connection" '
            f'data-diagram-style="{esc(self.id)}">\n'
            f'<rect width="100%" height="100%" fill="{esc(C.background)}"/>\n'
            f"{frame}\n{body}\n</svg>"
        )

    def legend_block(
        self,
        items: list[tuple[str, str, float | None]],
        x: float,
        y: float,
        title: str = "Legend",
    ) -> tuple[str, float]:
        if not items:
            return "", 0.0
        Leg = self.style.legend
        L = self.style.labels
        lines = [
            f'<g class="diagram-legend" data-style="{esc(self.id)}" '
            f'transform="translate({x:.1f},{y:.1f})">',
            f'<text x="0" y="0" font-family="{esc(L.font)}" '
            f'font-size="{Leg.title_size}" fill="{esc(L.color)}" '
            f'font-weight="600">{esc(title)}</text>',
        ]
        row = Leg.gap + Leg.title_size
        sw = Leg.swatch
        for i, (hex_c, label, width) in enumerate(items):
            yy = row + i * (Leg.font_size + Leg.gap)
            stroke_w = width or 2.0
            lines.append(
                f'<line x1="0" y1="{yy}" x2="{sw * 2.8:.1f}" y2="{yy}" '
                f'stroke="{esc(hex_c)}" stroke-width="{stroke_w}"/>'
                f'<text x="{sw * 2.8 + 6:.1f}" y="{yy + 3:.1f}" '
                f'font-family="{esc(L.font_mono)}" font-size="{Leg.font_size}" '
                f'fill="{esc(L.color)}">{esc(label)}</text>'
            )
        lines.append("</g>")
        h = row + len(items) * (Leg.font_size + Leg.gap)
        return "\n".join(lines), h


def resolve_style(style: "DiagramStyle | str | None" = None) -> "DiagramStyle":
    if style is None:
        return get_diagram_style()
    if isinstance(style, str):
        return get_diagram_style(style)
    return style


def paint(style: "DiagramStyle | str | None" = None) -> PaintContext:
    return PaintContext(resolve_style(style))
