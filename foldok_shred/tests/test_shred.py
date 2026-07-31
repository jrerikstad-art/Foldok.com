"""Tests that lock the shredder contract: body text never survives the return.

Run:  python -m pytest foldok_shred/tests -q
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from foldok_shred import Shred, Shredder, ShredRefused, consensus
from foldok_shred.console_bridge import proposals_as_findings
from foldok_shred.model import GRADE_LEARNS

SECRET_PHRASE = "Every final circuit shall be subjected to an insulation resistance measurement of at least one megohm under NEK 400 exclusive wording."
BODY_MARKER = "CLIENT_ACME_JOB_114_SECRET_BODY_TEXT_NEVER_KEEP"


def _manual(tmp_path: Path) -> Path:
    p = tmp_path / "manual.md"
    p.write_text(
        "\n".join([
            "# Installation manual",
            "",
            BODY_MARKER,
            "",
            "## Scope",
            BODY_MARKER,
            "",
            "## Commissioning",
            BODY_MARKER,
            "",
            "## Verification by testing",
            SECRET_PHRASE,
            "",
            "Table 1 — measurements",
            "Figure 1 — board layout",
        ]),
        encoding="utf-8",
    )
    return p


def test_shred_has_no_text_ish_fields():
    names = {f.name for f in fields(Shred)}
    forbidden = {"text", "body", "content", "raw", "document", "pages", "paragraphs"}
    assert not (names & forbidden)


def test_body_text_does_not_survive_to_dict(tmp_path):
    shred = Shredder().shred(_manual(tmp_path), grade="exemplary")
    blob = json.dumps(shred.to_dict(), ensure_ascii=False)
    assert BODY_MARKER not in blob
    assert SECRET_PHRASE not in blob
    assert "the document itself was not retained" in shred.notes


def test_section_titles_are_kept(tmp_path):
    shred = Shredder().shred(_manual(tmp_path), grade="exemplary")
    titles = " ".join(shred.skeleton.titles()).lower()
    assert "verification by testing" in titles
    assert shred.skeleton.section_count >= 3


def test_sample_grade_learns_nothing(tmp_path):
    shred = Shredder().shred(_manual(tmp_path), grade="sample")
    assert shred.proposals == []
    assert shred.learns == ()
    assert any("learns nothing" in n for n in shred.notes)


def test_exemplary_grade_offers_skeleton_proposal(tmp_path):
    shred = Shredder().shred(_manual(tmp_path), grade="exemplary")
    assert "skeleton" in GRADE_LEARNS["exemplary"]
    assert any(p.kind == "skeleton" for p in shred.proposals)


def test_source_id_is_content_hash_not_filename(tmp_path):
    a = _manual(tmp_path)
    b = tmp_path / "CLIENT_ACME_JOB_114.pdf.md"
    b.write_bytes(a.read_bytes())
    s1 = Shredder().shred(a)
    s2 = Shredder().shred(b)
    assert s1.source_id == s2.source_id
    assert "CLIENT" not in s1.source_id
    assert "ACME" not in s1.source_id


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(ShredRefused):
        Shredder().shred(tmp_path / "gone.md")


def test_kind_guess_from_titles(tmp_path):
    shred = Shredder().shred(_manual(tmp_path))
    assert shred.kind == "installation_manual"


def test_consensus_needs_three_exemplary(tmp_path):
    paths = []
    for i in range(3):
        p = tmp_path / f"m{i}.md"
        p.write_text(
            "# Installation\n## Scope\n## Commissioning\n## Verification by testing\n",
            encoding="utf-8",
        )
        paths.append(p)
    shreds = Shredder().shred_many(paths, grade="exemplary")
    props = consensus(shreds, min_documents=3)
    assert props and props[0].kind == "skeleton"


def test_proposals_map_to_console_findings(tmp_path):
    shred = Shredder().shred(_manual(tmp_path), grade="exemplary")
    findings = proposals_as_findings(shred.proposals)
    assert findings
    assert all(f["action"] for f in findings)
    assert all("accept" in f["action"] for f in findings)
    blob = json.dumps(findings, ensure_ascii=False)
    assert BODY_MARKER not in blob
    assert SECRET_PHRASE not in blob


def test_report_leads_with_source_id(tmp_path):
    shred = Shredder().shred(_manual(tmp_path), grade="sample")
    text = shred.report()
    assert text.startswith("SHRED")
    assert shred.source_id in text
