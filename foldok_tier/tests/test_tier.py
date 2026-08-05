"""Tests for foldok_tier — strong / candidate / rejected.

Run:  python -m pytest foldok_tier/tests -q
"""

from __future__ import annotations

from foldok_tier import compare, fill_section, tier_sentences
from foldok_tier.integrate import candidate_chunks, tier_from_prose

PROSE = """
Equipotential bonding can be divided into protective and functional bonding.
An FE connection must never be used as a protective equipotential bonding.
The shielding is applied over a large area to keep the connection as low-impedance as possible.
Experience shows that the shielding should be applied on both sides.
Data transfer between devices and systems is increasing.
All rights reserved. Subject to change without notice.
See figure 12 for the recommended arrangement.
1.5 2.5 4.0 6.0 10.0
"""


def test_strong_candidates_and_rejects_are_separated():
    strong = {
        "An FE connection must never be used as a protective equipotential bonding.": "rule",
        "Experience shows that the shielding should be applied on both sides.": "practice",
    }
    topics = {
        "equipotential", "bonding", "shielding", "connection", "devices", "systems",
        "protective", "functional", "impedance", "transfer",
    }
    sents = [ln.strip() for ln in PROSE.splitlines() if ln.strip()]
    r = tier_sentences(sents, source="sick.pdf", strong_ids=strong, topics=topics)
    assert r.of("strong")
    assert any("low-impedance" in s.text for s in r.of("candidate"))
    assert any(s.reason == "copyright" for s in r.of("rejected"))
    assert any(s.reason == "navigation" for s in r.of("rejected"))


def test_fill_section_uses_candidates_when_strong_is_thin():
    strong = {
        "An FE connection must never be used as a protective equipotential bonding.": "rule",
    }
    topics = {
        "shielding", "connection", "impedance", "equipotential", "bonding", "applied",
    }
    sents = [ln.strip() for ln in PROSE.splitlines() if ln.strip()]
    r = tier_sentences(sents, source="x", strong_ids=strong, topics=topics)
    c = compare(r, section_terms=["shield", "shielding", "connection", "impedance"])
    assert c["loose"] >= c["strict"]
    # Descriptive shielding sentence fills when patterns alone are thin
    loose = fill_section(
        r, section_terms=["shield", "shielding", "connection", "impedance"], want=4,
    )
    assert any("low-impedance" in s.text or "shielding" in s.text.lower() for s in loose)


def test_copyright_and_address_never_become_candidates():
    sents = [
        "1 79183 Waldkirch Germany Legal information This work is protected by copyright.",
        "The shielding is applied over a large area to keep the connection as low-impedance as possible.",
    ]
    r = tier_sentences(
        sents, source="x",
        topics={"shielding", "connection", "impedance", "applied"},
    )
    assert all(s.tier == "rejected" for s in r.sentences if "Waldkirch" in s.text)
    assert any(s.tier == "candidate" for s in r.sentences if "low-impedance" in s.text)


def test_candidate_chunks_carry_tier_metadata():
    r = tier_from_prose(
        "The shielding is applied over a large area to keep the connection as low-impedance as possible. "
        "Shielded cable shall be used for Class 4 circuits.",
        source="guide.pdf",
        topics=["shielding", "connection", "impedance", "cable", "class", "circuits"],
    )
    chunks = candidate_chunks(r)
    assert all(c["kind"] == "candidate" for c in chunks)
    assert all(c.get("claim_tier") == "candidate" for c in chunks)


def test_summary_uses_keyword_lang():
    r = tier_sentences(
        ["The shielding should be applied on both sides."],
        source="x",
        strong_ids={"The shielding should be applied on both sides.": "practice"},
    )
    assert "strong" in r.summary(lang="en")
    assert "sterke" in r.summary(lang="no")
