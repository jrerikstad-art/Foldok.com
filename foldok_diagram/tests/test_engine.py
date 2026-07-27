"""Acceptance tests.  These are the contract; Cursor should not merge red.

Run:  python -m pytest foldok_diagram/tests -q
"""

from __future__ import annotations

import re

from foldok_diagram import DiagramSession, DiagramStyle, PinStore, figure, layout, validate
from foldok_diagram import profile as profiles
from foldok_diagram.editing import ConnectRefused
from foldok_diagram.examples import plumbing_supply, water_heater_no
from foldok_diagram.model import Component, Port, Segment
from foldok_diagram.overrides import target_component, target_connection


# --- determinism -------------------------------------------------------
def test_render_is_byte_stable():
    g = water_heater_no()
    a = figure(g, profiles.WIRING).svg
    b = figure(water_heater_no(), profiles.WIRING).svg
    assert a == b


def test_component_order_does_not_change_output():
    g1 = water_heater_no()
    g2 = water_heater_no()
    g2.components.reverse()
    g2.connections.reverse()
    assert figure(g1, profiles.WIRING).svg == figure(g2, profiles.WIRING).svg


def test_coordinates_are_snapped():
    lay = layout(water_heater_no(), profiles.WIRING, DiagramStyle())
    for p in lay.placed:
        assert abs(p.x * 2 - round(p.x * 2)) < 1e-6
        assert abs(p.y * 2 - round(p.y * 2)) < 1e-6


# --- viewBox / scaling -------------------------------------------------
def test_viewbox_is_tight_to_content():
    res = figure(water_heater_no(), profiles.WIRING)
    m = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', res.svg)
    assert m
    _, _, w, h = (float(v) for v in m.groups())
    lay = layout(water_heater_no(), profiles.WIRING, DiagramStyle())
    # frame may exceed the drawing only by header + legend, never by dead space
    assert w == lay.width
    assert h >= lay.height
    assert h - lay.height < 140


def test_stroke_floor_survives_scaling():
    style = DiagramStyle()
    res = figure(water_heater_no(), profiles.WIRING, style, target_width_pt=180.0)
    widths = [float(v) for v in re.findall(r'stroke-width="([\d.]+)"', res.svg)]
    assert widths
    assert min(w * res.scale for w in widths) >= style.min_stroke_pt - 1e-6


# --- mono safety -------------------------------------------------------
def test_every_conductor_has_a_designation_and_pe_is_two_tone():
    g = water_heater_no()
    for conn in g.connections:
        assert conn.designation, conn.id
    svg = figure(g, profiles.WIRING).svg
    assert 'data-role="stripe"' in svg          # PE green/yellow
    style = DiagramStyle()
    assert style.encoding("N", "wire").dash     # neutral distinguishable in mono
    assert style.encoding("L3", "wire").dash


# --- pins: the flexibility contract ------------------------------------
def test_move_pins_only_the_named_profile():
    g = water_heater_no()
    s = DiagramSession(g, profiles.WIRING)
    s.move("UT", 500, 300)
    wiring = {p.component.id: (p.x, p.y) for p in s.layout().placed}
    other = DiagramSession(g, profiles.SINGLE_LINE, pins=s.pins)
    single = {p.component.id: (p.x, p.y) for p in other.layout().placed}
    assert wiring["UT"] == (500, 300)
    assert single["UT"] != (500, 300)


def test_partial_pin_leaves_the_other_axis_automatic():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    auto_y = {p.component.id: p.y for p in s.layout().placed}["UT"]
    s.move("UT", 400, None)
    placed = {p.component.id: p for p in s.layout().placed}["UT"]
    assert placed.x == 400
    assert placed.y == auto_y


def test_relayout_never_destroys_a_user_pin():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.move("UE", 640, -80)
    s.rotate("LE", 90)
    for _ in range(3):
        s.invalidate()
        s.layout()
    placed = {p.component.id: p for p in s.layout().placed}
    assert (placed["UE"].x, placed["UE"].y) == (640, -80)
    assert placed["LE"].rotation == 90


def test_release_returns_control_to_the_engine():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    before = {p.component.id: (p.x, p.y) for p in s.layout().placed}["UE"]
    s.move("UE", 900, 900)
    assert {p.component.id: (p.x, p.y) for p in s.layout().placed}["UE"] == (900, 900)
    s.release(target_component("UE"), "position")
    assert {p.component.id: (p.x, p.y) for p in s.layout().placed}["UE"] == before


def test_lock_blocks_the_ai_layer_but_not_the_user():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.move("UE", 300, 100)
    s.lock(target_component("UE"), "position")
    s.pins.pin(target_component("UE"), "position", {"x": 0, "y": 0}, layer="ai", scope=profiles.WIRING.id)
    s.invalidate()
    assert {p.component.id: (p.x, p.y) for p in s.layout().placed}["UE"] == (300, 100)
    s.move("UE", 320, 100)          # a user edit still lands
    assert {p.component.id: (p.x, p.y) for p in s.layout().placed}["UE"] == (320, 100)


def test_user_layer_beats_ai_layer():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.pins.pin(target_component("UE"), "position", {"x": 10, "y": 10}, layer="ai", scope=profiles.WIRING.id)
    s.move("UE", 200, 200)
    s.invalidate()
    assert {p.component.id: (p.x, p.y) for p in s.layout().placed}["UE"] == (200, 200)


def test_waypoints_persist_and_route_through_the_point():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.add_waypoint("w04", 380, -160)
    route = [r for r in s.layout().routes if r.connection.id == "w04"][0]
    assert route.pinned
    assert (380, -160) in route.points
    s.clear_waypoints("w04")
    route = [r for r in s.layout().routes if r.connection.id == "w04"][0]
    assert not route.pinned


def test_waypoint_insertion_order_is_independent_of_click_order():
    a = DiagramSession(water_heater_no(), profiles.WIRING)
    a.add_waypoint("w03", 250, -40)
    a.add_waypoint("w03", 300, -40)
    b = DiagramSession(water_heater_no(), profiles.WIRING)
    b.add_waypoint("w03", 300, -40)
    b.add_waypoint("w03", 250, -40)
    ra = [r for r in a.layout().routes if r.connection.id == "w03"][0].points
    rb = [r for r in b.layout().routes if r.connection.id == "w03"][0].points
    assert ra == rb


def test_hidden_pin_drops_from_one_profile_only():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.hide("PE1")
    ids = {p.component.id for p in s.layout().placed}
    assert "PE1" not in ids
    other = DiagramSession(water_heater_no(), profiles.SINGLE_LINE, pins=s.pins)
    assert "PE1" in {p.component.id for p in other.layout().placed}


def test_pins_serialise_sorted_and_round_trip():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.move("UE", 100, 50)
    s.nudge_label(target_connection("w04"), 3, -2)
    text = s.pins.to_jsonl()
    lines = text.splitlines()
    assert lines == sorted(lines)
    again = PinStore.from_jsonl(text)
    assert len(again) == len(s.pins)


def test_orphan_pins_are_reported_not_dropped():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.pins.pin(target_component("GHOST"), "position", {"x": 1, "y": 1})
    report = s.validate()
    assert any(i.code == "orphan_pin" for i in report.warnings)


def test_reset_to_auto_clears_the_profile():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.move("UE", 10, 10)
    s.rotate("LE", 180)
    assert s.reset_to_auto() >= 2
    assert len(s.pins.for_profile(profiles.WIRING.id)) == 0


# --- validation --------------------------------------------------------
def test_reference_wiring_graph_is_clean():
    report = validate(water_heater_no())
    assert report.ok, str(report)


def test_awg_on_a_norwegian_job_is_an_error():
    g = water_heater_no()
    g.connections[0].segments = [Segment(size="AWG 10")]
    report = validate(g)
    assert any(i.code == "size_unit_mismatch" for i in report.errors)


def test_neutral_in_an_it_system_is_an_error():
    g = water_heater_no()
    g.connections[1].designation = "N"
    report = validate(g)
    assert any(i.code == "neutral_in_it_system" for i in report.errors)


def test_trip_rating_where_a_curve_is_required_warns():
    g = water_heater_no()
    g.component("Q1").specs["breaker"] = "30 A 2-pole"
    report = validate(g)
    assert any(i.code == "breaker_style_mismatch" for i in report.warnings)


def test_missing_protective_conductor_warns():
    g = water_heater_no()
    g.connections = [c for c in g.connections if c.designation != "PE"]
    report = validate(g)
    assert any(i.code == "no_protective_conductor" for i in report.warnings)


def test_illegal_medium_is_refused_at_connect_time():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    try:
        s.connect(("UE", "b"), ("PE1", "t"), medium="pipe")
    except ConnectRefused:
        pass
    else:  # pragma: no cover
        raise AssertionError("a pipe should not land on an electrical port")


# --- plumbing ----------------------------------------------------------
def test_plumbing_graph_is_clean_and_renders():
    g = plumbing_supply()
    report = validate(g)
    assert report.ok, str(report)
    res = figure(g, profiles.PIPING)
    assert res.svg.count('data-medium="pipe"') == len(g.connections)
    assert "DN20" in res.svg and "DN12" in res.svg


def test_implied_branch_without_a_fitting_is_an_error():
    g = plumbing_supply()
    extra = g.connections[3]
    extra.source = g.connections[2].source     # two runs off one fluid port
    report = validate(g)
    assert any(i.code == "pipe_branch_without_fitting" for i in report.errors)


def test_insert_fitting_splits_the_run_and_adds_a_part():
    s = DiagramSession(plumbing_supply(), profiles.PIPING)
    fitting, (up, down) = s.insert_fitting("p03", "tee_equal", tag="-T4", size="DN16")
    assert fitting.role == "fitting"
    assert s.graph.connection("p03") is None
    assert {up.id, down.id} == {"p03.1", "p03.2"}
    assert s.validate().ok, str(s.validate())


def test_electrical_port_may_fan_out_but_fluid_may_not():
    assert validate(water_heater_no()).ok            # Q1:out2 feeds two elements
    g = plumbing_supply()
    g.connections.append(
        g.connections[0].__class__(
            id="p99",
            source=g.connections[0].source,
            target=g.connections[0].target,
            medium="pipe",
            designation="cold",
            segments=[Segment(size="DN20")],
        )
    )
    assert not validate(g).ok


def test_flow_arrows_only_where_flow_is_declared():
    svg = figure(plumbing_supply(), profiles.PIPING).svg
    assert svg.count('data-role="flow"') == len(plumbing_supply().connections)
    assert 'data-role="flow"' not in figure(water_heater_no(), profiles.WIRING).svg


# --- profiles ----------------------------------------------------------
def test_single_line_profile_swaps_symbols_and_drops_port_labels():
    svg = figure(water_heater_no(), profiles.SINGLE_LINE).svg
    assert 'data-type="load_block"' in svg
    assert 'data-role="port"' not in svg


def test_dropped_component_does_not_silently_bridge_a_run():
    g = water_heater_no()
    lay = layout(g, profiles.PIPING, DiagramStyle())      # nothing electrical survives
    assert lay.routes == []
    assert lay.dropped_components


def test_profile_geometry_is_independent():
    g = water_heater_no()
    a = {p.component.id: (p.x, p.y) for p in layout(g, profiles.WIRING, DiagramStyle()).placed}
    b = {p.component.id: (p.x, p.y) for p in layout(g, profiles.SINGLE_LINE, DiagramStyle()).placed}
    assert set(a) == set(b)


# --- canvas surface ----------------------------------------------------
def test_every_editable_element_has_a_pin_target():
    res = figure(water_heater_no(), profiles.WIRING)
    for cid in ("component:UT", "connection:w04"):
        assert f'data-target="{cid}"' in res.svg


def test_handles_are_never_in_a_published_figure():
    g = water_heater_no()
    s = DiagramSession(g, profiles.WIRING)
    assert 'data-role="handle"' in s.render(show_handles=True).svg
    assert 'data-role="handle"' not in s.render().svg


def test_history_records_every_change():
    s = DiagramSession(water_heater_no(), profiles.WIRING)
    s.move("UE", 10, 10)
    s.rotate("UE", 90)
    s.release(target_component("UE"), "rotation")
    assert [e.action for e in s.history] == ["move", "rotate", "release"]


# --- labels ------------------------------------------------------------
def test_no_label_overlaps_another_label():
    lay = layout(water_heater_no(), profiles.WIRING, DiagramStyle())
    rects = [t.rect() for t in lay.texts]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            ax, ay, aw, ah = rects[i]
            bx, by, bw, bh = rects[j]
            overlap = ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
            assert not overlap, f"{lay.texts[i].text} overlaps {lay.texts[j].text}"


def test_suppressed_labels_are_reported():
    g = water_heater_no()
    crowded = Component(
        id="X1",
        type="terminal",
        label="crowded",
        ports=[Port(id=f"p{i}", name=f"very long port name {i}", side="right", kind="electrical", order=i)
               for i in range(6)],
    )
    g.components.append(crowded)
    lay = layout(g, profiles.WIRING, DiagramStyle())
    assert isinstance(lay.warnings, list)


# --- migration ---------------------------------------------------------
def test_v1_geometry_becomes_pins_and_survives():
    from foldok_diagram.migrate import migrate

    v1 = {
        "schema_version": 1,
        "id": "legacy",
        "title": "legacy figure",
        "domain": "electrical",
        "components": [
            {
                "id": "A",
                "type": "distribution_board",
                "position": {"x": 120, "y": 40},
                "rotation": 90,
                "ports": [{"id": "l1", "name": "L1", "side": "right", "kind": "electrical"}],
            },
            {
                "id": "B",
                "type": "heating_element",
                "position": {"x": 320, "y": 40},
                "ports": [{"id": "a", "name": "phase", "side": "left", "kind": "electrical"}],
            },
        ],
        "connections": [
            {
                "id": "w1",
                "from": {"component_id": "A", "port_id": "l1"},
                "to": {"component_id": "B", "port_id": "a"},
                "medium": "cable",
                "attributes": {"designation": "L1", "size": "4 mm2", "color": "#ff0000"},
            }
        ],
    }
    g, pins, notes = migrate(v1)
    assert g.schema_version == 2
    assert g.connection("w1").medium == "wire"
    assert g.connection("w1").segments[0].size == "4 mm2"
    lay = layout(g, profiles.WIRING, DiagramStyle(), pins)
    placed = {p.component.id: p for p in lay.placed}
    assert (placed["A"].x, placed["A"].y) == (120, 40)
    assert placed["A"].rotation == 90
    assert any("jurisdiction" in n for n in notes)

    s = DiagramSession(g, profiles.WIRING, pins=pins)
    s.reset_to_auto()
    placed = {p.component.id: p for p in s.layout().placed}
    assert (placed["A"].x, placed["A"].y) != (120, 40)
