"""Tests for the folder scanner.

Run:  python -m pytest foldok_scan/tests -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

from foldok_scan import DOC_EXT, compare, scan, widened_doc_ext

LIBRARY = [
    "EMC BoD.pptx", "readme.txt",
    "Standards/EN 50174-2.pdf", "Standards/NEMA VE-2.doc", "Standards/IEEE 299.doc",
    "Suppliers/Chalfant.pdf", "Suppliers/quote.xls",
    "Suppliers/Correspondence/York reply.msg", "Suppliers/Correspondence/Aker spec.msg",
    "Test data/raw/sweep_01.dat",
    "Photos/tray.jpg", "Archive/bundle.zip", "assets/logo.png", ".DS_Store",
]


@pytest.fixture
def library(tmp_path: Path) -> Path:
    root = tmp_path / "EMC"
    for f in LIBRARY:
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * 2048)
    return root


# --- the reported bug ----------------------------------------------------
def test_subfolders_are_walked(library):
    """Reported as 'it does not include subfolders'. It does."""
    report = scan(library)
    assert report.max_depth >= 2
    assert any(e.depth == 2 for e in report.entries)


def test_a_level_with_nothing_indexed_is_named_as_a_format_problem(library):
    """Level 2 held only .msg and .dat, so it looked exactly like a recursion
    bug from outside. The report has to distinguish the two."""
    text = scan(library).report(lang="en")
    assert "the folder IS read, the formats are not" in text


def test_every_dropped_file_gets_a_reason(library):
    for entry in scan(library).dropped:
        assert entry.reason, entry.rel


def test_legacy_office_is_the_dominant_loss(library):
    ext, count, why = scan(library).biggest_win()
    assert ext in (".doc", ".msg")
    assert count >= 2 and why


def test_widening_the_extension_set_recovers_the_files(library):
    before, after = compare(library, widened_doc_ext(scan(library)))
    assert len(after.indexed) > len(before.indexed)
    assert after.coverage > before.coverage


def test_the_widened_set_never_loses_what_already_worked(library):
    assert DOC_EXT <= widened_doc_ext(scan(library))


# --- correct drops stay dropped ------------------------------------------
def test_archives_are_dropped_with_the_advice_to_expand_them(library):
    zips = [e for e in scan(library).dropped if e.path.suffix == ".zip"]
    assert zips and "expand it" in zips[0].reason
    assert not zips[0].recoverable


def test_hidden_files_and_skipped_folders_are_reported_not_silent(library):
    reasons = scan(library).by_reason()
    assert any("hidden" in r for r in reasons)
    assert any("skip list" in r for r in reasons)


def test_an_empty_file_is_not_counted_as_indexed(tmp_path):
    (tmp_path / "empty.pdf").write_bytes(b"")
    report = scan(tmp_path)
    assert report.dropped and "empty" in report.dropped[0].reason


def test_an_oversized_file_says_the_limit(tmp_path):
    (tmp_path / "big.pdf").write_bytes(b"x" * 4096)
    report = scan(tmp_path, max_bytes=1024)
    assert "larger than" in report.dropped[0].reason


def test_a_file_with_no_extension_is_offered_rather_than_assumed(tmp_path):
    (tmp_path / "NOTES").write_bytes(b"x" * 100)
    entry = scan(tmp_path).dropped[0]
    assert entry.recoverable and "check one before deciding" in entry.note


# --- reporting -----------------------------------------------------------
def test_coverage_is_the_headline(library):
    report = scan(library)
    assert 0.0 < report.coverage < 1.0
    assert "%" in report.report(lang="en")


def test_the_report_is_bilingual_without_leaking(library):
    english = scan(library).report(lang="en")
    assert "indeksert" not in english and "droppet" not in english
    norsk = scan(library).report(lang="no")
    assert "indeksert" in norsk


def test_the_biggest_win_names_one_change(library):
    text = scan(library).report(lang="en")
    assert "Biggest single win" in text


def test_a_healthy_folder_reports_full_coverage(tmp_path):
    for name in ("a.pdf", "b.md", "c.docx"):
        (tmp_path / name).write_bytes(b"x" * 100)
    report = scan(tmp_path)
    assert report.coverage == 1.0 and not report.dropped


def test_a_missing_folder_is_not_an_exception(tmp_path):
    assert scan(tmp_path / "nope").entries == []


def test_the_report_serialises_for_the_ui(library):
    data = scan(library).to_dict()
    assert data["total"] > data["indexed"]
    assert data["by_reason"] and data["by_depth"]
