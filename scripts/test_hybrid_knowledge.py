"""Tests for HybridKnowledgeEngine (Excel registry; vectors optional)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hybrid_knowledge_engine import HybridKnowledgeEngine  # noqa: E402


class HybridKnowledgeEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        # Disable vectors so tests don't need lancedb
        self.eng = HybridKnowledgeEngine(self.root, enable_vectors=False)

    def tearDown(self):
        self.tmp.cleanup()

    def test_registry_created(self):
        path = Path(self.root) / "project_findings.xlsx"
        self.assertTrue(path.exists())

    def test_update_and_get(self):
        fid = self.eng.update_finding({
            "source_file": "drawings/pump.step",
            "source_type": "CAD",
            "component": "Impeller",
            "property": "Outer Diameter",
            "value": "125.4",
            "unit": "mm",
            "citation": "STEP: Impeller.OD",
        })
        self.assertTrue(fid.startswith("FIND-"))
        rows = self.eng.get_findings(component="Impeller", property_name="Diameter")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value"], "125.4")
        self.assertEqual(rows[0]["citation"], "STEP: Impeller.OD")

    def test_update_existing(self):
        fid = self.eng.update_finding({
            "finding_id": "FIND-TEST-1",
            "source_file": "a.pdf",
            "source_type": "doc",
            "component": "Pump",
            "property": "Power",
            "value": "5",
            "unit": "kW",
            "citation": "a.pdf p.2",
        })
        self.eng.update_finding({
            "finding_id": fid,
            "source_file": "a.pdf",
            "source_type": "doc",
            "component": "Pump",
            "property": "Power",
            "value": "7.5",
            "unit": "kW",
            "citation": "a.pdf p.2",
        })
        rows = self.eng.get_findings(component="Pump")
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0]["value"]), "7.5")

    def test_semantic_fallback(self):
        self.eng.update_finding({
            "source_file": "pump.step",
            "source_type": "CAD",
            "component": "Impeller",
            "property": "Outer Diameter",
            "value": "125.4",
            "unit": "mm",
            "citation": "STEP",
        })
        hits = self.eng.semantic_search("impeller outer diameter")
        self.assertGreaterEqual(len(hits), 1)

    def test_import_index_facts(self):
        ids = self.eng.import_from_index_facts([{
            "file": "spec.pdf",
            "kind": "doc",
            "facts": [{
                "id": "abc-1",
                "key": "mass",
                "fact_type": "spec",
                "value": "12",
                "unit": "kg",
                "confidence": 0.9,
                "source_excerpt": "mass 12 kg",
                "source_location": "p.3",
            }],
        }])
        self.assertEqual(len(ids), 1)
        rows = self.eng.get_findings(property_name="mass")
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0]["value"]), "12")

    def test_index_project(self):
        result = self.eng.index_project()
        self.assertEqual(result["rows"], 0)
        self.assertTrue(result["registry_path"].endswith("project_findings.xlsx"))


if __name__ == "__main__":
    unittest.main()
