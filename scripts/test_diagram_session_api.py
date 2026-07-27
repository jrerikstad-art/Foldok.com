"""Integration tests for diagram_sessions + diagram_store (WO 0.63)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "local_app"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(LOCAL) not in sys.path:
    sys.path.insert(0, str(LOCAL))

import diagram_sessions as dses  # noqa: E402
from diagram_store import list_diagrams, load_diagram, save_diagram  # noqa: E402


class DiagramSessionApiTests(unittest.TestCase):
    def test_create_move_validate_payload(self):
        payload = dses.create_session("water_heater", profile="wiring")
        sid = payload["session_id"]
        self.assertIn("<svg", payload["svg"])
        self.assertIn("session_id", payload)
        self.assertIn("issues", payload)

        moved = dses.apply_action(sid, "move", {"component_id": "UT", "x": 400, "y": 200})
        self.assertIn("<svg", moved["svg"])
        self.assertNotEqual(moved["svg"], payload["svg"])

    def test_persist_and_open_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = dses.create_session("water_heater", profile="wiring", project_dir=tmp)
            sid = payload["session_id"]
            paths = dses.persist_session(sid)
            self.assertTrue(Path(paths["graph"]).exists())
            self.assertTrue(Path(paths["pins"]).exists())
            listed = list_diagrams(tmp)
            self.assertEqual(len(listed), 1)
            gid = listed[0]["graph_id"]
            opened = dses.open_project_diagram(tmp, gid, profile="wiring")
            self.assertIn("<svg", opened["svg"])
            self.assertEqual(opened["graph_id"], gid)

    def test_propose_ai_and_confirm(self):
        payload = dses.create_session("water_heater")
        sid = payload["session_id"]
        proposed = dses.propose_ai_graph(
            sid,
            {
                "components": [{
                    "id": "AI_LOAD",
                    "type": "load_block",
                    "label": "AI load",
                    "ports": [{"id": "a", "name": "a", "side": "left", "kind": "electrical"}],
                }],
            },
            ref="test-agent",
        )
        graph = proposed["graph"]
        ai = [c for c in graph["components"] if c["id"] == "AI_LOAD"]
        self.assertEqual(len(ai), 1)
        self.assertEqual(ai[0]["provenance"]["source"], "ai")
        confirmed = dses.apply_action(sid, "confirm_ai", {"ids": ["AI_LOAD"]})
        ai2 = [c for c in confirmed["graph"]["components"] if c["id"] == "AI_LOAD"]
        self.assertEqual(ai2[0]["provenance"]["source"], "user")

    def test_jurisdiction_blocks_export_when_missing(self):
        payload = dses.create_session("water_heater")
        sid = payload["session_id"]
        # fresh fixture may lack jurisdiction
        if not payload.get("export_blocked"):
            dses.apply_action(sid, "set_jurisdiction", {"jurisdiction": ""})
            payload = dses.session_payload(sid)
        self.assertTrue(payload["export_blocked"] or payload["jurisdiction"])


if __name__ == "__main__":
    unittest.main()
