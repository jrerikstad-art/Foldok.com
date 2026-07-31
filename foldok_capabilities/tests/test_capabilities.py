"""Tests for capability reconciliation.

The first test is the bug that started this: a build shipping 45 diagram symbols
telling a user it had no drawing tools.

Run:  python -m pytest foldok_capabilities/tests -q
"""

from __future__ import annotations

import json

import pytest

from foldok_capabilities import (
    Capability,
    Limit,
    load_manifest,
    manifest_block,
    merge_into,
    prompt_lines,
    reconcile,
)


def diagrams(**kw) -> Capability:
    base = dict(
        id="diagrams",
        anchors=("diagram", "schematic", "koblingsskjema"),
        verb="produce",
        object="single-line and interconnection diagrams",
        summary="Produce single-line and interconnection diagrams as SVG",
        domains=("electrical", "piping"),
        limits=(
            Limit("board-level electronics are out of scope",
                  "no microcontroller, header-pin or GPIO symbols"),
            Limit("no 3D modelling", "the engine is 2D on a page grid"),
        ),
        evidence={"symbols": 45},
        engine="foldok_diagram",
    )
    base.update(kw)
    return Capability(**base)


# --- the original bug ----------------------------------------------------
def test_a_shipped_capability_missing_from_the_manifest_is_blocking():
    """The exact failure: the engine ships it, the manifest never says so, and
    the assistant is under a hard rule never to claim what is not listed."""
    rec = reconcile(manifest={"templates": [], "cannot": []}, capabilities=[diagrams()])
    undeclared = rec.of("undeclared")
    assert undeclared and undeclared[0].capability == "diagrams"
    assert undeclared[0].severity == "fail"
    assert "deny it to every user" in undeclared[0].fix


def test_an_input_checklist_does_not_count_as_declaring_a_capability():
    """A template asking the user for '□ koblingsskjema' is a request for a file,
    not a claim that Foldok draws one. Reading it as a claim is how a checker
    misses the very gap it exists to find."""
    manifest = {"templates": [{"inputs": ["□ koblingsskjema", "□ tegning (PDF)"]}],
                "cannot": []}
    assert reconcile(manifest=manifest, capabilities=[diagrams()]).of("undeclared")


def test_a_declared_capability_is_not_flagged():
    manifest = manifest_block([diagrams()])
    assert reconcile(manifest=manifest, capabilities=[diagrams()]).of("undeclared") == []


def test_a_domain_word_appearing_somewhere_is_not_a_declaration():
    """'electrical' in a template name says nothing about diagrams."""
    manifest = {"scale": "electrical installations up to 400 V", "cannot": []}
    assert reconcile(manifest=manifest, capabilities=[diagrams()]).of("undeclared")


# --- denials -------------------------------------------------------------
def test_a_denial_that_contradicts_a_shipped_capability_is_blocking():
    manifest = manifest_block([diagrams()])
    manifest["cannot"] = ["lage diagrammer"]
    rec = reconcile(manifest=manifest, capabilities=[diagrams()])
    assert rec.of("contradicted")
    assert rec.blocking


def test_a_denial_the_capability_already_qualifies_is_not_a_contradiction():
    """'lese native CAD (DWG/STEP)' is true and scoped — the diagram capability
    says so itself."""
    manifest = manifest_block([diagrams()])
    manifest["cannot"] = ["lese native CAD (DWG/STEP)"]
    assert reconcile(manifest=manifest, capabilities=[diagrams()]).of("contradicted") == []


def test_a_bare_broad_verb_is_flagged_as_generalisable():
    """'tegne eller modellere i 3D' was written to disclaim CAD. A model reading
    it under pressure drops the '3D' and concludes it cannot draw."""
    manifest = manifest_block([diagrams()])
    manifest["cannot"] = ["tegne eller modellere i 3D"]
    rec = reconcile(manifest=manifest, capabilities=[diagrams()])
    unqualified = rec.of("unqualified_denial")
    assert unqualified
    assert "generalised" in unqualified[0].fix


def test_a_denial_with_a_concrete_object_and_no_broad_verb_is_fine():
    manifest = manifest_block([diagrams()])
    manifest["cannot"] = ["signere for deg", "gi juridisk råd"]
    assert reconcile(manifest=manifest, capabilities=[diagrams()]).of("unqualified_denial") == []


def test_generating_the_manifest_moves_a_covered_denial_into_the_limits():
    """Norwegian denial, English limit — the matcher normalises verbs so the
    dangerous line does not survive by being in the other language."""
    manifest = {"cannot": ["tegne eller modellere i 3D", "signere for deg"]}
    after = merge_into(manifest, [diagrams()])
    assert "tegne eller modellere i 3D" in after["cannot_moved_to_limits"]
    assert "signere for deg" in after["cannot"]


def test_generation_closes_the_loop():
    manifest = merge_into({"cannot": ["tegne eller modellere i 3D"]}, [diagrams()])
    assert reconcile(manifest=manifest, capabilities=[diagrams()]).of("undeclared") == []


# --- overclaiming --------------------------------------------------------
def test_the_manifest_promising_something_no_engine_provides_is_flagged():
    manifest = {"capabilities": [{"id": "translation", "summary": "translate documents"}],
                "cannot": []}
    rec = reconcile(manifest=manifest, capabilities=[diagrams()])
    over = rec.of("overclaimed")
    assert over and over[0].capability == "translation"
    assert over[0].severity == "warn"


# --- limits travel with their capability ---------------------------------
def test_every_limit_is_attached_to_something():
    """A floating negative gets over-generalised; a qualified one cannot."""
    for capability in [diagrams()]:
        for limit in capability.limits:
            assert limit.text and capability.object


def test_the_generated_block_carries_limits_next_to_the_claim():
    block = manifest_block([diagrams()])
    entry = block["capabilities"][0]
    assert entry["summary"]
    assert any("board-level" in l["text"] for l in entry["limits"])


def test_prompt_lines_state_the_limit_under_the_claim():
    lines = prompt_lines([diagrams()])
    assert lines[0].startswith("- Produce")
    assert any(l.strip().startswith("not:") for l in lines)


def test_evidence_is_counted_not_asserted():
    rec = reconcile(manifest={"cannot": []}, capabilities=[diagrams()])
    assert "45 symbols" in rec.of("undeclared")[0].detail


# --- discovery against the real tree -------------------------------------
def test_discovery_finds_the_engines_that_are_installed():
    from foldok_capabilities import discover

    found = {c.id for c in discover(".")}
    assert "diagrams" in found or "gaps" in found


def test_a_generated_manifest_is_marked_as_generated():
    block = manifest_block([diagrams()])
    assert block["capabilities_generated"] is True
    assert "hand-edit" in block["capabilities_note"]


def test_the_report_is_readable_when_clean():
    manifest = manifest_block([diagrams()])
    assert "no drift" in reconcile(manifest=manifest, capabilities=[diagrams()]).report()


def test_reconciliation_serialises():
    rec = reconcile(manifest={"cannot": []}, capabilities=[diagrams()])
    data = json.loads(rec.to_json())
    assert data["schema_version"] == 1 and data["capabilities"]
