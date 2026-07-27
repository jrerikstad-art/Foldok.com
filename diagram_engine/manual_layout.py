"""Manual layout SVG — user positions from graph; engine routes edges only.

Used by the canvas editor. Profiles still pick domain paint defaults;
component.position / rotation are authoritative when present.
"""
from __future__ import annotations

from typing import Any

from .graph import (
    SYM_H,
    SYM_W,
    find_port,
    flow_arrow_marker_defs,
    legend_block,
    normalize_graph,
    ortho_path_with_stubs,
    place_lr_chain,
    port_point,
    resolve_pipe_style,
    resolve_shaft_style,
    symbol_inner,
    topo_order,
    wrap_svg,
)
from .labels import label_svg, place_component_label
from .paint import paint as get_paint


def ensure_positions(graph: dict, *, profile: str = "piping", style: Any = None) -> dict:
    """Fill missing component.position via chain layout (does not move set ones)."""
    g = normalize_graph(graph, default_type=profile)
    comps = [c for c in (g.get("components") or []) if isinstance(c, dict) and c.get("id")]
    missing = [c for c in comps if not (c.get("position") and "x" in (c.get("position") or {}))]
    if not missing:
        return g
    p = get_paint(style)
    gap = float(p.style.gaps.min_component)
    step_x = max(96.0, SYM_W + gap)
    ordered = topo_order(comps, g.get("connections") or [])
    placed = place_lr_chain(ordered, origin_x=100, origin_y=140, step_x=step_x)
    if profile in ("single_line", "sld", "power"):
        step_y = max(72.0, SYM_H + gap)
        placed = {
            cid: (180.0, 80.0 + i * step_y) for i, cid in enumerate(ordered)
        }
    elif profile in ("wiring",):
        # Panel/sources left, loads right — denser vertical with style gap
        left_ids = []
        right_ids = []
        for cid in ordered:
            c = next((x for x in comps if x["id"] == cid), None)
            t = ((c or {}).get("type") or "").lower()
            if t in ("terminal_strip", "terminal", "busbar", "distribution_board"):
                left_ids.append(cid)
            else:
                right_ids.append(cid)
        if not left_ids and ordered:
            left_ids = [ordered[0]]
            right_ids = ordered[1:]
        step_y = max(56.0, SYM_H + gap * 0.6)
        placed = {}
        for i, cid in enumerate(left_ids):
            placed[cid] = (128.0, 100.0 + i * (step_y + 24))
        for i, cid in enumerate(right_ids):
            placed[cid] = (400.0 + (i % 2) * 100, 100.0 + i * step_y)
    for c in comps:
        if c.get("position") and "x" in c["position"]:
            continue
        xy = placed.get(c["id"])
        if xy:
            c["position"] = {"x": xy[0], "y": xy[1]}
    return g


def auto_spread_positions(graph: dict, *, style: Any = None, profile: str = "wiring") -> dict:
    """Nudge overlapping components along the grid; preserve L→R signal flow.

    Does not change topology — only position fields.
    """
    p = get_paint(style)
    g = ensure_positions(graph, profile=profile, style=p.style)
    comps = [c for c in (g.get("components") or []) if isinstance(c, dict) and c.get("id")]
    if not comps:
        return g
    min_gap = float(p.style.gaps.min_component)
    step = float(p.style.grid.step) if p.style.grid.snap else 1.0
    # Sort by x then y (left-to-right flow)
    comps_sorted = sorted(
        comps,
        key=lambda c: (
            float((c.get("position") or {}).get("x", 0)),
            float((c.get("position") or {}).get("y", 0)),
        ),
    )
    placed: list[tuple[str, float, float]] = []
    for c in comps_sorted:
        pos = c.get("position") or {}
        x = float(pos.get("x", 0))
        y = float(pos.get("y", 0))
        for _ in range(40):
            hit = False
            for _, px, py in placed:
                if abs(x - px) < SYM_W + min_gap and abs(y - py) < SYM_H + min_gap:
                    # Push down-right along grid
                    y += step * max(1, int((SYM_H + min_gap) / step))
                    hit = True
                    break
            if not hit:
                break
        if step > 0:
            x = round(x / step) * step
            y = round(y / step) * step
        c["position"] = {"x": x, "y": y}
        placed.append((c["id"], x, y))
    return g


def render_manual_diagram(
    spec: dict,
    *,
    profile: str | None = None,
    title: str | None = None,
    style: Any = None,
) -> str:
    """Render using component.position; orthogonal edges from ports."""
    p = get_paint(style)
    prof = (profile or (spec or {}).get("type") or "piping").lower().replace("-", "_")
    if prof == "sld":
        prof = "single_line"
    g = ensure_positions(spec, profile=prof, style=p.style)
    ttl = title or g.get("title") or "Diagram"
    comps = [c for c in (g.get("components") or []) if isinstance(c, dict) and c.get("id")]
    edges = list(g.get("connections") or [])
    by_id = {c["id"]: c for c in comps}

    positions: dict[str, tuple[float, float]] = {}
    for c in comps:
        pos = c.get("position") or {}
        positions[c["id"]] = (float(pos.get("x", 100)), float(pos.get("y", 100)))

    margin = float(p.style.canvas.padding) * 3
    max_x = max((xy[0] for xy in positions.values()), default=200) + 120
    max_y = max((xy[1] for xy in positions.values()), default=200) + 100

    legend_map: dict[str, tuple[str, str, float | None]] = {}
    for e in edges:
        medium = (e.get("medium") or "pipe").lower()
        attrs = e.get("attributes") or {}
        if medium == "wire":
            hex_c, lab = p.wire(attrs.get("color"))
            legend_map.setdefault(
                f"w:{lab}", (hex_c, f"Wire · {lab}", p.wire_width(attrs.get("color"))),
            )
        elif medium in ("shaft", "belt"):
            hex_c, sw, lab = p.shaft()
            legend_map.setdefault("shaft", (hex_c, lab, sw))
        else:
            hex_c, w, lab = resolve_pipe_style(attrs, p.style)
            legend_map.setdefault(f"p:{lab}", (hex_c, lab, w))

    legend_svg, legend_h = legend_block(
        list(legend_map.values()), max_x + 16, margin + 20, "Legend", style=p.style,
    )
    width = max(640.0, max_x + 200)
    height = max(max_y + 40, margin + 20 + legend_h + 48)

    stub = float(p.style.routing.stub_length)
    bus = bool(p.style.routing.bus_align)
    grid = float(p.style.grid.step)

    parts = [
        flow_arrow_marker_defs(p.style),
        f'<text x="{margin}" y="28" {p.title_attrs()}>{_esc(ttl)}</text>',
        f'<text x="{margin}" y="44" {p.subtitle_attrs()}>'
        f'{_esc(prof)} · manual layout · engine routes</text>',
    ]

    for i, e in enumerate(edges):
        fr, to = e.get("from"), e.get("to")
        if not fr or not to:
            continue
        c0, c1 = by_id.get(fr["component_id"]), by_id.get(to["component_id"])
        if not c0 or not c1:
            continue
        pos0, pos1 = positions.get(c0["id"]), positions.get(c1["id"])
        if not pos0 or not pos1:
            continue
        rot0 = int(c0.get("rotation") or 0)
        rot1 = int(c1.get("rotation") or 0)
        port0 = find_port(c0, fr["port_id"])
        port1 = find_port(c1, to["port_id"])
        x0, y0 = _rotated_port(pos0[0], pos0[1], port0, rot0)
        x1, y1 = _rotated_port(pos1[0], pos1[1], port1, rot1)
        medium = (e.get("medium") or "pipe").lower()
        attrs = e.get("attributes") or {}
        if medium == "wire":
            hex_c, _ = p.wire(attrs.get("color"))
            sw, dash = p.wire_width(attrs.get("color")), ""
        elif medium in ("shaft", "belt"):
            hex_c, sw, _ = resolve_shaft_style(attrs, p.style)
            dash = ' stroke-dasharray="5 3"'
        else:
            hex_c, sw, _ = resolve_pipe_style(attrs, p.style)
            dash = ""
        side0 = _rotated_side(port0.get("side"), rot0)
        side1 = _rotated_side(port1.get("side"), rot1)
        path = ortho_path_with_stubs(
            x0, y0, x1, y1,
            side0=side0, side1=side1, stub=stub,
            bus_align=bus, grid_step=grid,
        )
        flow = (attrs.get("flow_direction") or "").lower()
        marker = ' marker-end="url(#flowArrow)"' if flow == "forward" else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="{_esc(hex_c)}" stroke-width="{sw}"'
            f'{dash}{marker} data-connection="{_esc(e.get("id") or f"c{i}")}" '
            f'data-medium="{_esc(medium)}"/>'
        )
        des = attrs.get("designation") or ""
        if des:
            parts.append(
                f'<text x="{(x0 + x1) / 2:.1f}" y="{(y0 + y1) / 2 - 6:.1f}" '
                f'text-anchor="middle" {p.annotation_attrs()}>{_esc(str(des))}</text>'
            )

    occupied = []
    symbol_centers = list(positions.values())
    for cid, (cx, cy) in positions.items():
        c = by_id[cid]
        sym = c.get("symbol") or c.get("type") or "junction"
        tag = c.get("tag") or c.get("label") or cid
        rot = int(c.get("rotation") or 0) % 360
        transform = f"translate({cx - SYM_W/2:.1f},{cy - SYM_H/2:.1f})"
        if rot:
            transform = (
                f"translate({cx:.1f},{cy:.1f}) rotate({rot}) "
                f"translate({-SYM_W/2:.1f},{-SYM_H/2:.1f})"
            )
        parts.append(
            f'<g class="component" data-component="{_esc(cid)}" data-symbol="{_esc(sym)}" '
            f'transform="{transform}">{symbol_inner(sym)}</g>'
        )
        box = place_component_label(
            str(tag), cx, cy, p.style,
            occupied=occupied, symbol_centers=symbol_centers,
        )
        occupied.append(box)
        parts.append(label_svg(str(tag), box, p.style, symbol_xy=(cx, cy), paint_attrs=p.tag_attrs()))

    parts.append(legend_svg)
    return wrap_svg(
        "\n".join(parts), width=width, height=height, layout=f"manual_{prof}", style=p.style,
    )


def _rotated_side(side: str | None, rotation: int) -> str:
    s = (side or "right").lower()
    cycle = ["top", "right", "bottom", "left"]
    if s not in cycle:
        return s
    rot = rotation % 360
    if not rot:
        return s
    return cycle[(cycle.index(s) + rot // 90) % 4]


def _rotated_port(cx: float, cy: float, port: dict, rotation: int) -> tuple[float, float]:
    """Port in world space; rotation in 90° steps remaps side."""
    side = _rotated_side(port.get("side"), rotation)
    port2 = dict(port)
    port2["side"] = side
    port2["order"] = int(port.get("order") or 1)
    return port_point(cx, cy, port2)


def _esc(s: str) -> str:
    from .graph import esc
    return esc(s)
