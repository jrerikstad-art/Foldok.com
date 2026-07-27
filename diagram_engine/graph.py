"""Shared connection graph — all domains.

Component + Port + Connection is the single model. Domains differ by
symbol pack and connection attributes (wire color vs DN vs shaft), not
by separate product engines.
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

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"
SYM_W, SYM_H = 64.0, 48.0

DIAGRAM_TYPES = frozenset({
    "single_line", "wiring", "piping", "pid", "mechanical", "hybrid", "block",
})

DEFAULT_MEDIUM = {
    "electrical": "wire",
    "piping": "pipe",
    "mechanical": "shaft",
    "hybrid": "pipe",
}


@lru_cache(maxsize=1)
def load_media_palette() -> dict[str, Any]:
    path = SCHEMA_DIR / "media.yaml"
    if not path.exists():
        return {"media": {}, "size_class": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def esc(s: str) -> str:
    return html_lib.escape(s or "", quote=True)


def normalize_endpoint(ep: Any) -> dict | None:
    if isinstance(ep, dict):
        cid = ep.get("component_id") or ep.get("component") or ep.get("id")
        pid = (
            ep.get("port_id") or ep.get("terminal_id")
            or ep.get("port") or ep.get("terminal")
        )
        if cid and pid:
            return {"component_id": str(cid), "port_id": str(pid)}
        ref = ep.get("ref") or ep.get("pin")
        if isinstance(ref, str) and "." in ref:
            a, b = ref.split(".", 1)
            return {"component_id": a, "port_id": b}
        return None
    if isinstance(ep, str) and "." in ep:
        a, b = ep.split(".", 1)
        return {"component_id": a.strip(), "port_id": b.strip()}
    return None


def normalize_graph(
    spec: dict,
    *,
    default_type: str = "block",
    default_domain: str | None = None,
    default_medium: str | None = None,
) -> dict:
    """Normalize components/ports/connections for any domain diagram."""
    g = deepcopy(spec or {})
    g.setdefault("components", [])
    g.setdefault("connections", [])
    g["type"] = (g.get("type") or default_type).lower().replace("-", "_")
    if g["type"] == "sld":
        g["type"] = "single_line"
    if g["type"] in ("p_and_id", "p&id", "pnid"):
        g["type"] = "pid"
    if default_domain and not g.get("domain"):
        g["domain"] = default_domain
    elif not g.get("domain"):
        # Infer from components
        domains = {
            (c.get("domain") or "").lower()
            for c in g["components"] if isinstance(c, dict) and c.get("domain")
        }
        domains.discard("")
        if len(domains) == 1:
            g["domain"] = next(iter(domains))
        elif len(domains) > 1:
            g["domain"] = "hybrid"

    domain = (g.get("domain") or default_domain or "hybrid").lower()
    medium_default = default_medium or DEFAULT_MEDIUM.get(domain, "pipe")

    for c in g["components"]:
        if not isinstance(c, dict):
            continue
        if not c.get("domain"):
            lib = get_symbol(c.get("symbol") or c.get("type") or "") or {}
            c["domain"] = lib.get("domain") or domain
        sym = c.get("symbol") or c.get("type")
        if sym:
            c["type"] = sym
            c["symbol"] = sym
            lib = get_symbol(sym) or {}
            if lib.get("domain") and not c.get("domain"):
                c["domain"] = lib["domain"]
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
        if not ports and c.get("type"):
            lib = get_symbol(c["type"]) or {}
            ports = deepcopy(list(lib.get("ports") or []))
        c["ports"] = ports
        c["terminals"] = ports  # electrical alias

    ATTR_KEYS = (
        "color", "designation", "size", "cross_section", "cable_ref",
        "material", "dn", "media", "flow_direction", "size_class",
    )
    norm_edges = []
    for i, e in enumerate(g["connections"]):
        if not isinstance(e, dict):
            continue
        edge = dict(e)
        edge.setdefault("id", edge.get("id") or f"c{i+1}")
        edge.setdefault("medium", medium_default)
        attrs = dict(edge.get("attributes") or {})
        for k in ATTR_KEYS:
            if edge.get(k) is not None and attrs.get(k) is None:
                attrs[k] = edge[k]
        if edge.get("label") and not attrs.get("designation"):
            attrs["designation"] = edge["label"]
        # DN alias
        if attrs.get("dn") and not attrs.get("size"):
            attrs["size"] = f"DN{attrs['dn']}" if str(attrs["dn"]).isdigit() else str(attrs["dn"])
        edge["attributes"] = attrs
        edge["from"] = normalize_endpoint(edge.get("from"))
        edge["to"] = normalize_endpoint(edge.get("to"))
        if edge["from"] and edge["to"]:
            norm_edges.append(edge)
    g["connections"] = norm_edges
    return g


# medium → acceptable port kinds / media tokens (mirrors schema/graph.yaml)
_MEDIUM_COMPAT = {
    "wire": {"kinds": {"electrical", "signal"}, "media": {"wire", "signal"}},
    "pipe": {
        "kinds": {"fluid"},
        "media": {"water", "oil", "air", "steam", "fluid", "chemical", "drain", "vent"},
    },
    "shaft": {"kinds": {"mechanical"}, "media": {"shaft"}},
    "belt": {"kinds": {"mechanical"}, "media": {"belt", "shaft"}},
    "duct": {"kinds": {"fluid"}, "media": {"air"}},
    "signal": {"kinds": {"signal", "electrical"}, "media": {"signal", "wire"}},
}


def validate_graph(spec: dict, *, strict: bool = False) -> list[str]:
    """Return list of rule violations (empty = OK).

    Rules: endpoints reference existing ports; medium compatible with
    both ports' kind / allowed_media.
    """
    g = normalize_graph(spec)
    errors: list[str] = []
    by_id = {c["id"]: c for c in g.get("components") or [] if c.get("id")}

    for e in g.get("connections") or []:
        eid = e.get("id") or "?"
        ports_ok = True
        resolved_ports: dict[str, dict] = {}
        for end in ("from", "to"):
            ep = e.get(end) or {}
            cid, pid = ep.get("component_id"), ep.get("port_id")
            if not cid or cid not in by_id:
                errors.append(f"{eid}: {end} component {cid!r} not found")
                ports_ok = False
                continue
            ports = by_id[cid].get("ports") or []
            match = next(
                (p for p in ports if p.get("id") == pid or p.get("name") == pid),
                None,
            )
            if not match:
                errors.append(f"{eid}: {end} port {cid}.{pid} not found")
                ports_ok = False
            else:
                resolved_ports[end] = match
        if not ports_ok:
            continue
        medium = (e.get("medium") or "").lower()
        if not medium:
            continue
        compat = _MEDIUM_COMPAT.get(medium)
        if not compat:
            if strict:
                errors.append(f"{eid}: unknown medium {medium!r}")
            continue
        for end in ("from", "to"):
            ep = e.get(end) or {}
            port = resolved_ports[end]
            kind = (port.get("kind") or "").lower()
            if kind and kind not in compat["kinds"]:
                errors.append(
                    f"{eid}: medium {medium!r} incompatible with "
                    f"{ep.get('component_id')}.{ep.get('port_id')} kind={kind!r}"
                )
            allowed = {str(m).lower() for m in (port.get("allowed_media") or [])}
            if allowed and allowed.isdisjoint(compat["media"]) and medium not in allowed:
                errors.append(
                    f"{eid}: medium {medium!r} not in allowed_media "
                    f"{sorted(allowed)} on {ep.get('component_id')}.{ep.get('port_id')}"
                )
    return errors


def symbol_inner(symbol_id: str) -> str:
    lib = get_symbol(symbol_id) or {}
    path = lib.get("_svg_path")
    if not path or not Path(path).exists():
        return (
            f'<rect x="8" y="8" width="48" height="32" fill="#fff" '
            f'stroke="#16181D" stroke-width="1.5"/>'
            f'<text x="32" y="28" text-anchor="middle" '
            f'font-family="IBM Plex Mono,monospace" font-size="7">'
            f'{esc(symbol_id or "?")}</text>'
        )
    raw = Path(path).read_text(encoding="utf-8")
    m = re.search(r"<svg[^>]*>(.*)</svg>", raw, re.DOTALL | re.IGNORECASE)
    return (m.group(1).strip() if m else raw)


def find_port(comp: dict, port_id: str) -> dict:
    for p in comp.get("ports") or []:
        if p.get("id") == port_id or p.get("name") == port_id:
            return p
    return {"id": port_id, "side": "right", "order": 1}


def port_point(
    cx: float, cy: float, port: dict, w: float = SYM_W, h: float = SYM_H,
) -> tuple[float, float]:
    side = (port.get("side") or "right").lower()
    order = int(port.get("order") or 1)
    spread = 10.0
    off = (order - 1) * spread - spread * 0.5
    if side == "left":
        return cx - w / 2, cy + off
    if side == "right":
        return cx + w / 2, cy + off
    if side == "top":
        return cx + off, cy - h / 2
    return cx + off, cy + h / 2


def ortho_path(
    x0: float, y0: float, x1: float, y1: float, *, via_x: float | None = None,
) -> str:
    if via_x is None:
        mid = (x0 + x1) / 2
        return f"M {x0:.1f},{y0:.1f} H {mid:.1f} V {y1:.1f} H {x1:.1f}"
    return f"M {x0:.1f},{y0:.1f} H {via_x:.1f} V {y1:.1f} H {x1:.1f}"


def stub_exit(
    x: float, y: float, side: str | None, stub: float,
) -> tuple[float, float]:
    """Short orthogonal exit from a port before the first bend."""
    s = (side or "right").lower()
    if stub <= 0:
        return x, y
    if s == "left":
        return x - stub, y
    if s == "right":
        return x + stub, y
    if s == "top":
        return x, y - stub
    return x, y + stub


def ortho_path_with_stubs(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    side0: str | None = None,
    side1: str | None = None,
    stub: float = 12.0,
    via_x: float | None = None,
    bus_align: bool = True,
    grid_step: float = 8.0,
) -> str:
    """Orthogonal route with style stub exits; optional grid-aligned bus."""
    sx0, sy0 = stub_exit(x0, y0, side0, stub)
    sx1, sy1 = stub_exit(x1, y1, side1, stub)
    if via_x is None:
        mid = (sx0 + sx1) / 2
        if bus_align and grid_step > 0:
            mid = round(mid / grid_step) * grid_step
    else:
        mid = via_x
        if bus_align and grid_step > 0:
            mid = round(mid / grid_step) * grid_step
    return (
        f"M {x0:.1f},{y0:.1f} L {sx0:.1f},{sy0:.1f} "
        f"H {mid:.1f} V {sy1:.1f} H {sx1:.1f} L {x1:.1f},{y1:.1f}"
    )


def resolve_pipe_style(
    attrs: dict,
    style: Any = None,
) -> tuple[str, float, str]:
    """Return (stroke_hex, stroke_width, legend_label) for a pipe connection."""
    from .paint import paint as get_paint
    p = get_paint(style)
    media = attrs.get("media") or attrs.get("material") or "water"
    size_class = attrs.get("size_class")
    dn = attrs.get("size") or attrs.get("dn")
    hex_c, width, label = p.pipe(media, size_class=size_class, dn=dn)
    # Prefer explicit designation size already in label
    return hex_c, width, label


def resolve_shaft_style(attrs: dict, style: Any = None) -> tuple[str, float, str]:
    from .paint import paint as get_paint
    return get_paint(style).shaft()


def flow_arrow_marker_defs(style: Any = None) -> str:
    from .paint import paint as get_paint
    ink = get_paint(style).style.colors.ink
    return (
        '<defs>'
        '<marker id="flowArrow" markerWidth="8" markerHeight="8" '
        'refX="7" refY="3" orient="auto">'
        f'<path d="M0,0 L7,3 L0,6 Z" fill="{ink}"/>'
        "</marker>"
        "</defs>"
    )


def legend_block(
    items: list[tuple[str, str, float | None]],
    x: float,
    y: float,
    title: str = "Legend",
    style: Any = None,
) -> tuple[str, float]:
    from .paint import paint as get_paint
    return get_paint(style).legend_block(items, x, y, title)


def wrap_svg(
    body: str,
    *,
    width: float,
    height: float,
    layout: str,
    title_hint: str = "",
    style: Any = None,
) -> str:
    from .paint import paint as get_paint
    return get_paint(style).wrap_svg(body, width=width, height=height, layout=layout)


def topo_order(comps: list[dict], edges: list[dict]) -> list[str]:
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
    roots = [i for i in ids if indeg[i] == 0] or [ids[0]]
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


def place_lr_chain(
    ordered: list[str],
    *,
    origin_x: float = 100.0,
    origin_y: float = 120.0,
    step_x: float = 110.0,
) -> dict[str, tuple[float, float]]:
    return {cid: (origin_x + i * step_x, origin_y) for i, cid in enumerate(ordered)}
