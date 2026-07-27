"""Worked examples — also the fixtures for the golden tests.

``water_heater_no()`` is the corrected version of the 0.62 output.  Note what
changed and what did not: two line conductors and no neutral is CORRECT for a
Norwegian IT installation, so L1/L2/PE stays.  What was wrong was the AWG
cross-section and the "30 A 2-pole" breaker: 5 kW at 230 V is 21.7 A, so C25 and
4 mm2 per NEK 400.  The jurisdiction field is what makes that checkable instead
of a matter of taste.

``plumbing_supply()`` is the first piping case, chosen because it is topological:
no gradient, no elevation, and every branch is a real tee.
"""

from __future__ import annotations

from .model import Component, Connection, Endpoint, Graph, Port, Provenance, Segment

BOM = "BOM_2026-07.xlsx"


def _p(pid: str, name: str, side: str, kind: str, order: int, label: str | None = None) -> Port:
    return Port(id=pid, name=name, side=side, kind=kind, order=order, label=label)  # type: ignore[arg-type]


def _wire(
    wid: str,
    a: tuple[str, str],
    b: tuple[str, str],
    designation: str,
    size: str = "4 mm2",
    ref: str | None = None,
) -> Connection:
    return Connection(
        id=wid,
        source=Endpoint(*a),
        target=Endpoint(*b),
        medium="wire",
        designation=designation,
        segments=[Segment(size=size, material="PN")],
        provenance=Provenance(source="user", ref=ref),
    )


def water_heater_no() -> Graph:
    """230 V / 5 kW non-simultaneous water heater, Norwegian IT system."""
    db = Component(
        id="DB",
        type="distribution_board",
        label="Service panel",
        tag="-DB1",
        specs={"location": "utility room"},
        ports=[
            _p("l1", "L1", "right", "electrical", 0),
            _p("l2", "L2", "right", "electrical", 1),
            _p("pe", "PE", "right", "electrical", 2),
        ],
        provenance=Provenance(source="import", ref=f"{BOM}#row=2"),
    )
    breaker = Component(
        id="Q1",
        type="breaker_2p",
        label="Water heater circuit",
        tag="-Q1",
        specs={"breaker": "C25, 2-pole", "rated_current_a": 25},
        ports=[
            _p("in1", "in L1", "left", "electrical", 0, label="1"),
            _p("in2", "in L2", "left", "electrical", 1, label="3"),
            _p("out1", "out L1", "right", "electrical", 2, label="2"),
            _p("out2", "out L2", "right", "electrical", 3, label="4"),
        ],
        provenance=Provenance(source="import", ref=f"{BOM}#row=7"),
    )
    upper_stat = Component(
        id="UT",
        type="thermostat",
        label="Upper thermostat",
        tag="-UT",
        specs={"setpoint_c": 75, "function": "priority"},
        ports=[
            _p("line", "line", "left", "electrical", 0, label="L"),
            _p("upper", "to upper element", "right", "electrical", 1, label="1"),
            _p("lower", "to lower element", "right", "electrical", 2, label="2"),
        ],
        provenance=Provenance(source="import", ref=f"{BOM}#row=11"),
    )
    lower_stat = Component(
        id="LT",
        type="thermostat",
        label="Lower thermostat",
        tag="-LT",
        specs={"setpoint_c": 70},
        ports=[
            _p("line", "line", "left", "electrical", 0, label="L"),
            _p("load", "load", "right", "electrical", 1, label="1"),
        ],
        provenance=Provenance(source="import", ref=f"{BOM}#row=12"),
    )
    upper_el = Component(
        id="UE",
        type="heating_element",
        label="Upper element 2.5 kW",
        tag="-UE",
        specs={"power_w": 2500},
        ports=[
            _p("a", "phase", "left", "electrical", 0),
            _p("b", "return", "right", "electrical", 1),
        ],
        provenance=Provenance(source="import", ref=f"{BOM}#row=14"),
    )
    lower_el = Component(
        id="LE",
        type="heating_element",
        label="Lower element 2.5 kW",
        tag="-LE",
        specs={"power_w": 2500},
        ports=[
            _p("a", "phase", "left", "electrical", 0),
            _p("b", "return", "right", "electrical", 1),
        ],
        provenance=Provenance(source="import", ref=f"{BOM}#row=15"),
    )
    earth = Component(
        id="PE1",
        type="earth",
        label="Tank earth",
        tag="PE",
        role="terminal",
        ports=[_p("t", "PE", "top", "electrical", 0)],
        provenance=Provenance(source="user", ref="photo_0031.jpg"),
    )

    conns = [
        _wire("w01", ("DB", "l1"), ("Q1", "in1"), "L1", ref=f"{BOM}#row=7"),
        _wire("w02", ("DB", "l2"), ("Q1", "in2"), "L2", ref=f"{BOM}#row=7"),
        _wire("w03", ("Q1", "out1"), ("UT", "line"), "L1"),
        _wire("w04", ("UT", "upper"), ("UE", "a"), "L1"),
        _wire("w05", ("UT", "lower"), ("LT", "line"), "L1"),
        _wire("w06", ("LT", "load"), ("LE", "a"), "L1"),
        _wire("w07", ("Q1", "out2"), ("UE", "b"), "L2"),
        _wire("w08", ("Q1", "out2"), ("LE", "b"), "L2"),
        _wire("w09", ("DB", "pe"), ("PE1", "t"), "PE"),
    ]

    return Graph(
        id="wiring_water_heater_230_no",
        title="Electric water heater — 230 V / 5 kW, non-simultaneous",
        subtitle="Terminal interconnection · Norwegian IT system",
        domain="electrical",
        jurisdiction="NO_IT_230",
        notes=[
            "230 V between L1 and L2; no neutral (IT system).",
            "Upper thermostat has priority; the lower element runs only when the upper is satisfied.",
            "Circuit protection C25, 2-pole. Conductors 4 mm2 per NEK 400.",
        ],
        components=[db, breaker, upper_stat, lower_stat, upper_el, lower_el, earth],
        connections=conns,
    )


def _pipe(
    wid: str,
    a: tuple[str, str],
    b: tuple[str, str],
    designation: str,
    size: str,
    material: str = "PEX",
    flow: str = "forward",
) -> Connection:
    return Connection(
        id=wid,
        source=Endpoint(*a),
        target=Endpoint(*b),
        medium="pipe",
        designation=designation,
        flow=flow,  # type: ignore[arg-type]
        segments=[Segment(size=size, material=material)],
        provenance=Provenance(source="user"),
    )


def _tee(tid: str, tag: str, size: str) -> Component:
    return Component(
        id=tid,
        type="tee_equal",
        domain="piping",
        role="fitting",
        label="tee",
        tag=tag,
        specs={"size": size, "material": "brass"},
        ports=[
            _p("a", "in", "left", "fluid", 0),
            _p("b", "out", "right", "fluid", 1),
            _p("c", "branch", "bottom", "fluid", 2),
        ],
        provenance=Provenance(source="user"),
    )


def plumbing_supply() -> Graph:
    """Cold/hot supply schematic — every branch is a fitting, not a crossing."""
    stop = Component(
        id="SV1",
        type="stopcock",
        domain="piping",
        label="Main stopcock",
        tag="-SV1",
        specs={"size": "DN20"},
        ports=[_p("a", "in", "left", "fluid", 0), _p("b", "out", "right", "fluid", 1)],
        provenance=Provenance(source="user", ref="photo_0102.jpg"),
    )
    heater = Component(
        id="WH1",
        type="water_heater",
        domain="piping",
        label="Water heater 200 l",
        tag="-WH1",
        specs={"volume_l": 200},
        ports=[
            _p("cold", "cold in", "left", "fluid", 0),
            _p("hot", "hot out", "right", "fluid", 1),
        ],
        provenance=Provenance(source="import", ref=f"{BOM}#row=21"),
    )
    sink = Component(
        id="SK1",
        type="fixture",
        domain="piping",
        label="Kitchen sink",
        tag="SK1",
        ports=[
            _p("cold", "cold", "left", "fluid", 0),
            _p("hot", "hot", "left", "fluid", 1),
        ],
        provenance=Provenance(source="user"),
    )
    shower = Component(
        id="SH1",
        type="fixture",
        domain="piping",
        label="Shower",
        tag="SH1",
        ports=[
            _p("cold", "cold", "left", "fluid", 0),
            _p("hot", "hot", "left", "fluid", 1),
        ],
        provenance=Provenance(source="user"),
    )

    t_cold = _tee("T1", "-T1", "DN20")
    t_dist = _tee("T2", "-T2", "DN16")
    t_hot = _tee("T3", "-T3", "DN16")

    conns = [
        _pipe("p01", ("SV1", "b"), ("T1", "a"), "cold", "DN20"),
        _pipe("p02", ("T1", "c"), ("WH1", "cold"), "cold", "DN20"),
        _pipe("p03", ("T1", "b"), ("T2", "a"), "cold", "DN16"),
        _pipe("p04", ("T2", "b"), ("SK1", "cold"), "cold", "DN12"),
        _pipe("p05", ("T2", "c"), ("SH1", "cold"), "cold", "DN12"),
        _pipe("p06", ("WH1", "hot"), ("T3", "a"), "hot", "DN16"),
        _pipe("p07", ("T3", "b"), ("SK1", "hot"), "hot", "DN12"),
        _pipe("p08", ("T3", "c"), ("SH1", "hot"), "hot", "DN12"),
    ]

    return Graph(
        id="piping_supply_bathroom_kitchen",
        title="Domestic supply — cold and hot",
        subtitle="Piping schematic · PEX in conduit",
        domain="piping",
        jurisdiction="NO_IT_230",
        notes=[
            "Every branch is a tee with a size and a material, so it appears in the BOM.",
            "Sizes are on the runs, not in a note.",
        ],
        components=[stop, heater, sink, shower, t_cold, t_dist, t_hot],
        connections=conns,
    )
