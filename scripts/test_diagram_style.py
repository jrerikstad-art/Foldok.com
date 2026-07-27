"""Golden test: same graph + DiagramStyle → identical SVG hash."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from artifact_engine.diagram_style import get_diagram_style  # noqa: E402
from artifact_engine.design_system import get_design_system  # noqa: E402
from diagram_engine import DiagramEngine, render_electrical_diagram  # noqa: E402
from diagram_engine.electrical import SLD_FIXTURE  # noqa: E402


def _hash(svg: str) -> str:
    return hashlib.sha256(svg.encode("utf-8")).hexdigest()


class DiagramStyleTests(unittest.TestCase):
    def test_style_loads_from_yaml(self):
        from artifact_engine.diagram_style import clear_diagram_style_cache
        clear_diagram_style_cache()
        s = get_diagram_style("engineering_default")
        self.assertEqual(s.id, "engineering_default")
        self.assertEqual(s.canvas.background, "#FFFFFF")
        self.assertTrue(s.routing.orthogonal)
        self.assertEqual(s.ports.snap_radius, 10.0)
        self.assertEqual(s.gaps.min_label, 8.0)
        hex_c, _ = s.wire_hex("PE")
        self.assertEqual(hex_c, "#16A34A")

    def test_design_system_bridge(self):
        ds = get_design_system("engineering")
        self.assertEqual(ds.diagram_style_id, "engineering_default")
        self.assertEqual(ds.diagram_style().id, "engineering_default")

    def test_golden_hash_same_graph_style(self):
        style = get_diagram_style()
        a = render_electrical_diagram(SLD_FIXTURE, mode="single_line", style=style)
        b = render_electrical_diagram(SLD_FIXTURE, mode="single_line", style=style)
        self.assertEqual(a, b)
        self.assertEqual(_hash(a), _hash(b))
        self.assertIn('data-diagram-style="engineering_default"', a)

    def test_engine_uses_style(self):
        eng = DiagramEngine().load_fixture("piping")
        svg = eng.render("svg")
        self.assertIn("data-diagram-style=", svg)
        eng2 = DiagramEngine().set_diagram_style("engineering_default").load_fixture("piping")
        self.assertEqual(eng.render("svg"), eng2.render("svg"))


if __name__ == "__main__":
    unittest.main()
