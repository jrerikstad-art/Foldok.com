"""Regression: foldok_index watermarks are wired into the update path."""
from __future__ import annotations

import inspect
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import foldok_index_bridge as fib  # noqa: E402
import index_tools as idx  # noqa: E402


def test_callers_exist_outside_foldok_index():
    """The user's diagnostic: empty grep outside foldok_index/ must fail now."""
    src_tools = Path(idx.__file__).read_text(encoding="utf-8")
    src_bridge = Path(fib.__file__).read_text(encoding="utf-8")
    assert "context_for_update" in src_tools or "context_for_document_update" in src_tools
    assert "set_watermark" in src_bridge or "set_document_watermark" in src_bridge
    assert "context_for_update" in inspect.getsource(fib.context_for_document_update)
    assert "set_watermark" in inspect.getsource(fib.set_document_watermark)


def test_watermark_roundtrip_drives_update_targets(tmp_path: Path):
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "old.md").write_text("alpha baseline content here for extract", encoding="utf-8")
    sync = fib.sync_project_index(folder, [folder])
    assert sync["ok"]
    mark = fib.set_document_watermark(folder, template_file="topic_brief.json", note="gen")
    assert mark["ok"]
    (folder / "new.md").write_text("beta addendum 2026 fresh material", encoding="utf-8")
    ctx = fib.context_for_document_update(
        folder, [folder], template_file="topic_brief.json", sync=True,
    )
    assert ctx is not None
    assert ctx["first_time"] is False
    assert ctx["new_document_count"] >= 1
    assert any(r.endswith("new.md") for r in (ctx.get("new_rels") or []))


def test_diff_index_attaches_recency(tmp_path: Path):
    folder = tmp_path / "proj"
    folder.mkdir()
    cache = folder / ".foldok_cache"
    cache.mkdir()
    p = folder / "a.md"
    p.write_text("enough text for the extractor to keep this file", encoding="utf-8")

    class FakeFc:
        PHOTO_EXT = set()
        DOC_EXT = {".md", ".pdf"}
        CAD_EXT = set()

        @staticmethod
        def read_json_file(path):
            return {}

    def source_files(_folders):
        return [(p, "a.md", cache)]

    fib.set_document_watermark(folder, template_file="topic_brief.json", sync_folders=[folder])
    (folder / "b.md").write_text("second file after watermark was set deliberately", encoding="utf-8")
    diff = idx.diff_index(
        folder, [folder], FakeFc, source_files,
        template_file="topic_brief.json",
    )
    assert "recency" in diff
    assert diff["recency"]["new_document_count"] >= 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
