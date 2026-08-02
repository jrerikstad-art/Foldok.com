"""Tests for citation scope and pipeline health.

The first group is the blocker that kept every document thin.

Run:  python -m pytest foldok_budget/tests -q
"""

from __future__ import annotations

import pytest

from foldok_budget import CiteScope, check_pipeline, rank_key, section_budget


# --- the blocker ---------------------------------------------------------
def test_a_rich_source_can_be_cited_across_many_sections():
    """The old rule spent a 30-page standard on one sentence, document-wide."""
    scope = CiteScope()
    total = 0
    for section in ("scope", "shielding", "earthing", "separation"):
        scope.enter_section(section)
        while scope.may_cite("EMC_BoD.pdf"):
            scope.mark("EMC_BoD.pdf")
            total += 1
    assert total > 8


def test_one_source_cannot_dominate_a_single_section():
    """The intent behind the old rule was right; only its scope was wrong."""
    scope = CiteScope(per_section=3)
    scope.enter_section("shielding")
    used = 0
    while scope.may_cite("EMC_BoD.pdf"):
        scope.mark("EMC_BoD.pdf")
        used += 1
    assert used == 3
    assert "already cited 3x in this section" in scope.refusal_reason("EMC_BoD.pdf")


def test_one_source_cannot_dominate_the_whole_document_either():
    scope = CiteScope(per_section=3, document_share=0.4)
    for i in range(10):
        scope.enter_section(f"s{i}")
        while scope.may_cite("dominant.pdf"):
            scope.mark("dominant.pdf")
    assert "accounts for" in scope.refusal_reason("dominant.pdf")


def test_entering_a_section_resets_the_budget():
    scope = CiteScope(per_section=2)
    scope.enter_section("a")
    scope.mark("f.pdf")
    scope.mark("f.pdf")
    assert not scope.may_cite("f.pdf")
    scope.enter_section("b")
    assert scope.may_cite("f.pdf")


def test_unused_now_means_unused_here_not_unused_ever():
    scope = CiteScope()
    scope.enter_section("a")
    scope.mark("f.pdf")
    assert not scope.unused("f.pdf")
    scope.enter_section("b")
    assert scope.unused("f.pdf")


def test_identical_claim_text_is_still_refused_document_wide():
    """Repeating a sentence is a different problem from reusing a source."""
    scope = CiteScope()
    scope.enter_section("a")
    assert scope.claim_fresh("Skjerming skal termineres 360 grader")
    scope.enter_section("b")
    assert not scope.claim_fresh("Skjerming skal termineres 360 grader")


def test_the_citation_numbering_contract_is_unchanged():
    """author_doc depends on these; the drop-in must not break them."""
    scope = CiteScope()
    assert scope.number_for("a.pdf") == 1
    assert scope.number_for("b.pdf") == 2
    assert scope.number_for("a.pdf") == 1
    assert scope.mark("a.pdf") == "[1]"
    assert scope.mark("") == ""


# --- budgets scale -------------------------------------------------------
def test_the_claim_budget_scales_with_what_survived_retrieval():
    """n=2 was a constant whether four candidates were found or four hundred."""
    assert section_budget(4) == 3
    assert section_budget(40) > section_budget(4)
    assert section_budget(4000) <= 12


def test_no_material_means_no_budget():
    assert section_budget(0) == 0


# --- ranking -------------------------------------------------------------
def test_project_material_outranks_a_vendor_manual_before_any_keyword():
    """A four-word aside from page 23 of a supplier PDF became step 1 of an
    installation sequence, because keyword overlap was the only ordering."""
    scope = CiteScope()
    vendor = rank_key("sick.pdf", scope=scope, role="reference", signal_match=True)
    project = rank_key("plan.pdf", scope=scope, role="project", signal_match=False)
    assert project < vendor


def test_a_fresh_source_is_preferred_but_not_required():
    scope = CiteScope()
    scope.enter_section("a")
    scope.mark("used.pdf")
    assert rank_key("fresh.pdf", scope=scope, role="project") < \
           rank_key("used.pdf", scope=scope, role="project")
    assert scope.may_cite("used.pdf")


# --- pipeline health -----------------------------------------------------
def test_the_thin_document_is_diagnosed_at_the_right_stage():
    report = check_pipeline(files_indexed=51, files_usable=44, claims_extracted=380,
                            sections_planned=7, sections_with_content=7, claims_cited=14,
                            gap_ledger_entries=12, gaps_found=3)
    failure = report.first_failure()
    assert failure and failure.stage == "cite"
    assert "366 of 380" in failure.detail
    assert "per section" in failure.fix


def test_a_document_that_was_never_checked_is_not_exportable():
    """'No gaps' meant 'nothing was examined', and it said ready to export."""
    report = check_pipeline(files_indexed=51, files_usable=44, claims_extracted=380,
                            sections_planned=7, sections_with_content=7, claims_cited=200,
                            gap_ledger_entries=0)
    ok, why = report.exportable()
    assert not ok
    assert "nothing was examined" in why or "produced nothing" in why


def test_an_unrun_gap_engine_is_unchecked_not_clean():
    report = check_pipeline(files_indexed=10, files_usable=10, claims_extracted=50,
                            sections_planned=5, sections_with_content=5, claims_cited=30)
    completeness = [s for s in report.stages if s.stage == "completeness"][0]
    assert completeness.health == "unchecked"
    assert not report.exportable()[0]


def test_a_healthy_pipeline_is_exportable():
    report = check_pipeline(files_indexed=20, files_usable=18, claims_extracted=200,
                            sections_planned=8, sections_with_content=8, claims_cited=90,
                            gap_ledger_entries=24, gaps_found=5)
    ok, why = report.exportable()
    assert ok and report.health == "ok"


def test_downstream_stages_are_not_reported_when_an_upstream_one_collapsed():
    """'0 claims' is one problem, not six."""
    report = check_pipeline(files_indexed=51, files_usable=0)
    assert len(report.stages) == 1
    assert report.stages[0].health == "broken"


def test_an_unreadable_folder_points_at_the_scanner():
    report = check_pipeline(files_indexed=51, files_usable=6, claims_extracted=0)
    failure = report.first_failure()
    assert "foldok_scan" in failure.fix


def test_the_report_names_where_to_look():
    text = check_pipeline(files_indexed=51, files_usable=44, claims_extracted=380,
                          sections_planned=7, sections_with_content=7, claims_cited=14,
                          gap_ledger_entries=0).report()
    assert "PIPELINE [BROKEN]" in text
    assert "EXPORT: blocked" in text


def test_the_report_serialises():
    data = check_pipeline(files_indexed=10, files_usable=9, claims_extracted=40,
                          sections_planned=5, sections_with_content=5, claims_cited=20,
                          gap_ledger_entries=10, gaps_found=2).to_dict()
    assert data["schema_version"] == 1 and data["exportable"] is True
