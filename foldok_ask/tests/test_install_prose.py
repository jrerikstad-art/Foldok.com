"""Authoring must not dump TOC titles as installation content.

Run:  python -m pytest foldok_ask/tests/test_install_prose.py -q
"""

from __future__ import annotations

from foldok_ask.author_doc import (
    _usable_evidence_quote,
    bridge_opening,
    section_summary,
    write_volume_section,
)
from foldok_ask.plan import OutlineSection


class _Cites:
    def may_cite(self, _src):
        return True

    def mark(self, src, body=True):
        return "[1]"


def test_hollow_installation_guide_quotes_rejected():
    assert not _usable_evidence_quote("Installation_guide")
    assert not _usable_evidence_quote("Installation_guidance")
    assert not _usable_evidence_quote("Installation")
    assert _usable_evidence_quote(
        "Mount the tray to the wall with M10 anchors at 1.2 m centres."
    )


def test_bridge_does_not_nest_argument_meta():
    prev = (
        "Etter dette — Reglene forankres i navngitte standarder med en rolle "
        "i argumentet — følger neste ledd i argumentet."
    )
    assert "argumentet" not in section_summary(prev).lower() or section_summary(prev) == ""
    line = bridge_opening(
        prev_summary=prev,
        prev_beat="rules",
        next_beat="evidence",
        next_purpose="installation steps",
        heading="Installation",
        lang="no",
    )
    assert "etter dette" not in line.lower()
    assert "argumentet" not in line.lower()


def test_scrub_compatibility_block():
    from foldok_ask.author_doc import scrub_authored_prose
    junk = (
        "Etter dette — Etter dette — Etter dette — Reglene forankres i navngitte "
        "standarder med en rolle i argumentet.\n\n"
        "Electromagnetic_compatibility. [20]\n\n"
        "Electromagnetic_compatibility. [21]\n\n"
        "Electromagnetic_compatibility. [22]\n\n"
        "Electromagnetic_compatibility. [19]"
    )
    cleaned = scrub_authored_prose(junk)
    assert "Etter dette" not in cleaned
    assert "Electromagnetic_compatibility" not in cleaned
    assert "argumentet" not in cleaned or cleaned == ""


def test_topic_slug_rejected_as_quote():
    from foldok_ask.author_doc import _is_topic_slug, _usable_evidence_quote
    assert _is_topic_slug("Electromagnetic_compatibility")
    assert _is_topic_slug("Electromagnetic_compatibility. [20]")
    assert not _usable_evidence_quote("Electromagnetic_compatibility")
    assert _usable_evidence_quote(
        "Shielding effectiveness shall exceed 60 dB at 100 MHz for the tray."
    )


def test_bridge_opening_is_disabled():
    assert bridge_opening(
        prev_summary="anything", prev_beat="rules", next_beat="evidence",
        next_purpose="x", heading="Protection", lang="no",
    ) == ""


def test_volume_emc_slug_hits_become_gap():
    sec = OutlineSection(
        heading="Compatibility",
        purpose="EMC rules",
        retrieve_query="electromagnetic compatibility",
        kind="teach",
    )
    evidence = [
        {"quote": "Electromagnetic_compatibility", "source": "a.pdf"},
        {"quote": "Electromagnetic_compatibility", "source": "b.pdf"},
        {"quote": "Electromagnetic_compatibility", "source": "c.pdf"},
        {"quote": "Electromagnetic_compatibility", "source": "d.pdf"},
    ]
    draft = write_volume_section(sec, evidence, cites=_Cites(), lang="no")
    assert draft.fidelity_ok is False
    assert "MANGLER" in (draft.gap or "")
    assert "Electromagnetic_compatibility" not in (draft.prose or "")
    assert "[20]" not in (draft.prose or "")


def test_merged_volume_cites_one_statement():
    from foldok_ask.author_doc import _merged_volume_prose
    usable = [
        {
            "quote": "Shielding effectiveness shall exceed 60 dB at 100 MHz for the tray.",
            "source": "a.pdf",
        },
        {
            "quote": "Shielding effectiveness shall exceed 60 dB at 100 MHz for the tray.",
            "source": "b.pdf",
        },
    ]
    prose = _merged_volume_prose(usable, _Cites(), heading="Compatibility", lang="en")
    assert prose.count("Shielding effectiveness") == 1
    assert "[1]" in prose
