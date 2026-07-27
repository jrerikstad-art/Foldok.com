"""Diagram → document bridge."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))

import diagram_document as ddoc  # noqa: E402


class DiagramDocumentTest(unittest.TestCase):
    def test_resolve_targets(self):
        t = ddoc.resolve_target("installation_guide")
        self.assertEqual(t["template"], "installation_manual.json")
        self.assertEqual(t["section"], "system_overview")
        t2 = ddoc.resolve_target("samsvar", "work_description")
        self.assertEqual(t2["document_type"], "samsvarserklaring")
        self.assertEqual(t2["section"], "work_description")

    def test_insert_into_section(self):
        state = {"doc": {"sections": {}}}
        md = ddoc.diagram_markdown(
            title="WH",
            graph_id="wh1",
            profile="wiring",
            jurisdiction="NO_IT_230",
            svg="<svg/>",
        )
        sec = ddoc.insert_into_section(
            state,
            section_key="system_overview",
            md=md,
            svg="<svg/>",
            graph={"id": "wh1", "components": [], "connections": []},
            paths={"graph": "diagrams/wh1.json"},
            profile="wiring",
        )
        self.assertEqual(sec["block_type"], "DiagramBlock")
        self.assertIn("<svg/>", state["doc"]["sections"]["system_overview"]["md"])
        self.assertEqual(sec["foldok_diagram"]["graph_id"], "wh1")


if __name__ == "__main__":
    unittest.main()
