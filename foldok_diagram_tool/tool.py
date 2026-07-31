"""The callable tool — because a capability with no call path is still absent.

Fixing the manifest lets the assistant *claim* it can draw. This is what makes
the claim true. The two have to ship together: a manifest that promises drawing
with nothing to invoke just moves the failure one turn later, from "I have no
tool" to "let me draw that… " and then nothing.

Design notes worth keeping:

**The schema carries the vocabulary.**  A model cannot produce a valid graph
without knowing which symbols exist. Rather than listing 45 symbol ids in the
tool description, unknown types fall back to a sized module box — which is the
right shape for a breakout board anyway — and validation returns the real
vocabulary when something else is wrong.

**Errors teach.**  Every refusal names the field, the value, and what would have
worked. A tool that says "invalid input" to a model produces three more identical
attempts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from foldok_diagram import (
    Component,
    Connection,
    Endpoint,
    Graph,
    Port,
    Provenance,
    Segment,
    figure,
)
from foldok_diagram import profile as profiles
from foldok_diagram import symbols as symbol_pack
from foldok_diagram.validate import validate

from .symbols import register

SIDES = ("left", "right", "top", "bottom")
KINDS = ("electrical", "fluid", "mechanical", "signal")
MEDIA = ("wire", "pipe", "shaft", "duct", "signal")

TOOL_SCHEMA: dict[str, Any] = {
    "name": "create_wiring_diagram",
    "description": (
        "Draw a wiring, interconnection or piping diagram as a print-ready SVG figure "
        "and place it in the document. Use this whenever the user asks how components "
        "connect, or asks for a schematic, wiring diagram, single-line diagram or "
        "koblingsskjema. Components you name that have no standard symbol are drawn as "
        "labelled boxes with their pins, which is the normal convention for modules and "
        "breakout boards."
    ),
    "input_schema": {
        "type": "object",
        "required": ["title", "components", "connections"],
        "properties": {
            "title": {"type": "string"},
            "subtitle": {"type": "string"},
            "domain": {"type": "string", "enum": ["electrical", "piping", "mechanical"]},
            "jurisdiction": {
                "type": "string",
                "description": (
                    "Only for fixed installations — NO_IT_230, NO_TN_230_400, "
                    "EU_TN_230_400, US_NEC_120_240. Leave unset for control "
                    "electronics and anything below 50 V DC."
                ),
            },
            "profile": {"type": "string", "enum": sorted(profiles.PROFILES)},
            "components": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "label", "ports"],
                    "properties": {
                        "id": {"type": "string", "description": "short, unique, e.g. PWM"},
                        "label": {"type": "string", "description": "what it is, e.g. PCA9685 PWM"},
                        "tag": {"type": "string", "description": "designation, e.g. -U3"},
                        "type": {"type": "string",
                                 "description": "symbol id if a standard symbol fits; "
                                                "otherwise omit and a module box is drawn"},
                        "ports": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "name", "side"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string",
                                             "description": "printed on the pin, e.g. SDA"},
                                    "side": {"type": "string", "enum": list(SIDES)},
                                    "kind": {"type": "string", "enum": list(KINDS)},
                                },
                            },
                        },
                    },
                },
            },
            "connections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["from", "to"],
                    "properties": {
                        "from": {"type": "string", "description": "COMPONENT.PORT, e.g. PI.sda"},
                        "to": {"type": "string", "description": "COMPONENT.PORT"},
                        "designation": {"type": "string",
                                        "description": "L1, GND, signal, cold, hot …"},
                        "size": {"type": "string", "description": "e.g. 20 AWG, 2.5 mm2, DN20"},
                        "medium": {"type": "string", "enum": list(MEDIA)},
                    },
                },
            },
        },
    },
}


class DiagramToolError(Exception):
    """A refusal the model can act on."""


@dataclass
class ToolResult:
    svg: str
    graph: Graph
    warnings: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    modules_drawn: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Diagram '{self.graph.title}' — {len(self.graph.components)} component(s), "
            f"{len(self.graph.connections)} connection(s)"
        ]
        if self.modules_drawn:
            lines.append(
                f"  {len(self.modules_drawn)} drawn as labelled module boxes: "
                + ", ".join(self.modules_drawn[:6])
            )
        for issue in self.issues[:6]:
            lines.append(f"  check: {issue}")
        return "\n".join(lines)


def _endpoint(ref: str, field_name: str) -> Endpoint:
    if "." not in ref:
        raise DiagramToolError(
            f"'{field_name}': {ref!r} must be COMPONENT.PORT, for example 'PI.sda'"
        )
    component_id, port_id = ref.split(".", 1)
    return Endpoint(component_id.strip(), port_id.strip())


def build(spec: Mapping[str, Any]) -> tuple[Graph, list[str]]:
    """Spec to graph, with refusals that say what would have worked."""
    if not spec.get("components"):
        raise DiagramToolError("'components' is empty — name at least two things to connect")

    domain = str(spec.get("domain") or "electrical")
    default_kind = {"piping": "fluid", "mechanical": "mechanical"}.get(domain, "electrical")
    default_medium = {"piping": "pipe", "mechanical": "shaft"}.get(domain, "wire")

    modules: list[str] = []
    components: list[Component] = []
    for raw in spec["components"]:
        cid = str(raw.get("id") or "").strip()
        if not cid:
            raise DiagramToolError("every component needs an 'id'")
        ports: list[Port] = []
        for order, p in enumerate(raw.get("ports") or []):
            side = str(p.get("side") or "left")
            if side not in SIDES:
                raise DiagramToolError(
                    f"component {cid}: side {side!r} is not one of {list(SIDES)}"
                )
            ports.append(
                Port(
                    id=str(p.get("id") or f"p{order}"),
                    name=str(p.get("name") or p.get("id") or f"p{order}"),
                    side=side,                              # type: ignore[arg-type]
                    kind=str(p.get("kind") or default_kind),  # type: ignore[arg-type]
                    order=order,
                    label=str(p.get("name") or ""),
                )
            )
        if not ports:
            raise DiagramToolError(
                f"component {cid} has no ports — a diagram needs to know where wires land"
            )
        component = Component(
            id=cid,
            type=str(raw.get("type") or "") or "load_block",
            domain=domain,                                   # type: ignore[arg-type]
            label=str(raw.get("label") or cid),
            tag=raw.get("tag"),
            specs=dict(raw.get("specs") or {}),
            ports=ports,
            provenance=Provenance(source="ai", note="proposed by the assistant"),
        )
        if not symbol_pack.known(component.type) or component.type == "load_block":
            component.type = register(component, title=component.label)
            modules.append(cid)
        components.append(component)

    connections: list[Connection] = []
    for i, raw in enumerate(spec.get("connections") or [], start=1):
        connections.append(
            Connection(
                id=str(raw.get("id") or f"w{i:02d}"),
                source=_endpoint(str(raw.get("from", "")), "from"),
                target=_endpoint(str(raw.get("to", "")), "to"),
                medium=str(raw.get("medium") or default_medium),   # type: ignore[arg-type]
                designation=raw.get("designation"),
                segments=[Segment(size=raw.get("size"), material=raw.get("material"))],
                provenance=Provenance(source="ai", note="proposed by the assistant"),
            )
        )

    graph = Graph(
        id=str(spec.get("id") or "diagram"),
        title=str(spec.get("title") or "Diagram"),
        subtitle=str(spec.get("subtitle") or ""),
        domain=domain,                                       # type: ignore[arg-type]
        # Not a fixed installation unless somebody says so. Defaulting to
        # EU_TN_230_400 made the validator refuse "20 AWG" on a 7.4 V DC control
        # circuit, which is a correct rule applied to the wrong context.
        jurisdiction=str(spec.get("jurisdiction") or "ELV_DC"),
        components=components,
        connections=connections,
    )
    return graph, modules


def run(spec: Mapping[str, Any], *, target_width_pt: float = 520.0) -> ToolResult:
    """Build, validate, render. The whole tool."""
    graph, modules = build(spec)

    report = validate(graph)
    blocking = [i for i in report.errors]
    if blocking:
        raise DiagramToolError(
            "the diagram does not hold together:\n"
            + "\n".join(f"  {i.message} — {i.fix}" for i in blocking[:6])
        )

    profile_id = str(spec.get("profile") or "wiring")
    try:
        prof = profiles.get(profile_id)
    except ValueError as exc:
        raise DiagramToolError(str(exc)) from exc

    result = figure(graph, prof, target_width_pt=target_width_pt)
    return ToolResult(
        svg=result.svg,
        graph=graph,
        warnings=list(result.warnings),
        issues=[f"{i.message} — {i.fix}" for i in report.warnings][:8],
        modules_drawn=modules,
    )


def vocabulary() -> dict[str, Any]:
    """What the model may use. Handed back on error so it can self-correct."""
    by_domain: dict[str, list[str]] = {}
    for entry in symbol_pack.describe():
        if entry["id"].startswith("module::"):
            continue
        by_domain.setdefault("symbols", []).append(entry["id"])
    return {
        "symbols": sorted(by_domain.get("symbols", [])),
        "profiles": sorted(profiles.PROFILES),
        "sides": list(SIDES),
        "media": list(MEDIA),
        "note": (
            "Omit 'type' for anything without a standard symbol — modules and "
            "breakout boards are drawn as labelled boxes with their pins."
        ),
    }
