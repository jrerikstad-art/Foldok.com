"""Tests for the sense-making assembler.

Run:  python -m pytest foldok_sense/tests -q
"""

from __future__ import annotations

import pytest

from foldok_sense import Passage, assemble, discover_topics, passages_from
from foldok_sense.assemble import _stem


def corpus():
    out = []
    for i in range(7):
        out.append(Passage(f"Skjermingen skal termineres 360 grader i punkt {i}.",
                           source="EMC_BoD.pdf", tier="strong", claim_type="rule"))
    for i in range(3):
        out.append(Passage(f"Skjerming av kabel kontrolleres ved mottak {i}.",
                           source="Protokoll.pdf", tier="candidate"))
    for i in range(5):
        out.append(Passage(f"Kabelen legges i egen kabelbro langs vegg {i}.",
                           source="Kabelplan.pdf", tier="candidate"))
    for i in range(4):
        out.append(Passage(f"Jording av tavlen utføres til hovedjordskinne {i}.",
                           source="EMC_BoD.pdf", tier="strong", claim_type="rule"))
    for i in range(3):
        out.append(Passage(f"Jordingen kontrolleres ved overlevering {i}.",
                           source="Protokoll.pdf", tier="candidate"))
    return out


# --- topics come from the folder ----------------------------------------
def test_topics_are_discovered_not_named_in_advance():
    """The template asked 'what fills Installation?' and reported empty. This
    asks what the folder contains."""
    topics = discover_topics(corpus())
    joined = " ".join(topics).lower()
    assert "skjerm" in joined or "kabel" in joined
    assert "jord" in joined


def test_a_topic_needs_to_recur_across_sources():
    passages = [Passage(f"Korrosjon i skjøtene punkt {i}.", source="one.pdf")
                for i in range(3)]
    passages += [Passage(f"Skjerming skal termineres {i}.", source="a.pdf") for i in range(3)]
    passages += [Passage(f"Skjerming er kritisk {i}.", source="b.pdf") for i in range(3)]
    topics = discover_topics(passages)
    assert any("skjerm" in t for t in topics)


def test_a_single_document_folder_still_yields_topics():
    """Cross-source recurrence is impossible with one file, and a folder of one
    file is still a folder somebody wants sense made of."""
    single = [Passage(f"Skjerming av kabler skal termineres {i}.", source="only.pdf")
              for i in range(6)]
    assert discover_topics(single)


def test_document_furniture_never_becomes_a_topic():
    """'Page 17' appears in every cross-reference."""
    passages = [Passage(f"See figure {i} on page 17 for the arrangement shown.",
                        source=f"f{i}.pdf") for i in range(6)]
    topics = [t.lower() for t in discover_topics(passages)]
    assert "page" not in topics and "figure" not in topics


# --- inflection ----------------------------------------------------------
@pytest.mark.parametrize("a,b,same", [
    ("cable", "cables", True),
    ("connection", "connected", True),
    ("shielding", "shield", True),
    ("earth", "earthing", True),
    ("kabel", "kabler", True),
    ("skjerming", "skjerm", True),
    ("jording", "jord", True),
    ("cable", "cabinet", False),
])
def test_inflected_forms_are_one_topic(a, b, same):
    """'Cable' and 'Cables' as two headings about the same thing is what this
    prevents."""
    assert (_stem(a) == _stem(b)) is same


def test_the_heading_reads_as_a_word_not_a_stem():
    for title in discover_topics(corpus()):
        assert not title.endswith(("bl", "ngr"))
        assert title.isalpha()


# --- assembly ------------------------------------------------------------
def test_passages_are_grouped_under_the_topics_they_mention():
    draft = assemble(corpus())
    assert draft.justified()
    for group in draft.justified():
        assert group.passages and group.sources


def test_strong_passages_lead_and_descriptive_ones_follow():
    draft = assemble(corpus())
    group = max(draft.justified(), key=lambda g: g.weight)
    tiers = [p.tier for p in group.passages]
    assert tiers[0] == "strong"
    assert tiers == sorted(tiers, key=lambda t: 0 if t == "strong" else 1)


def test_a_descriptive_passage_is_marked_in_the_output():
    """The user deletes, so the user has to see which is which."""
    md = assemble(corpus()).markdown()
    assert " ^  *(" in md or "^  *(" in md
    assert "beskrivende tekst uten eksplisitt krav" in md


def test_provenance_is_honest_about_the_tier():
    strong = Passage("Skjerming skal termineres.", source="a.pdf",
                     tier="strong", claim_type="rule")
    weak = Passage("Kabelen legges i kabelbro.", source="a.pdf", tier="candidate")
    assert "rule" in strong.provenance
    assert weak.provenance == "a.pdf"


def test_every_passage_keeps_its_source():
    for group in assemble(corpus()).justified():
        assert all(p.source for p in group.passages)


# --- figures -------------------------------------------------------------
def test_a_figure_lands_in_the_topic_its_caption_matches():
    figures = [{"id": "FIG1", "caption": "Figure 3: Skjerming av kabel i bro",
                "source": "EMC_BoD.pdf"}]
    draft = assemble(corpus(), figures=figures)
    placed = [g for g in draft.justified() if g.figures]
    assert placed


def test_a_figure_with_no_matching_topic_stays_unplaced():
    """Dropping it into the nearest group would be a quiet lie."""
    figures = [{"id": "FIG9", "caption": "Figure 9: Organisasjonskart", "source": "x.pdf"}]
    draft = assemble(corpus(), figures=figures)
    assert any(f["id"] == "FIG9" for f in draft.orphan_figures)


def test_unplaced_figures_are_listed_rather_than_dropped():
    figures = [{"id": "FIG9", "caption": "Organisasjonskart", "source": "x.pdf"}]
    md = assemble(corpus(), figures=figures).markdown()
    assert "Figurer uten tema" in md


# --- what the folder does not contain ------------------------------------
def test_a_missing_topic_is_a_finding_not_an_empty_heading():
    """'Installation: (empty)' is useless. 'Your folder has no installation
    procedures' is what the user needs."""
    draft = assemble(corpus(), expected=["installasjon", "prisberegning"])
    assert "installasjon" in draft.absent
    assert "Ikke dekket i mappen" in draft.summary()


def test_the_absent_section_says_what_to_do():
    draft = assemble(corpus(), expected=["installasjon"])
    md = draft.markdown()
    assert "Ikke dekket av kildene" in md
    assert "må skrives eller kildene må utvides" in md


def test_a_topic_that_is_present_is_not_reported_absent():
    draft = assemble(corpus(), expected=["skjerming"])
    assert "skjerming" not in draft.absent


# --- the bridge ----------------------------------------------------------
def test_rejected_sentences_never_reach_the_draft():
    class FakeSentence:
        def __init__(self, text, tier):
            self.text, self.tier, self.source, self.claim_type = text, tier, "a.pdf", ""

    class FakeReport:
        sentences = [FakeSentence("Copyright notice.", "rejected"),
                     FakeSentence("Skjerming skal termineres.", "strong")]

    passages = passages_from(FakeReport())
    assert len(passages) == 1 and "Skjerming" in passages[0].text


def test_candidates_can_be_excluded_for_a_strict_draft():
    class FakeSentence:
        def __init__(self, text, tier):
            self.text, self.tier, self.source, self.claim_type = text, tier, "a.pdf", ""

    class FakeReport:
        sentences = [FakeSentence("Beskrivende setning her.", "candidate"),
                     FakeSentence("Skjerming skal termineres.", "strong")]

    assert len(passages_from(FakeReport(), include_candidates=False)) == 1


def test_an_empty_folder_produces_an_honest_empty_draft():
    draft = assemble([])
    assert draft.justified() == []
    assert draft.markdown().strip()


# --- degrading honestly --------------------------------------------------
def test_a_folder_with_no_shared_vocabulary_still_produces_topics():
    """Measured on a real mixed folder — one English PDF plus two Norwegian
    files — zero stems appeared in two sources. Returning nothing there is the
    wrong answer; the folder still has topics, just per document."""
    mixed = [Passage(f"Shielding shall be terminated at the gland {i}.",
                     source="en.pdf", tier="strong", claim_type="rule")
             for i in range(6)]
    mixed += [Passage(f"Jording utføres til hovedjordskinne punkt {i}.",
                      source="no.pdf", tier="strong", claim_type="rule")
              for i in range(6)]
    draft = assemble(mixed)
    assert draft.justified()


def test_uncorroborated_topics_are_declared_as_such():
    """A compliance engineer signing this should know which topics recur across
    sources and which came from one document."""
    single_lang = [Passage(f"Shielding shall be terminated {i}.", source="en.pdf")
                   for i in range(6)]
    draft = assemble(single_lang)
    assert not draft.corroborated
    assert "ikke bekreftet" in draft.summary() or "not corroborated" in draft.summary(lang="en")


def test_a_corroborated_folder_says_nothing_extra():
    draft = assemble(corpus())
    assert draft.corroborated
    assert "ikke bekreftet" not in draft.summary()


def test_function_words_never_become_topics():
    """'Separate', 'Over' and 'Under' became headings, because they recur across
    every document precisely by being prose."""
    passages = []
    for i in range(6):
        passages.append(Passage(
            f"Kabler skal føres separate over og under kabelbroen punkt {i}.",
            source=f"f{i % 3}.pdf"))
    titles = {g.title.lower() for g in assemble(passages).justified()}
    for word in ("separate", "over", "under"):
        assert word not in titles


def test_domain_nouns_ending_in_ing_survive():
    """A suffix rule for '-ing' and '-ed' removed shielding, earthing, bonding
    and jording — every real topic in this domain."""
    from foldok_sense.assemble import NOT_A_TOPIC

    for noun in ("shielding", "earthing", "bonding", "jording", "skjerming"):
        assert not NOT_A_TOPIC.search(noun), noun


def test_verb_stems_are_still_excluded():
    from foldok_sense.assemble import NOT_A_TOPIC

    for verb in ("required", "recommended", "utføres", "krever", "separate"):
        assert NOT_A_TOPIC.search(verb), verb
