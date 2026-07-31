"""foldok_scan enrichment on prescan — silent drops explained."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import index_prescan as prescan  # noqa: E402
from editor_chat import index_coverage_reply, is_index_coverage_ask  # noqa: E402


def test_attach_coverage_explains_legacy_doc(tmp_path: Path):
    (tmp_path / "ok.pdf").write_bytes(b"%PDF-1.4 minimal")
    (tmp_path / "legacy.doc").write_bytes(b"OLE legacy word")
    (tmp_path / "mail.msg").write_bytes(b"msg")
    report = prescan.scan_folders([tmp_path], check_cache=False)
    assert "coverage" in report
    assert report["coverage_total"] >= 3
    assert report["coverage"] < 1.0
    text = report.get("coverage_text") or ""
    assert ".doc" in text or "doc" in text.lower()
    card = prescan.format_decision_card_no(report)
    assert "Dekning" in card or "indexed" in card.lower() or ".doc" in card


def test_coverage_ask_detector():
    assert is_index_coverage_ask("Hvorfor er ikke filene indeksert?")
    assert is_index_coverage_ask("what was dropped from the index")
    assert not is_index_coverage_ask("lag en temabrief")


def test_coverage_reply_fallback():
    prose = index_coverage_reply(
        {"coverage": 0.46, "coverage_indexed": 12, "coverage_total": 26,
         "biggest_win": {"ext": ".doc", "count": 4, "why": "legacy Word"}},
        lang="no",
    )
    assert "12/26" in prose
    assert ".doc" in prose


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        test_attach_coverage_explains_legacy_doc(Path(d))
    test_coverage_ask_detector()
    test_coverage_reply_fallback()
    print("ok")
