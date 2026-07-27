"""Mechanical arrangement SVG — motor / coupling / gearbox / driven equipment.

Same connection graph; medium=shaft (and optional belt). Print-clear tags.
"""
from __future__ import annotations

from .graph import (
    SYM_H,
    SYM_W,
    esc,
    find_port,
    legend_block,
    normalize_graph,
    ortho_path,
    place_lr_chain,
    port_point,
    resolve_pipe_style,
    resolve_shaft_style,
    symbol_inner,
    topo_order,
    wrap_svg,
)

MECHANICAL_FIXTURE: dict = {
    "id": "mech_drive_sample",
    "type": "mechanical",
    "domain": "mechanical",
    "title": "Drive train — mechanical arrangement",
    "components": [
        {"id": "SKID", "type": "skid_frame", "label": "Skid", "tag": "SK-01",
         "position": {"x": 280, "y": 160}},
        {"id": "M1", "type": "motor_ac", "label": "Motor 2.2 kW", "tag": "M-101"},
        {"id": "C1", "type": "coupling", "label": "Coupling", "tag": "C-101"},
        {"id": "G1", "type": "gearbox", "label": "Gearbox", "tag": "G-101"},
        {"id": "P1", "type": "centrifugal_pump", "label": "Pump", "tag": "P-101",
         "domain": "piping"},
        {"id": "B1", "type": "bearing_block", "label": "Bearing", "tag": "B-101"},
    ],
    "connections": [
        {"from": "M1.shaft", "to": "C1.in", "medium": "shaft", "designation": "drive"},
        {"from": "C1.out", "to": "G1.input_shaft", "medium": "shaft"},
        {"from": "G1.output_shaft", "to": "P1.drive", "medium": "shaft", "designation": "to pump"},
        {"from": "G1.output_shaft", "to": "B1.shaft_l", "medium": "shaft"},
    ],
}

HYBRID_FIXTURE: dict = {
    "id": "hybrid_skid_sample",
    "type": "hybrid",
    "domain": "hybrid",
    "title": "Pump skid — hybrid overview",
    "components": [
        {"id": "SKID", "type": "skid_frame", "label": "Skid frame", "tag": "SK-01"},
        {"id": "T1", "type": "tank_vertical", "label": "Tank", "tag": "T-101", "domain": "piping"},
        {"id": "P1", "type": "centrifugal_pump", "label": "Pump", "tag": "P-101", "domain": "piping"},
        {"id": "M1", "type": "motor_ac", "label": "Motor", "tag": "M-101", "domain": "mechanical"},
        {"id": "C1", "type": "coupling", "label": "Coupling", "tag": "C-101", "domain": "mechanical"},
        {"id": "V1", "type": "valve_ball", "label": "Discharge valve", "tag": "V-12", "domain": "piping"},
        {"id": "Q1", "type": "mcb", "label": "Motor MCB", "tag": "F3", "domain": "electrical"},
    ],
    "connections": [
        {"from": "T1.outlet", "to": "P1.suction", "medium": "pipe", "media": "water", "dn": 80, "flow_direction": "forward"},
        {"from": "P1.discharge", "to": "V1.in", "medium": "pipe", "media": "water", "dn": 50, "flow_direction": "forward"},
        {"from": "M1.shaft", "to": "C1.in", "medium": "shaft"},
        {"from": "C1.out", "to": "P1.drive", "medium": "shaft"},
        {"from": "Q1.load", "to": "M1.electrical", "medium": "wire", "color": "L1", "designation": "power"},
    ],
}


def render_mechanical_diagram(
    spec: dict,
    *,
    mode: str | None = None,
    title: str | None = None,
    style=None,
) -> str:
    from .paint import paint as get_paint
    p = get_paint(style)
    g = normalize_graph(
        spec, default_type="mechanical", default_domain="mechanical", default_medium="shaft",
    )
    layout = (mode or g.get("type") or "mechanical").lower()
    ttl = title or g.get("title") or "Mechanical arrangement"
    return _render_mech(g, ttl, layout, p)


def render_hybrid_diagram(
    spec: dict,
    *,
    title: str | None = None,
    style=None,
) -> str:
    from .paint import paint as get_paint
    p = get_paint(style)
    g = normalize_graph(spec, default_type="hybrid", default_domain="hybrid", default_medium="pipe")
    ttl = title or g.get("title") or "Hybrid skid overview"
    return _render_hybrid(g, ttl, p)


def _render_mech(g: dict, title: str, layout: str, p) -> str:
    comps = [c for c in (g.get("components") or []) if isinstance(c, dict) and c.get("id")]
    edges = [e for e in (g.get("connections") or []) if (e.get("medium") or "shaft") in ("shaft", "belt")]
    # If no shaft edges filtered empty wrongly, use all
    if not edges:
        edges = list(g.get("connections") or [])
    by_id = {c["id"]: c for c in comps}

    drive = [c for c in comps if (c.get("type") or "") != "skid_frame"]
    ordered = topo_order(drive, edges)
    positions = place_lr_chain(ordered, origin_x=100, origin_y=140, step_x=100)

    # Skid as background outline under the chain
    skids = [c for c in comps if (c.get("type") or "") == "skid_frame"]
    margin = 48.0
    max_x = max((p[0] for p in positions.values()), default=200) + 80
    max_y = max((p[1] for p in positions.values()), default=140) + 100
    width = max(560.0, max_x + 160)
    height = max_y + 40

    parts = [
        f'<text x="{margin}" y="28" {p.title_attrs()}>{esc(title)}</text>',
        f'<text x="{margin}" y="44" {p.subtitle_attrs()}>mechanical · shaft train</text>',
    ]

    if positions:
        xs = [p[0] for p in positions.values()]
        ys = [p[1] for p in positions.values()]
        pad = 50
        rx, ry = min(xs) - pad, min(ys) - pad
        rw, rh = (max(xs) - min(xs)) + 2 * pad, (max(ys) - min(ys)) + 2 * pad + 20
        parts.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
            f'fill="none" stroke="#C5C8CE" stroke-width="1.5" stroke-dasharray="6 4" '
            f'rx="4" data-skid="outline"/>'
        )
        if skids:
            tag = skids[0].get("tag") or skids[0].get("label") or "Skid"
            parts.append(
                f'<text x="{rx + 8:.1f}" y="{ry + 16:.1f}" '
                f'font-family="IBM Plex Mono,monospace" font-size="10" '
                f'fill="#5C6370">{esc(str(tag))}</text>'
            )

    hex_s, sw_s, lab_s = p.shaft()
    legend_items = [(hex_s, lab_s, sw_s)]
    legend_svg, legend_h = legend_block(legend_items, max_x + 10, margin + 20, "Drives", style=p.style)
    height = max(height, margin + 20 + legend_h + 40)
    width = max(width, max_x + 180)

    for i, e in enumerate(edges):
        fr, to = e.get("from"), e.get("to")
        if not fr or not to:
            continue
        c0, c1 = by_id.get(fr["component_id"]), by_id.get(to["component_id"])
        if not c0 or not c1:
            continue
        p0, p1 = positions.get(c0["id"]), positions.get(c1["id"])
        if not p0 or not p1:
            continue
        x0, y0 = port_point(p0[0], p0[1], find_port(c0, fr["port_id"]))
        x1, y1 = port_point(p1[0], p1[1], find_port(c1, to["port_id"]))
        attrs = e.get("attributes") or {}
        hex_c, sw, _ = resolve_shaft_style(attrs, p.style)
        path = ortho_path(x0, y0, x1, y1)
        dash = ' stroke-dasharray="5 3"' if (e.get("medium") or "") == "shaft" else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="{esc(hex_c)}" stroke-width="{sw}"'
            f'{dash} data-connection="{esc(e.get("id") or f"c{i}")}" data-medium="shaft"/>'
        )
        des = attrs.get("designation") or ""
        if des:
            parts.append(
                f'<text x="{(x0 + x1) / 2:.1f}" y="{(y0 + y1) / 2 - 6:.1f}" '
                f'text-anchor="middle" {p.annotation_attrs()}>{esc(str(des))}</text>'
            )

    for cid, (cx, cy) in positions.items():
        c = by_id[cid]
        sym = c.get("symbol") or c.get("type") or "coupling"
        tag = c.get("tag") or c.get("label") or cid
        parts.append(
            f'<g class="component" data-component="{esc(cid)}" data-symbol="{esc(sym)}" '
            f'transform="translate({cx - SYM_W/2:.1f},{cy - SYM_H/2:.1f})">'
            f"{symbol_inner(sym)}</g>"
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + SYM_H/2 + 14:.1f}" text-anchor="middle" '
            f'{p.tag_attrs()}>{esc(str(tag))}</text>'
        )

    parts.append(legend_svg)
    return wrap_svg("\n".join(parts), width=width, height=height, layout=layout, style=p.style)


def _render_hybrid(g: dict, title: str, p) -> str:
    """Equipment + main pipe/shaft/wire connections on one sheet."""
    comps = [c for c in (g.get("components") or []) if isinstance(c, dict) and c.get("id")]
    edges = list(g.get("connections") or [])
    by_id = {c["id"]: c for c in comps}

    lanes = {"electrical": 90.0, "mechanical": 180.0, "piping": 280.0, "hybrid": 180.0}
    counters = {"electrical": 0, "mechanical": 0, "piping": 0, "hybrid": 0}
    positions: dict[str, tuple[float, float]] = {}
    for c in comps:
        if (c.get("type") or "") == "skid_frame":
            continue
        dom = (c.get("domain") or "hybrid").lower()
        if dom not in counters:
            dom = "hybrid"
        i = counters[dom]
        counters[dom] += 1
        y = lanes.get(dom, 180.0)
        positions[c["id"]] = (90 + i * 120, y)

    margin = float(p.style.canvas.padding) * 4
    max_x = max((pt[0] for pt in positions.values()), default=200) + 90
    max_y = max((pt[1] for pt in positions.values()), default=280) + 80

    legend_map: dict[str, tuple[str, str, float | None]] = {}
    for e in edges:
        medium = (e.get("medium") or "pipe").lower()
        attrs = e.get("attributes") or {}
        if medium == "wire":
            hex_c, lab = p.wire(attrs.get("color"))
            legend_map.setdefault(f"w:{lab}", (hex_c, f"Wire · {lab}", p.wire_width()))
        elif medium == "shaft":
            hex_c, sw, lab = p.shaft()
            legend_map.setdefault("shaft", (hex_c, lab, sw))
        else:
            hex_c, w, lab = resolve_pipe_style(attrs, p.style)
            legend_map.setdefault(f"p:{lab}", (hex_c, lab, w))

    legend_svg, legend_h = legend_block(
        list(legend_map.values()), max_x + 16, margin + 20, "Connections", style=p.style,
    )
    width = max(720.0, max_x + 220)
    height = max(max_y + 40, margin + 20 + legend_h + 40)
    frame_c = p.style.canvas.frame_color

    parts = [
        f'<text x="{margin}" y="28" {p.title_attrs()}>{esc(title)}</text>',
        f'<text x="{margin}" y="44" {p.subtitle_attrs()}>'
        f'hybrid · electrical + mechanical + piping</text>',
    ]
    for lab, y in (("Electrical", 90), ("Mechanical", 180), ("Piping", 280)):
        parts.append(
            f'<text x="16" y="{y + 4}" {p.annotation_attrs()} '
            f'transform="rotate(-90 16 {y})">{lab}</text>'
        )

    if positions:
        xs = [pt[0] for pt in positions.values()]
        ys = [pt[1] for pt in positions.values()]
        pad = 40
        parts.append(
            f'<rect x="{min(xs)-pad:.1f}" y="{min(ys)-pad:.1f}" '
            f'width="{(max(xs)-min(xs))+2*pad:.1f}" height="{(max(ys)-min(ys))+2*pad:.1f}" '
            f'fill="none" stroke="{esc(frame_c)}" stroke-width="1.5" '
            f'stroke-dasharray="6 4" rx="4"/>'
        )

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
        x0, y0 = port_point(pos0[0], pos0[1], find_port(c0, fr["port_id"]))
        x1, y1 = port_point(pos1[0], pos1[1], find_port(c1, to["port_id"]))
        medium = (e.get("medium") or "pipe").lower()
        attrs = e.get("attributes") or {}
        if medium == "wire":
            hex_c, _ = p.wire(attrs.get("color"))
            sw, dash = p.wire_width(), ""
        elif medium == "shaft":
            hex_c, sw, _ = resolve_shaft_style(attrs, p.style)
            dash = ' stroke-dasharray="5 3"'
        else:
            hex_c, sw, _ = resolve_pipe_style(attrs, p.style)
            dash = ""
        path = ortho_path(x0, y0, x1, y1)
        parts.append(
            f'<path d="{path}" fill="none" stroke="{esc(hex_c)}" stroke-width="{sw}"'
            f'{dash} data-medium="{esc(medium)}" data-connection="{esc(e.get("id") or f"c{i}")}"/>'
        )

    for cid, (cx, cy) in positions.items():
        c = by_id[cid]
        sym = c.get("symbol") or c.get("type") or "junction"
        tag = c.get("tag") or c.get("label") or cid
        parts.append(
            f'<g class="component" data-component="{esc(cid)}" data-symbol="{esc(sym)}" '
            f'data-domain="{esc(c.get("domain") or "")}" '
            f'transform="translate({cx - SYM_W/2:.1f},{cy - SYM_H/2:.1f})">'
            f"{symbol_inner(sym)}</g>"
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + SYM_H/2 + 14:.1f}" text-anchor="middle" '
            f'{p.tag_attrs()}>{esc(str(tag))}</text>'
        )

    parts.append(legend_svg)
    return wrap_svg("\n".join(parts), width=width, height=height, layout="hybrid", style=p.style)
