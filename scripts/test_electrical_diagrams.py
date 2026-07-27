"""Electrical SLD / wiring diagram smoke tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_engine import (  # noqa: E402
    DiagramEngine,
    SLD_FIXTURE,
    WIRING_FIXTURE,
    list_symbols,
    normalize_electrical_graph,
    render_electrical_diagram,
    resolve_wire_color,
)


class ElectricalDiagramTests(unittest.TestCase):
    def test_symbol_pack(self):
        rows = list_symbols(domain="electrical")
        ids = {r["id"] for r in rows}
        self.assertGreaterEqual(len(ids), 20)
        for need in ("breaker", "rcd", "motor", "terminal_strip", "earth"):
            self.assertIn(need, ids)

    def test_wire_colors_iec(self):
        hex_c, label = resolve_wire_color("L1")
        self.assertTrue(hex_c.startswith("#"))
        self.assertIn("L1", label)
        pe, _ = resolve_wire_color("PE")
        self.assertNotEqual(pe, resolve_wire_color("N")[0])

    def test_normalize_terminals(self):
        g = normalize_electrical_graph({
            "type": "wiring",
            "components": [{
                "id": "A",
                "type": "breaker",
                "terminals": [{"id": "line", "name": "Line", "side": "top"}],
            }],
            "connections": [
                {"from": "A.line", "to": "A.load", "color": "L1"},
            ],
        })
        self.assertTrue(g["components"][0]["ports"])
        self.assertEqual(g["connections"][0]["from"]["port_id"], "line")
        self.assertEqual(g["connections"][0]["attributes"]["color"], "L1")

    def test_sld_deterministic(self):
        a = render_electrical_diagram(SLD_FIXTURE, mode="single_line")
        b = render_electrical_diagram(SLD_FIXTURE, mode="single_line")
        self.assertEqual(a, b)
        self.assertIn('data-layout="single_line"', a)
        self.assertIn("Wire colors", a)
        self.assertIn("RCD", a)

    def test_wiring_deterministic(self):
        a = render_electrical_diagram(WIRING_FIXTURE, mode="wiring")
        b = render_electrical_diagram(WIRING_FIXTURE, mode="wiring")
        self.assertEqual(a, b)
        self.assertIn('data-layout="wiring"', a)
        self.assertIn("stroke=", a)

    def test_engine_fixture_and_embed_path(self):
        eng = DiagramEngine().load_fixture("electrical_sld")
        svg = eng.render("svg")
        self.assertIn("electrical_diagram", svg)
        svg2 = eng.render_electrical("single_line")
        self.assertEqual(svg, svg2)
        w = DiagramEngine().load_fixture("electrical_wiring")
        self.assertIn("wiring", w.render_electrical("wiring"))


if __name__ == "__main__":
    unittest.main()
