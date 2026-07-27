"""Hit-testing + port hotspots for SVG-in-canvas overlay (approach A).

Invisible hit targets over engine SVG. Sizes in pt (same as DiagramStyle).
Z-order: ports > components > connections.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .graph import SYM_H, SYM_W, find_port, normalize_graph, port_point
from .manual_layout import _rotated_port, ensure_positions
from .paint import resolve_style

# Hotspot radii / padding (pt) — defaults; overridden by DiagramStyle.ports
PORT_HIT_RADIUS = 6.0
PORT_SNAP_RADIUS = 10.0
COMPONENT_PAD = 4.0
CONNECTION_HIT_WIDTH = 6.0


@dataclass
class Hotspot:
    kind: str  # port | component | connection
    id: str
    x: float
    y: float
    # AABB or circle
    width: float = 0.0
    height: float = 0.0
    radius: float = 0.0
    meta: dict = field(default_factory=dict)

    def contains(self, px: float, py: float) -> bool:
        if self.kind == "port" or self.radius > 0:
            dx, dy = px - self.x, py - self.y
            return (dx * dx + dy * dy) <= (self.radius * self.radius)
        # AABB centered at x,y for components; for connections use segment band via meta
        if self.kind == "connection":
            return _near_polyline(px, py, self.meta.get("points") or [], CONNECTION_HIT_WIDTH)
        hw, hh = self.width / 2, self.height / 2
        return (self.x - hw) <= px <= (self.x + hw) and (self.y - hh) <= py <= (self.y + hh)

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "radius": self.radius,
            "meta": dict(self.meta),
        }


@dataclass
class HitTestIndex:
    hotspots: list[dict] = field(default_factory=list)
    _items: list[Hotspot] = field(default_factory=list)

    def hit(self, x: float, y: float) -> dict | None:
        # Z-order: ports first, then components, then connections
        for kind in ("port", "component", "connection"):
            for h in self._items:
                if h.kind == kind and h.contains(x, y):
                    return h.to_dict()
        return None


def build_hit_index(graph: dict, *, style: Any = None) -> HitTestIndex:
    st = resolve_style(style)
    g = ensure_positions(normalize_graph(graph), profile=g_type(graph), style=st)
    comps = [c for c in (g.get("components") or []) if isinstance(c, dict) and c.get("id")]
    edges = list(g.get("connections") or [])
    by_id = {c["id"]: c for c in comps}
    items: list[Hotspot] = []

    port_r = float(getattr(st.ports, "hotspot_radius", PORT_HIT_RADIUS) or PORT_HIT_RADIUS)
    snap_r = float(getattr(st.ports, "snap_radius", PORT_SNAP_RADIUS) or PORT_SNAP_RADIUS)

    for c in comps:
        pos = c.get("position") or {}
        cx, cy = float(pos.get("x", 0)), float(pos.get("y", 0))
        rot = int(c.get("rotation") or 0)
        items.append(Hotspot(
            kind="component",
            id=c["id"],
            x=cx,
            y=cy,
            width=SYM_W + COMPONENT_PAD * 2,
            height=SYM_H + COMPONENT_PAD * 2,
            meta={"type": c.get("type"), "tag": c.get("tag"), "rotation": rot},
        ))
        for port in c.get("ports") or []:
            px, py = _rotated_port(cx, cy, port, rot)
            items.append(Hotspot(
                kind="port",
                id=f"{c['id']}.{port.get('id')}",
                x=px,
                y=py,
                radius=port_r,
                meta={
                    "component_id": c["id"],
                    "port_id": port.get("id"),
                    "side": port.get("side"),
                    "kind": port.get("kind"),
                    "name": port.get("name"),
                    "snap_radius": snap_r,
                },
            ))

    for e in edges:
        fr, to = e.get("from"), e.get("to")
        if not fr or not to:
            continue
        c0, c1 = by_id.get(fr["component_id"]), by_id.get(to["component_id"])
        if not c0 or not c1:
            continue
        p0 = c0.get("position") or {}
        p1 = c1.get("position") or {}
        x0, y0 = _rotated_port(
            float(p0.get("x", 0)), float(p0.get("y", 0)),
            find_port(c0, fr["port_id"]), int(c0.get("rotation") or 0),
        )
        x1, y1 = _rotated_port(
            float(p1.get("x", 0)), float(p1.get("y", 0)),
            find_port(c1, to["port_id"]), int(c1.get("rotation") or 0),
        )
        # Orthogonal mid polyline for hit band
        mid = (x0 + x1) / 2
        points = [(x0, y0), (mid, y0), (mid, y1), (x1, y1)]
        items.append(Hotspot(
            kind="connection",
            id=e.get("id") or f"{fr['component_id']}-{to['component_id']}",
            x=(x0 + x1) / 2,
            y=(y0 + y1) / 2,
            meta={"points": points, "medium": e.get("medium")},
        ))

    return HitTestIndex(
        hotspots=[h.to_dict() for h in items],
        _items=items,
    )


def g_type(graph: dict) -> str:
    return (graph.get("type") or graph.get("profile") or "piping").lower()


def _near_polyline(px: float, py: float, points: list, width: float) -> bool:
    if len(points) < 2:
        return False
    half = width / 2
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if _dist_point_segment(px, py, x0, y0, x1, y1) <= half:
            return True
    return False


def _dist_point_segment(
    px: float, py: float, x0: float, y0: float, x1: float, y1: float,
) -> float:
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return ((px - x0) ** 2 + (py - y0) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    qx, qy = x0 + t * dx, y0 + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


# Affordance constants for UI chrome (documented contract)
AFFORDANCES = {
    "port_hit_radius_pt": PORT_HIT_RADIUS,
    "port_snap_radius_pt": PORT_SNAP_RADIUS,
    "component_pad_pt": COMPONENT_PAD,
    "connection_hit_width_pt": CONNECTION_HIT_WIDTH,
    "z_order": ["port", "component", "connection"],
    "connect_cursor": "crosshair",
    "legal_target_ring_pt": 10.0,
    "ghost_opacity": 0.45,
}


def snap_port_at(
    graph: dict,
    x: float,
    y: float,
    *,
    style: Any = None,
    from_port: str | None = None,
    legal_only: list[str] | None = None,
) -> dict | None:
    """Nearest compatible port within style.ports.snap_radius, or None."""
    st = resolve_style(style)
    idx = build_hit_index(graph, style=st)
    snap_r = float(st.ports.snap_radius)
    best = None
    best_d = snap_r
    legal = set(legal_only or [])
    for h in idx._items:
        if h.kind != "port":
            continue
        if from_port and h.id == from_port:
            continue
        if legal and h.id not in legal:
            continue
        dx, dy = x - h.x, y - h.y
        d = (dx * dx + dy * dy) ** 0.5
        if d <= best_d:
            best_d = d
            best = h.to_dict()
            best["distance"] = d
    return best
