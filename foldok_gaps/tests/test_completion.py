"""Acceptance tests for the completion engine.  The guard tests are the contract.

Run:  python -m pytest foldok_gaps/tests -q
"""

from __future__ import annotations

import pytest

from foldok_gaps import (
    BUILD,
    COMPLIANCE,
    REVIEW,
    CompletionSession,
    Document,
    EvidentialGuard,
    ResolverRefused,
    default_registry,
    evaluate,
    gap_id,
)
from foldok_gaps import packs
from foldok_gaps.resolvers import TextDraftResolver


class StubDrafter:
    def draft(self, prompt, context):
        return f"Draft for {context['subject']}: {prompt[:40]}"


def electrical_job(circuits: int = 5, has_rcd: bool = True) -> Document:
    doc = Document(
        id="job_2026_114",
        title="Ny kurs — Storgata 14",
        segment="electrical",
        jurisdiction="NO_IT_230",
        facts={
            "has_rcd": has_rcd,
            "bom": [
                {"id": "Q1", "type": "breaker_2p", "tag": "-Q1", "ref": "BOM.xlsx#row=7"},
                {"id": "UE", "type": "heating_element", "tag": "-UE", "ref": "BOM.xlsx#row=14"},
                {"id": "X9", "type": "terminal", "tag": "-X9"},        # no ref: unsourced
            ],
        },
    )
    doc.add_subject("board", "DB1", "Main board")
    for i in range(1, circuits + 1):
        doc.add_subject("circuit", f"K{i}", f"Course {i}")
    return doc


def session(mode="build", circuits=5, drafter=None):
    doc = electrical_job(circuits)
    reg = default_registry(drafter or StubDrafter())
    return CompletionSession(doc, packs.NO_ELECTRICAL, reg, mode=mode)


# --- gap identity ------------------------------------------------------
def test_gap_id_is_content_addressed_not_positional():
    a = gap_id("p", "req.a", "circuit:K1")
    b = gap_id("p", "req.a", "circuit:K1")
    assert a == b
    assert a != gap_id("p", "req.a", "circuit:K2")


def test_resolving_one_gap_does_not_change_any_other_id():
    s = session()
    before = {g.id for g in s.gaps()}
    target = s.gaps().of_kind("measurement")[0]
    s.resolve(target.id, "measurement_form")
    assert {g.id for g in s.gaps()} == before


def test_gap_survives_across_reload():
    s = session()
    gid = s.gaps().open()[0].id
    reloaded = Document.from_dict(s.document.to_dict())
    again = CompletionSession(reloaded, packs.NO_ELECTRICAL, default_registry())
    assert again.gaps().get(gid) is not None


# --- the thirty mangler ------------------------------------------------
def test_requirements_multiply_over_subjects():
    s = session(circuits=5)
    gaps = s.gaps()
    assert len(gaps) == 35            # 8 per document + 2 per board + 5 x 5 per circuit
    assert len(gaps.of_subject("circuit:K3")) == 5


def test_batches_collapse_thirty_items_into_a_few_actions():
    s = session()
    batches = s.batches()
    biggest = batches[0]
    assert biggest.size == 5
    assert len({b.requirement.key for b in batches}) < len(s.gaps().open())


def test_batch_resolve_creates_one_form_per_subject():
    s = session()
    out = s.resolve_batch("el.insulation")
    assert len(out) == 5
    assert all(r.state == "in_progress" for r in out)
    assert all(a.empty for a in s.document.artifacts())


def test_prepare_everything_creates_forms_but_writes_nothing():
    s = session()
    done = s.prepare_everything()
    assert done
    for art in s.document.artifacts():
        assert art.provenance.source != "ai"      # nothing was authored
        assert art.empty                           # every one is waiting for a person
    assert s.summary()["in_progress"] == len(done)


def test_applies_when_removes_gaps_that_never_applied():
    with_rcd = len(session().gaps())
    doc = electrical_job(has_rcd=False)
    without = len(evaluate(doc, packs.NO_ELECTRICAL))
    assert without == with_rcd - 5


def test_missing_subject_kind_is_a_notice_not_silence():
    doc = Document(id="d", segment="electrical")      # no boards, no circuits
    gaps = evaluate(doc, packs.NO_ELECTRICAL)
    codes = {n.code for n in gaps.notices}
    assert "no_subjects_declared" in codes
    assert len(gaps) == 8                             # only the per-document ones


# --- the evidential guard ---------------------------------------------
def test_evidential_guard_blocks_a_generative_resolver_at_the_registry():
    reg = default_registry(StubDrafter())
    req = packs.NO_ELECTRICAL.requirement("el.insulation")
    with pytest.raises(EvidentialGuard):
        reg.check(TextDraftResolver(StubDrafter()), req)


def test_evidential_guard_blocks_it_at_the_session_too():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.board_schematic"][0]
    with pytest.raises(EvidentialGuard):
        s.resolve(gap.id, "diagram_draft")


def test_generative_resolvers_are_never_even_offered_for_evidence():
    s = session()
    for gap in s.gaps().evidential():
        for offer in s.options(gap.id):
            assert not offer.generates_content, (gap.requirement.key, offer.resolver_id)


def test_measurement_forms_come_out_empty():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.continuity"][0]
    res = s.resolve(gap.id, "measurement_form")
    art = res.artifact
    assert art.data == {}
    assert "resistance_ohm" in art.pending_fields
    assert s.gaps().get(gap.id).state == "in_progress"


def test_a_measurement_resolves_only_once_a_person_fills_it_in():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.continuity"][0]
    art = s.resolve(gap.id, "measurement_form").artifact
    s.fill(
        art.id,
        {"resistance_ohm": 0.21, "instrument": "Fluke 1664 #A2213", "date": "2026-07-27",
         "measured_by": "J. R. Erikstad"},
        by="J. R. Erikstad",
    )
    assert s.gaps().get(gap.id).state == "resolved"


def test_photo_gap_becomes_a_capture_task_with_an_instruction():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.board_photo"][0]
    res = s.resolve(gap.id)
    assert res.artifact.kind == "photo"
    assert "cover off" in res.artifact.instruction


def test_diagram_scaffold_places_only_sourced_parts():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.board_schematic"][0]
    res = s.resolve(gap.id, "diagram_scaffold")
    graph = res.artifact.data["graph"]
    ids = {c["id"] for c in graph["components"]}
    assert ids == {"Q1", "UE"}                      # X9 had no ref, so it is not placed
    assert graph["connections"] == []               # nothing assumed
    assert s.gaps().get(gap.id).state == "in_progress"


# --- drafting is allowed, but never counts on its own ------------------
def test_expository_text_may_be_drafted():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.scope"][0]
    res = s.resolve(gap.id, "text_draft")
    assert res.artifact.body
    assert res.artifact.provenance.source == "ai"


def test_a_draft_does_not_resolve_a_gap_until_a_person_confirms():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.scope"][0]
    art = s.resolve(gap.id, "text_draft").artifact
    assert s.gaps().get(gap.id).state == "in_progress"
    s.confirm(art.id, by="J. R. Erikstad")
    assert s.gaps().get(gap.id).state == "resolved"


def test_batch_drafting_is_refused_without_an_explicit_flag():
    s = session()
    doc = s.document
    for i in range(1, 4):
        doc.add_subject("machine", f"M{i}")
    with pytest.raises(ResolverRefused):
        s.resolve_batch("el.scope", "text_draft")
    assert s.resolve_batch("el.scope", "text_draft", include_generative=True)


# --- not applicable ----------------------------------------------------
def test_not_applicable_needs_a_reason_and_a_name():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.user_instructions"][0]
    with pytest.raises(ResolverRefused):
        s.mark_not_applicable(gap.id, "", "J.R.")
    with pytest.raises(ResolverRefused):
        s.mark_not_applicable(gap.id, "no user-serviceable parts", "")
    s.mark_not_applicable(gap.id, "no user-serviceable parts", "J. R. Erikstad")
    assert s.gaps().get(gap.id).state == "not_applicable"


def test_some_requirements_cannot_be_waived():
    s = session()
    gap = [g for g in s.gaps() if g.requirement.key == "el.declaration"][0]
    with pytest.raises(ResolverRefused):
        s.mark_not_applicable(gap.id, "small job", "J.R.")


# --- modes: the prototype user ----------------------------------------
def test_build_mode_blocks_nothing_and_watermarks_instead():
    s = session(mode="build")
    g = s.gate()
    assert g.ok
    assert g.watermark and "not a compliance package" in g.watermark
    assert "not checked this against any standard" in g.statement


def test_compliance_mode_on_the_same_document_blocks():
    s = session(mode="build")
    assert s.gate().ok
    s.set_mode("compliance")
    assert not s.gate().ok


def test_switching_mode_is_retroactive_over_work_already_done():
    s = session(mode="build")
    before = {g.id: g.state for g in s.gaps()}
    s.set_mode("compliance")
    after = {g.id: g.state for g in s.gaps()}
    assert before == after            # evaluation is pure; only gating changed
    assert not s.gate().ok


def test_prototype_pack_never_blocks_anyone():
    doc = Document(id="rig", title="Fog rig v2", segment="prototype")
    s = CompletionSession(doc, packs.PROTOTYPE_BUILD_LOG, default_registry(StubDrafter()), mode="review")
    assert s.gate().ok                # nothing in the pack is required or blocking
    assert all(g.requirement.severity in ("recommended", "optional") for g in s.gaps())


def test_build_mode_speaks_in_offers_not_failures():
    s = session(mode="build")
    assert s.progress()["framing"] == "offer"
    assert "help with" in s.progress()["label"]
    s.set_mode("compliance")
    assert s.progress()["framing"] == "gap"


def test_deferring_is_allowed_while_building_and_not_at_the_end():
    s = session(mode="build")
    gap = s.gaps().open()[0]
    s.defer(gap.id, "waiting for the customer")
    assert s.gaps().get(gap.id).state == "deferred"
    s.set_mode("compliance")
    with pytest.raises(ResolverRefused):
        s.defer(s.gaps().open()[0].id)


def test_artifacts_survive_a_pack_change():
    s = session(mode="build")
    gap = [g for g in s.gaps() if g.requirement.key == "el.scope"][0]
    s.resolve(gap.id, "text_draft")
    other = CompletionSession(s.document, packs.EU_MACHINERY, default_registry())
    assert len(other.document.artifacts()) == 1     # nothing is thrown away


# --- export gate -------------------------------------------------------
def test_unconfirmed_drafts_block_a_compliance_export():
    s = session(mode="compliance")
    gap = [g for g in s.gaps() if g.requirement.key == "el.scope"][0]
    s.resolve(gap.id, "text_draft")
    codes = {i.code for i in s.gate().errors}
    assert "unconfirmed_draft" in codes


def test_gate_never_claims_compliance():
    s = session(mode="compliance")
    text = (s.gate().statement + s.report()).lower()
    assert "is compliant" not in text
    assert "not a statement of compliance" in s.gate().statement.lower() or not s.gate().ok


def test_a_finished_document_passes():
    doc = electrical_job(circuits=1)
    s = CompletionSession(doc, packs.NO_ELECTRICAL, default_registry(StubDrafter()), mode="compliance")
    for gap in list(s.gaps().gaps):
        req = gap.requirement
        if req.kind == "text":
            art = s.resolve(gap.id, "text_draft").artifact
            s.confirm(art.id, by="J.R.")
        elif req.kind == "measurement":
            art = s.resolve(gap.id, "measurement_form").artifact
            s.fill(art.id, {f.key: 1 for f in req.fields}, by="J.R.")
        elif req.kind == "signature":
            s.resolve(gap.id, "signature", by="J. R. Erikstad")
        else:
            s.attach(gap.id, f"files/{req.key}.pdf", by="J.R.")
    assert s.gaps().complete, s.report()
    gate = s.gate()
    assert gate.ok, str(gate)
    assert "complete" in gate.statement.lower()


# --- packs -------------------------------------------------------------
def test_every_shipped_pack_is_structurally_sound():
    for pack in packs.PACKS.values():
        assert pack.validate() == [], f"{pack.id}: {pack.validate()}"


def test_packs_round_trip_through_plain_data():
    for pack in packs.PACKS.values():
        again = type(pack).from_dict(pack.to_dict())
        assert again.to_dict() == pack.to_dict()


def test_a_pack_can_define_its_own_sections():
    assert [s.id for s in packs.PROTOTYPE_BUILD_LOG.sections] != [
        s.id for s in packs.NO_ELECTRICAL.sections
    ]
    doc = Document(id="p", segment="prototype")
    assert len(evaluate(doc, packs.PROTOTYPE_BUILD_LOG)) == 7


def test_four_segments_run_on_the_same_engine():
    for pack in packs.PACKS.values():
        doc = Document(id=f"doc_{pack.id}", segment=pack.segment)
        for kind in pack.subject_kinds():
            doc.add_subject(kind, "A1")
        gaps = evaluate(doc, pack)
        assert len(gaps) > 0
        s = CompletionSession(doc, pack, default_registry(StubDrafter()), mode="build")
        assert s.gate().ok
        assert s.report()


def test_pack_validation_catches_a_badly_written_requirement():
    from foldok_gaps.requirements import Requirement, RequirementPack

    bad = RequirementPack(
        id="bad",
        title="bad",
        segment="test",
        requirements=(
            Requirement(key="a", section="verification", title="readings",
                        kind="text", evidence="evidential"),
            Requirement(key="b", section="handover", title="sign",
                        kind="signature", severity="blocking"),
        ),
    )
    problems = " ".join(bad.validate())
    assert "free text" in problems
    assert "waived" in problems
