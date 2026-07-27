"""Canvas editor — graph mutations + engine SVG preview."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_engine import (  # noqa: E402
    AFFORDANCES,
    DiagramCanvasEditor,
    DiagramDocument,
)


class CanvasEditorTests(unittest.TestCase):
    def test_place_move_connect_render(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="piping", title="Test line"))
        tank = ed.place_component("tank_vertical", {"x": 100, "y": 120}, tag="T-101")
        pump = ed.place_component("centrifugal_pump", {"x": 220, "y": 120}, tag="P-101")
        self.assertIn("T-101", ed.doc.svg)
        self.assertIn('data-layout="manual_piping"', ed.doc.svg)

        # Grid snap (step 8)
        ed.move_components([pump["id"]], {pump["id"]: {"x": 221, "y": 119}})
        pos = next(c["position"] for c in ed.doc.graph["components"] if c["id"] == pump["id"])
        self.assertEqual(pos["x"] % 8, 0)
        self.assertEqual(pos["y"] % 8, 0)

        edge = ed.connect(f"{tank['id']}.outlet", f"{pump['id']}.suction", medium="pipe")
        self.assertTrue(edge["id"])
        self.assertIn("data-connection=", ed.doc.svg)
        self.assertGreater(ed.doc.revision, 2)

    def test_illegal_connection_rejected(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="hybrid"))
        m = ed.place_component("motor_ac", {"x": 80, "y": 100}, tag="M-1")
        v = ed.place_component("valve_ball", {"x": 200, "y": 100}, tag="V-1", domain="piping")
        with self.assertRaises(ValueError):
            ed.connect(f"{m['id']}.shaft", f"{v['id']}.in", medium="shaft")

    def test_delete_component_removes_edges(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="piping"))
        a = ed.place_component("valve_ball", {"x": 80, "y": 100})
        b = ed.place_component("valve_check", {"x": 200, "y": 100})
        ed.connect(f"{a['id']}.out", f"{b['id']}.in")
        self.assertEqual(len(ed.doc.graph["connections"]), 1)
        ed.set_selection(component_ids=[a["id"]])
        ed.delete_selection()
        self.assertEqual(len(ed.doc.graph["components"]), 1)
        self.assertEqual(len(ed.doc.graph["connections"]), 0)

    def test_hit_test_ports(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="mechanical"))
        m = ed.place_component("motor_ac", {"x": 160, "y": 140}, tag="M-101")
        spots = ed.hotspots()
        ports = [h for h in spots if h["kind"] == "port" and h["meta"]["component_id"] == m["id"]]
        self.assertGreaterEqual(len(ports), 2)
        hit = ed.hit_test(ports[0]["x"], ports[0]["y"])
        self.assertIsNotNone(hit)
        self.assertEqual(hit["kind"], "port")
        self.assertIn("port_hit_radius_pt", AFFORDANCES)

    def test_figure_payload(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="piping", title="Feed"))
        ed.place_component("strainer", {"x": 100, "y": 100}, tag="Y-1")
        fig = ed.figure_payload()
        self.assertEqual(fig["type"], "diagram")
        self.assertIn("<svg", fig["svg"])
        self.assertEqual(fig["style_id"], "engineering_default")
        self.assertTrue(fig["visual_qa"]["ok"] or fig["visual_qa"]["n_errors"] == 0)

    def test_auto_arrange(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="piping"))
        ed.place_component("tank_vertical", {"x": 10, "y": 10})
        ed.place_component("centrifugal_pump", {"x": 20, "y": 20})
        ed.auto_arrange()
        xs = [c["position"]["x"] for c in ed.doc.graph["components"]]
        self.assertGreater(max(xs) - min(xs), 50)

    def test_water_heater_move_keeps_connections(self):
        from copy import deepcopy
        from diagram_engine.electrical import WATER_HEATER_240V_FIXTURE, normalize_electrical_graph
        from diagram_engine.manual_layout import ensure_positions

        g = ensure_positions(
            normalize_electrical_graph(deepcopy(WATER_HEATER_240V_FIXTURE)),
            profile="wiring",
        )
        g["layout_mode"] = "manual"
        ed = DiagramCanvasEditor(
            DiagramDocument.from_graph(g, profile="wiring", title="WH"),
        )
        before = [
            (e.get("id"), e.get("from"), e.get("to"))
            for e in ed.doc.graph["connections"]
        ]
        ut = next(c for c in ed.doc.graph["components"] if c["id"] == "UT")
        ed.move_components(["UT"], {"UT": {"x": ut["position"]["x"] + 40, "y": ut["position"]["y"] + 24}})
        after = [
            (e.get("id"), e.get("from"), e.get("to"))
            for e in ed.doc.graph["connections"]
        ]
        self.assertEqual(before, after)
        self.assertIn("#16A34A", ed.doc.svg)  # PE green
        self.assertIn("#A0522D", ed.doc.svg)  # L1

    def test_style_ports_and_gaps(self):
        from artifact_engine.diagram_style import clear_diagram_style_cache, get_diagram_style
        clear_diagram_style_cache()
        s = get_diagram_style()
        self.assertEqual(s.ports.snap_radius, 10.0)
        self.assertEqual(s.gaps.min_component, 28.0)
        self.assertEqual(s.routing.stub_length, 12.0)
        self.assertEqual(s.wire_stroke_width("PE"), s.strokes.wire_PE)

    def test_port_snap_and_finish_connect(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="piping"))
        a = ed.place_component("valve_ball", {"x": 80, "y": 100})
        b = ed.place_component("valve_check", {"x": 240, "y": 100})
        spots = [h for h in ed.hotspots() if h["kind"] == "port" and h["meta"]["component_id"] == b["id"]]
        target = next(h for h in spots if h["meta"]["port_id"] == "in")
        ed.begin_connect(f"{a['id']}.out")
        # Near but not exact — snap_radius 10
        hover = ed.preview_connect_at(target["x"] + 4, target["y"] - 3)
        self.assertIsNotNone(hover)
        self.assertEqual(hover["id"], f"{b['id']}.in")
        edge = ed.finish_connect_at(target["x"] + 4, target["y"] - 3)
        self.assertIsNotNone(edge)
        self.assertEqual(len(ed.doc.graph["connections"]), 1)

    def test_label_placement_avoids_symbol(self):
        from artifact_engine.diagram_style import get_diagram_style
        from diagram_engine.labels import place_component_label

        st = get_diagram_style()
        # Two close tags — second should not sit on preferred "above" of first if colliding
        a = place_component_label("UT", 200, 200, st)
        b = place_component_label(
            "HEATER", 200, 200, st,
            occupied=[a], symbol_centers=[(200, 200)],
        )
        self.assertNotEqual((a.x, a.y, a.side), (b.x, b.y, b.side))
        # Neither box should deeply cover symbol center
        self.assertFalse(abs(b.x - 200) < 8 and abs(b.y - 200) < 8)

    def test_move_component_contract(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="wiring"))
        c = ed.place_component("switch", {"x": 100, "y": 100}, tag="S1")
        before_ids = [e["id"] for e in ed.doc.graph["connections"]]
        moved = ed.move_component(c["id"], 133, 157)
        self.assertEqual(moved["position"]["x"] % 8, 0)
        self.assertEqual(moved["position"]["y"] % 8, 0)
        self.assertEqual([e["id"] for e in ed.doc.graph["connections"]], before_ids)
        ed.refresh()
        self.assertIn("data-layout=\"manual_wiring\"", ed.doc.svg)

    def test_auto_spread(self):
        ed = DiagramCanvasEditor(DiagramDocument(profile="wiring"))
        a = ed.place_component("mcb", {"x": 200, "y": 200}, tag="Q1")
        b = ed.place_component("switch", {"x": 200, "y": 200}, tag="S1")
        ed.auto_spread()
        pa = next(c["position"] for c in ed.doc.graph["components"] if c["id"] == a["id"])
        pb = next(c["position"] for c in ed.doc.graph["components"] if c["id"] == b["id"])
        self.assertTrue(abs(pa["x"] - pb["x"]) > 8 or abs(pa["y"] - pb["y"]) > 8)


if __name__ == "__main__":
    unittest.main()
