"""Regression: narrative story + author (not fact dump / caption paste)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "local_app"))

from foldok_ask import (  # noqa: E402
    compose_topic_brief,
    plan_document,
    plan_narrative,
    retrieve,
    ask,
)
from foldok_ask.ask import synthesize_scope  # noqa: E402


def _emc_index(n_files: int = 54):
    base = [
        {
            "file": "Documents/Chalfant 78411.pdf",
            "caption": "Chalfant EMI/RFI shielded cable tray",
            "detail_summary": (
                "Premium and Ultra RF classes are tested to MIL-STD-285. "
                "Attenuation is 70-120 dB across 150 kHz to 1 GHz."
            ),
            "content_tags": ["emc", "cable_tray", "shielding"],
            "facts": [
                {"id": "a1", "key": "h_field_attenuation_premium", "value": "70 to 83", "unit": "dB"},
                {"id": "a2", "key": "test_standard", "value": "MIL-STD-285"},
            ],
        },
        {
            "file": "Documents/Amucor-faraday-cage-leaflet.pdf",
            "caption": "Faraday cage systems",
            "detail_summary": (
                "EMC describes a system's ability to operate in its intended environment without EMI. "
                "Shielded cable shall be used at zone transitions."
            ),
            "content_tags": ["emc", "faraday", "shielding"],
            "facts": [
                {"id": "b1", "key": "attenuation_e_field", "value": "110", "unit": "dB"},
                {"id": "b2", "key": "test_standard", "value": "MIL-STD-188-125"},
            ],
        },
        {
            "file": "Documents/BEAMA-cable-tray-guide.pdf",
            "caption": "Cable classes and segregation",
            "detail_summary": (
                "Klasse 1A omfatter millivolt-transdusere og radiomottakere. "
                "Klasse 1A skal føres i separate bunter, adskilt fra Klasse 1B. "
                "Klasse 1B omfatter Ethernet og lignende datatrafikk; skjermet kabel kreves. "
                "For Klasse 4 er skjermede kabler og 360 bonding ved alle termineringer kritisk."
            ),
            "content_tags": ["cable_tray", "cable_class", "separation"],
            "facts": [
                {"id": "c1", "key": "cable_class", "value": "Class 4 power circuits"},
                {"id": "c2", "key": "governing_standard", "value": "EN 61537"},
            ],
        },
        {
            "file": "Documents/ASTM E1851.pdf",
            "caption": "ASTM E1851 shielding effectiveness",
            "detail_summary": "ASTM E1851 and IEEE Std 299 for electromagnetic shielding effectiveness measurements.",
            "content_tags": ["emc", "standard", "shielding"],
            "facts": [
                {"id": "d1", "key": "test_standard", "value": "ASTM E1851"},
            ],
        },
        {
            "file": "Documents/EMC-notes-no.pdf",
            "caption": "EMC design notes",
            "detail_summary": (
                "For å møte Hard Spec fra Aker er hovedregelen at fullstendig lukkede systemer er påkrevd. "
                "Trådstiger kan i visse frekvensområder gi bedre resultater enn lukkede baner. "
                "Armering alene er en dårlig skjerm for høye frekvenser. "
                "EN 50310 krever ekvipotensial jording og bonding i komplekse anlegg. "
                "EMC-testing skal dekke måling av emisjon og immunitet fra DC til 1 GHz."
            ),
            "content_tags": ["emc", "hypothesis", "risk"],
            "facts": [],
        },
        {
            "file": "Documents/Wibe Cable Trays For Demanding Application.pdf",
            "caption": "Wibe installation guide",
            "detail_summary": "Wibe cable trays installation guide for demanding applications.",
            "content_tags": ["cable_tray", "installation"],
            "facts": [
                {"id": "w1", "key": "installation_distance_tray_ceiling", "value": "300", "unit": "mm"},
            ],
        },
    ]
    out = list(base)
    i = 0
    while len(out) < n_files:
        i += 1
        out.append({
            "file": f"Documents/extra_{i:02d}.pdf",
            "caption": f"Technical note {i} on electromagnetic compatibility and cable management.",
            "content_tags": ["emc", "cable_management"],
            "facts": [],
        })
    return out


def test_narrative_has_thesis_and_arc():
    plan = plan_narrative("topic_brief", _emc_index(20), artifact={"name": "EMC"}, lang="no")
    assert plan.thesis
    assert "installation" in plan.thesis.lower() or "Installasjons" in plan.thesis or "skjerm" in plan.thesis.lower() or "EMC" in plan.thesis
    assert "frame" in plan.arc or "concepts" in plan.arc or "context" in plan.arc
    assert any(s.arc_beat == "concepts" for s in plan.sections)
    assert plan.intent.main_question
    assert all(s.purpose for s in plan.sections if s.kind == "teach")
    bp = plan.as_blueprint()
    assert bp.main_argument
    assert bp.reader_should_leave_with
    assert any(a.id == "frame" for a in bp.arc)
    assert "katalog" in bp.reader_should_leave_with.lower() or "catalog" in bp.reader_should_leave_with.lower() or "system" in bp.reader_should_leave_with.lower()


def test_blueprint_continuity_bridges():
    """Sections receive previous_summary bridges — document-level mind, not isolated islands."""
    parts = compose_topic_brief(_emc_index(20), artifact={"name": "EMC"}, lang="no")
    assert parts.get("_blueprint")
    bp = parts["_blueprint"]
    assert bp["main_argument"]
    assert bp["reader_should_leave_with"]
    assert any(a["id"] == "frame" for a in bp["arc"])
    answers = parts["answers"]
    # At least one continuity bridge phrase in body
    assert re.search(
        r"(?i)(med tesen|når begrep|når begrens|samme logikk|having established|"
        r"with the thesis|once the constraint|designimplik)",
        answers,
    )
    # Leave-with surfaces in conclusion-ish text
    blob = parts["overview"] + parts["answers"]
    assert "systemdesignbegrensning" in blob.lower() or "catalog" in blob.lower() or "katalog" in blob.lower() or "Oppsummering" in answers


def test_opening_is_thesis_not_file_count():
    parts = compose_topic_brief(_emc_index(54), artifact={"name": "EMC"}, lang="no")
    overview = parts["overview"]
    lead = overview.split("\n")[0]
    assert "MANGLER" not in overview
    assert not re.match(r"(?i)^.*\d+\s+indekserte filer\.?\s*$", lead.strip())
    assert "briefen samler" not in overview.lower()
    assert "kildematerialet" not in overview.lower()
    assert len(overview) > 80
    # Thesis should surface
    assert parts.get("_thesis")
    assert "Installasjons" in parts["_thesis"] or "installation" in parts["_thesis"].lower() or "EMC" in parts["_thesis"]


def test_lead_generator_half_page_framing():
    """Lead Generator: ~½ page, corpus character, thesis, roadmap, limits — not file-count story."""
    from foldok_ask.lead import generate_lead, LeadControls
    from foldok_ask.narrative import plan_narrative

    idx = _emc_index(54)
    plan = plan_narrative("topic_brief", idx, artifact={"name": "EMC"}, lang="no")
    lead = generate_lead(
        idx,
        sketch=plan.sketch,
        artifact={"name": "EMC"},
        thesis=plan.thesis,
        intent=plan.intent,
        section_headings=[s.heading for s in plan.sections],
        lang="no",
        controls=LeadControls(lead_depth="standard"),
    )
    assert lead.word_count >= 120
    assert lead.word_count <= 420
    prose = lead.prose
    first = prose.split("\n")[0]
    assert not re.match(r"(?i)^.{0,40}\d+\s+filer", first)
    assert "kildebibliotek" in prose.lower() or "source library" in prose.lower() or "Materialet" in prose
    assert "**" in prose  # thesis or limits emphasised
    assert re.search(r"\(\d+\s+filer indeksert", prose) or re.search(r"\(\d+\s+files indexed", prose)
    assert "comprehensive technical documentation" not in prose.lower()
    # Roadmap / limits signal
    assert "utvikler" in prose.lower() or "develops" in prose.lower() or "rammer" in prose.lower()
    assert "laborator" in prose.lower() or "åpne" in prose.lower() or "open" in prose.lower() or "tynt" in prose.lower()

    parts = compose_topic_brief(idx, artifact={"name": "EMC"}, lang="no")
    assert len(parts["overview"]) > 400
    assert parts["overview"].count("\n\n") >= 2


def test_no_abstract_salad():
    parts = compose_topic_brief(_emc_index(20), artifact={"name": "EMC"}, lang="no")
    blob = parts["overview"] + "\n" + parts["answers"]
    assert "Påstand | Verdi | Kilde" not in blob
    assert "comprehensive technical documentation" not in blob.lower()
    assert "Kildene beskriver også" not in blob
    assert "independently verified by York EMC to exceed" not in blob
    assert "York EMC" in blob or "50174" in blob or "skjerm" in blob.lower() or "kabelklasse" in blob.lower()
    assert re.search(r"\[\d+\]", parts["overview"] + parts["answers"] + parts["source_register"])


def test_standards_roles_clean():
    parts = compose_topic_brief(_emc_index(20), artifact={"name": "EMC"}, lang="no")
    std = parts["answers"]
    assert "MIL" in std or "EN 61537" in std or "50174" in std
    assert " — " in std
    assert "conflict minerals" not in std.lower()
    assert not re.search(r"ISO\s*9001\s*—\s*cable tray", std, re.I)


def test_arc_includes_conclusion_or_rules():
    parts = compose_topic_brief(_emc_index(20), artifact={"name": "EMC"}, lang="no")
    headings = parts["answers"].lower()
    assert "oppsummering" in headings or "tekniske hensyn" in headings or "kabelklasser" in headings


def test_planner_outline_teaches_not_keys():
    outline = plan_document("topic_brief", _emc_index(20), artifact={"name": "EMC"}, lang="no")
    kinds = [s.kind for s in outline]
    assert "framing" in kinds
    assert "appendix" in kinds
    assert "emc_zones" not in " ".join(s.heading.lower() for s in outline)


def test_kabelklasser_names_a_class():
    parts = compose_topic_brief(_emc_index(20), artifact={"name": "EMC"}, lang="no")
    blob = parts["answers"]
    assert re.search(r"(?i)(klasse\s*1[ab]?|class\s*1[ab]?|klasse\s*4)", blob)
    assert "comprehensive technical documentation" not in blob.lower()


def test_claim_chunks_outrank_in_retrieve():
    from foldok_ask.retrieve import index_to_chunks
    chunks = index_to_chunks(_emc_index(10))
    kinds = {c.get("kind") for c in chunks}
    assert "claim" in kinds
    claim_texts = " ".join(c["text"] for c in chunks if c.get("kind") == "claim")
    assert "Klasse 1A" in claim_texts or "1A" in claim_texts


def test_kabelklasser_retrieve_not_ceiling():
    hits = retrieve("Kabelklasser og avstandskrav", _emc_index(10), k=6)
    assert hits
    top = (hits[0].text + hits[0].file_id).lower()
    assert "ceiling" not in top


def test_omfang_helper_still_two_sentences():
    ans = synthesize_scope(_emc_index(54), artifact={"name": "EMC"}, lang="no")
    assert ans.grounded and "54" in ans.prose and "MANGLER" not in ans.prose


def test_ask_empty_hits_is_gap_not_essay():
    ans = ask(_emc_index(5), "sveisemetode WPS for aluminium trykktanker", lang="no")
    assert not ans.grounded and ans.gaps and len(ans.prose) < 80


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("ALL PASS")
