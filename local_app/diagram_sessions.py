"""In-memory Foldok diagram sessions (WO 0.63) — pins, not geometry on the graph."""
from __future__ import annotations

import uuid
from typing import Any

from foldok_diagram import (
    ConnectRefused,
    DiagramSession,
    DiagramStyle,
    PinStore,
    figure,
)
from foldok_diagram import profile as profiles
from foldok_diagram.examples import plumbing_supply, water_heater_no
from foldok_diagram.migrate import migrate
from foldok_diagram.model import Graph

_SESSIONS: dict[str, dict[str, Any]] = {}

_FIXTURES = {
    "water_heater": water_heater_no,
    "water_heater_no": water_heater_no,
    "plumbing_supply": plumbing_supply,
    "plumbing": plumbing_supply,
}

_PROFILE_MAP = {
    "wiring": profiles.WIRING,
    "single_line": profiles.SINGLE_LINE,
    "piping": profiles.PIPING,
    "drainage_riser": getattr(profiles, "DRAINAGE_RISER", profiles.PIPING),
}


def resolve_profile(name: str | None):
    key = (name or "wiring").strip().lower()
    return _PROFILE_MAP.get(key, profiles.WIRING)


def _fixture_graph(name: str) -> Graph:
    key = (name or "water_heater").strip().lower()
    factory = _FIXTURES.get(key) or water_heater_no
    return factory()


def create_session(
    fixture: str = "water_heater",
    *,
    profile: str | None = None,
    target_width_pt: float = 420.0,
    project_dir: str | None = None,
    graph_id: str | None = None,
) -> dict:
    graph = _fixture_graph(fixture)
    if not graph.jurisdiction:
        graph.jurisdiction = ""
    prof = resolve_profile(profile or ("piping" if "plumb" in (fixture or "") else "wiring"))
    session = DiagramSession(graph, prof, DiagramStyle(), PinStore())
    sid = uuid.uuid4().hex[:12]
    _SESSIONS[sid] = {
        "session": session,
        "fixture": fixture,
        "target_width_pt": float(target_width_pt),
        "project_dir": project_dir,
        "graph_id": graph_id or graph.id or fixture,
        "migration_notes": [],
    }
    return session_payload(sid)


def open_graph_dict(
    doc: dict,
    *,
    profile: str | None = None,
    pins_lines: list[str] | None = None,
    target_width_pt: float = 420.0,
    project_dir: str | None = None,
    graph_id: str | None = None,
) -> dict:
    pins = PinStore()
    if pins_lines:
        pins = PinStore.from_jsonl("\n".join(pins_lines))
    graph, pins, notes = migrate(doc, pins)
    prof = resolve_profile(profile or "wiring")
    session = DiagramSession(graph, prof, DiagramStyle(), pins)
    sid = uuid.uuid4().hex[:12]
    _SESSIONS[sid] = {
        "session": session,
        "fixture": "custom",
        "target_width_pt": float(target_width_pt),
        "project_dir": project_dir,
        "graph_id": graph_id or graph.id or "diagram",
        "migration_notes": notes,
    }
    return session_payload(sid)


def get_bundle(session_id: str) -> dict[str, Any] | None:
    return _SESSIONS.get(session_id)


def get_session(session_id: str) -> DiagramSession | None:
    b = _SESSIONS.get(session_id)
    return b["session"] if b else None


# Back-compat alias used by older callers
def get_editor(session_id: str) -> DiagramSession | None:
    return get_session(session_id)


def drop_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)


def render_fixture_svg(fixture: str = "water_heater", *, profile: str | None = None, target_width_pt: float = 420.0) -> dict:
    graph = _fixture_graph(fixture)
    prof = resolve_profile(profile or ("piping" if "plumb" in (fixture or "") else "wiring"))
    res = figure(graph, prof, DiagramStyle(), target_width_pt=target_width_pt)
    return {
        "fixture": fixture,
        "title": graph.title or fixture,
        "svg": res.svg,
        "bytes": len(res.svg.encode("utf-8")),
        "scale": res.scale,
        "profile": prof.id,
        "spec": graph.to_dict(),
    }


def session_payload(session_id: str, *, show_handles: bool = True) -> dict[str, Any]:
    bundle = _SESSIONS[session_id]
    session: DiagramSession = bundle["session"]
    width = bundle["target_width_pt"]
    rendered = session.render(target_width_pt=width, show_handles=show_handles)
    export = session.render(target_width_pt=width, show_handles=False)
    report = session.validate()
    issues = [
        {
            "severity": i.level,
            "code": i.code,
            "message": i.message,
            "fix": i.fix,
            "target": i.target,
        }
        for i in report.issues
    ]
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    return {
        "session_id": session_id,
        "title": session.graph.title or bundle.get("graph_id"),
        "profile": session.profile.id,
        "graph_id": bundle.get("graph_id"),
        "fixture": bundle.get("fixture"),
        "revision": getattr(session.graph, "revision", None) or "A",
        "jurisdiction": session.graph.jurisdiction or "",
        "svg": rendered.svg,
        "export_svg": export.svg,
        "bytes": len(rendered.svg.encode("utf-8")),
        "scale": rendered.scale,
        "graph": session.graph.to_dict(),
        "pins_jsonl": session.pins.to_jsonl(),
        "history": [str(e) for e in session.history[-40:]],
        "migration_notes": list(bundle.get("migration_notes") or []),
        "issues": issues,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "export_blocked": len(errors) > 0,
        "target_width_pt": width,
        "style": {"show_handles": show_handles},
        "project_dir": bundle.get("project_dir"),
    }


def apply_action(session_id: str, action: str, body: dict) -> dict:
    bundle = get_bundle(session_id)
    if not bundle:
        raise KeyError("unknown session")
    session: DiagramSession = bundle["session"]
    action = (action or "").strip().lower()

    if action == "move":
        cid = body.get("component_id") or body.get("id_component")
        x = body.get("x")
        y = body.get("y", None)
        if body.get("axis_lock") in ("x", "horizontal"):
            y = None
        elif body.get("axis_lock") in ("y", "vertical"):
            x = None
        session.move(cid, x if x is None else float(x), y if y is None else float(y))
    elif action == "nudge":
        session.nudge(body.get("component_id"), float(body.get("dx") or 0), float(body.get("dy") or 0))
    elif action == "rotate":
        session.rotate(body.get("component_id"), int(body.get("degrees") or 90))
    elif action == "hide":
        session.hide(body.get("component_id"), bool(body.get("hidden", True)))
    elif action == "add_waypoint":
        session.add_waypoint(body.get("connection_id"), float(body["x"]), float(body["y"]))
    elif action == "move_waypoint":
        session.move_waypoint(
            body.get("connection_id"),
            int(body.get("index") or 0),
            float(body["x"]),
            float(body["y"]),
        )
    elif action == "clear_waypoints":
        session.clear_waypoints(body.get("connection_id"))
    elif action == "nudge_label":
        session.nudge_label(body.get("target"), float(body.get("dx") or 0), float(body.get("dy") or 0))
    elif action == "release":
        session.release(body.get("target"), body.get("prop") or "position", force=bool(body.get("force")))
    elif action == "reset_to_auto" or action == "auto_arrange" or action == "auto_spread":
        session.reset_to_auto(force=bool(body.get("force", True)))
    elif action == "lock":
        session.lock(body.get("target"), body.get("prop") or "position", locked=bool(body.get("locked", True)))
    elif action == "lock_figure":
        session.lock_figure()
    elif action == "connect":
        src = body.get("from") or body.get("source")
        dst = body.get("to") or body.get("target")
        if isinstance(src, str) and ":" in src:
            src = tuple(src.split(":", 1))
        if isinstance(dst, str) and ":" in dst:
            dst = tuple(dst.split(":", 1))
        if isinstance(src, list):
            src = tuple(src)
        if isinstance(dst, list):
            dst = tuple(dst)
        try:
            session.connect(
                src,
                dst,
                medium=body.get("medium") or "wire",
                designation=body.get("designation"),
                size=body.get("size"),
            )
        except ConnectRefused as e:
            raise ValueError(str(e)) from e
    elif action == "insert_fitting":
        session.insert_fitting(
            body.get("connection_id"),
            body.get("fitting_type") or body.get("type") or "tee_equal",
            size=body.get("size"),
        )
    elif action == "set_jurisdiction":
        session.graph.jurisdiction = str(body.get("jurisdiction") or "").strip()
        session.invalidate()
    elif action == "set_width":
        bundle["target_width_pt"] = float(body.get("target_width_pt") or bundle["target_width_pt"])
    elif action == "confirm_ai":
        from foldok_diagram.model import Provenance

        ids = set(body.get("ids") or body.get("component_ids") or [])
        for c in session.graph.components:
            if not ids or c.id in ids:
                if c.provenance and c.provenance.source == "ai":
                    c.provenance = Provenance(source="user", ref=c.provenance.ref)
        for conn in session.graph.connections:
            if not ids or conn.id in ids:
                if conn.provenance and conn.provenance.source == "ai":
                    conn.provenance = Provenance(source="user", ref=conn.provenance.ref)
        session.invalidate()
    elif action == "select":
        pass  # selection is client-side for SVG hit targets
    else:
        raise ValueError(f"unknown diagram action: {action}")

    show_handles = body.get("show_handles")
    if show_handles is None:
        show_handles = True
    return session_payload(session_id, show_handles=bool(show_handles))


def bind_project(session_id: str, project_dir: str, graph_id: str | None = None) -> dict:
    bundle = get_bundle(session_id)
    if not bundle:
        raise KeyError("unknown session")
    bundle["project_dir"] = project_dir
    if graph_id:
        bundle["graph_id"] = graph_id
        session: DiagramSession = bundle["session"]
        if not session.graph.id:
            session.graph.id = graph_id
    return session_payload(session_id)


def persist_session(session_id: str) -> dict[str, str]:
    bundle = get_bundle(session_id)
    if not bundle:
        raise KeyError("unknown session")
    folder = bundle.get("project_dir")
    if not folder:
        raise ValueError("no project folder on session")
    from diagram_store import save_diagram

    session: DiagramSession = bundle["session"]
    paths = save_diagram(
        folder,
        session.graph,
        session.pins,
        profile_id=session.profile.id,
    )
    return paths


def open_project_diagram(
    project_dir: str,
    graph_id: str,
    *,
    profile: str | None = None,
    target_width_pt: float = 420.0,
) -> dict:
    from diagram_store import load_diagram

    graph, pins, notes = load_diagram(project_dir, graph_id, profile_id=profile or "wiring")
    prof = resolve_profile(profile or "wiring")
    session = DiagramSession(graph, prof, DiagramStyle(), pins)
    sid = uuid.uuid4().hex[:12]
    _SESSIONS[sid] = {
        "session": session,
        "fixture": "project",
        "target_width_pt": float(target_width_pt),
        "project_dir": project_dir,
        "graph_id": graph.id or graph_id,
        "migration_notes": notes,
    }
    return session_payload(sid)


def propose_ai_graph(
    session_id: str,
    graph_patch: dict,
    *,
    ref: str = "",
) -> dict:
    """Append AI-proposed components/connections (graph only, layer ai)."""
    bundle = get_bundle(session_id)
    if not bundle:
        raise KeyError("unknown session")
    session: DiagramSession = bundle["session"]
    from foldok_diagram.model import Component, Connection, Provenance

    prov = Provenance(source="ai", ref=ref or None)
    for raw in graph_patch.get("components") or []:
        if session.graph.component(raw.get("id")):
            continue
        ports = []
        for p in raw.get("ports") or []:
            from foldok_diagram.model import Port

            ports.append(
                Port(
                    id=p["id"],
                    name=p.get("name") or p["id"],
                    side=p.get("side") or "right",
                    kind=p.get("kind") or "electrical",
                    order=int(p.get("order") or 0),
                    label=p.get("label"),
                )
            )
        c = Component(
            id=raw["id"],
            type=raw.get("type") or "load_block",
            label=raw.get("label") or raw["id"],
            tag=raw.get("tag"),
            ports=ports,
            provenance=prov,
        )
        session.graph.components.append(c)
    for raw in graph_patch.get("connections") or []:
        if session.graph.connection(raw.get("id")):
            continue
        from foldok_diagram.model import Endpoint

        conn = Connection(
            id=raw["id"],
            source=Endpoint(raw["from"]["component_id"], raw["from"]["port_id"]),
            target=Endpoint(raw["to"]["component_id"], raw["to"]["port_id"]),
            medium=raw.get("medium") or "wire",
            designation=raw.get("designation"),
            provenance=prov,
        )
        session.graph.connections.append(conn)
    session.invalidate()
    return session_payload(session_id)
