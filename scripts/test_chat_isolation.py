#!/usr/bin/env python3
"""BUGFIX 0.19 — regression: Checkpoint-A chat context must not cross projects.

Creates two synthetic projects (lifting tool vs bathroom), then alternates
six context builds: open A, chat A, open B, chat B, chat A, chat B.

Asserts each chat context's captions/files contain THIS project's marker
and NEVER the other's. No Anthropic calls — tests the resolver + index path.

Run:  python scripts/test_chat_isolation.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "local_app"))

MARKER_A = "SWL_MARKER_LIFTING_TOOL_ZZZ"
MARKER_B = "TILE_MARKER_BATHROOM_YYY"
FILE_A = "heis_spec_ISOLATION_A.txt"
FILE_B = "bad_fliser_ISOLATION_B.txt"


def _seed_project(root: Path, name: str, pid: str, marker: str, filename: str) -> dict:
    folder = root / name
    folder.mkdir(parents=True)
    cache_dir = folder / ".foldok_cache"
    cache_dir.mkdir()
    path = folder / filename
    body = f"Synthetic source for isolation test.\nMARKER={marker}\n".encode("utf-8")
    path.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    entry = {
        "file": filename,
        "sha": sha,
        "kind": "doc",
        "caption": f"Indexed caption containing {marker}",
        "content_tags": ["isolation-test"],
        "doc_role_hints": ["spec"],
        "quality_flags": [],
        "facts": [
            {
                "id": f"{sha[:8]}-0",
                "fact_type": "text",
                "key": "isolation_marker",
                "value": marker,
                "unit": None,
                "confidence": 1.0,
                "source_excerpt": marker,
            }
        ],
    }
    (cache_dir / f"{sha}.json").write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
    (folder / ".foldok_state.json").write_text(
        json.dumps({"artifact": {"name": name, "purpose": marker}, "confirmed": False}, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"id": pid, "name": name, "folders": [str(folder)]}


class ChatIsolationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        self.proj_a = _seed_project(root, "lifting_tool_A", "proj-a", MARKER_A, FILE_A)
        self.proj_b = _seed_project(root, "bathroom_B", "proj-b", MARKER_B, FILE_B)
        self.projects = [self.proj_a, self.proj_b]

        import server as srv
        self.srv = srv
        self._patcher = mock.patch.object(srv, "load_projects", return_value=self.projects)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def _ctx(self, pid: str) -> dict:
        return self.srv.build_artifact_assist_sources(pid, lang="no")

    def _assert_only(self, ctx: dict, own: str, other: str, own_file: str):
        blob = ctx["captions"] + "\n" + "\n".join(e.get("file", "") for e in ctx["index"])
        self.assertIn(own, blob, f"expected own marker {own!r} in context")
        self.assertNotIn(other, blob, f"FOREIGN marker {other!r} leaked into project {ctx['project']['id']}")
        self.assertIn(own_file, blob)
        self.assertTrue(ctx["banner"].startswith("PROSJEKT:"))
        self.assertIn(ctx["primary"], ctx["banner"])
        self.assertEqual(str(Path(ctx["primary"])), str(Path(ctx["project"]["folders"][0])))

    def test_alternating_six_requests(self):
        """open A, chat A, open B, chat B, chat A, chat B — no cross contamination."""
        sequence = [
            ("proj-a", MARKER_A, MARKER_B, FILE_A),
            ("proj-a", MARKER_A, MARKER_B, FILE_A),
            ("proj-b", MARKER_B, MARKER_A, FILE_B),
            ("proj-b", MARKER_B, MARKER_A, FILE_B),
            ("proj-a", MARKER_A, MARKER_B, FILE_A),
            ("proj-b", MARKER_B, MARKER_A, FILE_B),
        ]
        for i, (pid, own, other, fname) in enumerate(sequence, 1):
            with self.subTest(step=i, pid=pid):
                ctx = self._ctx(pid)
                self.assertEqual(ctx["project"]["id"], pid)
                self._assert_only(ctx, own, other, fname)

    def test_missing_project_id_raises(self):
        with self.assertRaises(ValueError):
            self.srv.resolve_project("")
        with self.assertRaises(ValueError):
            self.srv.resolve_project(None)

    def test_unknown_project_raises(self):
        with self.assertRaises(LookupError):
            self.srv.resolve_project("does-not-exist")

    def test_folder_mismatch_raises(self):
        p = dict(self.proj_a)
        with self.assertRaises(self.srv.IsolationError):
            self.srv.assert_folder_on_project(p, str(Path(self.proj_b["folders"][0])))


    def test_conversation_isolation_alternating_turns(self):
        """BUGFIX_0.19 §A extended — conversation scoped per project_id.

        Two projects, alternating turns with distinct markers. Assert each
        project's conversation and chat-context history never contain the
        other's marker.
        """
        import editor_chat as edchat
        MARK_A = "CONV_MARKER_PROJECT_A_ALPHA"
        MARK_B = "CONV_MARKER_PROJECT_B_BETA"
        sequence = [
            ("proj-a", MARK_A, MARK_B),
            ("proj-b", MARK_B, MARK_A),
            ("proj-a", MARK_A, MARK_B),
            ("proj-b", MARK_B, MARK_A),
            ("proj-a", MARK_A, MARK_B),
            ("proj-b", MARK_B, MARK_A),
        ]
        for i, (pid, own, other) in enumerate(sequence, 1):
            with self.subTest(step=i, pid=pid):
                p = self.proj_a if pid == "proj-a" else self.proj_b
                folder = p["folders"][0]
                state = self.srv.load_state(folder, project_id=pid)
                edchat.append_turn(
                    state, "user", f"User turn mentioning {own}",
                    project_id=pid)
                edchat.append_turn(
                    state, "bot", f"Bot reply grounded in {own}",
                    project_id=pid)
                self.srv.save_state(folder, state)

                # Disk conversation must not contain foreign marker
                reloaded = self.srv.load_state(folder, project_id=pid)
                conv = edchat.conversation_for_project(reloaded, pid)
                blob = "\n".join(t.get("text") or "" for t in conv)
                self.assertIn(own, blob)
                self.assertNotIn(other, blob)

                # Chat context CONVERSATION HISTORY must not leak
                ctx = self.srv.build_artifact_assist_sources(pid, lang="no")
                hist = ctx.get("chat_context") or ""
                self.assertIn(own, hist)
                self.assertNotIn(other, hist)
                # And the other project's context must not see ours
                other_pid = "proj-b" if pid == "proj-a" else "proj-a"
                other_ctx = self.srv.build_artifact_assist_sources(other_pid, lang="no")
                other_hist = other_ctx.get("chat_context") or ""
                self.assertNotIn(own, other_hist)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ChatIsolationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
