"""Schema v1 -> v2 migration.

0.62 graphs carry ``position`` and ``rotation`` on the component and
``attributes`` on the connection.  v2 moves geometry into pins and splits
size/material onto segments.

The old coordinates are not thrown away and not treated as gospel either: they
land as pins at layer ``user`` with scope ``*`` and a note saying they were
migrated, unlocked.  So an existing figure opens looking exactly as it did, and
the first ``reset_to_auto()`` gives the new layout engine the wheel.
"""

from __future__ import annotations

from typing import Any

from .model import SCHEMA_VERSION, Graph
from .overrides import GLOBAL_SCOPE, PinStore, target_component

MEDIUM_FROM_V1 = {
    "wire": "wire",
    "pipe": "pipe",
    "shaft": "shaft",
    "duct": "duct",
    "signal": "signal",
    "cable": "wire",
}


def migrate(doc: dict[str, Any], pins: PinStore | None = None) -> tuple[Graph, PinStore, list[str]]:
    """Return (graph, pins, notes).  ``doc`` is a v1 or v2 graph dict."""
    notes: list[str] = []
    pins = pins or PinStore()
    version = int(doc.get("schema_version", 1))
    if version >= SCHEMA_VERSION:
        return Graph.from_dict(doc), pins, notes

    out = dict(doc)
    out["schema_version"] = SCHEMA_VERSION
    if "jurisdiction" not in out:
        out["jurisdiction"] = "NO_IT_230"
        notes.append(
            "jurisdiction was missing and defaulted to NO_IT_230 — confirm it before publishing, "
            "because conductor units and breaker notation are checked against it"
        )

    comps: list[dict[str, Any]] = []
    moved = 0
    for c in out.get("components", []):
        c = dict(c)
        pos = c.pop("position", None)
        rot = c.pop("rotation", None)
        if isinstance(pos, dict) and (pos.get("x") is not None or pos.get("y") is not None):
            pins.pin(
                target_component(c["id"]),
                "position",
                {"x": pos.get("x"), "y": pos.get("y")},
                layer="user",
                scope=GLOBAL_SCOPE,
                note="migrated from schema v1",
            )
            moved += 1
        if rot:
            pins.pin(
                target_component(c["id"]),
                "rotation",
                int(rot),
                layer="user",
                scope=GLOBAL_SCOPE,
                note="migrated from schema v1",
            )
        c.setdefault("role", "fitting" if c.get("type") in ("tee_equal", "elbow_90", "junction") else "equipment")
        c.setdefault("provenance", {"source": "import", "note": "schema v1"})
        comps.append(c)
    out["components"] = comps
    if moved:
        notes.append(
            f"{moved} component position(s) became global pins; they are unlocked, so "
            "reset_to_auto() hands the drawing to the layout engine"
        )

    conns: list[dict[str, Any]] = []
    for w in out.get("connections", []):
        w = dict(w)
        attrs = w.pop("attributes", {}) or {}
        w["medium"] = MEDIUM_FROM_V1.get(w.get("medium", "wire"), "wire")
        if attrs.get("designation") and not w.get("designation"):
            w["designation"] = attrs["designation"]
        seg: dict[str, Any] = {}
        if attrs.get("size"):
            seg["size"] = attrs["size"]
        if attrs.get("material"):
            seg["material"] = attrs["material"]
        if seg:
            w["segments"] = [seg]
        if attrs.get("flow_direction") and attrs["flow_direction"] != "none":
            w["flow"] = attrs["flow_direction"]
        if attrs.get("color"):
            notes.append(
                f"run '{w['id']}' carried an explicit colour; dropped in favour of the style "
                "encoding, because colour alone does not survive a mono print"
            )
        w.setdefault("provenance", {"source": "import", "note": "schema v1"})
        conns.append(w)
    out["connections"] = conns

    return Graph.from_dict(out), pins, notes
