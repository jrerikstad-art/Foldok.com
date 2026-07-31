"""Tests for the diagram tool.

Run:  python -m pytest foldok_diagram_tool/tests -q
"""

from __future__ import annotations

import pytest

from foldok_diagram_tool import TOOL_SCHEMA, DiagramToolError, build, run, vocabulary

SPEC = {
    "title": "Control electronics",
    "domain": "electrical",
    "components": [
        {"id": "BAT", "label": "LiPo 7.4 V", "ports": [{"id": "pos", "name": "+7V4", "side": "right"}]},
        {"id": "BUCK", "label": "Buck converter", "ports": [
            {"id": "vin", "name": "VIN", "side": "left"},
            {"id": "vout", "name": "5V", "side": "right"}]},
        {"id": "PI", "label": "Raspberry Pi 5", "ports": [{"id": "v5", "name": "5V", "side": "left"}]},
    ],
    "connections": [
        {"from": "BAT.pos", "to": "BUCK.vin", "designation": "V+", "size": "18 AWG"},
        {"from": "BUCK.vout", "to": "PI.v5", "designation": "V+", "size": "20 AWG"},
    ],
}


def test_board_level_wiring_renders():
    """The capability the assistant was denying. A breakout-board diagram is
    labelled boxes and lines, which the graph model always produced."""
    result = run(SPEC)
    assert result.svg.startswith("<svg")
    assert len(result.graph.components) == 3
    assert set(result.modules_drawn) == {"BAT", "BUCK", "PI"}


def test_pin_names_reach_the_drawing():
    svg = run(SPEC).svg
    for pin in ("VIN", "5V", "+7V4"):
        assert pin in svg


def test_low_voltage_dc_does_not_get_installation_rules():
    """Defaulting to a fixed-installation jurisdiction refused '20 AWG' on a
    7.4 V control circuit — a correct rule in the wrong context."""
    graph, _ = build(SPEC)
    assert graph.jurisdiction == "ELV_DC"
    run(SPEC)      # would raise if AWG were rejected


def test_a_fixed_installation_still_gets_its_rules():
    spec = dict(SPEC, jurisdiction="NO_IT_230")
    with pytest.raises(DiagramToolError) as exc:
        run(spec)
    assert "mm2" in str(exc.value)


def test_a_module_box_grows_with_its_pins():
    from foldok_diagram_tool.symbols import module_symbol
    from foldok_diagram import Component, Port

    def comp(n):
        return Component(id="X", type="load_block", label="Module", ports=[
            Port(id=f"p{i}", name=f"PIN{i}", side="left", kind="electrical", order=i)
            for i in range(n)])

    assert module_symbol(comp(8)).h > module_symbol(comp(2)).h


def test_pin_labels_are_not_suppressed_on_a_dense_diagram():
    """Bigger boxes with labels outside made this worse, not better; modules
    print their pin names inside, the way real board diagrams do."""
    dense = dict(SPEC)
    dense["components"] = [
        {"id": f"U{i}", "label": f"Module {i}", "ports": [
            {"id": f"p{j}", "name": f"PIN{j}", "side": "left" if j < 3 else "right"}
            for j in range(6)]}
        for i in range(4)
    ]
    dense["connections"] = [
        {"from": "U0.p3", "to": "U1.p0", "designation": "signal"},
        {"from": "U1.p4", "to": "U2.p0", "designation": "signal"},
    ]
    result = run(dense)
    suppressed = [w for w in result.warnings if "suppressed" in w]
    assert len(suppressed) <= 2, suppressed


# --- refusals teach ------------------------------------------------------
def test_a_malformed_endpoint_says_what_would_have_worked():
    spec = dict(SPEC, connections=[{"from": "BAT", "to": "BUCK.vin"}])
    with pytest.raises(DiagramToolError) as exc:
        run(spec)
    assert "COMPONENT.PORT" in str(exc.value) and "PI.sda" in str(exc.value)


def test_a_component_with_no_ports_is_refused_with_the_reason():
    spec = dict(SPEC, components=[{"id": "X", "label": "Thing", "ports": []}])
    with pytest.raises(DiagramToolError) as exc:
        run(spec)
    assert "where wires land" in str(exc.value)


def test_an_unknown_side_lists_the_valid_ones():
    spec = dict(SPEC)
    spec["components"] = [{"id": "X", "label": "T", "ports": [{"id": "a", "name": "A", "side": "up"}]}]
    with pytest.raises(DiagramToolError) as exc:
        run(spec)
    assert "'left'" in str(exc.value) or "left" in str(exc.value)


def test_a_dangling_connection_is_caught_before_rendering():
    spec = dict(SPEC, connections=[{"from": "BAT.pos", "to": "GHOST.x"}])
    with pytest.raises(DiagramToolError) as exc:
        run(spec)
    assert "does not hold together" in str(exc.value)


# --- the schema ----------------------------------------------------------
def test_the_schema_tells_the_model_when_to_reach_for_it():
    description = TOOL_SCHEMA["description"].lower()
    for trigger in ("wiring diagram", "schematic", "koblingsskjema", "how components"):
        assert trigger in description


def test_the_schema_says_a_missing_symbol_is_fine():
    assert "labelled boxes with their pins" in TOOL_SCHEMA["description"]


def test_the_vocabulary_is_available_for_self_correction():
    vocab = vocabulary()
    assert vocab["symbols"] and "wiring" in vocab["profiles"]
    assert not any(s.startswith("module::") for s in vocab["symbols"])
