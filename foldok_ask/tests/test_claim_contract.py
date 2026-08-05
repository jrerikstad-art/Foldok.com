"""Section author contract: claims→prose text, else specific GAP; scrub ≠ writer."""
from __future__ import annotations

from foldok_ask.author_doc import finalize_authored_section, scrub_authored_prose


def test_finalize_bridge_only_becomes_claims_gap():
    junk = "Etter dette — Etter dette — Electromagnetic_compatibility. [20]"
    assert scrub_authored_prose(junk, lang="en") == ""
    out = finalize_authored_section(
        junk, section_key="compatibility", lang="en", claim_count=0,
    )
    assert "GAP: claims" in out
    assert "budget 0" in out
    assert "Etter dette" not in out


def test_finalize_unwritable_hits_named_gap():
    junk = "Installation_guide. [17]\nElectromagnetic_compatibility. [20]"
    out = finalize_authored_section(
        junk, section_key="compatibility", lang="en", claim_count=2,
    )
    assert "writable claim text" in out
    assert "2 hit" in out


def test_finalize_keeps_claim_text():
    good = "Shielding effectiveness shall exceed 60 dB at 100 MHz for the tray. [1]"
    out = finalize_authored_section(
        good, section_key="compatibility", lang="en", claim_count=2,
    )
    assert "60 dB" in out
    assert "GAP:" not in out
