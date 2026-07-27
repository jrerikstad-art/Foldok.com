"""SVG renderer.

Two things worth knowing before editing this file.

**The SVG is the editor surface.**  Every element carries a stable
``data-target`` matching the pin target strings in overrides.py
(``component:PANEL``, ``connection:w1``, ``portlabel:UT:line``).  The Flutter
canvas hit-tests those ids and turns a drag into a pin.  That is how manual
editing works without a second document format for canvas vs export — the
thing on screen and the thing in the PDF are the same artefact.

**Output must be byte-stable.**  Same graph + same pins + same style = same
bytes.  No clock, no dict ordering, no float noise.  This is what makes golden
tests possible and what stops a re-issued manual from diffing on every page.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from . import symbols as symbol_pack
from .layout import Layout, Placed, Route, TextBox
from .style import DiagramStyle

WEIGHTS = {"thin": 0.72, "equipment": None, "heavy": 1.75}


def _n(v: float) -> str:
    if abs(v - round(v)) < 0.005:
        return str(int(round(v)))
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _attrs(pairs: list[tuple[str, Any]]) -> str:
    return " ".join(f'{k}="{v}"' for k, v in pairs if v is not None and v != "")


@dataclass
class RenderResult:
    svg: str
    width: float                 # intrinsic width in style units
    height: float
    scale: float                 # applied if target_width_pt was given
    legend_keys: list[str]
    warnings: list[str]

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.svg


def render_svg(
    layout: Layout,
    style: DiagramStyle,
    *,
    target_width_pt: float | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    show_handles: bool = False,
) -> RenderResult:
    x0, y0, w, h = layout.bbox

    header_h = 0.0
    if title:
        header_h += style.tag_size * 1.8
    if subtitle:
        header_h += style.label_size * 1.7
    if header_h:
        header_h += 6.0

    legend_keys = [e.key for e in layout.legend]
    legend_h = 0.0
    if style.show_legend and legend_keys:
        legend_h = 10.0 + len(legend_keys) * (style.legend_size + 4.0)

    total_w = w
    total_h = h + header_h + legend_h
    scale = style.scale_for(total_w, target_width_pt)

    body: list[str] = []
    body.append(
        f'<rect x="{_n(x0)}" y="{_n(y0 - header_h)}" width="{_n(total_w)}" '
        f'height="{_n(total_h)}" fill="{style.background}"/>'
    )

    if title or subtitle:
        ty = y0 - header_h + style.tag_size * 1.2
        if title:
            body.append(
                _text(
                    TextBox(x0 + style.padding, ty, title, style.tag_size * 1.15, "title", "start", 700),
                    style,
                )
            )
            ty += style.label_size * 1.7
        if subtitle:
            body.append(
                _text(
                    TextBox(
                        x0 + style.padding, ty, subtitle, style.label_size, "subtitle", "start",
                        400, style.muted_text_color, mono=True,
                    ),
                    style,
                )
            )

    # runs under symbols so symbol fill masks the line ends
    for route in sorted(layout.routes, key=lambda r: r.connection.id):
        body.extend(_route(route, style, scale))

    for placed in sorted(layout.placed, key=lambda p: p.component.id):
        body.append(_component(placed, style, scale))

    for text in layout.texts:
        body.append(_text(text, style))

    if show_handles:
        body.extend(_handles(layout, style))

    if legend_h:
        body.extend(_legend(layout, style, scale, x0, y0 + h, legend_keys))

    view = f"{_n(x0)} {_n(y0 - header_h)} {_n(total_w)} {_n(total_h)}"
    size_attrs = ""
    if target_width_pt:
        size_attrs = f' width="{_n(target_width_pt)}pt" height="{_n(total_h * scale)}pt"'

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}"{size_attrs} '
        f'data-graph="{escape(layout.graph_id)}" data-profile="{escape(layout.profile_id)}" '
        f'data-style="{escape(style.id)}">\n'
        + "\n".join("  " + line for line in body)
        + "\n</svg>\n"
    )
    return RenderResult(
        svg=svg,
        width=round(total_w, 2),
        height=round(total_h, 2),
        scale=round(scale, 4),
        legend_keys=legend_keys,
        warnings=list(layout.warnings),
    )


# ----------------------------------------------------------------------
def _stroke_width(weight: str, style: DiagramStyle, scale: float) -> float:
    base = WEIGHTS.get(weight)
    if base is None:
        base = style.equipment_width
    return round(style.floored(base, scale), 3)


def _component(placed: Placed, style: DiagramStyle, scale: float) -> str:
    sym = symbol_pack.get(placed.symbol_id)
    target = f"component:{placed.component.id}"
    transform = f"translate({_n(placed.x)} {_n(placed.y)})"
    if placed.rotation:
        transform += f" rotate({placed.rotation})"

    inner: list[str] = []
    if sym.fill_body:
        inner.append(
            f'<rect x="{_n(-sym.w / 2)}" y="{_n(-sym.h / 2)}" width="{_n(sym.w)}" '
            f'height="{_n(sym.h)}" fill="{style.symbol_fill}" stroke="none"/>'
        )
    for el in sym.elements:
        inner.append(_primitive(el, style, scale))

    pinned = ",".join(placed.pinned_props)
    return (
        f'<g id="{escape(target)}" data-target="{escape(target)}" '
        f'data-type="{escape(placed.symbol_id)}" data-pinned="{pinned}" '
        f'transform="{transform}" fill="none" stroke="{style.symbol_stroke}" '
        f'stroke-linecap="square" stroke-linejoin="miter">'
        + "".join(inner)
        + "</g>"
    )


def _primitive(el: tuple, style: DiagramStyle, scale: float) -> str:
    kind = el[0]
    if kind == "line":
        _, x1, y1, x2, y2, weight = el
        return (
            f'<line x1="{_n(x1)}" y1="{_n(y1)}" x2="{_n(x2)}" y2="{_n(y2)}" '
            f'stroke-width="{_n(_stroke_width(weight, style, scale))}"/>'
        )
    if kind == "rect":
        _, x, y, w, h, weight = el
        return (
            f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" '
            f'stroke-width="{_n(_stroke_width(weight, style, scale))}"/>'
        )
    if kind == "circle":
        _, cx, cy, r, weight = el
        return (
            f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(r)}" '
            f'stroke-width="{_n(_stroke_width(weight, style, scale))}"/>'
        )
    if kind == "path":
        _, d, weight = el
        return f'<path d="{d}" stroke-width="{_n(_stroke_width(weight, style, scale))}"/>'
    if kind == "poly":
        _, pts, weight, closed = el
        d = "M " + " L ".join(f"{_n(x)} {_n(y)}" for x, y in pts) + (" Z" if closed else "")
        return f'<path d="{d}" stroke-width="{_n(_stroke_width(weight, style, scale))}"/>'
    if kind == "glyph":
        _, x, y, text, size = el
        return (
            f'<text x="{_n(x)}" y="{_n(y)}" font-family="{escape(style.font)}" '
            f'font-size="{_n(size)}" font-weight="600" text-anchor="middle" '
            f'fill="{style.symbol_stroke}" stroke="none">{escape(text)}</text>'
        )
    raise ValueError(f"unknown symbol primitive '{kind}'")


def _route(route: Route, style: DiagramStyle, scale: float) -> list[str]:
    conn = route.connection
    enc = style.encoding(conn.designation, conn.medium)
    width = round(style.floored(enc.width, scale), 3)
    d = _route_path(route, style)
    target = f"connection:{conn.id}"
    dash = " ".join(_n(v) for v in enc.dash) if enc.dash else None

    out: list[str] = []
    base = _attrs(
        [
            ("id", escape(target)),
            ("data-target", escape(target)),
            ("data-medium", conn.medium),
            ("data-designation", conn.designation or ""),
            ("data-pinned", "true" if route.pinned else "false"),
            ("d", d),
            ("fill", "none"),
            ("stroke", enc.color),
            ("stroke-width", _n(width)),
            ("stroke-dasharray", None if enc.stripe else dash),
            ("stroke-linecap", "butt"),
            ("stroke-linejoin", "miter"),
        ]
    )
    out.append(f"<path {base}/>")
    if enc.stripe:
        # two-tone conductor (PE): solid base + dashed overlay, so it reads
        # green/yellow in colour and still prints as a continuous line in mono.
        overlay = _attrs(
            [
                ("d", d),
                ("fill", "none"),
                ("stroke", enc.stripe),
                ("stroke-width", _n(width)),
                ("stroke-dasharray", dash or "4 4"),
                ("stroke-linecap", "butt"),
                ("data-target", escape(target)),
                ("data-role", "stripe"),
            ]
        )
        out.append(f"<path {overlay}/>")
    arrow = _flow_arrow(route, style, enc.color, scale)
    if arrow:
        out.append(arrow)
    return out


def _route_path(route: Route, style: DiagramStyle) -> str:
    pts = route.points
    if not pts:
        return ""
    r = style.crossing_gap / 2.0
    d = [f"M {_n(pts[0][0])} {_n(pts[0][1])}"]
    for idx, (p, q) in enumerate(route.segments()):
        bridges = route.bridges.get(idx, [])
        if not bridges:
            d.append(f"L {_n(q[0])} {_n(q[1])}")
            continue
        dx, dy = q[0] - p[0], q[1] - p[1]
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        ordered = sorted(bridges, key=lambda b: (b[0] - p[0]) * ux + (b[1] - p[1]) * uy)
        for bx, by in ordered:
            d.append(f"L {_n(bx - ux * r)} {_n(by - uy * r)}")
            d.append(f"A {_n(r)} {_n(r)} 0 0 1 {_n(bx + ux * r)} {_n(by + uy * r)}")
        d.append(f"L {_n(q[0])} {_n(q[1])}")
    return " ".join(d)


def _flow_arrow(route: Route, style: DiagramStyle, color: str, scale: float) -> str | None:
    if route.connection.flow == "none":
        return None
    segs = route.segments()
    if not segs:
        return None
    idx = max(range(len(segs)), key=lambda i: math.hypot(
        segs[i][1][0] - segs[i][0][0], segs[i][1][1] - segs[i][0][1]
    ))
    (px, py), (qx, qy) = segs[idx]
    if route.connection.flow == "reverse":
        px, py, qx, qy = qx, qy, px, py
    mx, my = (px + qx) / 2.0, (py + qy) / 2.0
    dx, dy = qx - px, qy - py
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    a = 4.0
    p1 = (mx + ux * a, my + uy * a)
    p2 = (mx - ux * a + -uy * a * 0.7, my - uy * a + ux * a * 0.7)
    p3 = (mx - ux * a - -uy * a * 0.7, my - uy * a - ux * a * 0.7)
    pts = " ".join(f"{_n(x)} {_n(y)}" for x, y in (p1, p2, p3))
    return f'<path d="M {pts} Z" fill="{color}" stroke="none" data-role="flow"/>'


def _text(text: TextBox, style: DiagramStyle) -> str:
    family = style.mono_font if text.mono else style.font
    return _tag_text(
        x=text.x,
        y=text.y,
        content=text.text,
        family=family,
        size=text.size,
        weight=text.weight,
        anchor=text.anchor,
        fill=text.color or style.text_color,
        element_id=text.element_id,
        role=text.role,
    )


def _tag_text(
    *,
    x: float,
    y: float,
    content: str,
    family: str,
    size: float,
    weight: int,
    anchor: str,
    fill: str,
    element_id: str | None = None,
    role: str | None = None,
) -> str:
    attrs = _attrs(
        [
            ("id", escape(element_id) if element_id else None),
            ("data-target", escape(element_id) if element_id else None),
            ("data-role", role),
            ("x", _n(x)),
            ("y", _n(y)),
            ("font-family", escape(family)),
            ("font-size", _n(size)),
            ("font-weight", weight if weight != 400 else None),
            ("text-anchor", anchor if anchor != "start" else None),
            ("fill", fill),
            ("stroke", "none"),
        ]
    )
    return f"<text {attrs}>{escape(content)}</text>"


def _handles(layout: Layout, style: DiagramStyle) -> list[str]:
    """Drag handles for the canvas.  Never emitted into a published figure."""
    out: list[str] = []
    r = max(2.5, style.grid / 3)
    for route in sorted(layout.routes, key=lambda x: x.connection.id):
        for i, (x, y) in enumerate(route.points[1:-1], start=1):
            target = f"waypoint:{route.connection.id}:{i - 1}"
            out.append(
                f'<circle id="{escape(target)}" data-target="{escape(target)}" '
                f'cx="{_n(x)}" cy="{_n(y)}" r="{_n(r)}" fill="#FFFFFF" '
                f'stroke="#2563EB" stroke-width="0.75" data-role="handle"/>'
            )
    for placed in sorted(layout.placed, key=lambda p: p.component.id):
        x, y, w, h = placed.rect()
        target = f"handle:{placed.component.id}"
        out.append(
            f'<rect id="{escape(target)}" data-target="component:{escape(placed.component.id)}" '
            f'x="{_n(x - 2)}" y="{_n(y - 2)}" width="{_n(w + 4)}" height="{_n(h + 4)}" '
            f'fill="none" stroke="#2563EB" stroke-width="0.5" stroke-dasharray="2 2" '
            f'data-role="handle"/>'
        )
    return out


def _legend(
    layout: Layout,
    style: DiagramStyle,
    scale: float,
    x0: float,
    y_bottom: float,
    keys: list[str],
) -> list[str]:
    out: list[str] = []
    x = x0 + style.padding
    y = y_bottom + 10.0
    sample = 22.0
    for key in keys:
        enc = style.encoding(key, key)
        width = round(style.floored(enc.width, scale), 3)
        dash = " ".join(_n(v) for v in enc.dash) if enc.dash else None
        out.append(
            f'<line x1="{_n(x)}" y1="{_n(y)}" x2="{_n(x + sample)}" y2="{_n(y)}" '
            f'stroke="{enc.color}" stroke-width="{_n(width)}"'
            + (f' stroke-dasharray="{dash}"' if dash and not enc.stripe else "")
            + ' data-role="legend"/>'
        )
        if enc.stripe:
            out.append(
                f'<line x1="{_n(x)}" y1="{_n(y)}" x2="{_n(x + sample)}" y2="{_n(y)}" '
                f'stroke="{enc.stripe}" stroke-width="{_n(width)}" '
                f'stroke-dasharray="{dash or "4 4"}" data-role="legend"/>'
            )
        out.append(
            _tag_text(
                x=x + sample + 6,
                y=y + style.legend_size / 3,
                content=key,
                family=style.mono_font,
                size=style.legend_size,
                weight=400,
                anchor="start",
                fill=style.muted_text_color,
                role="legend",
            )
        )
        y += style.legend_size + 4.0
    return out
