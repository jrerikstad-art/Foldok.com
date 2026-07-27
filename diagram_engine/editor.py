"""Diagram canvas — graph editor with live DiagramEngine preview.

Canvas mutates the graph only. Engine owns symbols, routing, style, SVG.
Wire paths are never freehand ink.
"""
from __future__ import annotations

import re
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

from artifact_engine.diagram_style import DiagramStyle, get_diagram_style

from .graph import normalize_graph, validate_graph
from .hit_test import HitTestIndex, build_hit_index, snap_port_at
from .manual_layout import auto_spread_positions, ensure_positions, render_manual_diagram
from .paint import paint as get_paint
from .symbols import get_symbol
from .visual_qa import visual_qa_svg

MODES = frozenset({"select", "place", "connect", "pan", "drag"})
Listener = Callable[["DiagramDocument"], None]


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class ViewState:
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def to_dict(self) -> dict:
        return {"zoom": self.zoom, "pan": {"x": self.pan_x, "y": self.pan_y}}


@dataclass
class SelectionState:
    component_ids: list[str] = field(default_factory=list)
    connection_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "component_ids": list(self.component_ids),
            "connection_ids": list(self.connection_ids),
        }


@dataclass
class InteractionState:
    mode: str = "select"
    draft: dict | None = None  # PlaceDraft | ConnectDraft | DragDraft

    def to_dict(self) -> dict:
        return {"mode": self.mode, "draft": deepcopy(self.draft)}


@dataclass
class DiagramDocument:
    """One source of truth for canvas + document figure sync."""

    graph: dict = field(default_factory=lambda: {
        "type": "piping", "domain": "piping",
        "components": [], "connections": [],
        "layout_mode": "manual",
    })
    view: ViewState = field(default_factory=ViewState)
    selection: SelectionState = field(default_factory=SelectionState)
    interaction: InteractionState = field(default_factory=InteractionState)
    profile: str = "piping"
    style_id: str = "engineering_default"
    title: str = "Diagram"
    svg: str = ""
    revision: int = 0

    def to_dict(self) -> dict:
        return {
            "graph": deepcopy(self.graph),
            "view": self.view.to_dict(),
            "selection": self.selection.to_dict(),
            "interaction": self.interaction.to_dict(),
            "profile": self.profile,
            "style_id": self.style_id,
            "title": self.title,
            "svg": self.svg,
            "revision": self.revision,
        }

    @classmethod
    def from_graph(
        cls,
        graph: dict,
        *,
        profile: str | None = None,
        style_id: str = "engineering_default",
        title: str | None = None,
    ) -> "DiagramDocument":
        g = normalize_graph(deepcopy(graph))
        g["layout_mode"] = g.get("layout_mode") or "manual"
        prof = profile or g.get("type") or "piping"
        return cls(
            graph=g,
            profile=prof,
            style_id=style_id,
            title=title or g.get("title") or "Diagram",
        )


class DiagramCanvasEditor:
    """Event API: mutations → validate → layout → render_svg."""

    def __init__(
        self,
        doc: DiagramDocument | None = None,
        *,
        style: DiagramStyle | str | None = None,
        on_change: Listener | None = None,
    ):
        self.doc = doc or DiagramDocument()
        if isinstance(style, str):
            self.style_id = style
            self._style = get_diagram_style(style)
        elif style is not None:
            self._style = style
            self.style_id = style.id
        else:
            self.style_id = self.doc.style_id
            self._style = get_diagram_style(self.style_id)
        self.doc.style_id = self.style_id
        self._listeners: list[Listener] = []
        if on_change:
            self._listeners.append(on_change)
        self._hit: HitTestIndex | None = None
        # Initial render
        self.commit(notify=False)

    # ── view / selection / mode ───────────────────────────────────────

    def set_view(self, *, pan: dict | None = None, zoom: float | None = None) -> DiagramDocument:
        if pan:
            self.doc.view.pan_x = float(pan.get("x", self.doc.view.pan_x))
            self.doc.view.pan_y = float(pan.get("y", self.doc.view.pan_y))
        if zoom is not None:
            self.doc.view.zoom = max(0.25, min(4.0, float(zoom)))
        self._notify()
        return self.doc

    def set_selection(
        self,
        *,
        component_ids: list[str] | None = None,
        connection_ids: list[str] | None = None,
    ) -> DiagramDocument:
        if component_ids is not None:
            self.doc.selection.component_ids = list(component_ids)
        if connection_ids is not None:
            self.doc.selection.connection_ids = list(connection_ids)
        self._notify()
        return self.doc

    def set_mode(self, mode: str) -> DiagramDocument:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {sorted(MODES)}")
        self.doc.interaction.mode = mode
        self.doc.interaction.draft = None
        self._notify()
        return self.doc

    def cancel_draft(self) -> DiagramDocument:
        self.doc.interaction.draft = None
        if self.doc.interaction.mode in ("place", "connect", "drag"):
            self.doc.interaction.mode = "select"
        self._notify()
        return self.doc

    # ── graph mutations ───────────────────────────────────────────────

    def place_component(
        self,
        symbol_type: str,
        position: dict,
        *,
        rotation: int = 0,
        tag: str | None = None,
        label: str | None = None,
        component_id: str | None = None,
        domain: str | None = None,
    ) -> dict:
        """Place symbol → Component. Ports come from symbol library."""
        lib = get_symbol(symbol_type) or {}
        if not lib:
            raise ValueError(f"Unknown symbol type: {symbol_type}")
        cid = component_id or _new_id(re.sub(r"[^a-z0-9]+", "", symbol_type.lower())[:8] or "c")
        # Unique id
        used = {c.get("id") for c in self.doc.graph.get("components") or []}
        base = cid
        n = 2
        while cid in used:
            cid = f"{base}_{n}"
            n += 1
        pos = self._snap(position)
        comp = {
            "id": cid,
            "type": symbol_type,
            "symbol": symbol_type,
            "domain": domain or lib.get("domain") or self.doc.graph.get("domain") or "piping",
            "label": label or lib.get("label") or symbol_type,
            "tag": tag or cid.upper(),
            "position": {"x": pos["x"], "y": pos["y"]},
            "rotation": int(rotation) % 360,
            "ports": deepcopy(list(lib.get("ports") or [])),
            "specs": {},
        }
        self.doc.graph.setdefault("components", []).append(comp)
        self.doc.selection.component_ids = [cid]
        self.doc.selection.connection_ids = []
        self.doc.interaction.mode = "select"
        self.doc.interaction.draft = None
        self.commit()
        return comp

    def move_components(self, ids: list[str], new_positions: dict[str, dict]) -> None:
        by = {c["id"]: c for c in self.doc.graph.get("components") or [] if c.get("id")}
        for cid in ids:
            c = by.get(cid)
            if not c:
                continue
            raw = new_positions.get(cid) or {}
            snapped = self._snap(raw if "x" in raw else c.get("position") or {"x": 0, "y": 0})
            if "x" in raw:
                snapped = self._snap({"x": raw["x"], "y": raw.get("y", 0)})
            c["position"] = {"x": snapped["x"], "y": snapped["y"]}
        self.commit()

    def move_component(self, component_id: str, x: float, y: float) -> dict:
        """Contract helper: update position only (grid-snapped); wires re-route on commit."""
        self.move_components([component_id], {component_id: {"x": x, "y": y}})
        for c in self.doc.graph.get("components") or []:
            if c.get("id") == component_id:
                return c
        raise ValueError(f"Unknown component {component_id}")

    def connect_ports(
        self,
        from_ref: str | dict,
        to_ref: str | dict,
        medium: str | None = None,
        **kwargs: Any,
    ) -> dict:
        """Contract alias of connect() — validates media, then engine routes."""
        return self.connect(from_ref, to_ref, medium=medium, **kwargs)

    def refresh(self) -> DiagramDocument:
        """Re-layout edges + labels from current graph; return live document."""
        return self.commit()

    def rotate_components(self, ids: list[str], degrees: int = 90) -> None:
        by = {c["id"]: c for c in self.doc.graph.get("components") or [] if c.get("id")}
        step = int(degrees)
        if step % 90 != 0:
            step = 90 if step > 0 else -90
        for cid in ids:
            c = by.get(cid)
            if not c:
                continue
            c["rotation"] = (int(c.get("rotation") or 0) + step) % 360
        self.commit()

    def connect(
        self,
        from_port: str | dict,
        to_port: str | dict,
        *,
        medium: str | None = None,
        attributes: dict | None = None,
        connection_id: str | None = None,
    ) -> dict:
        """Port → port. Validates medium vs port kinds before commit."""
        from .graph import normalize_endpoint

        fr = normalize_endpoint(from_port)
        to = normalize_endpoint(to_port)
        if not fr or not to:
            raise ValueError("from_port and to_port required (component.port)")
        if fr == to:
            raise ValueError("Cannot connect a port to itself")

        med = medium or self._default_medium(fr, to)
        edge = {
            "id": connection_id or _new_id("w"),
            "from": fr,
            "to": to,
            "medium": med,
            "attributes": dict(attributes or {}),
        }
        # Probe validation on a copy
        probe = deepcopy(self.doc.graph)
        probe.setdefault("connections", []).append(edge)
        violations = validate_graph(probe)
        # Filter to this edge only for hard fail
        hard = [v for v in violations if edge["id"] in v or "incompatible" in v or "not in allowed" in v]
        if hard:
            raise ValueError("; ".join(hard))
        # Soft: missing ports
        missing = [v for v in violations if "not found" in v]
        if missing:
            raise ValueError("; ".join(missing))

        self.doc.graph.setdefault("connections", []).append(edge)
        self.doc.selection.connection_ids = [edge["id"]]
        self.doc.selection.component_ids = []
        self.doc.interaction.draft = None
        self.doc.interaction.mode = "select"
        self.commit()
        return edge

    def disconnect(self, connection_id: str) -> None:
        edges = self.doc.graph.get("connections") or []
        self.doc.graph["connections"] = [e for e in edges if e.get("id") != connection_id]
        self.doc.selection.connection_ids = [
            i for i in self.doc.selection.connection_ids if i != connection_id
        ]
        self.commit()

    def reconnect(
        self,
        connection_id: str,
        *,
        from_port: str | dict | None = None,
        to_port: str | dict | None = None,
    ) -> dict:
        from .graph import normalize_endpoint

        edges = self.doc.graph.get("connections") or []
        edge = next((e for e in edges if e.get("id") == connection_id), None)
        if not edge:
            raise ValueError(f"Unknown connection {connection_id}")
        if from_port is not None:
            edge["from"] = normalize_endpoint(from_port)
        if to_port is not None:
            edge["to"] = normalize_endpoint(to_port)
        # Re-validate via temporary disconnect + connect semantics
        probe = deepcopy(self.doc.graph)
        violations = [v for v in validate_graph(probe) if connection_id in v or "not found" in v or "incompatible" in v]
        if violations:
            raise ValueError("; ".join(violations))
        self.commit()
        return edge

    def delete_selection(self) -> None:
        comps = set(self.doc.selection.component_ids)
        conns = set(self.doc.selection.connection_ids)
        if comps:
            self.doc.graph["components"] = [
                c for c in (self.doc.graph.get("components") or [])
                if c.get("id") not in comps
            ]
            # Drop incident connections
            kept = []
            for e in self.doc.graph.get("connections") or []:
                fr = (e.get("from") or {}).get("component_id")
                to = (e.get("to") or {}).get("component_id")
                if fr in comps or to in comps:
                    continue
                kept.append(e)
            self.doc.graph["connections"] = kept
        if conns:
            self.doc.graph["connections"] = [
                e for e in (self.doc.graph.get("connections") or [])
                if e.get("id") not in conns
            ]
        self.doc.selection.component_ids = []
        self.doc.selection.connection_ids = []
        self.commit()

    def delete(self, selection: dict | None = None) -> None:
        if selection:
            self.set_selection(
                component_ids=selection.get("component_ids") or [],
                connection_ids=selection.get("connection_ids") or [],
            )
        self.delete_selection()

    def auto_arrange(self) -> DiagramDocument:
        """Engine proposes positions; user can still drag after."""
        g = deepcopy(self.doc.graph)
        for c in g.get("components") or []:
            if isinstance(c, dict):
                c.pop("position", None)
        g = ensure_positions(g, profile=self.doc.profile, style=self._style)
        self.doc.graph = g
        self.doc.graph["layout_mode"] = "manual"
        self.commit()
        return self.doc

    def auto_spread(self) -> DiagramDocument:
        """Nudge overlapping components on the grid; topology unchanged."""
        self.doc.graph = auto_spread_positions(
            self.doc.graph, style=self._style, profile=self.doc.profile,
        )
        self.doc.graph["layout_mode"] = "manual"
        self.commit()
        return self.doc

    def snap_port(
        self,
        x: float,
        y: float,
        *,
        from_port: str | None = None,
    ) -> dict | None:
        """Nearest legal port within DiagramStyle.ports.snap_radius."""
        legal = None
        if from_port:
            legal = [t["ref"] for t in self.legal_connect_targets(from_port)]
        return snap_port_at(
            self.doc.graph,
            x,
            y,
            style=self._style,
            from_port=from_port,
            legal_only=legal,
        )

    def update_component(self, component_id: str, **fields) -> dict:
        """Property panel: tag, label, specs, …"""
        for c in self.doc.graph.get("components") or []:
            if c.get("id") != component_id:
                continue
            for k, v in fields.items():
                if k in ("id", "ports") and v is None:
                    continue
                if k == "specs" and isinstance(v, dict):
                    c.setdefault("specs", {}).update(v)
                elif k != "id":
                    c[k] = v
            self.commit()
            return c
        raise ValueError(f"Unknown component {component_id}")

    # ── connect draft helpers (UI) ────────────────────────────────────

    def begin_connect(self, from_port: str) -> DiagramDocument:
        self.doc.interaction.mode = "connect"
        self.doc.interaction.draft = {"kind": "connect", "from": from_port, "to": None}
        self._notify()
        return self.doc

    def preview_connect_at(self, x: float, y: float) -> dict | None:
        """Pointer-move while connecting: highlight nearest legal port in snap_radius."""
        draft = self.doc.interaction.draft or {}
        if draft.get("kind") != "connect" or not draft.get("from"):
            return self.snap_port(x, y)
        hit = self.snap_port(x, y, from_port=draft["from"])
        self.doc.interaction.draft = {**draft, "hover": hit, "cursor": {"x": x, "y": y}}
        self._notify()
        return hit

    def finish_connect_at(self, x: float, y: float, *, medium: str | None = None) -> dict | None:
        """Pointer-up: commit to snapped port, or cancel if none in range."""
        draft = self.doc.interaction.draft or {}
        from_port = draft.get("from")
        if not from_port:
            self.cancel_draft()
            return None
        hit = self.snap_port(x, y, from_port=from_port)
        if not hit:
            self.cancel_draft()
            return None
        return self.connect(from_port, hit["id"], medium=medium)

    def legal_connect_targets(self, from_port: str) -> list[dict]:
        """Ports that would pass validation if connected from from_port."""
        from .graph import normalize_endpoint

        fr = normalize_endpoint(from_port)
        if not fr:
            return []
        out = []
        for c in self.doc.graph.get("components") or []:
            for port in c.get("ports") or []:
                to_ref = f"{c['id']}.{port['id']}"
                if to_ref == from_port:
                    continue
                probe = deepcopy(self.doc.graph)
                probe.setdefault("connections", []).append({
                    "id": "_probe",
                    "from": fr,
                    "to": {"component_id": c["id"], "port_id": port["id"]},
                    "medium": self._default_medium(fr, {"component_id": c["id"], "port_id": port["id"]}),
                    "attributes": {},
                })
                bad = [
                    v for v in validate_graph(probe)
                    if "_probe" in v and ("incompatible" in v or "not in allowed" in v or "not found" in v)
                ]
                if not bad:
                    out.append({
                        "component_id": c["id"],
                        "port_id": port["id"],
                        "ref": to_ref,
                        "side": port.get("side"),
                        "kind": port.get("kind"),
                    })
        return out

    # ── hit testing ───────────────────────────────────────────────────

    def hit_test(self, x: float, y: float) -> dict | None:
        if self._hit is None:
            self._rebuild_hit_index()
        return self._hit.hit(x, y) if self._hit else None

    def hotspots(self) -> list[dict]:
        if self._hit is None:
            self._rebuild_hit_index()
        return self._hit.hotspots if self._hit else []

    # ── commit / render ───────────────────────────────────────────────

    def commit(self, *, notify: bool = True) -> DiagramDocument:
        """validate → layout (edge routes) → render_svg → notify."""
        domain = (self.doc.graph.get("domain") or "").lower()
        if domain == "electrical" or self.doc.profile in ("wiring", "single_line"):
            from .electrical import normalize_electrical_graph
            self.doc.graph = normalize_electrical_graph(self.doc.graph)
        else:
            self.doc.graph = normalize_graph(
                self.doc.graph,
                default_type=self.doc.profile,
                default_domain=self.doc.graph.get("domain"),
            )
        self.doc.graph["layout_mode"] = "manual"
        self.doc.graph["type"] = self.doc.profile
        if self.doc.title:
            self.doc.graph["title"] = self.doc.title

        violations = validate_graph(self.doc.graph)
        self.doc.graph["_validation"] = {"ok": not violations, "violations": violations}

        self.doc.svg = render_manual_diagram(
            self.doc.graph,
            profile=self.doc.profile,
            title=self.doc.title,
            style=self._style,
        )
        self.doc.revision += 1
        self._rebuild_hit_index()
        if notify:
            self._notify()
        return self.doc

    def figure_payload(self) -> dict:
        """Payload for EngineeringFigure / DiagramBlock sync."""
        return {
            "type": "diagram",
            "svg": self.doc.svg,
            "title": self.doc.title,
            "caption": self.doc.title,
            "diagram_type": self.doc.profile,
            "style_id": self.doc.style_id,
            "graph_id": self.doc.graph.get("id"),
            "graph": deepcopy(self.doc.graph),
            "revision": self.doc.revision,
            "visual_qa": visual_qa_svg(self.doc.svg, graph=self.doc.graph),
        }

    # ── internals ─────────────────────────────────────────────────────

    def _snap(self, position: dict) -> dict:
        step = float(self._style.grid.step) if self._style.grid.snap else 1.0
        x = float(position.get("x", 0))
        y = float(position.get("y", 0))
        if self._style.grid.snap and step > 0:
            x = round(x / step) * step
            y = round(y / step) * step
        return {"x": x, "y": y}

    def _default_medium(self, fr: dict, to: dict) -> str:
        by = {c["id"]: c for c in self.doc.graph.get("components") or [] if c.get("id")}
        c0 = by.get(fr.get("component_id") or "")
        port = None
        if c0:
            for p in c0.get("ports") or []:
                if p.get("id") == fr.get("port_id"):
                    port = p
                    break
        kind = (port or {}).get("kind") or ""
        if kind == "electrical":
            return "wire"
        if kind == "mechanical":
            return "shaft"
        if kind == "signal":
            return "signal"
        return "pipe"

    def _rebuild_hit_index(self) -> None:
        self._hit = build_hit_index(self.doc.graph, style=self._style)

    def _notify(self) -> None:
        for fn in self._listeners:
            try:
                fn(self.doc)
            except Exception:
                pass

    def on_change(self, listener: Listener) -> None:
        self._listeners.append(listener)
