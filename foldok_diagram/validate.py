"""Validation.

Every issue carries a ``fix`` string.  An error message that does not say what
to do is a support ticket.

The two checks that matter most for Foldok's actual problem:

*  ``pipe_branch_without_fitting`` — a fluid port carrying more than one run
   means the drawing is implying a branch that has no component.  In a
   compliance package a tee is a part with a size and a material, so it must be
   a Component with three ports, not a geometric coincidence.
*  the ``jurisdiction_*`` family — catches the confidently-wrong diagram: AWG
   conductors on a Norwegian job, a neutral in an IT system, a trip rating
   where a curve is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from . import jurisdiction as juris_mod
from . import symbols as symbol_pack
from .model import KIND_MEDIA, Graph
from .overrides import PinStore

Level = Literal["error", "warning", "info"]


@dataclass
class Issue:
    level: Level
    code: str
    target: str
    message: str
    fix: str = ""

    def __str__(self) -> str:
        head = f"[{self.level.upper()}] {self.code} @ {self.target}: {self.message}"
        return f"{head}\n    fix: {self.fix}" if self.fix else head


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, level: Level, code: str, target: str, message: str, fix: str = "") -> None:
        self.issues.append(Issue(level, code, target, message, fix))

    def __str__(self) -> str:
        if not self.issues:
            return "no issues"
        return "\n".join(str(i) for i in self.issues)


def validate(graph: Graph, pins: PinStore | None = None) -> Report:
    rep = Report()
    _structure(graph, rep)
    _media(graph, rep)
    _fittings(graph, rep)
    _electrical(graph, rep)
    _provenance(graph, rep)
    if pins is not None:
        for orphan in pins.orphans(graph):
            rep.add(
                "warning",
                "orphan_pin",
                orphan.pin.target,
                f"pin '{orphan.pin.prop}' has no target: {orphan.reason}",
                "release the pin, or restore the element it refers to",
            )
    return rep


# ----------------------------------------------------------------------
def _structure(graph: Graph, rep: Report) -> None:
    seen: set[str] = set()
    for comp in graph.sorted_components():
        if comp.id in seen:
            rep.add("error", "duplicate_component_id", comp.id, "component id is used twice", "rename one")
        seen.add(comp.id)
        if not symbol_pack.known(comp.type):
            rep.add(
                "warning",
                "unknown_symbol",
                comp.id,
                f"symbol '{comp.type}' is not in the pack; a fallback box will print",
                "add the symbol to symbols.py or pick an existing type",
            )
        port_ids: set[str] = set()
        for port in comp.ports:
            if port.id in port_ids:
                rep.add("error", "duplicate_port_id", f"{comp.id}:{port.id}", "port id is used twice", "rename one")
            port_ids.add(port.id)
        if not comp.ports and comp.role != "reference":
            rep.add(
                "warning", "no_ports", comp.id, "component has no ports so nothing can connect to it",
                "add ports, or set role='reference'",
            )

    seen_conn: set[str] = set()
    for conn in graph.sorted_connections():
        if conn.id in seen_conn:
            rep.add("error", "duplicate_connection_id", conn.id, "connection id is used twice", "rename one")
        seen_conn.add(conn.id)
        for label, ep in (("from", conn.source), ("to", conn.target)):
            comp = graph.component(ep.component_id)
            if comp is None:
                rep.add(
                    "error", "dangling_endpoint", conn.id,
                    f"{label} references missing component '{ep.component_id}'",
                    "delete the run or restore the component",
                )
            elif comp.port(ep.port_id) is None:
                rep.add(
                    "error", "dangling_port", conn.id,
                    f"{label} references missing port '{ep.port_id}' on '{ep.component_id}'",
                    "point the run at an existing port",
                )
        if conn.source.key() == conn.target.key():
            rep.add("error", "self_loop", conn.id, "run starts and ends on the same port", "delete it")


def _media(graph: Graph, rep: Report) -> None:
    for conn in graph.sorted_connections():
        for label, ep in (("from", conn.source), ("to", conn.target)):
            comp = graph.component(ep.component_id)
            port = comp.port(ep.port_id) if comp else None
            if port is None:
                continue
            allowed = port.media()
            if conn.medium not in allowed:
                rep.add(
                    "error", "illegal_medium", conn.id,
                    f"medium '{conn.medium}' cannot land on {label} port "
                    f"'{ep.port_id}' (kind '{port.kind}', accepts {list(allowed)})",
                    f"use one of {list(allowed)}, or change the port kind",
                )
            if port.kind not in KIND_MEDIA:
                rep.add("error", "unknown_port_kind", f"{ep.component_id}:{ep.port_id}",
                        f"port kind '{port.kind}' is not known", f"use one of {sorted(KIND_MEDIA)}")


def _fittings(graph: Graph, rep: Report) -> None:
    for comp in graph.sorted_components():
        if comp.type in symbol_pack.FITTING_TYPES and comp.role != "fitting":
            rep.add(
                "warning", "fitting_role_mismatch", comp.id,
                f"'{comp.type}' is a fitting but role is '{comp.role}'",
                "set role='fitting' so it is counted as a part, not equipment",
            )
        for port in sorted(comp.ports, key=lambda p: p.id):
            if port.kind != "fluid":
                continue
            runs = graph.endpoints_on(comp.id, port.id)
            if len(runs) > 1:
                rep.add(
                    "error", "pipe_branch_without_fitting", f"{comp.id}:{port.id}",
                    f"{len(runs)} runs land on one fluid port ({', '.join(r.id for r in runs)}); "
                    "that is an implied branch with no part behind it",
                    "insert a fitting component (tee_equal / manifold) and route both runs through it",
                )


def _electrical(graph: Graph, rep: Report) -> None:
    try:
        juris = juris_mod.get(graph.jurisdiction)
    except ValueError as exc:
        rep.add("error", "unknown_jurisdiction", graph.id, str(exc),
                f"set jurisdiction to one of {sorted(juris_mod.JURISDICTIONS)}")
        return

    wires = [c for c in graph.sorted_connections() if c.medium == "wire"]
    if not wires:
        return

    known = set(juris.phase_names) | {juris.pe_name}
    if juris.neutral_name:
        known.add(juris.neutral_name)
    if juris.id == "ELV_DC":
        # Control wiring carries signal pairs and buses alongside the rails;
        # they are conductor classes here, not unknown designations.
        known |= {"signal", "SIG", "I2C", "SPI", "UART", "CAN", "PWM", "DATA", "CLK"}

    has_pe = False
    for conn in wires:
        des = conn.designation
        if not des:
            rep.add(
                "warning", "missing_designation", conn.id,
                "conductor has no designation, so the figure cannot be read in mono",
                "set designation (L1 / L2 / L3 / N / PE)",
            )
        elif des == juris.pe_name:
            has_pe = True
        elif des not in known:
            if des == "N" and juris.neutral_name is None:
                rep.add(
                    "error", "neutral_in_it_system", conn.id,
                    f"'N' is used but {juris.title} has no neutral",
                    "in an IT system 230 V is line-to-line: use two line conductors (L1 + L2)",
                )
            else:
                rep.add(
                    "warning", "unknown_designation", conn.id,
                    f"designation '{des}' is not a conductor of {juris.title}",
                    f"expected one of {sorted(known)}",
                )
        for i, seg in enumerate(conn.segments):
            if seg.size and not juris_mod.size_unit_matches(seg.size, juris):
                rep.add(
                    "error", "size_unit_mismatch", f"{conn.id}#seg{i}",
                    f"size '{seg.size}' is not in {juris.conductor_unit} as required by {juris.title}",
                    f"restate the cross-section, {juris.size_pattern}",
                )
            if not seg.size:
                rep.add(
                    "warning", "missing_size", f"{conn.id}#seg{i}",
                    "run has no cross-section; on a compliance figure it belongs on the line, not in a note",
                    f"set segment size, {juris.size_pattern}",
                )

    if not has_pe:
        rep.add(
            "warning", "no_protective_conductor", graph.id,
            f"no '{juris.pe_name}' run in an electrical graph",
            "add the protective conductor, or state why the circuit has none",
        )

    for comp in graph.sorted_components():
        spec = str(comp.specs.get("breaker", "") or comp.specs.get("protection", ""))
        if not spec:
            continue
        upper = spec.upper()
        if juris.breaker_style == "curve" and not any(f"{c}" in upper for c in ("B", "C", "D")):
            rep.add(
                "warning", "breaker_style_mismatch", comp.id,
                f"'{spec}' has no tripping curve but {juris.title} states breakers as curve + rating",
                "restate as e.g. 'C16, 2-pole'",
            )
        if juris.conductor_unit == "mm2" and "AWG" in upper:
            rep.add(
                "error", "size_unit_mismatch", comp.id,
                f"'{spec}' uses AWG on a {juris.title} job",
                "restate in mm2",
            )


def _provenance(graph: Graph, rep: Report) -> None:
    for comp in graph.sorted_components():
        p = comp.provenance
        if p.source == "ai" and not p.ref:
            rep.add(
                "warning", "unsourced_ai_component", comp.id,
                "component was proposed by the model with no source reference",
                "confirm it against the BOM/photo and set provenance.ref, or delete it",
            )
    for conn in graph.sorted_connections():
        p = conn.provenance
        if p.source == "ai" and not p.ref:
            rep.add(
                "warning", "unsourced_ai_connection", conn.id,
                "run was proposed by the model with no source reference",
                "confirm it and set provenance.ref",
            )


def check_drainage(graph: Graph) -> Report:
    """Extra checks that only apply to a drainage/riser view."""
    rep = Report()
    for comp in graph.sorted_components():
        if comp.domain != "piping":
            continue
        if comp.elevation_mm is None:
            rep.add(
                "warning", "missing_elevation", comp.id,
                "drainage views place components by real height",
                "set elevation_mm",
            )
    for conn in graph.sorted_connections():
        if conn.medium != "pipe" or conn.designation not in ("drain", "vent"):
            continue
        a = graph.component(conn.source.component_id)
        b = graph.component(conn.target.component_id)
        if a is None or b is None or a.elevation_mm is None or b.elevation_mm is None:
            continue
        if a.elevation_mm <= b.elevation_mm and conn.designation == "drain":
            rep.add(
                "error", "drain_without_fall", conn.id,
                f"'{a.id}' is not above '{b.id}', so this drain has no fall",
                "correct the elevations or reverse the run",
            )
    return rep
