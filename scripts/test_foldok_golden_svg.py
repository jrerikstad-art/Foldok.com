"""Golden SVG regression for foldok_diagram samples (WO 0.63 T6)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foldok_diagram import DiagramSession, DiagramStyle, figure  # noqa: E402
from foldok_diagram import profile as profiles  # noqa: E402
from foldok_diagram.examples import plumbing_supply, water_heater_no  # noqa: E402


def _golden(name: str) -> Path:
    return ROOT / "foldok_diagram" / name


class GoldenSvgTests(unittest.TestCase):
    def test_water_heater_wiring_matches_golden(self):
        svg = figure(water_heater_no(), profiles.WIRING, DiagramStyle()).svg
        golden = _golden("wiring_water_heater.svg")
        self.assertTrue(golden.exists(), "missing golden file")
        self.assertEqual(svg, golden.read_text(encoding="utf-8"))

    def test_plumbing_supply_matches_golden(self):
        svg = figure(plumbing_supply(), profiles.PIPING, DiagramStyle()).svg
        golden = _golden("piping_supply.svg")
        self.assertTrue(golden.exists(), "missing golden file")
        self.assertEqual(svg, golden.read_text(encoding="utf-8"))

    def test_pinned_move_matches_golden(self):
        g = water_heater_no()
        s = DiagramSession(g, profiles.WIRING)
        s.move("UT", 500, 300)
        svg = s.render(show_handles=True).svg
        golden = _golden("wiring_pinned.svg")
        self.assertTrue(golden.exists(), "missing golden file")
        self.assertEqual(svg, golden.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
