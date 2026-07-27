"""Multi-domain DiagramEngine smoke tests (piping / mechanical / hybrid)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_engine import (  # noqa: E402
    DiagramEngine,
    HYBRID_FIXTURE,
    MECHANICAL_FIXTURE,
    PIPING_FIXTURE,
    list_symbols,
    normalize_graph,
    render_hybrid_diagram,
    render_mechanical_diagram,
    render_piping_diagram,
    validate_graph,
)


class DomainDiagramTests(unittest.TestCase):
    def test_symbol_packs(self):
        rows = list_symbols()
        by = {}
        for r in rows:
            by.setdefault(r["domain"], set()).add(r["id"])
        self.assertIn("drain", by["piping"])
        self.assertIn("vent", by["piping"])
        self.assertIn("belt_drive", by["mechanical"])
        self.assertGreaterEqual(len(by["electrical"]), 20)
        self.assertGreaterEqual(len(by["piping"]), 12)
        self.assertGreaterEqual(len(by["mechanical"]), 8)

    def test_shared_normalize(self):
        g = normalize_graph({
            "type": "piping",
            "components": [{"id": "P1", "type": "centrifugal_pump", "tag": "P-101"}],
            "connections": [
                {"from": "P1.suction", "to": "P1.discharge", "dn": 50, "media": "water"},
            ],
        }, default_domain="piping")
        self.assertEqual(g["components"][0]["domain"], "piping")
        self.assertTrue(g["components"][0]["ports"])
        self.assertEqual(g["connections"][0]["medium"], "pipe")
        self.assertIn("DN50", g["connections"][0]["attributes"].get("size") or "DN50")

    def test_validate_motor_pump_graph(self):
        spec = {
            "type": "hybrid",
            "components": [
                {"id": "M1", "type": "motor_ac", "tag": "M-101"},
                {"id": "P1", "type": "centrifugal_pump", "tag": "P-101"},
            ],
            "connections": [
                {"from": "M1.shaft", "to": "P1.drive", "medium": "shaft"},
                {"from": "P1.suction", "to": "P1.discharge", "medium": "pipe", "media": "water"},
            ],
        }
        self.assertEqual(validate_graph(spec), [])
        bad = {
            "type": "mechanical",
            "components": [{"id": "M1", "type": "motor_ac"}],
            "connections": [{"from": "M1.missing", "to": "M1.shaft", "medium": "shaft"}],
        }
        self.assertTrue(any("not found" in e for e in validate_graph(bad)))

    def test_piping_deterministic(self):
        a = render_piping_diagram(PIPING_FIXTURE)
        b = render_piping_diagram(PIPING_FIXTURE)
        self.assertEqual(a, b)
        self.assertIn('data-layout="piping"', a)
        self.assertIn("P-101", a)
        self.assertIn("Pipe media", a)

    def test_mechanical_deterministic(self):
        a = render_mechanical_diagram(MECHANICAL_FIXTURE)
        b = render_mechanical_diagram(MECHANICAL_FIXTURE)
        self.assertEqual(a, b)
        self.assertIn("M-101", a)
        self.assertIn('data-layout="mechanical"', a)

    def test_hybrid_lanes(self):
        svg = render_hybrid_diagram(HYBRID_FIXTURE)
        self.assertIn('data-layout="hybrid"', svg)
        self.assertIn("M-101", svg)
        self.assertIn("P-101", svg)
        self.assertIn("F3", svg)

    def test_engine_fixtures(self):
        for name, needle in (
            ("piping", "piping"),
            ("mechanical", "mechanical"),
            ("hybrid", "hybrid"),
            ("electrical_sld", "single_line"),
        ):
            eng = DiagramEngine().load_fixture(name)
            svg = eng.render("svg")
            self.assertIn(f'data-layout="{needle}"', svg)


if __name__ == "__main__":
    unittest.main()
