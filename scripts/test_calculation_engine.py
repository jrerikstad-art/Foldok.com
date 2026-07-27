"""Calculation engine — library formulas, fact bind, confirm workflow."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import calculation_engine as ce  # noqa: E402
from artifact_engine.model.blocks import CalculationBlock, block_from_dict  # noqa: E402
from artifact_engine.render.html import HTMLRenderer  # noqa: E402


class CalculationEngineTest(unittest.TestCase):
    def setUp(self):
        ce.reload_profiles()

    def test_profiles_loaded(self):
        ids = {p["id"] for p in ce.list_profiles()}
        need = {
            "rect_area", "circle_area", "volume_rect", "cable_length_simple",
            "ohms_law", "power_dc", "wind_dynamic_pressure", "utilization",
        }
        self.assertTrue(need <= ids)

    def test_safe_eval_and_reject_bad(self):
        self.assertAlmostEqual(ce.evaluate_formula("L * W", {"L": 2, "W": 3}), 6.0)
        self.assertAlmostEqual(
            ce.evaluate_formula("0.613 * V ** 2", {"V": 24}),
            0.613 * 24 ** 2,
            places=3,
        )
        with self.assertRaises(ce.FormulaError):
            ce.evaluate_formula("__import__('os').system('x')", {})
        with self.assertRaises(ce.FormulaError):
            ce.evaluate_formula("open('/etc/passwd')", {})

    def test_unit_convert(self):
        self.assertAlmostEqual(ce.convert_unit(1000, "mm", "m"), 1.0)
        self.assertAlmostEqual(ce.convert_unit(36, "km/h", "m/s"), 10.0)
        self.assertIsNone(ce.convert_unit(1, "m", "Pa"))

    def test_bind_and_ready(self):
        index = [
            {"key": "length", "value": 4, "unit": "m", "source": "drawing A"},
            {"key": "width", "value": 2.5, "unit": "m", "source": "drawing A"},
        ]
        calc = ce.create_calculation("rect_area", index=index)
        self.assertEqual(calc["status"], "ready_for_review")
        self.assertAlmostEqual(calc["outputs"][0]["value"], 10.0)
        self.assertFalse(calc["certified_result"])
        self.assertIn("Library formula", calc["disclaimer"])

    def test_missing_needs_input(self):
        calc = ce.create_calculation("ohms_law", index=[])
        self.assertEqual(calc["status"], "needs_input")
        calc = ce.set_input(calc, "I", 2)
        self.assertEqual(calc["status"], "needs_input")
        calc = ce.set_input(calc, "R", 5)
        self.assertEqual(calc["status"], "ready_for_review")
        self.assertAlmostEqual(calc["outputs"][0]["value"], 10.0)

    def test_ambiguous_conflict(self):
        index = [
            {"key": "wind_speed", "value": 20, "unit": "m/s", "source": "note1"},
            {"key": "wind_speed", "value": 24, "unit": "m/s", "source": "note2"},
        ]
        calc = ce.create_calculation("wind_dynamic_pressure", index=index)
        self.assertEqual(calc["status"], "needs_input")
        wind = next(i for i in calc["inputs"] if i["key"] == "V")
        self.assertEqual(wind["status"], "ambiguous")

    def test_confirm_and_block(self):
        calc = ce.create_calculation(
            "power_dc",
            user_inputs={"V": 12, "I": 2},
        )
        confirmed = ce.confirm_calculation(calc, confirmed_by="tester")
        self.assertEqual(confirmed["status"], "confirmed")
        text = ce.render_calculation_text(confirmed)
        self.assertIn("24", text)
        self.assertIn("User confirmed", text)
        block = ce.calculation_to_block(confirmed)
        self.assertEqual(block["type"], "calculation")
        self.assertEqual(block["status"], "confirmed")
        ast_block = block_from_dict(block)
        self.assertIsInstance(ast_block, CalculationBlock)
        r = HTMLRenderer()
        out = r._render_calculation(ast_block)
        self.assertIn("calculation-block", out)
        self.assertIn("Confirmed", out)

    def test_cannot_confirm_incomplete(self):
        calc = ce.create_calculation("utilization", index=[])
        with self.assertRaises(ValueError):
            ce.confirm_calculation(calc)

    def test_suggest_intent(self):
        ids = ce.suggest_profiles(intent="wind pressure dynamic")
        self.assertIn("wind_dynamic_pressure", ids)

    def test_circle_area_pi(self):
        calc = ce.create_calculation("circle_area", user_inputs={"r": 1})
        self.assertAlmostEqual(calc["outputs"][0]["value"], math.pi, places=4)

    def test_set_input_unlocks_confirm(self):
        calc = ce.create_calculation("rect_area", user_inputs={"L": 2, "W": 3})
        calc = ce.confirm_calculation(calc)
        self.assertEqual(calc["status"], "confirmed")
        calc = ce.set_input(calc, "W", 4)
        self.assertEqual(calc["status"], "ready_for_review")
        self.assertIsNone(calc["confirmed_at"])
        self.assertAlmostEqual(calc["outputs"][0]["value"], 8.0)


if __name__ == "__main__":
    unittest.main()
