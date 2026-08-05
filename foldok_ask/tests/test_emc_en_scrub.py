"""EMC EN regenerate must never emit bridge spam or topic-slug body lines.

Run:  python -m pytest foldok_ask/tests/test_emc_en_scrub.py -q
"""
from __future__ import annotations

from foldok_ask.author_doc import scrub_authored_prose, write_volume_section
from foldok_ask.compose_brief import compose_topic_brief
from foldok_ask.plan import OutlineSection


class _Cites:
    def may_cite(self, _src):
        return True

    def mark(self, src, body=True):
        return "[1]"


def _emc_index():
    """Synthetic EMC folder — mix of real claims and TOC/slug noise."""
    return [
        {
            "file": "emc_guide.pdf",
            "kind": "pdf",
            "caption": "EMC installation guide",
            "facts": [
                {
                    "id": "f1",
                    "key": "electromagnetic_compatibility",
                    "value": "Electromagnetic_compatibility",
                    "fact_type": "requirement",
                    "source_excerpt": "Electromagnetic_compatibility",
                },
                {
                    "id": "f2",
                    "key": "shielding",
                    "value": "60 dB",
                    "fact_type": "requirement",
                    "source_excerpt": (
                        "Shielding effectiveness shall exceed 60 dB at 100 MHz "
                        "for cable trays in zone B."
                    ),
                },
            ],
            "chunks": [
                {
                    "text": "Shielding effectiveness shall exceed 60 dB at 100 MHz for cable trays in zone B.",
                    "page": 4,
                },
                {"text": "Electromagnetic_compatibility", "page": 1},
                {"text": "Installation_guide", "page": 2},
            ],
        }
    ]


def test_scrub_glued_bridge_and_slug():
    junk = (
        "Etter dette — Etter dette — Reglene forankres i navngitte "
        "standarder med en rolle i argumentet. Electromagnetic_compatibility. [20] "
        "Installation_guide. [17]"
    )
    cleaned = scrub_authored_prose(junk, lang="en")
    assert "Etter dette" not in cleaned
    assert "Electromagnetic_compatibility" not in cleaned
    assert "Installation_guide" not in cleaned
    assert "argumentet" not in cleaned
    assert "Reglene forankres" not in cleaned


def test_key_value_and_claim_id_banned():
    junk = (
        "electromagnetic_compatibility: zone B\n\n"
        "claim_abc123def. [3]\n\n"
        "Shielding effectiveness shall exceed 60 dB at 100 MHz for the tray. [1]"
    )
    cleaned = scrub_authored_prose(junk, lang="en")
    assert "electromagnetic_compatibility:" not in cleaned
    assert "claim_abc" not in cleaned
    assert "Shielding effectiveness" in cleaned


def test_compose_topic_brief_en_no_bridge_or_slug():
    # Bust any in-process compose cache from other tests
    import topic_brief_compile as tbc
    tbc._CACHE.clear()

    parts = compose_topic_brief(_emc_index(), artifact={"name": "EMC Pack"}, lang="en")
    blob = "\n".join(
        str(parts.get(k) or "")
        for k in ("overview", "answers", "gaps", "source_register")
    )
    assert "Etter dette" not in blob
    assert "Electromagnetic_compatibility." not in blob
    assert "Installation_guide." not in blob
    # Volume / corpus notes must follow lang=en
    note = parts.get("_volume_note") or ""
    assert "utsagn" not in note.lower()
    assert "seksjon(er) foreslås" not in note.lower()


def test_volume_slug_only_is_gap_en():
    sec = OutlineSection(
        heading="Compatibility",
        purpose="EMC",
        retrieve_query="emc",
        kind="teach",
    )
    evidence = [
        {"quote": "Electromagnetic_compatibility", "source": "a.pdf"},
        {"quote": "Installation_guide", "source": "b.pdf"},
    ]
    draft = write_volume_section(sec, evidence, cites=_Cites(), lang="en")
    assert draft.fidelity_ok is False
    assert "GAP" in (draft.gap or "")
    assert "Electromagnetic_compatibility" not in (draft.prose or "")
    assert "Etter dette" not in (draft.prose or "")
