"""Piping / simple P&ID-style schematic SVG.

Installation-manual clarity: orthogonal runs, tags, media legend, flow arrows.
"""
from __future__ import annotations

from .graph import (
    SYM_H,
    SYM_W,
    esc,
    find_port,
    flow_arrow_marker_defs,
    legend_block,
    normalize_graph,
    ortho_path,
    place_lr_chain,
    port_point,
    resolve_pipe_style,
    symbol_inner,
    topo_order,
    wrap_svg,
)

PIPING_FIXTURE: dict = {
    "id": "piping_feed_sample",
    "type": "piping",
    "domain": "piping",
    "title": "Feed line — piping schematic",
    "components": [
        {"id": "T1", "type": "tank_vertical", "label": "Feed tank", "tag": "T-101"},
        {"id": "S1", "type": "strainer", "label": "Strainer", "tag": "Y-101"},
        {"id": "P1", "type": "centrifugal_pump", "label": "Feed pump", "tag": "P-101"},
        {"id": "V1", "type": "valve_ball", "label": "Isolation", "tag": "V-12"},
        {"id": "V2", "type": "valve_check", "label": "Check", "tag": "V-13"},
        {"id": "PT", "type": "instrument_pt", "label": "Pressure", "tag": "PT-101"},
        {"id": "OUT", "type": "pipe_straight", "label": "To process", "tag": "→"},
    ],
    "connections": [
        {"from": "T1.outlet", "to": "S1.in", "medium": "pipe", "media": "water", "dn": 80, "designation": "L-101", "flow_direction": "forward"},
        {"from": "S1.out", "to": "P1.suction", "medium": "pipe", "media": "water", "dn": 80, "flow_direction": "forward"},
        {"from": "P1.discharge", "to": "V1.in", "medium": "pipe", "media": "water", "dn": 50, "flow_direction": "forward"},
        {"from": "V1.out", "to": "V2.in", "medium": "pipe", "media": "water", "dn": 50, "flow_direction": "forward"},
        {"from": "V2.out", "to": "OUT.in", "medium": "pipe", "media": "water", "dn": 50, "designation": "L-102", "flow_direction": "forward"},
        {"from": "V1.out", "to": "PT.process", "medium": "pipe", "media": "water", "dn": 15, "size_class": "small", "designation": "tap"},
    ],
}

PID_FIXTURE: dict = {
    **PIPING_FIXTURE,
    "id": "pid_feed_sample",
    "type": "pid",
    "title": "Feed utility — P&ID-style sketch",
}


def render_piping_diagram(
    spec: dict,
    *,
    mode: str | None = None,
    title: str | None = None,
    style=None,
) -> str:
    from .paint import paint as get_paint
    p = get_paint(style)
    g = normalize_graph(spec, default_type="piping", default_domain="piping", default_medium="pipe")
    layout = (mode or g.get("type") or "piping").lower()
    if layout in ("p_and_id", "pnid", "p&id"):
        layout = "pid"
    ttl = title or g.get("title") or (
        "P&ID-style sketch" if layout == "pid" else "Piping schematic"
    )
    return _render(g, ttl, layout, p)


def _render(g: dict, title: str, layout: str, p) -> str:
    comps = [c for c in (g.get("components") or []) if isinstance(c, dict) and c.get("id")]
    edges = list(g.get("connections") or [])
    by_id = {c["id"]: c for c in comps}
    ordered = topo_order(comps, edges)
    gap = p.style.grid.min_component_gap
    positions = place_lr_chain(ordered, origin_x=90, origin_y=130, step_x=max(96.0, gap * 4))

    for c in comps:
        if (c.get("type") or "").startswith("instrument") or c.get("type") == "instrument_pt":
            if c["id"] in positions:
                x, y = positions[c["id"]]
                positions[c["id"]] = (x, y - 70)

    margin = float(p.style.canvas.padding) * 4
    max_x = max((pt[0] for pt in positions.values()), default=200) + 80
    max_y = max((pt[1] for pt in positions.values()), default=130) + 90

    legend_items: list[tuple[str, str, float | None]] = []
    seen: set[str] = set()
    for e in edges:
        attrs = e.get("attributes") or {}
        hex_c, width, label = resolve_pipe_style(attrs, p.style)
        key = f"{hex_c}|{label}"
        if key not in seen:
            seen.add(key)
            legend_items.append((hex_c, label, width))

    legend_svg, legend_h = legend_block(
        legend_items, max_x + 20, margin + 20, "Pipe media", style=p.style,
    )
    width = max(640.0, max_x + 200)
    height = max(max_y + 40, margin + 20 + legend_h + 40)

    parts = [
        flow_arrow_marker_defs(p.style),
        f'<text x="{margin}" y="28" {p.title_attrs()}>{esc(title)}</text>',
        f'<text x="{margin}" y="44" {p.subtitle_attrs()}>{esc(layout)} · tags · orthogonal</text>',
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
        x0, y0 = port_point(pos0[0], pos0[1], find_port(c0, fr["port_id"]))
        x1, y1 = port_point(pos1[0], pos1[1], find_port(c1, to["port_id"]))
        attrs = e.get("attributes") or {}
        hex_c, sw, _ = resolve_pipe_style(attrs, p.style)
        via = None
        if abs(pos0[1] - pos1[1]) > 20:
            via = (pos0[0] + pos1[0]) / 2
        path = ortho_path(x0, y0, x1, y1, via_x=via)
        flow = (attrs.get("flow_direction") or "forward").lower()
        marker = ' marker-end="url(#flowArrow)"' if flow == "forward" else ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="{esc(hex_c)}" stroke-width="{sw}" '
            f'data-connection="{esc(e.get("id") or f"c{i}")}" '
            f'data-medium="pipe"{marker}/>'
        )
        des = attrs.get("designation") or attrs.get("size") or ""
        if des:
            parts.append(
                f'<text x="{(x0 + x1) / 2:.1f}" y="{(y0 + y1) / 2 - 6:.1f}" '
                f'text-anchor="middle" {p.annotation_attrs()}>{esc(str(des))}</text>'
            )

    for cid, (cx, cy) in positions.items():
        c = by_id[cid]
        sym = c.get("symbol") or c.get("type") or "pipe_straight"
        tag = c.get("tag") or c.get("label") or cid
        sub = c.get("label") if c.get("tag") else ""
        parts.append(
            f'<g class="component" data-component="{esc(cid)}" data-symbol="{esc(sym)}" '
            f'transform="translate({cx - SYM_W/2:.1f},{cy - SYM_H/2:.1f})">'
            f"{symbol_inner(sym)}</g>"
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + SYM_H/2 + 14:.1f}" text-anchor="middle" '
            f'{p.tag_attrs()}>{esc(str(tag))}</text>'
        )
        if sub and str(sub) != str(tag):
            parts.append(
                f'<text x="{cx:.1f}" y="{cy + SYM_H/2 + 26:.1f}" text-anchor="middle" '
                f'{p.annotation_attrs()}>{esc(str(sub))}</text>'
            )

    parts.append(legend_svg)
    return wrap_svg(
        "\n".join(parts), width=width, height=height, layout=layout, style=p.style,
    )
