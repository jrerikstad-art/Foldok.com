"""Tests for the inbound guard.

The first one is the incident: a travel insurance certificate in a technical
documentation package.

Run:  python -m pytest foldok_intake/tests -q
"""

from __future__ import annotations

import pytest

from foldok_intake import (
    audit_prose,
    classify,
    filter_index,
    gate,
    looks_broken,
    normalise,
    prepare,
    review,
)

INSURANCE = {
    "file": "Notater/trygg forsikring.pdf",
    "caption": "Reiseforsikringsbevis for Jan Rune Erikstad, polisenummer PRF46000, "
               "dekningsperiode 13.05.2024–12.05.2025",
    "doc_role_hints": [],
}
DATASHEET = {
    "file": "Datablad/PCA9685.pdf",
    "caption": "PCA9685 16-channel PWM controller datasheet",
    "doc_role_hints": ["datasheet"],
}


# --- the incident --------------------------------------------------------
def test_a_travel_insurance_certificate_never_reaches_the_documentation():
    result = classify(INSURANCE["file"], caption=INSURANCE["caption"])
    assert result.doc_class == "personal"
    assert result.excluded


def test_the_user_is_told_what_was_held_back():
    """They put the file in the folder; they get to know it was left out."""
    kept, report = filter_index([INSURANCE, DATASHEET])
    assert [e["file"] for e in kept] == [DATASHEET["file"]]
    assert "trygg forsikring" in report.notice("no")
    assert "Du kan inkludere dem manuelt" in report.notice("no")


def test_a_datasheet_in_a_notes_folder_is_still_a_datasheet():
    """A weak path hint must not outrank strong project content."""
    result = classify("Notater/PCA9685 datablad.pdf",
                      caption="PCA9685 datasheet, PWM controller")
    assert result.doc_class == "project"
    assert not result.excluded


def test_payslips_bank_statements_and_sick_notes_are_all_caught():
    for name, caption, expected in [
        ("lonnsslipp_mai.pdf", "Lønnsslipp mai 2026", "financial"),
        ("statement.pdf", "Bank statement, account number 1234", "financial"),
        ("sykemelding.pdf", "Sykemelding fra fastlege", "medical"),
        ("pass.jpg", "Passnummer og fødselsnummer", "identity"),
    ]:
        result = classify(name, caption=caption)
        assert result.doc_class == expected, name
        assert result.excluded


def test_inclusion_is_a_per_file_decision_not_a_switch():
    kept, report = filter_index([INSURANCE], allow=[INSURANCE["file"]])
    assert len(kept) == 1
    assert report.classifications[0].override


# --- relevance is a gate, not a request ---------------------------------
def test_a_file_the_model_mapped_wrongly_is_dropped():
    sections = [{"section_key": "certificates", "title": "Erklæringer og sertifikater",
                 "roles": ["declaration", "certificate"]}]
    index = [dict(INSURANCE, doc_class="personal")]
    report = gate({"certificates": [INSURANCE["file"]]}, index, sections)
    assert report.dropped and not report.kept
    assert "personal" in report.dropped[0].reasons[0]


def test_a_correctly_mapped_file_passes():
    sections = [{"section_key": "components", "title": "Komponenter og datablad",
                 "roles": ["datasheet"]}]
    index = [dict(DATASHEET, doc_class="project")]
    report = gate({"components": [DATASHEET["file"]]}, index, sections)
    assert report.kept["components"] == [DATASHEET["file"]]


def test_a_mapping_to_a_file_that_is_not_indexed_is_dropped():
    report = gate({"x": ["ghost.pdf"]}, [], [{"section_key": "x", "title": "X"}])
    assert report.dropped[0].reasons == ("not in the index",)


# --- the prose audit -----------------------------------------------------
def test_a_section_apologising_for_its_contents_is_a_bug_report():
    """The model wrote that because it had the file and could not remove it."""
    issues = audit_prose({
        "certificates": "Dette dokumentet er uten direkte relevans for produktets "
                        "tekniske sertifisering, men er registrert som vedlegg."
    })
    assert issues and "uten direkte relevans" in issues[0].phrase


def test_english_apologies_are_caught_too():
    assert audit_prose({"s": "This document has no direct relevance but is included "
                             "for completeness."})


def test_clean_prose_produces_nothing():
    assert audit_prose({"s": "Alle komponenter er dokumentert med datablad."}) == []


# --- markdown ------------------------------------------------------------
def test_a_heading_glued_to_a_sentence_is_repaired():
    broken = ("Denne seksjonen gir en oversikt. ## Identifiserte dokumenter "
              "- Reiseforsikringsbevis. > GAP: ingen CE-erklæringer.")
    assert looks_broken(broken)
    fixed = normalise(broken)
    assert "\n\n## Identifiserte dokumenter" in fixed
    assert "\n\n> GAP" in fixed
    assert not looks_broken(fixed)


def test_already_valid_markdown_is_left_alone():
    good = "# Title\n\nSome prose.\n\n## Section\n\nMore prose.\n"
    assert normalise(good).strip() == good.strip()


def test_consecutive_bullets_do_not_get_blank_lines_between_them():
    assert "\n\n- b" not in normalise("- a\n- b\n- c\n")


# --- the whole review ----------------------------------------------------
def test_review_flags_broken_markdown_and_returns_it_fixed():
    result = review({"certificates": "Oversikt. ## Identifiserte dokumenter - x"})
    assert any(f.code == "markdown_not_rendered" for f in result.findings)
    assert "\n\n##" in result.sections["certificates"]


def test_an_apology_is_a_failure_not_a_warning():
    result = review({"s": "Dokumentet er uten direkte relevans for sertifiseringen."})
    assert not result.ok
    assert any(f.code == "section_apologises_for_its_contents" for f in result.findings)


def test_the_vault_is_asked_whether_an_identifier_reached_the_document():
    """foldok_private masks names on the way out; the same vault can be asked
    about the way in. The boundary existed, pointed one way."""
    from foldok_private import EntityVault

    vault = EntityVault(project_id="job")
    vault.add("Jan Rune Erikstad", "person")
    result = review({"certificates": "Reiseforsikringsbevis for Jan Rune Erikstad."},
                    vault=vault)
    leaks = [f for f in result.findings if f.code == "identifier_in_deliverable"]
    assert leaks and not result.ok
    assert "may be sent to a client" in leaks[0].fix


def test_a_clean_document_passes_review():
    from foldok_private import EntityVault

    result = review({"s": "# Komponenter\n\nAlle komponenter er dokumentert.\n"},
                    vault=EntityVault(project_id="job"))
    assert result.ok


def test_prepare_tags_the_index_so_the_gate_can_see_the_class():
    kept, _ = prepare([DATASHEET])
    assert kept[0]["doc_class"] == "project"
