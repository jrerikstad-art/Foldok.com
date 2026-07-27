"""Layout — deterministic geometry for one profile of one graph.

Order of operations, and why:

1.  Filter to the profile.  Hidden pins are honoured here.
2.  Columns from longest-path layering, so a feed reads left to right and
    Q30 / UT / LT land on shared verticals instead of drifting.
3.  Rows from barycentre ordering, then centred per column.
4.  Pins applied last, so a hand-placed component wins over anything computed
    and a released pin snaps straight back to auto.
5.  Routes: pinned waypoints if present, otherwise L/Z with lane offsets.
    Nothing cleverer.  Stable output beats optimal routing, because a re-issued
    compliance package must not diff on every edge.
6.  Labels placed against a collision index; if a label cannot be placed it is
    reported, never overlapped.
7.  Crossing bridges applied to the higher-sorting connection only.
8.  Bounding box computed from actual content, so the figure fills its frame.

Determinism: every iteration is over a sorted list, every coordinate is snapped
to half-grid and rounded, and nothing reads the clock.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from . import symbols as symbol_pack
from .model import Component, Connection, Graph
from .overrides import (
    PinStore,
    target_component,
    target_connection,
    target_port_label,
)
from .profile import Profile
from .style import DiagramStyle

NORMALS: dict[str, tuple[float, float]] = {
    "right": (1.0, 0.0),
    "bottom": (0.0, 1.0),
    "left": (-1.0, 0.0),
    "top": (0.0, -1.0),
}
SIDES = ("right", "bottom", "left", "top")


# ----------------------------------------------------------------------
# result types
# ----------------------------------------------------------------------
@dataclass
class Anchor:
    component_id: str
    port_id: str
    x: float
    y: float
    side: str

    @property
    def normal(self) -> tuple[float, float]:
        return NORMALS[self.side]


@dataclass
class Placed:
    component: Component
    symbol_id: str
    x: float                      # centre
    y: float
    rotation: int
    w: float                      # bbox after rotation
    h: float
    column: int
    anchors: dict[str, Anchor] = field(default_factory=dict)
    pinned_props: tuple[str, ...] = ()

    def rect(self) -> tuple[float, float, float, float]:
        return (self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)


@dataclass
class Route:
    connection: Connection
    points: list[tuple[float, float]]
    bridges: dict[int, list[tuple[float, float]]] = field(default_factory=dict)
    pinned: bool = False

    def segments(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        return list(zip(self.points, self.points[1:]))


@dataclass
class TextBox:
    x: float
    y: float
    text: str
    size: float
    role: str                     # tag | label | port | designation | size | axis
    anchor: str = "start"         # start | middle | end
    weight: int = 400
    color: str | None = None
    element_id: str | None = None
    mono: bool = False

    def rect(self, pad: float = 1.0) -> tuple[float, float, float, float]:
        w = len(self.text) * self.size * 0.55
        h = self.size * 1.15
        if self.anchor == "middle":
            x = self.x - w / 2
        elif self.anchor == "end":
            x = self.x - w
        else:
            x = self.x
        return (x - pad, self.y - h + pad, w + 2 * pad, h)


@dataclass
class LegendEntry:
    key: str
    label: str


@dataclass
class Layout:
    graph_id: str
    profile_id: str
    placed: list[Placed]
    routes: list[Route]
    texts: list[TextBox]
    legend: list[LegendEntry]
    bbox: tuple[float, float, float, float]
    warnings: list[str] = field(default_factory=list)
    dropped_components: list[str] = field(default_factory=list)
    broken_runs: list[str] = field(default_factory=list)

    @property
    def width(self) -> float:
        return self.bbox[2]

    @property
    def height(self) -> float:
        return self.bbox[3]


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _snap(v: float, grid: float) -> float:
    half = grid / 2.0
    return round(round(v / half) * half, 2)


def _rotate(x: float, y: float, deg: int) -> tuple[float, float]:
    deg %= 360
    if deg == 0:
        return (x, y)
    if deg == 90:
        return (-y, x)
    if deg == 180:
        return (-x, -y)
    return (y, -x)


def _rotate_side(side: str, deg: int) -> str:
    steps = (deg % 360) // 90
    return SIDES[(SIDES.index(side) + steps) % 4]


def _axis(p: tuple[float, float], q: tuple[float, float]) -> str:
    return "h" if abs(q[0] - p[0]) >= abs(q[1] - p[1]) else "v"


def _dedupe(
    points: list[tuple[float, float]],
    protected: frozenset[tuple[float, float]] = frozenset(),
) -> list[tuple[float, float]]:
    """Drop duplicates and collinear middles — except pinned waypoints, which
    stay in the point list so the canvas can put a handle on them."""
    out: list[tuple[float, float]] = []
    for p in points:
        if out and abs(out[-1][0] - p[0]) < 0.01 and abs(out[-1][1] - p[1]) < 0.01:
            continue
        out.append(p)
    # drop collinear middles
    cleaned: list[tuple[float, float]] = []
    for p in out:
        if len(cleaned) >= 2 and cleaned[-1] not in protected:
            a, b = cleaned[-2], cleaned[-1]
            if (abs(a[0] - b[0]) < 0.01 and abs(b[0] - p[0]) < 0.01) or (
                abs(a[1] - b[1]) < 0.01 and abs(b[1] - p[1]) < 0.01
            ):
                cleaned[-1] = p
                continue
        cleaned.append(p)
    return cleaned


class RectIndex:
    """Very small occupancy index — good enough for a page-sized figure."""

    def __init__(self) -> None:
        self._rects: list[tuple[float, float, float, float]] = []

    def add(self, r: tuple[float, float, float, float]) -> None:
        self._rects.append(r)

    def free(self, r: tuple[float, float, float, float]) -> bool:
        ax, ay, aw, ah = r
        for bx, by, bw, bh in self._rects:
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                return False
        return True


# ----------------------------------------------------------------------
# main entry
# ----------------------------------------------------------------------
def layout(
    graph: Graph,
    profile: Profile,
    style: DiagramStyle,
    pins: PinStore | None = None,
) -> Layout:
    pins = pins or PinStore()
    warnings: list[str] = []

    # 1 ---------------------------------------------------------------- filter
    visible: list[Component] = []
    dropped: list[str] = []
    for comp in graph.sorted_components():
        if not profile.wants_component(comp):
            dropped.append(comp.id)
            continue
        if bool(pins.value(target_component(comp.id), "hidden", profile.id, False)):
            dropped.append(comp.id)
            continue
        visible.append(comp)
    visible_ids = {c.id for c in visible}

    conns: list[Connection] = []
    broken: list[str] = []
    for conn in graph.sorted_connections():
        if not profile.wants_connection(conn):
            continue
        if bool(pins.value(target_connection(conn.id), "hidden", profile.id, False)):
            continue
        if conn.source.component_id not in visible_ids or conn.target.component_id not in visible_ids:
            broken.append(conn.id)
            continue
        conns.append(conn)
    if broken:
        warnings.append(
            f"{len(broken)} run(s) hidden because an endpoint is not in this profile: "
            + ", ".join(broken)
            + ". The engine does not bridge across a dropped component — that would invent a circuit."
        )

    # 2 -------------------------------------------------------------- columns
    columns = _assign_columns(visible, conns, pins, profile)

    # 3 ----------------------------------------------------------------- rows
    rows = _assign_rows(visible, conns, columns)

    # 4/5 -------------------------------------------------- place and pin
    placed = _place(visible, columns, rows, pins, profile, style)
    by_id = {p.component.id: p for p in placed}

    # 6 --------------------------------------------------------------- routes
    routes = _route_all(conns, by_id, pins, profile, style, warnings)

    # 7 -------------------------------------------------------------- bridges
    _apply_bridges(routes, style)

    # 8 --------------------------------------------------------------- labels
    index = RectIndex()
    for p in placed:
        index.add(p.rect())
    texts: list[TextBox] = []
    texts += _component_labels(placed, pins, profile, style, index, warnings)
    if profile.show_port_labels and style.show_port_labels:
        texts += _port_labels(placed, graph, pins, profile, style, index, warnings)
    texts += _run_labels(routes, pins, profile, style, index, warnings)
    if profile.show_elevation_axis:
        texts += _elevation_axis(placed, style)

    legend = _legend(conns, style)
    bbox = _bbox(placed, routes, texts, style)

    return Layout(
        graph_id=graph.id,
        profile_id=profile.id,
        placed=placed,
        routes=routes,
        texts=texts,
        legend=legend,
        bbox=bbox,
        warnings=warnings,
        dropped_components=dropped,
        broken_runs=broken,
    )


# ----------------------------------------------------------------------
# columns / rows
# ----------------------------------------------------------------------
def _assign_columns(
    comps: list[Component],
    conns: list[Connection],
    pins: PinStore,
    profile: Profile,
) -> dict[str, int]:
    ids = [c.id for c in comps]
    succ: dict[str, list[str]] = {i: [] for i in ids}
    indeg: dict[str, int] = {i: 0 for i in ids}
    seen: set[tuple[str, str]] = set()
    for conn in conns:
        a, b = conn.source.component_id, conn.target.component_id
        if a == b or (a, b) in seen:
            continue
        seen.add((a, b))
        succ[a].append(b)
        indeg[b] += 1

    col: dict[str, int] = {i: 0 for i in ids}
    queue = sorted([i for i in ids if indeg[i] == 0])
    processed: set[str] = set()
    while queue:
        node = queue.pop(0)
        processed.add(node)
        for nxt in sorted(succ[node]):
            col[nxt] = max(col[nxt], col[node] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
                queue.sort()
    # nodes left in cycles: place after their processed predecessors
    for node in sorted(set(ids) - processed):
        preds = [a for (a, b) in seen if b == node and a in processed]
        col[node] = max((col[p] + 1 for p in preds), default=0)

    for c in comps:
        forced = pins.value(target_component(c.id), "column", profile.id, None)
        if isinstance(forced, int):
            col[c.id] = max(0, forced)
    return col


def _assign_rows(
    comps: list[Component],
    conns: list[Connection],
    columns: dict[str, int],
) -> dict[str, int]:
    buckets: dict[int, list[str]] = {}
    for c in comps:
        buckets.setdefault(columns[c.id], []).append(c.id)
    for k in buckets:
        buckets[k].sort()

    neighbours: dict[str, set[str]] = {c.id: set() for c in comps}
    for conn in conns:
        a, b = conn.source.component_id, conn.target.component_id
        if a in neighbours and b in neighbours and a != b:
            neighbours[a].add(b)
            neighbours[b].add(a)

    rows: dict[str, int] = {}
    for k in sorted(buckets):
        for i, node in enumerate(buckets[k]):
            rows[node] = i

    for _ in range(4):
        for k in sorted(buckets):
            scored = []
            for node in buckets[k]:
                near = [rows[n] for n in sorted(neighbours[node]) if columns[n] != k]
                bary = sum(near) / len(near) if near else rows[node]
                scored.append((round(bary, 4), node))
            scored.sort()
            buckets[k] = [n for _, n in scored]
            for i, node in enumerate(buckets[k]):
                rows[node] = i
    return rows


def _place(
    comps: list[Component],
    columns: dict[str, int],
    rows: dict[str, int],
    pins: PinStore,
    profile: Profile,
    style: DiagramStyle,
) -> list[Placed]:
    per_column: dict[int, int] = {}
    for c in comps:
        per_column[columns[c.id]] = per_column.get(columns[c.id], 0) + 1

    elevations = [c.elevation_mm for c in comps if c.elevation_mm is not None]
    elev_scale = 0.0
    elev_top = 0.0
    if profile.axis == "elevation" and len(elevations) >= 2:
        elev_top = max(elevations)
        span = elev_top - min(elevations)
        if span > 0:
            elev_scale = (max(2, len(comps)) * style.row_gap) / span

    out: list[Placed] = []
    for comp in comps:
        symbol_id = profile.symbol_for(comp)
        sym = symbol_pack.get(symbol_id)
        rotation = int(pins.value(target_component(comp.id), "rotation", profile.id, 0) or 0)
        rotation = (rotation // 90 * 90) % 360
        w, h = (sym.w, sym.h) if rotation in (0, 180) else (sym.h, sym.w)

        col = columns[comp.id]
        row = rows[comp.id]
        count = per_column.get(col, 1)
        x = col * style.column_gap
        if elev_scale and comp.elevation_mm is not None:
            y = (elev_top - comp.elevation_mm) * elev_scale
        else:
            y = row * style.row_gap - (count - 1) * style.row_gap / 2.0

        pinned: list[str] = []
        pos = pins.value(target_component(comp.id), "position", profile.id, None)
        if isinstance(pos, dict):
            if pos.get("x") is not None:
                x = float(pos["x"])
                pinned.append("x")
            if pos.get("y") is not None:
                y = float(pos["y"])
                pinned.append("y")
        if pins.resolve(target_component(comp.id), "rotation", profile.id):
            pinned.append("rotation")

        p = Placed(
            component=comp,
            symbol_id=symbol_id,
            x=_snap(x, style.grid),
            y=_snap(y, style.grid),
            rotation=rotation,
            w=w,
            h=h,
            column=col,
            pinned_props=tuple(pinned),
        )
        p.anchors = _anchors(p, sym, style)
        out.append(p)
    return out


def _anchors(placed: Placed, sym, style: DiagramStyle) -> dict[str, Anchor]:
    by_side: dict[str, list] = {}
    for port in sorted(placed.component.ports, key=lambda pt: (pt.order, pt.id)):
        by_side.setdefault(port.side, []).append(port)

    anchors: dict[str, Anchor] = {}
    for side, ports in by_side.items():
        n = len(ports)
        for i, port in enumerate(ports):
            frac = (i + 1) / (n + 1)
            if side in ("left", "right"):
                lx = sym.w / 2 if side == "right" else -sym.w / 2
                ly = -sym.h / 2 + sym.h * frac
            else:
                ly = sym.h / 2 if side == "bottom" else -sym.h / 2
                lx = -sym.w / 2 + sym.w * frac
            rx, ry = _rotate(lx, ly, placed.rotation)
            anchors[port.id] = Anchor(
                component_id=placed.component.id,
                port_id=port.id,
                x=_snap(placed.x + rx, style.grid),
                y=_snap(placed.y + ry, style.grid),
                side=_rotate_side(side, placed.rotation),
            )
    return anchors


# ----------------------------------------------------------------------
# routing
# ----------------------------------------------------------------------
def _orth(
    p: tuple[float, float],
    q: tuple[float, float],
    a_axis: str,
    b_axis: str,
    lane: float,
) -> list[tuple[float, float]]:
    if abs(p[0] - q[0]) < 0.01 and abs(p[1] - q[1]) < 0.01:
        return [p]
    if a_axis == "h" and b_axis == "v":
        return [p, (q[0], p[1]), q]
    if a_axis == "v" and b_axis == "h":
        return [p, (p[0], q[1]), q]
    if a_axis == "h":
        if abs(p[1] - q[1]) < 0.01:
            return [p, q]
        mx = (p[0] + q[0]) / 2.0 + lane
        return [p, (mx, p[1]), (mx, q[1]), q]
    if abs(p[0] - q[0]) < 0.01:
        return [p, q]
    my = (p[1] + q[1]) / 2.0 + lane
    return [p, (p[0], my), (q[0], my), q]


def _route_all(
    conns: list[Connection],
    by_id: dict[str, Placed],
    pins: PinStore,
    profile: Profile,
    style: DiagramStyle,
    warnings: list[str],
) -> list[Route]:
    routes: list[Route] = []
    for i, conn in enumerate(conns):
        a_place = by_id[conn.source.component_id]
        b_place = by_id[conn.target.component_id]
        a = a_place.anchors.get(conn.source.port_id)
        b = b_place.anchors.get(conn.target.port_id)
        if a is None or b is None:
            warnings.append(f"run '{conn.id}' skipped: port not found on component")
            continue

        wp_raw = pins.value(target_connection(conn.id), "waypoints", profile.id, None)
        waypoints: list[tuple[float, float]] = []
        if isinstance(wp_raw, list):
            for w in wp_raw:
                try:
                    waypoints.append((float(w["x"]), float(w["y"])))
                except (KeyError, TypeError, ValueError):
                    warnings.append(f"run '{conn.id}': malformed waypoint pin ignored")

        lane_span = max(1, style.lane_count)
        lane = ((i % lane_span) - lane_span // 2) * style.lane_step
        if waypoints:
            lane = 0.0

        na, nb = a.normal, b.normal
        start = (a.x + na[0] * style.stub, a.y + na[1] * style.stub)
        end = (b.x + nb[0] * style.stub, b.y + nb[1] * style.stub)

        points: list[tuple[float, float]] = [(a.x, a.y), start]
        chain = waypoints + [end]
        prev = start
        a_axis = "h" if abs(na[0]) > 0 else "v"
        for j, node in enumerate(chain):
            last = j == len(chain) - 1
            b_axis = ("h" if abs(nb[0]) > 0 else "v") if last else a_axis
            seg = _orth(prev, node, a_axis, b_axis, lane)
            points.extend(seg[1:])
            if len(seg) >= 2:
                a_axis = _axis(seg[-2], seg[-1])
            prev = node
        points.append((b.x, b.y))

        snapped = [(_snap(x, style.grid), _snap(y, style.grid)) for x, y in points]
        protected = frozenset(
            (_snap(x, style.grid), _snap(y, style.grid)) for x, y in waypoints
        )
        routes.append(
            Route(
                connection=conn,
                points=_dedupe(snapped, protected),
                pinned=bool(waypoints),
            )
        )
    return routes


def _apply_bridges(routes: list[Route], style: DiagramStyle) -> None:
    if style.crossing_gap <= 0:
        return
    flat: list[tuple[str, int, tuple[float, float], tuple[float, float], str, Route]] = []
    for r in routes:
        for idx, (p, q) in enumerate(r.segments()):
            orient = "h" if abs(p[1] - q[1]) < 0.01 else ("v" if abs(p[0] - q[0]) < 0.01 else "d")
            if orient == "d":
                continue
            flat.append((r.connection.id, idx, p, q, orient, r))

    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            a_id, a_idx, ap, aq, a_or, a_route = flat[i]
            b_id, b_idx, bp, bq, b_or, b_route = flat[j]
            if a_id == b_id or a_or == b_or:
                continue
            if _shares_endpoint(a_route.connection, b_route.connection):
                continue
            h, v = (ap, aq, a_id, a_idx, a_route), (bp, bq, b_id, b_idx, b_route)
            if a_or == "v":
                h, v = v, h
            (hp, hq, h_id, h_idx, h_route) = h
            (vp, vq, v_id, v_idx, v_route) = v
            x = vp[0]
            y = hp[1]
            if not (min(hp[0], hq[0]) + 1 < x < max(hp[0], hq[0]) - 1):
                continue
            if not (min(vp[1], vq[1]) + 1 < y < max(vp[1], vq[1]) - 1):
                continue
            # the higher-sorting connection id yields and gets the bridge
            if h_id > v_id:
                h_route.bridges.setdefault(h_idx, []).append((x, y))
            else:
                v_route.bridges.setdefault(v_idx, []).append((x, y))


def _shares_endpoint(a: Connection, b: Connection) -> bool:
    keys_a = {a.source.key(), a.target.key()}
    keys_b = {b.source.key(), b.target.key()}
    return bool(keys_a & keys_b)


# ----------------------------------------------------------------------
# labels
# ----------------------------------------------------------------------
def _try_place(
    candidates: Iterable[TextBox],
    index: RectIndex,
) -> TextBox | None:
    for cand in candidates:
        if index.free(cand.rect()):
            index.add(cand.rect())
            return cand
    return None


def _component_labels(
    placed: list[Placed],
    pins: PinStore,
    profile: Profile,
    style: DiagramStyle,
    index: RectIndex,
    warnings: list[str],
) -> list[TextBox]:
    out: list[TextBox] = []
    for p in placed:
        comp = p.component
        offset = pins.value(target_component(comp.id), "label_offset", profile.id, None)
        dx = float(offset.get("dx", 0.0)) if isinstance(offset, dict) else 0.0
        dy = float(offset.get("dy", 0.0)) if isinstance(offset, dict) else 0.0
        preferred = pins.value(target_component(comp.id), "label_side", profile.id, None)

        gap = 5.0
        spots: dict[str, tuple[float, float, str]] = {
            "above": (p.x, p.y - p.h / 2 - gap, "middle"),
            "below": (p.x, p.y + p.h / 2 + gap + style.tag_size, "middle"),
            "right": (p.x + p.w / 2 + gap, p.y + style.tag_size / 3, "start"),
            "left": (p.x - p.w / 2 - gap, p.y + style.tag_size / 3, "end"),
        }
        order = ["above", "below", "right", "left"]
        if preferred in spots:
            order = [preferred] + [s for s in order if s != preferred]

        if comp.tag:
            cands = [
                TextBox(
                    x=spots[s][0] + dx,
                    y=spots[s][1] + dy,
                    text=comp.tag,
                    size=style.tag_size,
                    role="tag",
                    anchor=spots[s][2],
                    weight=style.tag_weight,
                    element_id=f"tag:{comp.id}",
                )
                for s in order
            ]
            box = _try_place(cands, index)
            if box is None:
                warnings.append(f"tag '{comp.tag}' on '{comp.id}' could not be placed clear of other ink")
            else:
                out.append(box)

        if comp.label and comp.label != comp.tag:
            below = spots["below"]
            y = below[1] + (style.label_size + 2 if comp.tag else 0)
            cands = [
                TextBox(
                    x=below[0] + dx,
                    y=y + dy,
                    text=comp.label,
                    size=style.label_size,
                    role="label",
                    anchor="middle",
                    color=style.muted_text_color,
                    element_id=f"label:{comp.id}",
                ),
                TextBox(
                    x=p.x + p.w / 2 + 5 + dx,
                    y=p.y + style.label_size + 4 + dy,
                    text=comp.label,
                    size=style.label_size,
                    role="label",
                    anchor="start",
                    color=style.muted_text_color,
                    element_id=f"label:{comp.id}",
                ),
            ]
            box = _try_place(cands, index)
            if box is not None:
                out.append(box)
    return out


def _port_labels(
    placed: list[Placed],
    graph: Graph,
    pins: PinStore,
    profile: Profile,
    style: DiagramStyle,
    index: RectIndex,
    warnings: list[str],
) -> list[TextBox]:
    out: list[TextBox] = []
    for p in sorted(placed, key=lambda q: q.component.id):
        for port in sorted(p.component.ports, key=lambda pt: (pt.order, pt.id)):
            anchor = p.anchors.get(port.id)
            if anchor is None:
                continue
            text = port.label or port.name
            if not text:
                continue
            offset = pins.value(
                target_port_label(p.component.id, port.id), "label_offset", profile.id, None
            )
            dx = float(offset.get("dx", 0.0)) if isinstance(offset, dict) else 0.0
            dy = float(offset.get("dy", 0.0)) if isinstance(offset, dict) else 0.0

            nx, ny = anchor.normal
            base_x = anchor.x + nx * (style.stub * 0.45)
            base_y = anchor.y + ny * (style.stub * 0.45)
            if anchor.side == "right":
                cands = [(base_x + 2, base_y - 2, "start"), (base_x + 2, base_y + style.port_label_size + 2, "start")]
            elif anchor.side == "left":
                cands = [(base_x - 2, base_y - 2, "end"), (base_x - 2, base_y + style.port_label_size + 2, "end")]
            elif anchor.side == "top":
                cands = [(base_x, base_y - 2, "middle"), (base_x + 4, base_y - 2, "start")]
            else:
                cands = [(base_x, base_y + style.port_label_size, "middle"), (base_x + 4, base_y + style.port_label_size, "start")]

            box = _try_place(
                [
                    TextBox(
                        x=cx + dx,
                        y=cy + dy,
                        text=text,
                        size=style.port_label_size,
                        role="port",
                        anchor=ca,
                        color=style.muted_text_color,
                        element_id=f"portlabel:{p.component.id}:{port.id}",
                    )
                    for cx, cy, ca in cands
                ],
                index,
            )
            if box is None:
                warnings.append(
                    f"port label '{text}' on {p.component.id}:{port.id} suppressed — no clear position"
                )
            else:
                out.append(box)
    return out


def _run_labels(
    routes: list[Route],
    pins: PinStore,
    profile: Profile,
    style: DiagramStyle,
    index: RectIndex,
    warnings: list[str],
) -> list[TextBox]:
    out: list[TextBox] = []
    for r in sorted(routes, key=lambda q: q.connection.id):
        segs = r.segments()
        if not segs:
            continue
        longest = max(range(len(segs)), key=lambda i: _length(segs[i]))
        (px, py), (qx, qy) = segs[longest]
        mx, my = (px + qx) / 2.0, (py + qy) / 2.0
        horizontal = abs(py - qy) < 0.01

        offset = pins.value(target_connection(r.connection.id), "label_offset", profile.id, None)
        dx = float(offset.get("dx", 0.0)) if isinstance(offset, dict) else 0.0
        dy = float(offset.get("dy", 0.0)) if isinstance(offset, dict) else 0.0

        if profile.show_designation and r.connection.designation:
            if horizontal:
                cands = [(mx, my - 3, "middle"), (mx, my + style.designation_size + 3, "middle")]
            else:
                cands = [(mx + 3, my, "start"), (mx - 3, my, "end")]
            box = _try_place(
                [
                    TextBox(
                        x=cx + dx,
                        y=cy + dy,
                        text=r.connection.designation,
                        size=style.designation_size,
                        role="designation",
                        anchor=ca,
                        weight=600,
                        element_id=f"designation:{r.connection.id}",
                    )
                    for cx, cy, ca in cands
                ],
                index,
            )
            if box is None:
                warnings.append(f"designation '{r.connection.designation}' on run '{r.connection.id}' suppressed")
            else:
                out.append(box)

        if profile.show_size:
            forced = pins.value(target_connection(r.connection.id), "size_label", profile.id, None)
            size_text = forced if isinstance(forced, str) else _size_text(r.connection, longest)
            if size_text:
                if horizontal:
                    cands = [(mx, my + style.designation_size + 4, "middle"), (mx, my - 4, "middle")]
                else:
                    cands = [(mx - 4, my + style.designation_size, "end"), (mx + 4, my + style.designation_size, "start")]
                box = _try_place(
                    [
                        TextBox(
                            x=cx + dx,
                            y=cy + dy,
                            text=size_text,
                            size=style.designation_size - 0.5,
                            role="size",
                            anchor=ca,
                            color=style.muted_text_color,
                            mono=True,
                            element_id=f"size:{r.connection.id}",
                        )
                        for cx, cy, ca in cands
                    ],
                    index,
                )
                if box is not None:
                    out.append(box)
    return out


def _size_text(conn: Connection, segment_index: int) -> str | None:
    if not conn.segments:
        return None
    seg = conn.segments[min(segment_index, len(conn.segments) - 1)]
    parts = [p for p in (seg.size, seg.material) if p]
    return " ".join(parts) if parts else None


def _length(seg: tuple[tuple[float, float], tuple[float, float]]) -> float:
    (x1, y1), (x2, y2) = seg
    return math.hypot(x2 - x1, y2 - y1)


def _elevation_axis(placed: list[Placed], style: DiagramStyle) -> list[TextBox]:
    out: list[TextBox] = []
    seen: set[float] = set()
    if not placed:
        return out
    left = min(p.x - p.w / 2 for p in placed) - 28.0
    for p in sorted(placed, key=lambda q: q.component.id):
        if p.component.elevation_mm is None or p.component.elevation_mm in seen:
            continue
        seen.add(p.component.elevation_mm)
        out.append(
            TextBox(
                x=left,
                y=p.y + style.legend_size / 3,
                text=f"{p.component.elevation_mm:.0f} mm",
                size=style.legend_size,
                role="axis",
                anchor="end",
                color=style.muted_text_color,
                mono=True,
            )
        )
    return out


def _legend(conns: list[Connection], style: DiagramStyle) -> list[LegendEntry]:
    keys: list[str] = []
    for conn in conns:
        key = conn.designation or conn.medium
        if key not in keys:
            keys.append(key)
    return [LegendEntry(key=k, label=k) for k in sorted(keys)]


def _bbox(
    placed: list[Placed],
    routes: list[Route],
    texts: list[TextBox],
    style: DiagramStyle,
) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for p in placed:
        x, y, w, h = p.rect()
        xs += [x, x + w]
        ys += [y, y + h]
    for r in routes:
        for x, y in r.points:
            xs.append(x)
            ys.append(y)
    for t in texts:
        x, y, w, h = t.rect()
        xs += [x, x + w]
        ys += [y, y + h]
    if not xs:
        return (0.0, 0.0, style.padding * 2, style.padding * 2)
    pad = style.padding
    x0, y0 = min(xs) - pad, min(ys) - pad
    x1, y1 = max(xs) + pad, max(ys) + pad
    return (round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2))
