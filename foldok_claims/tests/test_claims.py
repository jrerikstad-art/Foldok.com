"""Tests for claim extraction and coherence.

Fixtures are the real EMC material: the failure that forced this package was a
standards folder yielding eight quantities and nothing else.

Run:  python -m pytest foldok_claims/tests -q
"""

from __future__ import annotations

import pytest

from foldok_claims import Claim, Quantity, Scope, check, extract, extract_many

EMC = """
EMC beskriver et systems evne til å operere i sitt tiltenkte miljø uten å bli påvirket av EMI.
Klasse 1A omfatter millivolt-transdusere og radiomottakere.
Klasse 1A skal føres i separate bunter, adskilt fra Klasse 1B.
For Klasse 4 er skjermede kabler og 360 bonding ved alle termineringer kritisk.
Armering benyttes ofte som skjerm, men armering alene er en dårlig skjerm for høye frekvenser.
For å møte Hard Spec fra Aker er hovedregelen at fullstendig lukkede systemer er påkrevd.
Trådstiger kan i visse frekvensområder gi bedre resultater enn lukkede baner.
Maksimalt to gjenger skal stikke ut fra mutteren.
Bruk av blindmutre er foretrukket for å sikre en glatt overflate.
Systemfeil forårsaket av magnetisk interferens er ekstremt vanskelig å lokalisere.
EMC-testing skal dekke måling av emisjon og immunitet fra DC til 1 GHz.
Kontakt oss på post@example.no eller +47 51 22 33 44.
"""

CHALFANT = """
Premium and Ultra RF classes are tested to MIL-STD-285.
Attenuation is 70-120 dB across 150 kHz to 1 GHz.
"""


def both():
    return extract_many([("emc_notes", EMC), ("Chalfant.pdf", CHALFANT)])


# --- the failure this replaces -------------------------------------------
def test_knowledge_that_is_not_a_quantity_survives_extraction():
    """Under the fact schema this folder produced eight quantities. Everything
    below was in the same text and had nowhere to go."""
    counts = extract(EMC, source="emc").claims.counts()
    for kind in ("rule", "classification", "hypothesis", "distinction", "risk"):
        assert counts.get(kind), kind


def test_a_measured_assertion_is_still_a_claim():
    """'Attenuation is 70-120 dB across 150 kHz to 1 GHz' matched no family in
    the first version and produced nothing — the most useful line in the
    datasheet."""
    claims = extract(CHALFANT, source="c").claims
    quantities = claims.of_type("quantity")
    assert quantities and quantities[0].quantity.unit == "dB"
    assert quantities[0].quantity.low == 70 and quantities[0].quantity.high == 120


def test_contact_details_and_marketing_are_dropped():
    for c in extract(EMC, source="emc").claims:
        assert "@" not in c.text and "+47" not in c.text


def test_an_obligation_is_not_a_description():
    claims = extract(EMC, source="emc").claims
    assert any(c.modality == "shall" and c.binding for c in claims)
    assert any(c.modality == "hypothesis" and not c.binding for c in claims)


def test_a_hypothesis_is_never_binding():
    for c in extract(EMC, source="emc").claims.hypotheses():
        assert not c.binding


def test_an_obligation_without_a_modal_verb_is_still_an_obligation():
    """'For Klasse 4 er skjermede kabler ... kritisk' has no skal/må."""
    claims = extract("For Klasse 4 er skjermede kabler og bonding kritisk.", source="x").claims
    assert claims.binding()


def test_a_stated_inadequacy_is_kept():
    claims = extract(
        "Armering alene er en dårlig skjerm for høye frekvenser.", source="x"
    ).claims
    assert claims.of_type("distinction")
    assert claims.claims[0].negated


def test_scope_is_lifted_out_of_the_sentence():
    claims = extract("Klasse 1A skal føres i separate bunter.", source="x").claims
    assert claims.claims[0].scope.cable_class == "1A"


def test_a_frequency_range_becomes_comparable():
    claims = extract("EMC-testing skal dekke DC til 1 GHz.", source="x").claims
    freq = claims.claims[0].scope.frequency
    assert freq and freq.low == 0 and freq.high == 1e9


# --- coherence: what a summary cannot do --------------------------------
def test_a_hypothesis_against_a_hard_spec_is_surfaced():
    """The project hypothesises wire trays may beat closed trays; the customer
    requires fully closed systems. A summary states both and moves on."""
    findings = check(both()).of("contested")
    assert findings
    assert "trådstige" in findings[0].summary and "lukket" in findings[0].summary
    assert "until the hypothesis is tested" in findings[0].question


def test_an_uncovered_frequency_band_is_surfaced():
    """Required DC–1 GHz, evidenced 150 kHz–1 GHz. Nobody reading a summary of
    both documents notices the bottom of the band."""
    findings = check(both()).of("scope_gap")
    assert findings
    assert "below 150 kHz" in findings[0].summary
    assert "DC–1 GHz" in findings[0].summary


def test_a_frequency_range_is_shown_the_way_engineers_write_it():
    summary = check(both()).of("scope_gap")[0].summary
    assert "1000000000" not in summary


def test_no_regex_ever_reaches_the_user():
    for finding in check(both()).findings:
        blob = finding.summary + finding.detail + finding.question
        for token in ("\\w", "[åa]", "|", "re.I"):
            assert token not in blob, finding.summary


def test_every_finding_asks_a_question_a_person_can_answer():
    for finding in check(both()).findings:
        assert finding.question.endswith("?")


def test_contradicting_quantities_on_the_same_property_are_caught():
    claims = [
        Claim(id="a", type="rule", subject="tray", text="attenuation shall be 30-40 dB",
              modality="shall", predicate="attenuation",
              quantity=Quantity(30, 40, "dB"), source="spec_a"),
        Claim(id="b", type="rule", subject="tray", text="attenuation shall be 70-120 dB",
              modality="shall", predicate="attenuation",
              quantity=Quantity(70, 120, "dB"), source="spec_b"),
    ]
    findings = check(claims).of("contradicts")
    assert findings and "30–40 dB" in findings[0].summary


def test_overlapping_quantities_are_not_a_conflict():
    claims = [
        Claim(id="a", type="rule", subject="t", text="at least 60 dB", modality="shall",
              predicate="attenuation", quantity=Quantity(60, 120, "dB"), source="a"),
        Claim(id="b", type="rule", subject="t", text="70-120 dB", modality="shall",
              predicate="attenuation", quantity=Quantity(70, 120, "dB"), source="b"),
    ]
    assert check(claims).of("contradicts") == []


def test_claims_in_different_cable_classes_do_not_conflict():
    """Class 1A and Class 4 requirements are allowed to differ."""
    claims = [
        Claim(id="a", type="rule", subject="c", text="skal skjermes", modality="shall",
              predicate="shielding", scope=Scope(cable_class="1A"), source="a"),
        Claim(id="b", type="rule", subject="c", text="kan være uskjermet", modality="shall",
              predicate="shielding", scope=Scope(cable_class="4"), source="b"),
    ]
    assert check(claims).of("contradicts") == []


def test_the_same_requirement_from_several_sources_is_flagged_once():
    text = "Alle termineringer skal ha 360 graders bonding langs hele traséen."
    claims = extract_many([("en50174.pdf", text), ("nek400.pdf", text)])
    assert check(claims).of("duplicate")


def test_a_clean_library_reports_no_conflicts():
    report = check(extract("Klasse 1A omfatter millivolt-transdusere.", source="x").claims)
    assert report.ok


def test_the_report_is_readable():
    text = check(both()).report()
    assert "claim(s) from 2 source(s)" in text
    assert "[high]" in text


# --- retrieval integration -----------------------------------------------
INDEX = [
    {"file": "Docs/EMC BoD.pptx", "caption": "EMC and HVDC foundations",
     "detail_summary": (
         "Klasse 1A omfatter millivolt-transdusere og radiomottakere. "
         "Klasse 1A skal føres i separate bunter, adskilt fra Klasse 1B.\n"
         "Klasse 1B omfatter Ethernet og lignende datatrafikk; skjermet kabel kreves.\n"
         "For å møte Hard Spec fra Aker er hovedregelen at fullstendig lukkede "
         "systemer er påkrevd.\n"
         "Trådstiger kan i visse frekvensområder gi bedre resultater enn lukkede baner.\n"
         "EMC-testing skal dekke måling av emisjon og immunitet fra DC til 1 GHz.\n"
         "EN 50310 krever ekvipotensial jording og bonding i komplekse anlegg."
     )},
    {"file": "Docs/Chalfant.pdf", "caption": "Chalfant EMI/RFI shielded cable tray",
     "detail_summary": "Attenuation is 70-120 dB across 150 kHz to 1 GHz."},
    {"file": "Docs/photo.jpg", "kind": "skipped"},
]


def indexed():
    from foldok_claims import claims_from_index

    return claims_from_index(INDEX)


def test_the_cable_class_section_can_now_be_filled():
    """The Temabrief had this heading and never named a class, because the only
    retrievable units were file-level summaries."""
    classes = [c for c in indexed().claims if c.scope.cable_class or c.type == "classification"]
    text = " ".join(c.text for c in classes)
    assert "Klasse 1A" in text and "Klasse 1B" in text


def test_a_sentence_can_be_both_a_classification_and_a_rule():
    """'Klasse 1B omfatter Ethernet; skjermet kabel kreves' is both, and losing
    the classification is what emptied the section."""
    claims = [c for c in indexed().claims if "1B omfatter" in c.text]
    assert {c.type for c in claims} >= {"classification", "rule"}


def test_skipped_index_entries_are_ignored():
    assert all(c.source != "photo.jpg" for c in indexed().claims)


def test_claims_become_chunks_in_the_shape_retrieval_expects():
    from foldok_claims import as_chunks

    chunks = as_chunks(indexed().claims)
    assert chunks
    for chunk in chunks:
        for field in ("chunk_id", "file_id", "path", "text", "kind", "tags", "fact_key"):
            assert field in chunk
        assert chunk["kind"] == "claim"


def test_a_claim_chunk_is_never_truncated():
    """span=text[:80] is where 'enabling more efficie relevant for samme
    argument' came from — a summary cut mid-word with a connector glued on."""
    from foldok_claims import as_chunks

    for chunk in as_chunks(indexed().claims):
        assert not chunk["text"].endswith("…")
        assert chunk["text"][-1] in ".!?" or len(chunk["text"]) < 200


def test_chunks_carry_the_metadata_ranking_needs():
    from foldok_claims import as_chunks

    binding = [c for c in as_chunks(indexed().claims) if c["claim_binding"]]
    assert binding
    assert any(c["claim_scope"] for c in as_chunks(indexed().claims))


# --- the standards register ----------------------------------------------
def test_the_register_says_what_a_standard_requires():
    """The old one printed '); cable classification (Class 1-6)' — a character
    window taken from wherever the name appeared."""
    from foldok_claims import standards_register

    register = {r["standard"]: r for r in standards_register(indexed().claims)}
    assert "EN 50310" in register
    entry = register["EN 50310"]
    assert not entry["mentioned_only"]
    assert "jording" in entry["requirements"][0]


def test_no_register_entry_begins_mid_sentence():
    from foldok_claims import standards_register

    for entry in standards_register(indexed().claims):
        for requirement in entry["requirements"]:
            assert not requirement.lstrip().startswith((")", ";", ",", "and "))


def test_a_standard_only_mentioned_is_marked_as_such():
    from foldok_claims import extract, standards_register

    claims = extract("Se også ISO 9001 for kvalitetsstyring.", source="x").claims
    register = standards_register(claims)
    assert not register or all(r["mentioned_only"] for r in register)


def test_the_register_renders_without_regex_or_fragments():
    from foldok_claims import register_markdown, standards_register

    text = register_markdown(standards_register(indexed().claims))
    assert "EN 50310" in text and "Krav fra standarder" in text


# --- the coherence block --------------------------------------------------
def test_the_findings_block_is_produced_for_a_real_index():
    from foldok_claims import coherence_section

    text = coherence_section(indexed().claims)
    assert "Konflikter" in text
    assert "trådstige" in text


# --- the ranking patch ----------------------------------------------------
def test_the_ranking_patch_is_idempotent_and_reports_honestly(tmp_path):
    from foldok_claims import apply_ranking_patch

    target = tmp_path / "retrieve.py"
    target.write_text(
        'def s(chunk):\n'
        '    if chunk.get("kind") in ("caption", "detail"):\n'
        '        score += 0.05\n'
        '    return score\n',
        encoding="utf-8",
    )
    ok, msg = apply_ranking_patch(target, dry_run=True)
    assert ok and "would patch" in msg
    ok, msg = apply_ranking_patch(target)
    assert ok and 'kind") == "claim"' in target.read_text(encoding="utf-8")
    ok, msg = apply_ranking_patch(target)
    assert ok and msg == "already patched"


def test_the_patch_refuses_rather_than_guessing_when_the_file_moved_on(tmp_path):
    from foldok_claims import apply_ranking_patch

    target = tmp_path / "retrieve.py"
    target.write_text("def s(chunk):\n    return 0.0\n", encoding="utf-8")
    ok, msg = apply_ranking_patch(target)
    assert not ok and "by hand" in msg
