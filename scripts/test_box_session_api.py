"""WO 0.73 — foldok_boxes session API + parity smoke."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "local_app"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(LOCAL) not in sys.path:
    sys.path.insert(0, str(LOCAL))

import box_sessions as bses  # noqa: E402
from foldok_boxes import fingerprint  # noqa: E402
from foldok_boxes.integration import migrate_layout  # noqa: E402
from foldok_boxes.model import PageGrid  # noqa: E402
from foldok_boxes.pins import PinStore  # noqa: E402


class BoxSessionApiTests(unittest.TestCase):
    def test_create_resize_release(self):
        payload = bses.create_session()
        sid = payload["session_id"]
        self.assertIn("geometry", payload)
        moved = bses.apply(sid, {"type": "resize", "blockId": "img1", "handle": "e", "dx": -90, "dy": 0})
        box = next(b for b in moved["geometry"]["boxes"] if b["block_id"] == "img1")
        self.assertLessEqual(box["span"], 6)
        released = bses.apply(sid, {"type": "release", "blockId": "img1"})
        self.assertIn("geometry", released)

    def test_migrate_full_half_third(self):
        grid = PageGrid(columns=12)
        pins, notes = migrate_layout(
            [
                {"block_id": "a", "layout": {"width": "full"}},
                {"block_id": "b", "layout": {"width": "half"}},
                {"block_id": "c", "layout": {"width": "third"}},
            ],
            grid,
            PinStore(),
            layer="template",
        )
        self.assertTrue(notes or pins.to_jsonl())
        # Pins exist for migrated blocks
        self.assertTrue(pins.to_jsonl())

    def test_fingerprint_stable(self):
        a = bses.create_session()
        b = bses.create_session()
        fa = fingerprint(bses.get_session(a["session_id"]).geometry())
        fb = fingerprint(bses.get_session(b["session_id"]).geometry())
        self.assertEqual(fa, fb)


if __name__ == "__main__":
    unittest.main()
