"""Materials knowledge + steel/GFRP schema (Quantity + nested packs)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import calculation_engine as ce  # noqa: E402
import materials_engine as me  # noqa: E402
from artifact_engine.model.blocks import MaterialBlock, block_from_dict  # noqa: E402
from artifact_engine.render.html import HTMLRenderer  # noqa: E402


class MaterialsSchemaTest(unittest.TestCase):
    def setUp(self):
        me.reload()
        ce.reload_profiles()

    def test_steel_grades_quantity(self):
        ids = {m["id"] for m in me.list_materials(family="steel")}
        self.assertTrue({"steel_s235", "steel_s355", "steel_s460"} <= ids)
        s355 = me.get_material("S355")
        self.assertIsNotNone(s355)
        self.assertEqual(s355.get("designation"), "S355")
        self.assertEqual(s355.get("standard_family"), "EN 10025 family")
        fy = s355["properties"]["fy"]
        self.assertEqual(fy["status"], "assumed")
        self.assertEqual(fy["source"], "profile_default")
        self.assertAlmostEqual(me.property_value(s355, "fy"), 355.0)
        # E stored as GPa — convert to MPa when requested
        self.assertAlmostEqual(me.property_value(s355, "E", unit="MPa"), 210000.0)

    def test_sections_ipe200(self):
        ipe = me.get_section("IPE200")
        self.assertIsNotNone(ipe)
        self.assertEqual(ipe.get("family"), "ipe")
        self.assertIn("geometry", ipe)
        self.assertAlmostEqual(me.property_value(ipe, "A"), 2850.0)
        self.assertIsNotNone(me.get_section("IPE 200"))
        self.assertIsNotNone(me.get_section("ipe_200"))

    def test_gfrp_template_xt(self):
        g = me.get_material("gfrp_template")
        self.assertTrue(g.get("template") or g.get("status") == "user_defined")
        self.assertIsNone(me.property_value(g, "Xt"))
        filled = me.apply_property_overrides(
            g, {"Xt": {"value": 240, "unit": "MPa", "source": "datasheet_ref"}},
            source="datasheet_ref",
        )
        self.assertAlmostEqual(me.property_value(filled, "Xt"), 240.0)
        self.assertAlmostEqual(me.property_value(filled, "ft1"), 240.0)  # alias sync
        self.assertEqual(filled.get("status"), "from_datasheet")

    def test_runtime_steel_axial_instance(self):
        # Schema runtime example: N_ed=180 kN, S355, IPE200 → N_rd=1011.75, U≈0.178
        calc = ce.create_calculation(
            "steel_axial_tension_simple",
            material_id="steel_s355",
            section_id="IPE200",
            user_inputs={"N_ed": 180},
        )
        self.assertEqual(calc["status"], "ready_for_review")
        self.assertFalse(calc["code_compliance_claimed"])
        fy = next(i for i in calc["inputs"] if i["key"] == "fy")
        self.assertEqual(fy["status"], "assumed")
        nrd = next(o for o in calc["outputs"] if o["key"] == "N_rd")
        u = next(o for o in calc["outputs"] if o["key"] == "U")
        self.assertAlmostEqual(nrd["value"], 1011.75, places=2)
        self.assertAlmostEqual(u["value"], 180 / 1011.75, places=3)
        # Alias profile id still works
        calc2 = ce.create_calculation(
            "steel_axial_tension",
            material_id="steel_s355",
            section_id="IPE200",
            user_inputs={"NEd": 180},
        )
        self.assertEqual(calc2["status"], "ready_for_review")

    def test_steel_bending_unfactored(self):
        calc = ce.create_calculation(
            "steel_bending_simple",
            material_id="steel_s355",
            section_id="IPE200",
            user_inputs={"M_ed": 40},
        )
        self.assertEqual(calc["status"], "ready_for_review")
        mrd = next(o for o in calc["outputs"] if o["key"] == "M_rd")
        self.assertAlmostEqual(mrd["value"], 194300 * 355 / 1e6, places=2)

    def test_gfrp_axial_needs_xt(self):
        calc = ce.create_calculation(
            "gfrp_axial_tension_simple",
            material_id="gfrp_template",
            user_inputs={"N_ed": 10, "A": 500},
        )
        self.assertEqual(calc["status"], "needs_input")
        calc2 = ce.create_calculation(
            "gfrp_axial_tension_simple",
            material_id="gfrp_template",
            material_overrides={"Xt": 400},
            user_inputs={"N_ed": 10, "A": 500},
        )
        self.assertEqual(calc2["status"], "ready_for_review")
        self.assertIn("manufacturer", " ".join(calc2.get("messages") or []).lower())

    def test_multi_statement_formula(self):
        r = ce.evaluate_formula_program("N_rd = A * fy / 1000; U = N_ed / N_rd", {
            "A": 2850, "fy": 355, "N_ed": 180,
        })
        self.assertAlmostEqual(r["N_rd"], 1011.75, places=2)
        self.assertAlmostEqual(r["U"], 180 / 1011.75, places=4)

    def test_material_block(self):
        _, binding = me.resolve_binds(
            {"binds": {"fy": {"from": "material.fy", "unit": "MPa"}}},
            material_id="steel_s355",
            section_id="IPE200",
        )
        block = me.material_to_block(binding)
        ast_b = block_from_dict(block)
        self.assertIsInstance(ast_b, MaterialBlock)
        html = HTMLRenderer()._render_material(ast_b)
        self.assertIn("material-block", html)


if __name__ == "__main__":
    unittest.main()
