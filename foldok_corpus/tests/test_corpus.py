"""Tests for wider extraction and the section market.

Run:  python -m pytest foldok_corpus/tests -q
"""

from __future__ import annotations

import copy

import pytest

from foldok_corpus import (
    BAND,
    build_offer,
    check_order,
    compare_documents,
    extract_many,
    extract_wide,
    to_outline,
)

DOCS = [
    ("EMC_BoD.pdf", """
Vi valgte lukkede kabelbaner framfor trådstiger for å møte Hard Spec fra Aker.
Begrunnelsen er at armering alene er en dårlig skjerm ved høye frekvenser.
Dette gir en 40 mm større bøyeradius enn opprinnelig prosjektert.
Ved temperaturer under -20 grader gjelder ikke kravet til bøyeradius.
Korrosjon i skjøtene ble oppdaget under befaring i mai 2026.
Det er ikke avklart om kabelbroen skal jordes i begge ender.
"""),
    ("Kabelplan.pdf", """
Vi valgte 6 mm2 framfor 4 mm2 etter revisjon C.
Kravet er revidert fra 4 mm2 til 6 mm2 i revisjon C.
Leverandøren skal levere samsvarserklæring før montering starter.
Sone 2 er unntatt fra kravet om 360 graders terminering.
Ved forhold under -20 grader kreves egen vurdering.
Skade på skjerm ble oppdaget ved mottakskontroll.
Det er ikke avklart hvem som eier grensesnittet mot leverandøren.
Etter at kabelbroen er montert, trekkes kabel i henhold til kabelplan.
"""),
]


def offer():
    wide = extract_many(DOCS)
    return build_offer([c.to_dict() for c in wide.claims])


# --- extraction variety --------------------------------------------------
def test_content_that_is_not_a_fact_is_extracted():
    """All ten existing claim types answer 'what is true?'. A folder is full of
    decisions, problems and open questions, and none of them fit."""
    counts = extract_many(DOCS).counts()
    for kind in ("decision", "problem", "open_question", "condition", "change"):
        assert counts.get(kind), kind


def test_each_new_type_seeds_a_different_kind_of_section():
    seen = {c.section_hint[0] for c in extract_many(DOCS).claims}
    assert len(seen) >= 6


def test_one_sentence_can_be_two_kinds_of_content():
    """'Vi valgte X fordi Y' is a decision and a justification, and they feed
    different sections. Forcing one reading is what made documents alike."""
    found = extract_wide(
        "Vi valgte lukkede baner fordi armering skjermer dårlig.", source="x"
    )
    assert {c.type for c in found.claims} >= {"decision", "justification"}


def test_a_change_is_recognised_as_its_own_content():
    found = extract_wide("Kravet er revidert fra 4 mm2 til 6 mm2 i revisjon C.", source="x")
    assert any(c.type == "change" for c in found.claims)


def test_an_unresolved_item_is_recognised():
    found = extract_wide("Det er ikke avklart hvem som eier grensesnittet.", source="x")
    assert any(c.type == "open_question" for c in found.claims)


def test_english_prose_works_too():
    found = extract_wide(
        "We chose closed trays instead of wire ladders because armouring shields poorly.",
        source="x")
    assert {c.type for c in found.claims} >= {"decision"}


def test_boilerplate_is_not_content():
    found = extract_wide(
        "Subject to change without notice. Contact us at post@example.no for details.",
        source="x")
    assert found.claims == []


# --- the market ----------------------------------------------------------
def test_the_folder_is_reported_before_any_document_type_is_chosen():
    text = offer().report()
    assert "Ingen dokumenttype er valgt" in text
    assert "Dokumentet blir det du beholder" in text


def test_two_statements_from_two_sources_is_enough():
    """Requiring three suppressed exactly the sections that make documents
    differ — decisions, conditions, problems. They are rarer by nature, not less
    important."""
    keys = {o.key for o in offer().offers}
    assert "sec.decision" in keys and "sec.open_question" in keys


def test_one_source_saying_it_twice_is_not_enough():
    single = extract_many([("only.pdf", DOCS[0][1])])
    keys = {o.key for o in build_offer([c.to_dict() for c in single.claims]).offers}
    assert "sec.decision" not in keys


def test_one_source_saying_it_four_times_is_enough():
    text = "\n".join(
        f"Vi valgte alternativ {i} framfor alternativ {i + 1} av hensyn til EMC."
        for i in range(4)
    )
    found = extract_many([("only.pdf", text)])
    keys = {o.key for o in build_offer([c.to_dict() for c in found.claims]).offers}
    assert "sec.decision" in keys


def test_everything_is_offered_as_kept():
    """Abundance: the user deletes, rather than hunting for what to add."""
    assert all(o.kept for o in offer().offers)


def test_every_offer_carries_its_evidence():
    for o in offer().offers:
        assert o.weight and o.sources and o.samples


# --- the arc -------------------------------------------------------------
def test_narrative_order_is_enforced_not_left_to_weight():
    """A pile of sections in no order is not a document."""
    ordered = offer().ordered()
    ranks = [o.rank for o in ordered]
    assert ranks == sorted(ranks)


def test_evidence_never_precedes_its_basis():
    outline = to_outline(offer())
    assert check_order(outline) == []


def test_a_broken_arc_is_reported():
    bad = [
        {"title": "Avvik", "band": "exception"},
        {"title": "Omfang", "band": "frame"},
    ]
    problems = check_order(bad)
    assert problems and "reads as a mistake" in problems[0]


def test_weight_orders_within_a_band_only():
    ordered = offer().ordered()
    basis = [o for o in ordered if o.band == "basis"]
    assert [o.weight for o in basis] == sorted((o.weight for o in basis), reverse=True)


# --- the user decides ----------------------------------------------------
def test_deleting_a_section_changes_the_document():
    o = offer()
    before = len(o.ordered())
    o.drop("sec.decision")
    assert len(o.ordered()) == before - 1


def test_two_selections_produce_genuinely_different_documents():
    a = copy.deepcopy(offer()).keep_only(["sec.rule", "sec.condition", "sec.problem"])
    b = copy.deepcopy(offer()).keep_only(["sec.rule", "sec.decision", "sec.open_question"])
    assert {s["key"] for s in to_outline(a)} != {s["key"] for s in to_outline(b)}


def test_the_overlap_between_documents_is_stated_not_hidden():
    """Five documents that differ only in name is what this replaces."""
    a = copy.deepcopy(offer()).keep_only(["sec.condition", "sec.problem"])
    b = copy.deepcopy(offer()).keep_only(["sec.condition", "sec.decision"])
    text = compare_documents([a, b], ["Kravdokument", "Beslutningsnotat"])
    assert "unik" in text and "felles for alle" in text


def test_identical_selections_are_called_identical():
    """Abundance cannot manufacture distinctness that is not in the corpus."""
    a = copy.deepcopy(offer()).keep_only(["sec.rule"])
    b = copy.deepcopy(offer()).keep_only(["sec.rule"])
    text = compare_documents([a, b], ["A", "B"])
    assert "identiske i innhold" in text


def test_documents_that_share_nothing_are_told_so():
    """Zero overlap is a finding, not a blank line."""
    a = copy.deepcopy(offer()).keep_only(["sec.problem"])
    b = copy.deepcopy(offer()).keep_only(["sec.decision"])
    assert "deler ikke innhold" in compare_documents([a, b], ["A", "B"])


def test_an_empty_folder_offers_nothing_rather_than_a_template():
    assert build_offer([]).offers == []
