"""Foldok diagram graph model — schema v2.

Design rules encoded here (do not undo without a work order):

1.  A Component has NO position and NO rotation.  Geometry is per-profile and
    lives in the pin store (see overrides.py).  One graph -> many views.
2.  Every Component and Connection carries Provenance.  A compliance figure
    must be able to say "this pump is BOM row 14".
3.  Branching is structural, never geometric.  A pipe branch is a fitting
    Component with three ports, not a connection touching a line.
4.  Size/material live on Segments, not on the Connection, because a run
    changes size mid-way.
5.  Serialisation is sorted and stable so graphs diff cleanly in git.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

SCHEMA_VERSION = 2

Domain = Literal["electrical", "piping", "mechanical", "signal", "hybrid"]
Role = Literal["equipment", "fitting", "terminal", "reference"]
Side = Literal["right", "bottom", "left", "top"]
PortKind = Literal["electrical", "fluid", "mechanical", "signal"]
Medium = Literal["wire", "pipe", "shaft", "duct", "signal"]

SIDES: tuple[Side, ...] = ("right", "bottom", "left", "top")

# Which media may terminate on which port kind.  Enforced at connect time.
KIND_MEDIA: dict[str, tuple[str, ...]] = {
    "electrical": ("wire",),
    "fluid": ("pipe", "duct"),
    "mechanical": ("shaft",),
    "signal": ("signal", "wire"),
}


@dataclass(frozen=True)
class Provenance:
    """Where a fact came from.  ``source`` is the only required part."""

    source: Literal["user", "ai", "import", "engine"] = "user"
    ref: str | None = None          # e.g. "BOM.xlsx#row=14", "photo_0031.jpg"
    confidence: float | None = None  # only meaningful for source="ai"
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Port:
    id: str
    name: str
    side: Side
    kind: PortKind
    order: int = 0
    allowed_media: tuple[str, ...] = ()
    label: str | None = None        # shown on the drawing; falls back to name

    def media(self) -> tuple[str, ...]:
        return self.allowed_media or KIND_MEDIA[self.kind]

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "side": self.side,
            "kind": self.kind,
            "order": self.order,
        }
        if self.allowed_media:
            d["allowed_media"] = list(self.allowed_media)
        if self.label:
            d["label"] = self.label
        return d


@dataclass
class Component:
    id: str
    type: str                       # symbol id, e.g. "centrifugal_pump"
    domain: Domain = "electrical"
    role: Role = "equipment"
    label: str = ""
    tag: str | None = None
    specs: dict[str, Any] = field(default_factory=dict)
    ports: list[Port] = field(default_factory=list)
    elevation_mm: float | None = None   # drainage / riser views only
    provenance: Provenance = field(default_factory=Provenance)

    def port(self, port_id: str) -> Port | None:
        for p in self.ports:
            if p.id == port_id:
                return p
        return None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "domain": self.domain,
            "role": self.role,
            "label": self.label,
        }
        if self.tag:
            d["tag"] = self.tag
        if self.specs:
            d["specs"] = dict(sorted(self.specs.items()))
        d["ports"] = [p.to_dict() for p in sorted(self.ports, key=lambda p: (p.order, p.id))]
        if self.elevation_mm is not None:
            d["elevation_mm"] = self.elevation_mm
        prov = self.provenance.to_dict()
        if prov:
            d["provenance"] = prov
        return d


@dataclass(frozen=True)
class Endpoint:
    component_id: str
    port_id: str

    def key(self) -> str:
        return f"{self.component_id}:{self.port_id}"

    def to_dict(self) -> dict[str, str]:
        return {"component_id": self.component_id, "port_id": self.port_id}


@dataclass
class Segment:
    """A stretch of one run.  Index i spans anchor i -> anchor i+1."""

    size: str | None = None         # "2.5 mm2", "DN25", "AWG 10"
    material: str | None = None
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Connection:
    id: str
    source: Endpoint
    target: Endpoint
    medium: Medium = "wire"
    designation: str | None = None  # "L1", "PE", "N", "cold", "drain"
    flow: Literal["forward", "reverse", "none"] = "none"
    segments: list[Segment] = field(default_factory=list)
    provenance: Provenance = field(default_factory=Provenance)

    def segment(self, index: int) -> Segment:
        if not self.segments:
            self.segments = [Segment()]
        return self.segments[min(index, len(self.segments) - 1)]

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "from": self.source.to_dict(),
            "to": self.target.to_dict(),
            "medium": self.medium,
        }
        if self.designation:
            d["designation"] = self.designation
        if self.flow != "none":
            d["flow"] = self.flow
        segs = [s.to_dict() for s in self.segments]
        if any(segs):
            d["segments"] = segs
        prov = self.provenance.to_dict()
        if prov:
            d["provenance"] = prov
        return d


@dataclass
class Graph:
    id: str
    title: str = ""
    subtitle: str = ""
    domain: Domain = "electrical"
    jurisdiction: str = "NO_IT_230"      # see jurisdiction.py
    notes: list[str] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    # -- lookup ---------------------------------------------------------
    def component(self, cid: str) -> Component | None:
        for c in self.components:
            if c.id == cid:
                return c
        return None

    def connection(self, wid: str) -> Connection | None:
        for w in self.connections:
            if w.id == wid:
                return w
        return None

    def endpoints_on(self, component_id: str, port_id: str) -> list[Connection]:
        out = []
        for w in self.connections:
            if (w.source.component_id == component_id and w.source.port_id == port_id) or (
                w.target.component_id == component_id and w.target.port_id == port_id
            ):
                out.append(w)
        return sorted(out, key=lambda w: w.id)

    def sorted_components(self) -> list[Component]:
        return sorted(self.components, key=lambda c: c.id)

    def sorted_connections(self) -> list[Connection]:
        return sorted(self.connections, key=lambda w: w.id)

    # -- serialisation --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "domain": self.domain,
            "jurisdiction": self.jurisdiction,
            "notes": list(self.notes),
            "components": [c.to_dict() for c in self.sorted_components()],
            "connections": [w.to_dict() for w in self.sorted_connections()],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, sort_keys=False)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Graph":
        version = int(d.get("schema_version", 1))
        if version > SCHEMA_VERSION:
            raise ValueError(f"graph schema_version {version} is newer than engine {SCHEMA_VERSION}")
        comps: list[Component] = []
        for c in d.get("components", []):
            ports = [
                Port(
                    id=p["id"],
                    name=p.get("name", p["id"]),
                    side=p.get("side", "right"),
                    kind=p.get("kind", "electrical"),
                    order=int(p.get("order", 0)),
                    allowed_media=tuple(p.get("allowed_media", ()) or ()),
                    label=p.get("label"),
                )
                for p in c.get("ports", [])
            ]
            prov = c.get("provenance") or {}
            comps.append(
                Component(
                    id=c["id"],
                    type=c["type"],
                    domain=c.get("domain", "electrical"),
                    role=c.get("role", "equipment"),
                    label=c.get("label", ""),
                    tag=c.get("tag"),
                    specs=dict(c.get("specs", {})),
                    ports=ports,
                    elevation_mm=c.get("elevation_mm"),
                    provenance=Provenance(**prov) if prov else Provenance(source="import"),
                )
            )
        conns: list[Connection] = []
        for w in d.get("connections", []):
            prov = w.get("provenance") or {}
            conns.append(
                Connection(
                    id=w["id"],
                    source=Endpoint(**w["from"]),
                    target=Endpoint(**w["to"]),
                    medium=w.get("medium", "wire"),
                    designation=w.get("designation"),
                    flow=w.get("flow", "none"),
                    segments=[Segment(**s) for s in w.get("segments", [])],
                    provenance=Provenance(**prov) if prov else Provenance(source="import"),
                )
            )
        return Graph(
            id=d["id"],
            title=d.get("title", ""),
            subtitle=d.get("subtitle", ""),
            domain=d.get("domain", "electrical"),
            jurisdiction=d.get("jurisdiction", "NO_IT_230"),
            notes=list(d.get("notes", [])),
            components=comps,
            connections=conns,
            schema_version=SCHEMA_VERSION,
        )
