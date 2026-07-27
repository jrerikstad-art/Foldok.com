"""Electrical single-line (SLD) and wiring diagram SVG renderer.

Structured graph in → deterministic SVG out. Not AutoCAD Electrical.
Uses diagram_engine/symbols/electrical/ + IEC/NO wire color palette.
"""
from __future__ import annotations

import html as html_lib
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("PyYAML required") from e

from .symbols import get_symbol

_SCHEMA = Path(__file__).resolve().parent / "schema" / "wire_colors.yaml"
_SYM_W, _SYM_H = 64.0, 48.0


@lru_cache(maxsize=1)
def load_wire_palette() -> dict[str, dict]:
    data = yaml.safe_load(_SCHEMA.read_text(encoding="utf-8")) or {}
    return dict(data.get("colors") or {})


def resolve_wire_color(key_or_hex: str | None, style=None) -> tuple[str, str]:
    """Return (hex, legend_label) — prefers DiagramStyle tokens when provided."""
    from .paint import paint as get_paint
    return get_paint(style).wire(key_or_hex)


def normalize_electrical_graph(spec: dict) -> dict:
    """Merge terminals→ports, normalize connection endpoints, set medium=wire."""
    g = deepcopy(spec or {})
    g.setdefault("components", [])
    g.setdefault("connections", [])
    g["type"] = g.get("type") or "single_line"
    g["domain"] = g.get("domain") or "electrical"

    for c in g["components"]:
        if not isinstance(c, dict):
            continue
        c.setdefault("domain", "electrical")
        sym = c.get("symbol") or c.get("type")
        if sym:
            c["type"] = sym
            c["symbol"] = sym
        ports = list(c.get("ports") or [])
        terms = list(c.get("terminals") or [])
        if terms and not ports:
            ports = terms
        elif terms:
            by_id = {p.get("id"): p for p in ports if p.get("id")}
            for t in terms:
                tid = t.get("id")
                if tid and tid not in by_id:
                    ports.append(t)
        # Fill from symbol library if still empty
        if not ports and c.get("type"):
            lib = get_symbol(c["type"]) or {}
            ports = deepcopy(list(lib.get("ports") or []))
        c["ports"] = ports
        c["terminals"] = ports

    norm_edges = []
    for i, e in enumerate(g["connections"]):
        if not isinstance(e, dict):
            continue
        edge = dict(e)
        edge.setdefault("id", edge.get("id") or f"w{i+1}")
        edge.setdefault("medium", "wire")
        attrs = dict(edge.get("attributes") or {})
        # Promote flat fields into attributes
        for k in ("color", "designation", "size", "cross_section", "cable_ref", "material"):
            if edge.get(k) and not attrs.get(k):
                attrs[k] = edge[k]
        if edge.get("label") and not attrs.get("designation"):
            attrs["designation"] = edge["label"]
        edge["attributes"] = attrs
        edge["from"] = _normalize_endpoint(edge.get("from"))
        edge["to"] = _normalize_endpoint(edge.get("to"))
        if edge["from"] and edge["to"]:
            norm_edges.append(edge)
    g["connections"] = norm_edges
    return g


def _normalize_endpoint(ep: Any) -> dict | None:
    if isinstance(ep, dict):
        cid = ep.get("component_id") or ep.get("component") or ep.get("id")
        pid = ep.get("port_id") or ep.get("terminal_id") or ep.get("port") or ep.get("terminal")
        if cid and pid:
            return {"component_id": str(cid), "port_id": str(pid)}
        # "Q1.line" style inside dict
        ref = ep.get("ref") or ep.get("pin")
        if isinstance(ref, str) and "." in ref:
            a, b = ref.split(".", 1)
            return {"component_id": a, "port_id": b}
        return None
    if isinstance(ep, str) and "." in ep:
        a, b = ep.split(".", 1)
        return {"component_id": a.strip(), "port_id": b.strip()}
    return None


def _esc(s: str) -> str:
    return html_lib.escape(s or "", quote=True)


def _symbol_inner(symbol_id: str) -> str:
    lib = get_symbol(symbol_id) or {}
    path = lib.get("_svg_path")
    if not path or not Path(path).exists():
        return (
            f'<rect x="8" y="8" width="48" height="32" fill="#fff" '
            f'stroke="#16181D" stroke-width="1.5"/>'
            f'<text x="32" y="28" text-anchor="middle" '
            f'font-family="IBM Plex Mono,monospace" font-size="7">'
            f'{_esc(symbol_id or "?")}</text>'
        )
    raw = Path(path).read_text(encoding="utf-8")
    m = re.search(r"<svg[^>]*>(.*)</svg>", raw, re.DOTALL | re.IGNORECASE)
    return (m.group(1).strip() if m else raw)


def _port_point(cx: float, cy: float, port: dict, w: float = _SYM_W, h: float = _SYM_H) -> tuple[float, float]:
    side = (port.get("side") or "right").lower()
    order = int(port.get("order") or 1)
    # Approximate multi-port offset along side
    spread = 10.0
    off = (order - 1) * spread - spread
    if side == "left":
        return cx - w / 2, cy + off
    if side == "right":
        return cx + w / 2, cy + off
    if side == "top":
        return cx + off, cy - h / 2
    return cx + off, cy + h / 2


def _ortho_path(x0: float, y0: float, x1: float, y1: float, *, via_x: float | None = None) -> str:
    """Simple orthogonal HVH or VHV path."""
    if via_x is None:
        mid = (x0 + x1) / 2
        return f"M {x0:.1f},{y0:.1f} H {mid:.1f} V {y1:.1f} H {x1:.1f}"
    return f"M {x0:.1f},{y0:.1f} H {via_x:.1f} V {y1:.1f} H {x1:.1f}"


# ── fixtures ──────────────────────────────────────────────────────────

SLD_FIXTURE: dict = {
    "id": "sld_panel_sample",
    "type": "single_line",
    "domain": "electrical",
    "title": "Distribution — single-line diagram",
    "components": [
        {"id": "SUP", "type": "meter", "label": "Supply / meter", "tag": "M1"},
        {"id": "Q0", "type": "disconnect", "label": "Main isolator", "tag": "Q0"},
        {"id": "RCD", "type": "rcd", "label": "RCD 40A/30mA", "tag": "Q1"},
        {"id": "DB", "type": "distribution_board", "label": "DB-A", "tag": "DB-A"},
        {"id": "F1", "type": "mcb", "label": "Lighting 10A", "tag": "F1"},
        {"id": "F2", "type": "mcb", "label": "Socket 16A", "tag": "F2"},
        {"id": "F3", "type": "mcb", "label": "Motor 16A", "tag": "F3"},
        {"id": "L1", "type": "lamp", "label": "Lighting", "tag": "E1"},
        {"id": "S1", "type": "socket", "label": "Socket", "tag": "X1"},
        {"id": "M1", "type": "motor", "label": "Pump motor", "tag": "M1"},
        {"id": "PE", "type": "earth", "label": "PE bar", "tag": "PE"},
    ],
    "connections": [
        {"id": "w1", "from": "SUP.out", "to": "Q0.line", "color": "L1", "designation": "L"},
        {"id": "w2", "from": "Q0.load", "to": "RCD.line", "color": "L1"},
        {"id": "w3", "from": "RCD.load", "to": "DB.in", "color": "L1"},
        {"id": "w4", "from": "DB.c1", "to": "F1.line", "color": "L1", "designation": "C1"},
        {"id": "w5", "from": "DB.c2", "to": "F2.line", "color": "L1", "designation": "C2"},
        {"id": "w6", "from": "DB.c3", "to": "F3.line", "color": "L1", "designation": "C3"},
        {"id": "w7", "from": "F1.load", "to": "L1.l", "color": "L1"},
        {"id": "w8", "from": "F2.load", "to": "S1.l", "color": "L1"},
        {"id": "w9", "from": "F3.load", "to": "M1.u", "color": "L1"},
        {"id": "w10", "from": "S1.pe", "to": "PE.pe", "color": "PE"},
        {"id": "w11", "from": "M1.pe", "to": "PE.pe", "color": "PE"},
    ],
}

WIRING_FIXTURE: dict = {
    "id": "wiring_motor_sample",
    "type": "wiring",
    "domain": "electrical",
    "title": "Motor starter — interconnection",
    "components": [
        {
            "id": "XT",
            "type": "terminal_strip",
            "label": "XT1",
            "tag": "XT1",
            "terminals": [
                {"id": "t1", "name": "L1", "side": "right", "kind": "electrical", "order": 1},
                {"id": "t2", "name": "L2", "side": "right", "kind": "electrical", "order": 2},
                {"id": "t3", "name": "L3", "side": "right", "kind": "electrical", "order": 3},
                {"id": "t4", "name": "N", "side": "right", "kind": "electrical", "order": 4},
                {"id": "t5", "name": "PE", "side": "right", "kind": "electrical", "order": 5},
            ],
        },
        {"id": "KM", "type": "contactor", "label": "KM1", "tag": "KM1"},
        {"id": "F1", "type": "overload_relay", "label": "F1", "tag": "F1"},
        {"id": "M", "type": "motor", "label": "M1 2.2kW", "tag": "M1"},
        {"id": "PE", "type": "earth", "label": "PE", "tag": "PE"},
    ],
    "connections": [
        {"from": "XT.t1", "to": "KM.line", "color": "L1", "designation": "1", "cable_ref": "W1", "cross_section": "2.5mm2"},
        {"from": "XT.t2", "to": "KM.coil_a", "color": "L2", "designation": "3", "cable_ref": "W1"},
        {"from": "XT.t3", "to": "KM.coil_b", "color": "L3", "designation": "5", "cable_ref": "W1"},
        {"from": "KM.load", "to": "F1.in", "color": "L1", "designation": "2"},
        {"from": "F1.out", "to": "M.u", "color": "L1", "designation": "U1", "cable_ref": "W2"},
        {"from": "XT.t5", "to": "PE.pe", "color": "PE", "designation": "PE"},
        {"from": "M.pe", "to": "PE.pe", "color": "PE"},
        {"from": "XT.t4", "to": "M.v", "color": "N", "designation": "N"},
    ],
}

# Residential 240V electric water heater — non-simultaneous elements.
# Schematic interconnection (not a pictorial tank cutaway).
WATER_HEATER_240V_FIXTURE: dict = {
    "id": "wiring_water_heater_240v",
    "type": "wiring",
    "domain": "electrical",
    "title": "Electric water heater — 240V / 5kW (non-simultaneous)",
    "notes": [
        "10 AWG phase conductors · 30A 2-pole breaker",
        "Upper thermostat prioritizes upper element; lower only when upper satisfied",
    ],
    "components": [
        {
            "id": "PANEL",
            "type": "distribution_board",
            "label": "Service panel",
            "tag": "DB",
        },
        {
            "id": "Q30",
            "type": "mcb",
            "label": "30A 2P breaker",
            "tag": "Q30",
        },
        {
            "id": "UT",
            "type": "switch",
            "label": "Upper thermostat",
            "tag": "UT",
        },
        {
            "id": "UE",
            "type": "heater_element",
            "label": "Upper element 5kW",
            "tag": "UE",
        },
        {
            "id": "LT",
            "type": "switch",
            "label": "Lower thermostat",
            "tag": "LT",
        },
        {
            "id": "LE",
            "type": "heater_element",
            "label": "Lower element 5kW",
            "tag": "LE",
        },
        {
            "id": "PE",
            "type": "earth",
            "label": "Tank / PE",
            "tag": "PE",
        },
    ],
    "connections": [
        {
            "id": "w1",
            "from": "PANEL.c1",
            "to": "Q30.line",
            "color": "L1",
            "designation": "L1",
            "cable_ref": "W-WH",
            "cross_section": "10 AWG",
        },
        {
            "id": "w2",
            "from": "Q30.load",
            "to": "UT.line",
            "color": "L1",
            "designation": "L1",
        },
        {
            "id": "w3",
            "from": "UT.load",
            "to": "UE.l",
            "color": "L1",
            "designation": "upper",
        },
        {
            "id": "w4",
            "from": "UT.load",
            "to": "LT.line",
            "color": "L1",
            "designation": "inter",
        },
        {
            "id": "w5",
            "from": "LT.load",
            "to": "LE.l",
            "color": "L1",
            "designation": "lower",
        },
        {
            "id": "w6",
            "from": "PANEL.c2",
            "to": "UE.n",
            "color": "L2",
            "designation": "L2",
            "cable_ref": "W-WH",
            "cross_section": "10 AWG",
        },
        {
            "id": "w7",
            "from": "UE.n",
            "to": "LE.n",
            "color": "L2",
            "designation": "L2",
        },
        {
            "id": "w8",
            "from": "PANEL.c3",
            "to": "PE.pe",
            "color": "PE",
            "designation": "PE",
            "cable_ref": "W-WH",
        },
    ],
}


# ── renderers ─────────────────────────────────────────────────────────

def render_electrical_diagram(
    spec: dict,
    *,
    mode: str | None = None,
    title: str | None = None,
    style=None,
) -> str:
    """Render single_line or wiring SVG from an electrical graph."""
    from .paint import paint as get_paint
    p = get_paint(style)
    g = normalize_electrical_graph(spec)
    diagram_type = (mode or g.get("type") or "single_line").lower().replace("-", "_")
    if diagram_type in ("sld", "singleline", "power"):
        diagram_type = "single_line"
    if diagram_type in ("interconnection", "terminal_wiring"):
        diagram_type = "wiring"
    ttl = title or g.get("title") or (
        "Single-line diagram" if diagram_type == "single_line" else "Wiring diagram"
    )
    if diagram_type == "wiring":
        return _render_wiring(g, ttl, p)
    return _render_sld(g, ttl, p)


def _collect_legend(edges: list[dict], p) -> list[tuple[str, str, float | None]]:
    seen: dict[str, tuple[str, float]] = {}
    for e in edges:
        attrs = e.get("attributes") or {}
        color = attrs.get("color")
        hex_c, label = p.wire(color)
        seen.setdefault(hex_c, (label, p.wire_width(color)))
    return [(h, lab, w) for h, (lab, w) in seen.items()]


def _render_sld(g: dict, title: str, p) -> str:
    comps = list(g.get("components") or [])
    edges = list(g.get("connections") or [])
    by_id = {c["id"]: c for c in comps if c.get("id")}

    # Vertical main trunk + side feeders for leaves connected from DB
    margin_x, margin_y = 80.0, 56.0
    col_main = margin_x + 120.0
    step_y = 72.0
    positions: dict[str, tuple[float, float]] = {}

    # Order: follow chain from first component, then remaining by list order
    ordered = _topo_order_sld(comps, edges)
    for i, cid in enumerate(ordered):
        positions[cid] = (col_main, margin_y + 40 + i * step_y)

    # Fan loads slightly to the right if they are sinks with degree 1
    sinks = {e["to"]["component_id"] for e in edges if e.get("to")}
    sources = {e["from"]["component_id"] for e in edges if e.get("from")}
    leaves = [c for c in ordered if c in sinks and c not in sources]
    for j, cid in enumerate(leaves):
        if cid in positions:
            y = positions[cid][1]
            positions[cid] = (col_main + 140 + (j % 3) * 20, y)

    max_x = max((p0[0] for p0 in positions.values()), default=col_main) + 100
    max_y = max((p0[1] for p0 in positions.values()), default=margin_y) + 80
    legend = _collect_legend(edges, p)
    legend_svg, legend_h = p.legend_block(legend, max_x + 40, margin_y + 20, "Wire colors")
    width = max(520, max_x + 220)
    height = max(max_y + 40, margin_y + 20 + legend_h + 40)

    parts: list[str] = []
    parts.append(
        f'<text x="{margin_x}" y="28" {p.title_attrs()}>{_esc(title)}</text>'
    )
    parts.append(
        f'<text x="{margin_x}" y="44" {p.subtitle_attrs()}>single_line · deterministic</text>'
    )

    # Wires first (under symbols)
    for e in edges:
        fr, to = e.get("from"), e.get("to")
        if not fr or not to:
            continue
        c0, c1 = by_id.get(fr["component_id"]), by_id.get(to["component_id"])
        if not c0 or not c1:
            continue
        pos0 = positions.get(c0["id"])
        pos1 = positions.get(c1["id"])
        if not pos0 or not pos1:
            continue
        port0 = _find_port(c0, fr["port_id"])
        port1 = _find_port(c1, to["port_id"])
        x0, y0 = _port_point(pos0[0], pos0[1], port0)
        x1, y1 = _port_point(pos1[0], pos1[1], port1)
        attrs = e.get("attributes") or {}
        hex_c, _ = p.wire(attrs.get("color"))
        path = _ortho_path(x0, y0, x1, y1)
        des = attrs.get("designation") or ""
        parts.append(
            f'<path d="{path}" fill="none" stroke="{_esc(hex_c)}" '
            f'stroke-width="{p.wire_width(attrs.get("color"))}" '
            f'data-wire="{_esc(e.get("id") or "")}" data-color="{_esc(str(attrs.get("color") or ""))}"/>'
        )
        if des:
            mx, my = (x0 + x1) / 2 + 4, (y0 + y1) / 2 - 4
            parts.append(
                f'<text x="{mx:.1f}" y="{my:.1f}" {p.annotation_attrs(color=hex_c)}>'
                f'{_esc(str(des))}</text>'
            )

    # Components
    for cid, (cx, cy) in positions.items():
        c = by_id[cid]
        sym = c.get("symbol") or c.get("type") or "junction"
        inner = _symbol_inner(sym)
        label = c.get("tag") or c.get("label") or cid
        sub = c.get("label") if c.get("tag") else (c.get("type") or "")
        parts.append(
            f'<g class="component" data-component="{_esc(cid)}" data-symbol="{_esc(sym)}" '
            f'transform="translate({cx - _SYM_W/2:.1f},{cy - _SYM_H/2:.1f})">{inner}</g>'
        )
        parts.append(
            f'<text x="{cx + _SYM_W/2 + 8:.1f}" y="{cy - 4:.1f}" {p.tag_attrs()}>'
            f'{_esc(str(label))}</text>'
        )
        if sub and str(sub) != str(label):
            parts.append(
                f'<text x="{cx + _SYM_W/2 + 8:.1f}" y="{cy + 10:.1f}" {p.annotation_attrs()}>'
                f'{_esc(str(sub))}</text>'
            )

    parts.append(legend_svg)
    body = "\n".join(parts)
    # Electrical marker + style id
    svg = p.wrap_svg(body, width=width, height=height, layout="single_line")
    return svg.replace('data-foldok="domain_diagram"', 'data-foldok="electrical_diagram"', 1).replace(
        'data-graph="connection"', 'data-graph="electrical"', 1
    )


def _render_wiring(g: dict, title: str, p) -> str:
    from .graph import ortho_path_with_stubs
    from .labels import label_svg, place_component_label

    comps = list(g.get("components") or [])
    edges = list(g.get("connections") or [])
    by_id = {c["id"]: c for c in comps if c.get("id")}

    margin_x, margin_y = 48.0, 56.0
    left_x = margin_x + 80.0
    right_start = left_x + 280.0
    gap = float(p.style.gaps.min_component)
    row_h = max(56.0, _SYM_H + gap * 0.5)

    # Prefer user positions when present (canvas edits)
    positions: dict[str, tuple[float, float]] = {}
    missing = []
    for c in comps:
        pos = c.get("position") or {}
        if "x" in pos and "y" in pos:
            positions[c["id"]] = (float(pos["x"]), float(pos["y"]))
        else:
            missing.append(c)

    if missing or not positions:
        left, right = [], []
        for c in comps:
            t = (c.get("type") or "").lower()
            if t in ("terminal_strip", "terminal", "busbar", "distribution_board"):
                left.append(c)
            else:
                right.append(c)
        if not left:
            left = comps[:1]
            right = comps[1:]
        for i, c in enumerate(left):
            if c["id"] not in positions:
                positions[c["id"]] = (left_x, margin_y + 50 + i * (row_h + 40))
        for i, c in enumerate(right):
            if c["id"] not in positions:
                positions[c["id"]] = (right_start + (i % 2) * 100, margin_y + 50 + i * row_h)

    # Write resolved positions back so canvas can edit without topology change
    for c in comps:
        if c.get("id") in positions and not (c.get("position") and "x" in c["position"]):
            xy = positions[c["id"]]
            c["position"] = {"x": xy[0], "y": xy[1]}

    max_x = max((pt[0] for pt in positions.values()), default=right_start) + 120
    max_y = max((pt[1] for pt in positions.values()), default=margin_y) + 90
    legend = _collect_legend(edges, p)
    legend_svg, legend_h = p.legend_block(legend, max_x + 24, margin_y + 20, "Wire colors")
    width = max(640, max_x + 200)
    height = max(max_y + 40, margin_y + 20 + legend_h + 40)
    ink = p.style.colors.ink
    port_r = float(p.style.ports.dot_size) / 2 if hasattr(p.style, "ports") else p.style.symbols.port_dot / 2
    stub = float(p.style.routing.stub_length)
    bus = bool(p.style.routing.bus_align)
    grid = float(p.style.grid.step)

    parts: list[str] = [
        f'<text x="{margin_x}" y="28" {p.title_attrs()}>{_esc(title)}</text>',
        f'<text x="{margin_x}" y="44" {p.subtitle_attrs()}>wiring · terminal interconnection</text>',
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
        port0 = _find_port(c0, fr["port_id"])
        port1 = _find_port(c1, to["port_id"])
        x0, y0 = _port_point(pos0[0], pos0[1], port0)
        x1, y1 = _port_point(pos1[0], pos1[1], port1)
        via = left_x + 140 + (i % 6) * 14
        if bus and grid > 0:
            via = round(via / grid) * grid
        attrs = e.get("attributes") or {}
        color_key = attrs.get("color")
        hex_c, _ = p.wire(color_key)
        path = ortho_path_with_stubs(
            x0, y0, x1, y1,
            side0=port0.get("side"), side1=port1.get("side"),
            stub=stub, via_x=via, bus_align=bus, grid_step=grid,
        )
        parts.append(
            f'<path d="{path}" fill="none" stroke="{_esc(hex_c)}" '
            f'stroke-width="{p.wire_width(color_key)}" '
            f'data-wire="{_esc(e.get("id") or f"w{i}")}" '
            f'data-cable="{_esc(str(attrs.get("cable_ref") or ""))}"/>'
        )
        des = attrs.get("designation") or attrs.get("cross_section") or ""
        if des:
            parts.append(
                f'<text x="{via + 4:.1f}" y="{(y0 + y1) / 2 - 3:.1f}" '
                f'{p.annotation_attrs(color=hex_c)}>{_esc(str(des))}</text>'
            )

    occupied = []
    symbol_centers = list(positions.values())
    for cid, (cx, cy) in positions.items():
        c = by_id[cid]
        sym = c.get("symbol") or c.get("type") or "terminal"
        inner = _symbol_inner(sym)
        label = c.get("tag") or c.get("label") or cid
        parts.append(
            f'<g class="component" data-component="{_esc(cid)}" data-symbol="{_esc(sym)}" '
            f'transform="translate({cx - _SYM_W/2:.1f},{cy - _SYM_H/2:.1f})">{inner}</g>'
        )
        box = place_component_label(
            str(label), cx, cy, p.style,
            occupied=occupied, symbol_centers=symbol_centers,
        )
        occupied.append(box)
        parts.append(
            label_svg(str(label), box, p.style, symbol_xy=(cx, cy), paint_attrs=p.tag_attrs())
        )
        for port in c.get("ports") or []:
            px, py = _port_point(cx, cy, port)
            parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{port_r:.1f}" fill="{_esc(ink)}" '
                f'data-port="{_esc(cid)}.{_esc(port.get("id") or "")}"/>'
            )
            nm = port.get("name") or port.get("id")
            if nm:
                side = (port.get("side") or "right").lower()
                tx = px - 8 if side == "left" else px + 8
                anchor = "end" if side == "left" else "start"
                parts.append(
                    f'<text x="{tx:.1f}" y="{py + 3:.1f}" text-anchor="{anchor}" '
                    f'{p.annotation_attrs()}>{_esc(str(nm))}</text>'
                )

    parts.append(legend_svg)
    body = "\n".join(parts)
    svg = p.wrap_svg(body, width=width, height=height, layout="wiring")
    return svg.replace('data-foldok="domain_diagram"', 'data-foldok="electrical_diagram"', 1).replace(
        'data-graph="connection"', 'data-graph="electrical"', 1
    )


def _find_port(comp: dict, port_id: str) -> dict:
    for p in comp.get("ports") or []:
        if p.get("id") == port_id or p.get("name") == port_id:
            return p
    return {"id": port_id, "side": "bottom", "order": 1}


def _topo_order_sld(comps: list[dict], edges: list[dict]) -> list[str]:
    ids = [c["id"] for c in comps if c.get("id")]
    if not ids:
        return []
    succ: dict[str, list[str]] = {i: [] for i in ids}
    indeg = {i: 0 for i in ids}
    for e in edges:
        fr, to = e.get("from"), e.get("to")
        if not fr or not to:
            continue
        a, b = fr["component_id"], to["component_id"]
        if a in succ and b in indeg and b not in succ[a]:
            succ[a].append(b)
            indeg[b] += 1
    roots = [i for i in ids if indeg[i] == 0]
    if not roots:
        roots = [ids[0]]
    out: list[str] = []
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        n = stack.pop(0)
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
        for s in succ.get(n) or []:
            if s not in seen:
                stack.append(s)
    for i in ids:
        if i not in seen:
            out.append(i)
    return out
