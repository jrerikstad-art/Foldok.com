"""Unit tests for index_tools (reindex / diff_index / update helpers)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import index_tools as idx  # noqa: E402


class FakeFc:
    PHOTO_EXT = {".jpg", ".png"}
    DOC_EXT = {".pdf", ".md"}
    CAD_EXT = {".step"}

    @staticmethod
    def read_json_file(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))


def _touch(p: Path, data: bytes = b"hello"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


class IndexToolsTest(unittest.TestCase):
    def test_diff_inventories(self):
        before = {"a.pdf": {"sha": "1", "type": "doc", "path": "a.pdf"}}
        after = {
            "a.pdf": {"sha": "2", "type": "doc", "path": "a.pdf"},
            "b.pdf": {"sha": "3", "type": "doc", "path": "b.pdf"},
        }
        d = idx.diff_inventories(before, after)
        self.assertEqual([x["path"] for x in d["added"]], ["b.pdf"])
        self.assertEqual([x["path"] for x in d["changed"]], ["a.pdf"])
        self.assertEqual(d["removed"], [])
        self.assertEqual(idx.delta_count(d), 2)

    def test_reindex_plan_confirm_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = root / ".foldok_cache"
            cache.mkdir()
            # Seed a baseline with 0 files
            idx.save_manifest(root, {"index_version": "1", "files": {}})

            files = []
            for i in range(16):
                p = root / f"f{i}.pdf"
                _touch(p, f"content-{i}".encode())
                files.append((p, p.name, cache))

            def source_files(_folders):
                return files

            plan = idx.reindex_plan(root, [str(root)], FakeFc, source_files, confirm=False)
            self.assertTrue(plan["needs_confirm"])
            self.assertEqual(plan["delta_count"], 16)

            plan2 = idx.reindex_plan(root, [str(root)], FakeFc, source_files, confirm=True)
            self.assertFalse(plan2["needs_confirm"])

    def test_commit_manifest_bumps_version(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cache = root / ".foldok_cache"
            cache.mkdir()
            p = root / "doc.pdf"
            _touch(p, b"abc")
            sha = __import__("hashlib").sha256(b"abc").hexdigest()
            (cache / f"{sha}.json").write_text(
                json.dumps({"file": "doc.pdf", "facts": [], "caption": "x"}),
                encoding="utf-8",
            )

            def source_files(_folders):
                return [(p, "doc.pdf", cache)]

            result = idx.commit_manifest_after_index(root, [str(root)], FakeFc, source_files)
            self.assertEqual(result["index_version"], "1")
            self.assertIn("doc.pdf", result["added"])
            m = idx.load_manifest(root)
            self.assertEqual(m["index_version"], "1")
            self.assertIn("doc.pdf", m["files"])

            # Second commit with same files → version 2, empty diff names
            result2 = idx.commit_manifest_after_index(root, [str(root)], FakeFc, source_files)
            self.assertEqual(result2["index_version"], "2")
            self.assertEqual(result2["added"], [])
            self.assertEqual(result2["changed"], [])

    def test_format_diff_reply_empty(self):
        msg = idx.format_diff_reply({"added": [], "changed": [], "removed": []})
        self.assertIn("ajour", msg)


if __name__ == "__main__":
    unittest.main()
