"""Tests for coverage-driven document length.

Run:  python -m pytest foldok_volume/tests -q
"""

from __future__ import annotations

import pytest

from foldok_volume.coverage import analyse, claim_budget, themes_of_corpus, widen

OUTLINE = [
    {"key": "scope", "title": "Omfang", "purpose": "hva dokumentet dekker"},
    {"key": "verify", "title": "Verifikasjon", "purpose": "måling og kontroll"},
]


def corpus():
    claims = []
    for i in range(14):
        claims.append({"text": f"Jording og ekvipotensialforbindelse skal utføres i punkt {i}",
                       "source": f"f{i % 4}.pdf"})
    for i in range(11):
        claims.append({"text": f"Skjerming av kabler krever 360 graders terminering {i}",
                       "source": f"g{i % 3}.pdf"})
    for i in range(7):
        claims.append({"text": f"Separasjonsavstand mellom kabelklasser er angitt {i}",
                       "source": f"h{i % 3}.pdf"})
    for i in range(2):
        claims.append({"text": f"Kuriositet nevnt en gang {i}", "source": "one.pdf"})
    return claims


# --- the reported problem ------------------------------------------------
def test_a_large_corpus_produces_more_sections_than_a_small_one():
    """6-7 fixed sections x 6 claims meant hundreds of pages became three."""
    small = analyse(corpus()[:4], OUTLINE)
    large = analyse(corpus(), OUTLINE)
    assert len(widen(OUTLINE, large)) > len(widen(OUTLINE, small))


def test_coverage_reports_how_much_the_fixed_outline_misses():
    report = analyse(corpus(), OUTLINE)
    assert report.coverage < 0.5
    assert "passer i den faste disposisjonen" in report.summary()


def test_the_claim_budget_scales_with_what_exists():
    """extract_claims(hits, limit=6) is a constant regardless of corpus size."""
    assert claim_budget(40, 8) == 6
    assert claim_budget(400, 8) > 6
    assert claim_budget(4000, 8) <= 24


def test_the_budget_never_drops_below_a_readable_floor():
    assert claim_budget(2, 8) == 6


# --- themes are topics, not filler ---------------------------------------
def test_verbs_and_prepositions_are_not_topics():
    """'Utføres', 'krever' and 'mellom' recur across documents exactly as
    reliably as 'jording' — frequency cannot tell them apart."""
    titles = {p.title.lower() for p in analyse(corpus(), OUTLINE).justified()}
    for filler in ("utføres", "krever", "mellom", "angitt"):
        assert filler not in titles


def test_real_subject_matter_becomes_a_section():
    titles = " ".join(p.title.lower() for p in analyse(corpus(), OUTLINE).justified())
    assert "kabelklasser" in titles or "separasjonsavstand" in titles


def test_a_theme_must_appear_in_more_than_one_document():
    """Filler recurs within one writer's prose; subject matter recurs between
    sources."""
    vocabulary = themes_of_corpus(corpus(), min_documents=2)
    assert all(len(docs) >= 2 for docs in vocabulary.values())


def test_a_one_off_mention_never_becomes_a_section():
    assert not any("uriositet" in p.title for p in analyse(corpus(), OUTLINE).justified())


def test_a_theme_the_outline_already_covers_is_not_duplicated():
    outline = [{"key": "shield", "title": "Skjerming", "purpose": "skjerming av kabler"}]
    report = analyse(corpus(), outline)
    assert not any(p.title.lower() == "skjerming" for p in report.justified())


# --- the user deletes, so the user must be able to judge -----------------
def test_every_proposal_carries_the_evidence_that_justified_it():
    for proposal in analyse(corpus(), OUTLINE).justified():
        assert proposal.evidence
        assert all(e.source for e in proposal.evidence)


def test_a_proposal_says_how_much_is_behind_it():
    proposal = analyse(corpus(), OUTLINE).justified()[0]
    assert "utsagn fra" in proposal.explain()
    assert str(proposal.weight) in proposal.explain()


def test_proposed_sections_are_marked_not_blended_in():
    """A document that grew for reasons nobody can see is worse than a short
    one."""
    widened = widen(OUTLINE, analyse(corpus(), OUTLINE))
    proposed = [s for s in widened if s.get("proposed")]
    assert proposed
    assert all(s.get("optional") for s in proposed)
    assert all(not s.get("proposed") for s in widened[:len(OUTLINE)])


def test_the_original_outline_survives_untouched():
    widened = widen(OUTLINE, analyse(corpus(), OUTLINE))
    assert [s["key"] for s in widened[:2]] == ["scope", "verify"]


def test_proposals_are_ordered_by_weight():
    proposals = analyse(corpus(), OUTLINE).justified()
    assert [p.weight for p in proposals] == sorted((p.weight for p in proposals), reverse=True)


# --- refusing to pad -----------------------------------------------------
def test_an_empty_corpus_proposes_nothing():
    assert analyse([], OUTLINE).justified() == []


def test_a_thin_corpus_does_not_get_padded():
    """Volume from repetition buries the real content."""
    thin = [{"text": "En enkelt observasjon om noe", "source": "a.pdf"}]
    assert analyse(thin, OUTLINE).justified() == []


def test_a_theme_from_a_single_source_is_not_enough():
    same = [{"text": f"Jording og ekvipotensialforbindelse punkt {i}", "source": "only.pdf"}
            for i in range(9)]
    assert analyse(same, OUTLINE).justified() == []


def test_the_report_serialises_for_the_editor():
    data = analyse(corpus(), OUTLINE).to_dict()
    assert data["schema_version"] == 1
    assert data["proposed"] and "coverage" in data
