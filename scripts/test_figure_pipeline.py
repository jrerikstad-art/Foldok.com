"""Propose/confirm diagram tools + visual QA + figure embed."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import artifact_engine as ae  # noqa: E402
from diagram_engine import (  # noqa: E402
    DiagramEngine,
    confirm_diagram,
    list_diagram_templates,
    propose_diagram,
    visual_qa_engine,
)


class FigurePipelineTests(unittest.TestCase):
    def test_templates(self):
        ids = {t["id"] for t in list_diagram_templates()}
        self.assertTrue({"panel_sld", "pump_skid", "pipe_run"} <= ids)

    def test_propose_confirm_embed(self):
        prop = propose_diagram(template="panel_sld", title="DB-A single-line")
        self.assertEqual(prop["status"], "proposed")
        self.assertTrue(prop["confirm_required"])
        self.assertIn("<svg", prop["svg_preview"])
        conf = confirm_diagram(prop, confirm=True)
        self.assertEqual(conf["status"], "confirmed")
        self.assertTrue(conf["ready_to_embed"])

        eng = DiagramEngine().load_fixture("electrical_sld")
        doc = ae.Document(title="Manual", sections=[])
        doc = ae.embed_diagram_engine(
            doc, eng,
            caption="Main distribution overview",
            figure_number="4.1",
            source_citation="Panel schedule rev B",
            revision="A",
        )
        html = ae.render_document(doc)
        self.assertIn("Figure 4.1", html)
        self.assertIn("Panel schedule rev B", html)
        self.assertIn("data-figure=\"4.1\"", html)

    def test_visual_qa_fixtures(self):
        for name in ("electrical_sld", "piping", "mechanical", "hybrid"):
            qa = visual_qa_engine(DiagramEngine().load_fixture(name))
            self.assertTrue(qa["ok"], msg=f"{name}: {qa['issues']}")
            self.assertTrue(qa["checks"].get("has_svg"))


if __name__ == "__main__":
    unittest.main()
