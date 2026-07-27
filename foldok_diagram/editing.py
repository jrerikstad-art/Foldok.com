"""Canvas session — the user-facing editing API.

The whole point of this file: a gesture on the canvas becomes either

*  a graph edit (place, connect, delete, insert a fitting) — a change to what
   the installation *is*, or
*  a pin (move, rotate, waypoint, label nudge) — a change to how it is *drawn*.

Nothing in between, and geometry never leaks into the graph.  That separation is
what lets the same graph produce a wiring view and a piping view, lets a hand
adjustment survive a relayout, and makes ``release()`` a real undo rather than a
guess.

Every call appends an Edit to ``history``, so the document can show "what did a
human change" on a re-issue.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

from . import symbols as symbol_pack
from . import validate as validate_mod
from .layout import Layout, layout as compute_layout
from .model import Component, Connection, Endpoint, Port, Provenance, Segment
from .model import Graph
from .overrides import (
    GLOBAL_SCOPE,
    PinStore,
    target_component,
    target_connection,
    target_port_label,
)
from .profile import Profile
from .render import RenderResult, render_svg
from .style import DiagramStyle

EditKind = Literal["graph", "pin", "release", "lock"]


@dataclass
class Edit:
    kind: EditKind
    action: str
    target: str
    detail: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        bits = ", ".join(f"{k}={v}" for k, v in sorted(self.detail.items()))
        return f"{self.action} {self.target}" + (f" ({bits})" if bits else "")


class ConnectRefused(Exception):
    """Raised when a connect would produce an invalid graph."""


class DiagramSession:
    def __init__(
        self,
        graph: Graph,
        profile: Profile,
        style: DiagramStyle | None = None,
        pins: PinStore | None = None,
    ) -> None:
        self.graph = graph
        self.profile = profile
        self.style = style or DiagramStyle()
        self.pins = pins or PinStore()
        self.history: list[Edit] = []
        self._layout: Layout | None = None

    # -- derived ---------------------------------------------------------
    def invalidate(self) -> None:
        self._layout = None

    def layout(self) -> Layout:
        if self._layout is None:
            self._layout = compute_layout(self.graph, self.profile, self.style, self.pins)
        return self._layout

    def render(self, *, target_width_pt: float | None = None, show_handles: bool = False) -> RenderResult:
        return render_svg(
            self.layout(),
            self.style,
            target_width_pt=target_width_pt,
            title=self.graph.title or None,
            subtitle=self.graph.subtitle or None,
            show_handles=show_handles,
        )

    def validate(self) -> validate_mod.Report:
        return validate_mod.validate(self.graph, self.pins)

    def _log(self, kind: EditKind, action: str, target: str, **detail: Any) -> Edit:
        e = Edit(kind, action, target, detail)
        self.history.append(e)
        return e

    # ------------------------------------------------------------------
    # graph edits — what the installation is
    # ------------------------------------------------------------------
    def place(
        self,
        component: Component,
        *,
        x: float | None = None,
        y: float | None = None,
    ) -> Component:
        if self.graph.component(component.id) is not None:
            raise ValueError(f"component '{component.id}' already exists")
        self.graph.components.append(component)
        self.invalidate()
        self._log("graph", "place", target_component(component.id), type=component.type)
        if x is not None or y is not None:
            self.move(component.id, x, y, note="placed by hand")
        return component

    def connect(
        self,
        source: tuple[str, str],
        target: tuple[str, str],
        *,
        medium: str = "wire",
        designation: str | None = None,
        size: str | None = None,
        material: str | None = None,
        connection_id: str | None = None,
        flow: str = "none",
        provenance: Provenance | None = None,
    ) -> Connection:
        a = Endpoint(*source)
        b = Endpoint(*target)
        conn = Connection(
            id=connection_id or self._next_id("w", [c.id for c in self.graph.connections]),
            source=a,
            target=b,
            medium=medium,          # type: ignore[arg-type]
            designation=designation,
            flow=flow,              # type: ignore[arg-type]
            segments=[Segment(size=size, material=material)] if (size or material) else [Segment()],
            provenance=provenance or Provenance(source="user"),
        )
        self.graph.connections.append(conn)
        report = validate_mod.validate(self.graph)
        blocking = [i for i in report.errors if i.target in (conn.id, a.key(), b.key())]
        if blocking:
            self.graph.connections.remove(conn)
            raise ConnectRefused("; ".join(f"{i.message} — {i.fix}" for i in blocking))
        self.invalidate()
        self._log("graph", "connect", target_connection(conn.id),
                  **{"from": a.key(), "to": b.key(), "medium": medium})
        return conn

    def disconnect(self, connection_id: str) -> bool:
        conn = self.graph.connection(connection_id)
        if conn is None:
            return False
        self.graph.connections.remove(conn)
        self.pins.release_target(target_connection(connection_id), force=True)
        self.invalidate()
        self._log("graph", "disconnect", target_connection(connection_id))
        return True

    def delete_component(self, component_id: str) -> list[str]:
        comp = self.graph.component(component_id)
        if comp is None:
            return []
        removed = [
            c.id
            for c in list(self.graph.connections)
            if component_id in (c.source.component_id, c.target.component_id)
        ]
        for cid in removed:
            self.disconnect(cid)
        self.graph.components.remove(comp)
        self.pins.release_target(target_component(component_id), force=True)
        self.invalidate()
        self._log("graph", "delete", target_component(component_id), removed_runs=len(removed))
        return removed

    def insert_fitting(
        self,
        connection_id: str,
        fitting_type: str = "tee_equal",
        *,
        fitting_id: str | None = None,
        tag: str | None = None,
        size: str | None = None,
        material: str | None = None,
    ) -> tuple[Component, list[Connection]]:
        """Split a run with a real part.

        This is how a branch is made.  A pipe never branches by touching another
        pipe; a tee is a component with three ports, a size and a material, and
        it appears in the BOM because of this call.
        """
        conn = self.graph.connection(connection_id)
        if conn is None:
            raise ValueError(f"no connection '{connection_id}'")
        sym = symbol_pack.get(fitting_type)
        if sym.id == "fallback":
            raise ValueError(f"unknown fitting type '{fitting_type}'")

        fid = fitting_id or self._next_id("F", [c.id for c in self.graph.components])
        kind = "fluid" if conn.medium in ("pipe", "duct") else "electrical"
        fitting = Component(
            id=fid,
            type=fitting_type,
            domain="piping" if kind == "fluid" else "electrical",
            role="fitting",
            label=fitting_type.replace("_", " "),
            tag=tag,
            specs={k: v for k, v in (("size", size), ("material", material)) if v},
            ports=[
                Port(id="a", name="in", side="left", kind=kind, order=0),
                Port(id="b", name="out", side="right", kind=kind, order=1),
                Port(id="c", name="branch", side="bottom", kind=kind, order=2),
            ],
            provenance=Provenance(source="user", note=f"inserted into run {connection_id}"),
        )
        self.graph.components.append(fitting)

        seg = conn.segments[0] if conn.segments else Segment()
        upstream = Connection(
            id=f"{conn.id}.1",
            source=conn.source,
            target=Endpoint(fid, "a"),
            medium=conn.medium,
            designation=conn.designation,
            flow=conn.flow,
            segments=[Segment(size=seg.size, material=seg.material)],
            provenance=conn.provenance,
        )
        downstream = Connection(
            id=f"{conn.id}.2",
            source=Endpoint(fid, "b"),
            target=conn.target,
            medium=conn.medium,
            designation=conn.designation,
            flow=conn.flow,
            segments=[Segment(size=seg.size, material=seg.material)],
            provenance=conn.provenance,
        )
        self.graph.connections.remove(conn)
        self.graph.connections.extend([upstream, downstream])
        self.pins.release_target(target_connection(conn.id), force=True)
        self.invalidate()
        self._log("graph", "insert_fitting", target_component(fid),
                  split=connection_id, into=f"{upstream.id}+{downstream.id}")
        return fitting, [upstream, downstream]

    def set_segment(
        self,
        connection_id: str,
        index: int,
        *,
        size: str | None = None,
        material: str | None = None,
        label: str | None = None,
    ) -> Segment:
        conn = self.graph.connection(connection_id)
        if conn is None:
            raise ValueError(f"no connection '{connection_id}'")
        while len(conn.segments) <= index:
            conn.segments.append(Segment())
        seg = conn.segments[index]
        if size is not None:
            seg.size = size
        if material is not None:
            seg.material = material
        if label is not None:
            seg.label = label
        self.invalidate()
        self._log("graph", "set_segment", target_connection(connection_id), index=index, size=seg.size)
        return seg

    # ------------------------------------------------------------------
    # pins — how it is drawn
    # ------------------------------------------------------------------
    def move(
        self,
        component_id: str,
        x: float | None,
        y: float | None,
        *,
        scope: str | None = None,
        note: str | None = None,
    ) -> None:
        """Pin position.  Pass x=None to leave that axis automatic."""
        target = target_component(component_id)
        scope = self.profile.id if scope is None else scope
        current = self.pins.value(target, "position", self.profile.id, {}) or {}
        value = {
            "x": current.get("x") if x is None else round(float(x), 2),
            "y": current.get("y") if y is None else round(float(y), 2),
        }
        self.pins.pin(target, "position", value, scope=scope, note=note)
        self.invalidate()
        self._log("pin", "move", target, **{k: v for k, v in value.items() if v is not None})

    def nudge(self, component_id: str, dx: float = 0.0, dy: float = 0.0) -> None:
        placed = self._placed(component_id)
        self.move(component_id, placed.x + dx, placed.y + dy, note="nudged")

    def rotate(self, component_id: str, degrees: int) -> None:
        target = target_component(component_id)
        value = (int(degrees) // 90 * 90) % 360
        self.pins.pin(target, "rotation", value, scope=self.profile.id)
        self.invalidate()
        self._log("pin", "rotate", target, degrees=value)

    def set_column(self, component_id: str, column: int) -> None:
        target = target_component(component_id)
        self.pins.pin(target, "column", int(column), scope=self.profile.id)
        self.invalidate()
        self._log("pin", "set_column", target, column=int(column))

    def hide(self, component_id: str, hidden: bool = True) -> None:
        target = target_component(component_id)
        self.pins.pin(target, "hidden", bool(hidden), scope=self.profile.id)
        self.invalidate()
        self._log("pin", "hide" if hidden else "show", target)

    def add_waypoint(self, connection_id: str, x: float, y: float) -> list[dict[str, float]]:
        """Pull a run through a point.

        Insertion order is decided by arc position along the current route, so
        dropping a handle where you clicked does what you expect and the result
        does not depend on the order the handles were created.
        """
        base = self._base_route(connection_id)
        existing = list(self.pins.value(target_connection(connection_id), "waypoints", self.profile.id, []) or [])
        new = {"x": round(float(x), 2), "y": round(float(y), 2)}
        merged = existing + [new]
        # Order along the ORIGINAL auto route, not the current one: otherwise the
        # result depends on which handle was dropped first.
        # Ties (two handles projecting to the same point on the base route) are
        # broken by coordinate, never by insertion order.
        merged.sort(key=lambda w: (_arc_position(base.points, (w["x"], w["y"])), w["x"], w["y"]))
        self.pins.pin(target_connection(connection_id), "waypoints", merged, scope=self.profile.id)
        self.invalidate()
        self._log("pin", "add_waypoint", target_connection(connection_id), count=len(merged))
        return merged

    def move_waypoint(self, connection_id: str, index: int, x: float, y: float) -> list[dict[str, float]]:
        target = target_connection(connection_id)
        pinned = list(self.pins.value(target, "waypoints", self.profile.id, []) or [])
        if not pinned:
            # first drag of an auto-routed corner: adopt the computed interior
            route = self._route(connection_id)
            pinned = [{"x": px, "y": py} for px, py in route.points[1:-1]]
        if not (0 <= index < len(pinned)):
            raise IndexError(f"waypoint {index} does not exist on '{connection_id}'")
        pinned[index] = {"x": round(float(x), 2), "y": round(float(y), 2)}
        self.pins.pin(target, "waypoints", pinned, scope=self.profile.id)
        self.invalidate()
        self._log("pin", "move_waypoint", target, index=index)
        return pinned

    def clear_waypoints(self, connection_id: str) -> bool:
        released = self.pins.release(target_connection(connection_id), "waypoints", scope=self.profile.id)
        self.invalidate()
        self._log("release", "clear_waypoints", target_connection(connection_id), released=released)
        return released

    def nudge_label(self, target: str, dx: float, dy: float) -> None:
        current = self.pins.value(target, "label_offset", self.profile.id, {}) or {}
        value = {
            "dx": round(float(current.get("dx", 0.0)) + dx, 2),
            "dy": round(float(current.get("dy", 0.0)) + dy, 2),
        }
        self.pins.pin(target, "label_offset", value, scope=self.profile.id)
        self.invalidate()
        self._log("pin", "nudge_label", target, **value)

    def set_label_side(self, component_id: str, side: str) -> None:
        if side not in ("above", "below", "left", "right"):
            raise ValueError("side must be above/below/left/right")
        self.pins.pin(target_component(component_id), "label_side", side, scope=self.profile.id)
        self.invalidate()
        self._log("pin", "set_label_side", target_component(component_id), side=side)

    def style_override(self, target: str, tokens: dict[str, Any]) -> None:
        """Per-element escape hatch.  Use sparingly; the style spec is policy."""
        self.pins.pin(target, "style", dict(sorted(tokens.items())), scope=self.profile.id)
        self.invalidate()
        self._log("pin", "style_override", target, tokens=len(tokens))

    def force_size_label(self, connection_id: str, text: str) -> None:
        self.pins.pin(target_connection(connection_id), "size_label", text, scope=self.profile.id)
        self.invalidate()
        self._log("pin", "force_size_label", target_connection(connection_id), text=text)

    def pin_port_label(self, component_id: str, port_id: str, dx: float, dy: float) -> None:
        self.nudge_label(target_port_label(component_id, port_id), dx, dy)

    # -- give control back ----------------------------------------------
    def release(self, target: str, prop: str, *, force: bool = False) -> bool:
        released = self.pins.release(target, prop, scope=self.profile.id, force=force)
        if not released:
            released = self.pins.release(target, prop, scope=GLOBAL_SCOPE, force=force)
        self.invalidate()
        self._log("release", "release", target, prop=prop, released=released)
        return released

    def release_all(self, target: str, *, force: bool = False) -> int:
        n = self.pins.release_target(target, force=force)
        self.invalidate()
        self._log("release", "release_all", target, count=n)
        return n

    def reset_to_auto(self, *, force: bool = False) -> int:
        """Drop every pin in this profile.  The nuclear 'let the engine do it'."""
        n = 0
        for pin in self.pins.for_profile(self.profile.id):
            if self.pins.release(pin.target, pin.prop, scope=pin.scope, force=force):
                n += 1
        self.invalidate()
        self._log("release", "reset_to_auto", self.profile.id, count=n)
        return n

    def lock(self, target: str, prop: str, locked: bool = True) -> bool:
        ok = self.pins.set_lock(target, prop, locked, scope=self.profile.id)
        if not ok:
            ok = self.pins.set_lock(target, prop, locked, scope=GLOBAL_SCOPE)
        self._log("lock", "lock" if locked else "unlock", target, prop=prop, ok=ok)
        return ok

    def lock_figure(self) -> int:
        """Freeze every user pin — for a signed-off figure."""
        n = 0
        for pin in self.pins.user_pins():
            if self.pins.set_lock(pin.target, pin.prop, True, scope=pin.scope):
                n += 1
        self._log("lock", "lock_figure", self.graph.id, count=n)
        return n

    # -- helpers ---------------------------------------------------------
    def _placed(self, component_id: str):
        for p in self.layout().placed:
            if p.component.id == component_id:
                return p
        raise ValueError(f"'{component_id}' is not visible in profile '{self.profile.id}'")

    def _route(self, connection_id: str):
        for r in self.layout().routes:
            if r.connection.id == connection_id:
                return r
        raise ValueError(f"run '{connection_id}' is not visible in profile '{self.profile.id}'")

    def _base_route(self, connection_id: str):
        """The route this run would take with no waypoints pinned."""
        target = target_connection(connection_id)
        stripped = PinStore(
            [p for p in self.pins.all() if not (p.target == target and p.prop == "waypoints")]
        )
        lay = compute_layout(self.graph, self.profile, self.style, stripped)
        for r in lay.routes:
            if r.connection.id == connection_id:
                return r
        raise ValueError(f"run '{connection_id}' is not visible in profile '{self.profile.id}'")

    @staticmethod
    def _next_id(prefix: str, existing: list[str]) -> str:
        n = 1
        used = set(existing)
        while f"{prefix}{n}" in used:
            n += 1
        return f"{prefix}{n}"


def _arc_position(points: list[tuple[float, float]], pt: tuple[float, float]) -> float:
    """Distance along the polyline of the closest projection of ``pt``."""
    best = (float("inf"), 0.0)
    travelled = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        dx, dy = x2 - x1, y2 - y1
        seg_len = math.hypot(dx, dy)
        if seg_len == 0:
            continue
        t = ((pt[0] - x1) * dx + (pt[1] - y1) * dy) / (seg_len * seg_len)
        t = max(0.0, min(1.0, t))
        px, py = x1 + dx * t, y1 + dy * t
        dist = math.hypot(pt[0] - px, pt[1] - py)
        if dist < best[0]:
            best = (dist, travelled + seg_len * t)
        travelled += seg_len
    return best[1]
