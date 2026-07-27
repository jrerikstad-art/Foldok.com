"""HybridKnowledgeEngine location + schema tests (no network required for set_location with coords)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hybrid_knowledge_engine import HybridKnowledgeEngine, LOCATION_FINDING_ID  # noqa: E402


class LocationKnowledgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.eng = HybridKnowledgeEngine(self.root, enable_vectors=False)

    def tearDown(self):
        self.tmp.cleanup()

    def test_schema_has_location_columns(self):
        from hybrid_knowledge_engine import REGISTRY_COLUMNS
        for col in ("address", "municipality", "latitude", "longitude",
                    "map_image_path", "map_style", "location_type", "postal_code"):
            self.assertIn(col, REGISTRY_COLUMNS)

    def test_set_get_location_with_coords(self):
        loc = self.eng.set_location(
            "Testveien 1",
            municipality="Demo City",
            postal_code="0001",
            latitude=58.85,
            longitude=5.74,
            geocode_if_needed=False,
        )
        self.assertEqual(loc["finding_id"], LOCATION_FINDING_ID)
        self.assertEqual(loc["address"], "Testveien 1")
        self.assertEqual(loc["municipality"], "Demo City")
        self.assertAlmostEqual(float(loc["latitude"]), 58.85)
        got = self.eng.get_location()
        self.assertEqual(got["postal_code"], "0001")

    def test_generate_map_writes_under_assets(self):
        self.eng.set_location(
            "Testveien 1", municipality="Demo City",
            latitude=58.85, longitude=5.74, geocode_if_needed=False,
        )

        def fake_render(lat, lon, out_path, **kw):
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_bytes(b"\x89PNG\r\n\x1a\nfake")
            return out_path

        with patch("tools.osm_vector_tiles.render_location_map", fake_render):
            rel = self.eng.generate_location_map(style="technical")
        self.assertTrue(rel.startswith("assets/maps/"))
        self.assertTrue((Path(self.root) / rel).exists())
        loc = self.eng.get_location()
        self.assertEqual(loc["map_image_path"], rel)
        self.assertEqual(loc["map_style"], "technical")

    def test_propose_needs_confirm(self):
        self.eng.set_location(
            "Testveien 1", latitude=58.85, longitude=5.74, geocode_if_needed=False,
        )

        def fake_render(lat, lon, out_path, **kw):
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_bytes(b"fake")
            return out_path

        with patch("tools.osm_vector_tiles.render_location_map", fake_render):
            prop = self.eng.propose_location_map(style="default")
        self.assertTrue(prop["needs_confirm"])
        self.assertEqual(prop["block_type"], "ImageBlock")
        self.assertIn("path", prop["image"])


if __name__ == "__main__":
    unittest.main()
