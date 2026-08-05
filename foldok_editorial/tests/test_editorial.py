"""Editorial QA — fail on bridge spam, slug body, language mix."""
from __future__ import annotations

from foldok_editorial import review_markdown


def test_stacked_etter_dette_fails():
    md = """## Compatibility

Etter dette — Etter dette — Reglene forankres i argumentet.

Electromagnetic_compatibility. [20]
"""
    r = review_markdown(md, language="en")
    assert r.ok is False
    codes = {f.code for f in r.findings}
    assert "stacked_bridge" in codes or "repeated_transition" in codes
    assert "slug_as_body" in codes
    assert r.metrics["repeated_phrases"] >= 1


def test_clean_english_passes():
    md = """## Compatibility

Shielding effectiveness shall exceed 60 dB at 100 MHz for the tray. [1]

## Installation

Mount the tray with M10 anchors at 1.2 m centres. [2]
"""
    r = review_markdown(md, language="en")
    assert r.ok is True
    assert r.metrics["mixed_language"] == 0
    assert r.metrics["slug_body_lines"] == 0


def test_norwegian_in_english_doc_flagged():
    md = """## Overview

Denne seksjonen beskriver installasjonen og kravene som skal følges i prosjektet.
"""
    r = review_markdown(md, language="en")
    assert any(f.code == "mixed_language" for f in r.findings)


def test_assets_available_but_unused():
    md = "## Overview\n\nThe system uses cable trays in zone B.\n"
    r = review_markdown(md, language="en", assets_available=8, assets_used=0)
    assert any(f.code == "unused_assets" for f in r.findings)


def test_document_status_blocks_on_editorial_fail():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "local_app"))
    import account_metering as acct

    state = {
        "doc": {
            "sections": {"a": {"md": "x"}},
            "_editorial": {
                "ok": False,
                "findings": [
                    {"code": "stacked_bridge", "severity": "fail", "message": "spam"},
                ],
            },
        }
    }
    st = acct.document_status(
        {"generated_at": "2026-01-01"},
        blocking_gaps=0,
        state=state,
    )
    assert st["key"] == "editorial"
    assert "Klar" not in st["label"]
