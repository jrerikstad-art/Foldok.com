"""Tests for local learning.

The two that matter most: no text from a standard is ever stored, and nothing
learned here can be packaged for anyone else.

Run:  python -m pytest foldok_learn/tests -q
"""

from __future__ import annotations

import pytest

from foldok_learn import (
    ClauseFinding,
    Learner,
    Lesson,
    SharingRefused,
    extract,
    to_requirements,
)

STANDARD = """
6.1 General
The installation shall be verified before being put into service.

§6-61 Verification by testing
Every final circuit shall be subjected to an insulation resistance measurement.
The continuity of every protective conductor shall be measured and recorded.
Each circuit should be tested for earth fault loop impedance.

§8-1 Documentation
The distribution board shall be documented with a single line diagram.
A photograph of each board should be included in the handover documentation.
The responsible undertaking shall sign the declaration of conformity.
"""

NORSK = """
§6-61 Verifikasjon
Hver kurs skal måles for isolasjonsmotstand.
Hvert anlegg bør fotograferes før overlevering.
"""


# --- reading a standard --------------------------------------------------
def test_clauses_and_obligations_are_found():
    ex = extract(STANDARD, source="f1")
    clauses = {f.clause for f in ex.findings}
    assert "§6-61" in clauses and "§8-1" in clauses
    assert ex.with_obligation >= 5


def test_no_sentence_from_the_standard_is_ever_stored():
    """The line this whole package turns on: you may keep what a standard
    requires, never what it says."""
    ex = extract(STANDARD, source="f1")
    blob = str([f.to_dict() for f in ex.findings])
    for phrase in ("insulation resistance measurement", "protective conductor",
                   "declaration of conformity", "single line diagram", "shall be"):
        assert phrase not in blob
    assert all(f.quote_length > 0 for f in ex.findings)     # a number, not the text


def test_obligation_strength_becomes_severity():
    findings = {f.clause + f.artifact: f for f in extract(STANDARD).findings}
    shall = [f for f in findings.values() if f.obligation == "shall"]
    should = [f for f in findings.values() if f.obligation == "should"]
    assert all(f.severity == "blocking" for f in shall)
    assert all(f.severity == "recommended" for f in should)


def test_the_kind_of_evidence_is_detected():
    kinds = {f.artifact for f in extract(STANDARD).findings}
    assert {"measurement", "photo", "signature"} <= kinds


def test_repetition_scope_is_detected():
    per = {f.per for f in extract(STANDARD).findings}
    assert "circuit" in per and "board" in per


def test_measurements_and_photos_are_marked_evidential():
    for f in extract(STANDARD).findings:
        assert f.evidential == (f.artifact in ("measurement", "photo", "signature"))


def test_norwegian_standards_are_read_too():
    ex = extract(NORSK, source="f2")
    assert ex.findings
    assert {"measurement", "photo"} & {f.artifact for f in ex.findings}
    assert any(f.per == "circuit" for f in ex.findings)


def test_a_document_with_no_obligations_yields_nothing():
    assert extract("This brochure describes our range of enclosures.").findings == []


def test_low_confidence_findings_are_dropped():
    weak = "It may be useful to consider the layout."
    assert extract(weak, min_confidence=0.6).findings == []


# --- turning clauses into requirements -----------------------------------
def test_requirements_are_foldok_shaped_and_cite_the_clause():
    findings = extract(STANDARD).findings
    reqs = to_requirements(findings, standard="NEK 400:2022")
    assert reqs
    for r in reqs:
        assert r["authority"].startswith("NEK 400:2022")
        assert r["evidence"] in ("evidential", "expository")
        assert "local" in r["tags"]


def test_a_requirement_title_is_foldoks_wording_not_the_standards():
    reqs = to_requirements(extract(STANDARD).findings, standard="NEK 400")
    titles = " ".join(r["title"] for r in reqs)
    assert "shall" not in titles
    assert "Measurement required" in titles


def test_extracted_requirements_load_into_the_gap_engine():
    from foldok_gaps import RequirementPack

    pack = RequirementPack.from_dict({
        "id": "local.nek400", "title": "local", "segment": "electrical",
        "sections": [{"id": s, "title": s} for s in
                     ("verification", "installation", "handover", "drawings", "description")],
        "requirements": to_requirements(extract(STANDARD).findings, standard="NEK 400"),
    })
    assert pack.requirements
    assert all(r.authority for r in pack.requirements)


# --- the sharing wall ----------------------------------------------------
def test_a_local_pack_is_born_reference_only():
    learner = Learner()
    _, lessons = learner.observe_standard(STANDARD, standard="NEK 400", source="f1")
    for lesson in lessons:
        learner.accept(lesson.id)
    pack = learner.local_pack("NEK 400")
    assert pack["local_only"] is True
    assert pack["redistribution"] == "reference_only"


def test_foldok_assets_refuses_to_package_anything_learned_locally():
    from foldok_assets import Asset, AssetLibrary, PackRefused, Source

    lib = AssetLibrary([
        Asset(id="requirement_pack.local_nek400", kind="requirement_pack",
              source=Source(origin="foldok", redistribution="reference_only",
                            cites=("NEK 400",)))
    ])
    with pytest.raises(PackRefused) as exc:
        lib.seal(lib.pack("share_it", ["requirement_pack.local_nek400"]))
    assert "cited, never shipped" in str(exc.value)


def test_export_is_a_deliberate_wall_not_an_oversight():
    learner = Learner()
    learner.observe_standard(STANDARD, standard="NEK 400", source="f1")
    with pytest.raises(SharingRefused) as exc:
        learner.export()
    assert "consent, sanitising and a licence" in str(exc.value)


# --- learning from work --------------------------------------------------
class FakePin:
    def __init__(self, target, prop, value, layer="user"):
        self.target, self.prop, self.value, self.layer = target, prop, value, layer


class FakePins:
    def __init__(self, pins):
        self._pins = pins

    def user_pins(self):
        return [p for p in self._pins if p.layer == "user"]


class FakeBlock:
    def __init__(self, bid, role):
        self.id, self.role = bid, role


class FakeTemplate:
    id = "foldok.compliance.a4"

    def __init__(self):
        self.role_defaults: dict = {}


class FakeSession:
    def __init__(self, pins, blocks):
        self.pins, self.blocks, self.template = FakePins(pins), blocks, FakeTemplate()


def layout_session(span=4):
    return FakeSession(
        pins=[
            FakePin("block:img1", "span", span),
            FakePin("block:img2", "span", span),
            FakePin("block:tpl", "span", 12, layer="template"),
        ],
        blocks=[FakeBlock("img1", "image"), FakeBlock("img2", "image"), FakeBlock("tpl", "text")],
    )


def test_only_the_users_own_edits_count_as_evidence():
    """Template defaults are not evidence of anything — they are what the user
    was given."""
    learner = Learner()
    lessons = learner.observe_layout(layout_session(), document_id="doc1")
    assert [l.subject for l in lessons] == ["image"]


def test_one_example_is_not_a_preference():
    learner = Learner()
    learner.observe_layout(layout_session(), document_id="doc1")
    assert learner.proposals() == []


def test_repeated_evidence_makes_a_proposal():
    learner = Learner()
    for i in range(3):
        learner.observe_layout(layout_session(), document_id=f"doc{i}")
    proposals = learner.proposals()
    assert proposals
    assert "image" in proposals[0].effect and "4" in proposals[0].effect


def test_a_changed_habit_starts_the_evidence_again():
    """Averaging two different preferences produces one that is nobody's."""
    learner = Learner()
    for i in range(3):
        learner.observe_layout(layout_session(span=4), document_id=f"a{i}")
    learner.observe_layout(layout_session(span=6), document_id="b1")
    lesson = learner.lessons(kind="layout")[0]
    assert lesson.value == 6 and lesson.support == 1


def test_accepting_below_threshold_is_refused():
    learner = Learner()
    learner.observe_layout(layout_session(), document_id="doc1")
    lesson = learner.lessons(kind="layout")[0]
    with pytest.raises(ValueError) as exc:
        learner.accept(lesson.id)
    assert "needs" in str(exc.value)


def test_a_rejected_lesson_stops_asking():
    learner = Learner()
    for i in range(3):
        learner.observe_layout(layout_session(), document_id=f"doc{i}")
    lesson = learner.lessons(kind="layout")[0]
    learner.reject(lesson.id)
    for i in range(3):
        learner.observe_layout(layout_session(), document_id=f"later{i}")
    assert learner.proposals() == []


def test_an_applied_lesson_can_always_be_reverted():
    learner = Learner()
    for i in range(3):
        learner.observe_layout(layout_session(), document_id=f"doc{i}")
    lesson = learner.lessons(kind="layout")[0]
    learner.accept(lesson.id)
    template = FakeTemplate()
    assert learner.apply_layout(template) == [lesson.id]
    assert template.role_defaults["image"]["span"] == 4
    learner.revert(lesson.id)
    assert learner.apply_layout(FakeTemplate()) == []


def test_forgetting_everything_is_one_call(tmp_path):
    learner = Learner(tmp_path / "lessons.jsonl")
    learner.observe_standard(STANDARD, standard="NEK 400", source="f1")
    learner.save()
    assert learner.forget_all() > 0
    assert not (tmp_path / "lessons.jsonl").exists()


def test_lessons_persist_and_reload(tmp_path):
    path = tmp_path / "lessons.jsonl"
    a = Learner(path)
    for i in range(3):
        a.observe_layout(layout_session(), document_id=f"doc{i}")
    a.save()
    b = Learner(path)
    assert len(b.lessons()) == len(a.lessons())
    assert b.proposals()


def test_the_report_says_where_everything_lives():
    learner = Learner()
    for i in range(3):
        learner.observe_layout(layout_session(), document_id=f"doc{i}")
    text = learner.report()
    assert "Ready to apply" in text
    assert "stays on this machine" in text


def test_symbol_use_ranks_the_picker():
    class Comp:
        def __init__(self, t):
            self.type = t

    class Graph:
        domain = "piping"
        components = [Comp("valve_ball"), Comp("valve_ball"), Comp("centrifugal_pump")]

    learner = Learner()
    for i in range(3):
        learner.observe_symbols(Graph(), document_id=f"doc{i}")
    assert "valve_ball" in learner.favourite_symbols("piping")
