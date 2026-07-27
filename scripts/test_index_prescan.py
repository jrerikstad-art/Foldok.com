"""WORKORDER 0.55 — pre-scan + scope filter tests (no API key)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import index_prescan as ps  # noqa: E402


class IndexPrescanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "Bilder").mkdir()
        (self.root / "Docs").mkdir()
        (self.root / "Video").mkdir()
        (self.root / "Bilder" / "a.jpg").write_bytes(b"\xff\xd8\xff" + b"0" * 100)
        (self.root / "Docs" / "spec.pdf").write_bytes(b"%PDF-1.4 " + b"0" * 5000)
        (self.root / "Docs" / "notes.txt").write_text("hello", encoding="utf-8")
        (self.root / "Video" / "clip.mp4").write_bytes(b"0" * 200)
        # Oversize stub
        big = self.root / "Docs" / "huge.bin"
        big.write_bytes(b"0" * (ps.OVERSIZE_BYTES + 10))

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_counts_and_skips(self):
        report = ps.scan_folders([self.root], check_cache=False)
        self.assertGreaterEqual(report["total_files"], 4)
        self.assertGreaterEqual(report["indexable"], 3)  # jpg + pdf + txt
        self.assertGreaterEqual(report["skipped"], 1)  # mp4 and/or oversize
        self.assertEqual(len(report["est_cost_eur"]), 2)
        self.assertLessEqual(report["est_cost_eur"][0], report["est_cost_eur"][1])
        self.assertIn(".jpg", report["by_ext"])
        self.assertFalse(report["needs_decision_card"])  # tiny tree

    def test_filter_documents_only(self):
        files = [
            (self.root / "Bilder" / "a.jpg", "Bilder/a.jpg", self.root / ".foldok_cache"),
            (self.root / "Docs" / "spec.pdf", "Docs/spec.pdf", self.root / ".foldok_cache"),
            (self.root / "Docs" / "notes.txt", "Docs/notes.txt", self.root / ".foldok_cache"),
        ]
        docs = ps.filter_pending(files, mode="documents")
        rels = [r for _, r, _ in docs]
        self.assertIn("Docs/spec.pdf", rels)
        self.assertIn("Docs/notes.txt", rels)
        self.assertNotIn("Bilder/a.jpg", rels)

    def test_filter_subfolders(self):
        files = [
            (self.root / "Bilder" / "a.jpg", "Bilder/a.jpg", self.root / ".foldok_cache"),
            (self.root / "Docs" / "spec.pdf", "Docs/spec.pdf", self.root / ".foldok_cache"),
        ]
        only = ps.filter_pending(files, mode="all", subfolders=["Docs"])
        self.assertEqual([r for _, r, _ in only], ["Docs/spec.pdf"])

    def test_decision_threshold(self):
        self.assertEqual(ps.PRESCAN_THRESHOLD, 200)


if __name__ == "__main__":
    unittest.main()
