"""Tests for role classification, subject decision and photo binding.

Synthetic fixture names only — never real client/vendor catalogues in engine
logic. Fixtures may invent "AcmeVendor" / "SiteAlpha"; production code may not.

Run:  python -m pytest foldok_role/tests -q
"""

from __future__ import annotations

import pytest

from foldok_role import (
    ROLE_WEIGHT,
    classify,
    classify_index,
    decide_subject,
    offers_for,
    photos_in,
    rank,
    sketch_patch,
    weighted_themes,
)

# Invented OEM — publication number + reference language, not a real brand list.
OEM = {
    "file": "Ref/AcmeVendor EMC background.pdf",
    "caption": ("AcmeVendor GmbH technical information: background knowledge on EMC, "
                "safety laser scanners. 8027032/2022-07-19. "
                "Subject to change without notice."),
    "content_tags": ["sensor", "esd", "pelv", "shielding", "functional earth", "emc"],
    "doc_role_hints": ["manual"],
}
DRAWING = {
    "file": "Docs/Kabelplan rev C.pdf",
    "caption": "Kabelplan revisjon C, for construction, SiteAlpha",
    "content_tags": ["cable tray", "cable routing"],
    "doc_role_hints": ["drawing"],
}
PROTOCOL = {
    "file": "Docs/Måleprotokoll.xlsx",
    "caption": "Måleprotokoll isolasjonsmotstand, befaring 2026-05",
    "content_tags": ["measurement", "verification"],
    "doc_role_hints": ["test_report"],
}
STANDARD = {
    "file": "Ref/EN 50174-2.pdf",
    "caption": "EN 50174-2 cabling installation planning",
    "content_tags": ["standard", "separation"],
    "doc_role_hints": ["standard"],
}


# --- role classification -------------------------------------------------
def test_a_vendor_brochure_is_reference():
    result = classify(OEM, project_terms=["SiteAlpha"])
    assert result.role == "reference"
    assert result.confidence > 0.8


def test_a_publication_number_is_a_strong_signal():
    """Projects do not have document numbers like 8027032/2022-07-19."""
    entry = {"file": "x.pdf", "caption": "Some guide 8027032/2022-07-19"}
    assert any("publication number" in r for r in classify(entry).reasons)


def test_project_drawings_and_protocols_are_project():
    for entry in (DRAWING, PROTOCOL):
        assert classify(entry, project_terms=["SiteAlpha"]).role == "project"


def test_a_standard_as_the_subject_is_reference():
    assert classify(STANDARD).role == "reference"


def test_naming_the_project_pulls_a_file_towards_project():
    named = classify(DRAWING, project_terms=["SiteAlpha"])
    unnamed = classify(dict(DRAWING, caption="Kabelplan revisjon C"), project_terms=["SiteAlpha"])
    assert named.confidence >= unnamed.confidence


def test_not_knowing_the_project_name_is_no_signal_at_all():
    """Absence is only evidence when you knew what to look for."""
    result = classify(DRAWING)
    assert not any("does not mention" in r for r in result.reasons)


def test_an_ambiguous_file_is_unknown_rather_than_guessed():
    entry = {"file": "notes.pdf", "caption": "Notes"}
    assert classify(entry).role == "unknown"


def test_reference_material_weighs_least():
    assert ROLE_WEIGHT["project"] > ROLE_WEIGHT["unknown"] > ROLE_WEIGHT["reference"]


# --- the vendor-swamping bug ---------------------------------------------
def test_accumulating_reference_material_no_longer_decides_the_subject():
    """Four OEM documents were making the document about shielding and ESD."""
    project = [DRAWING, PROTOCOL,
               {"file": "Docs/BoD.pptx", "caption": "EMC basis of design SiteAlpha",
                "content_tags": ["emc", "cable routing", "separation"],
                "doc_role_hints": ["drawing"]}]
    reference = [
        OEM,
        {"file": "Ref/oem_scanner_manual.pdf",
         "caption": "AcmeVendor microScan operating instructions, manufactured by AcmeVendor GmbH",
         "content_tags": ["sensor", "shielding", "functional earth"], "doc_role_hints": ["manual"]},
        {"file": "Ref/clamp_catalogue.pdf",
         "caption": "VendorCo product catalogue — clamp range",
         "content_tags": ["shielding", "esd"], "doc_role_hints": ["datasheet"]},
        {"file": "Ref/emc_app_note.pdf",
         "caption": "Supplier application note EMC, all rights reserved",
         "content_tags": ["shielding", "esd", "functional earth"], "doc_role_hints": ["datasheet"]},
    ]
    themes, _ = weighted_themes(project + reference, project_terms=["SiteAlpha"])
    assert "cable routing" in themes[:3]
    assert "shielding" not in themes[:3]
    assert "sensor" not in themes


def test_reference_material_still_contributes():
    """It informs the sections — it is where the shielding knowledge lives."""
    _, weights = weighted_themes([DRAWING, OEM], project_terms=["SiteAlpha"])
    assert weights.get("shielding", 0) > 0


def test_a_reference_only_folder_still_produces_themes():
    themes, _ = weighted_themes([OEM, STANDARD])
    assert themes


# --- the subject bug ------------------------------------------------------
def test_the_artifact_names_the_document():
    subject = decide_subject(
        [DRAWING, OEM],
        artifact={"name": "Installasjonsdokumentasjon SiteAlpha"},
    )
    assert subject.title == "Installasjonsdokumentasjon SiteAlpha" and subject.source == "artifact"


def test_the_project_names_it_when_the_artifact_does_not():
    assert decide_subject([DRAWING], project_name="SiteAlpha Plant").source == "project"


def test_file_sort_order_never_names_a_document():
    """title = Path(usable[0]...).stem — whatever sorted first."""
    subject = decide_subject([OEM, DRAWING])
    assert subject.source == "asked"
    assert not subject.confident
    assert "Ask, rather than letting file order decide" in subject.note


def test_captions_for_the_sketch_come_from_project_files():
    patch = sketch_patch([DRAWING, PROTOCOL, OEM], project_name="SiteAlpha Plant")
    joined = " ".join(patch["sample_captions"])
    assert "Kabelplan" in joined and "AcmeVendor" not in joined


def test_the_sketch_reports_the_balance_of_material():
    patch = sketch_patch([DRAWING, OEM, STANDARD], project_name="SiteAlpha")
    assert patch["project_files"] == 1 and patch["reference_files"] == 2
    assert "informerer seksjonene" in patch["role_note"]


# --- the photo bug --------------------------------------------------------
PHOTOS = [
    {"file": "Bilder/hovedtavle_ferdig.jpg", "kind": "photo",
     "caption": "Hovedtavle DB1 med deksel av, merking synlig",
     "content_tags": ["board", "labels"]},
    {"file": "Bilder/kabelbro.jpg", "kind": "photo", "caption": "Kabelbro i gangen"},
    {"file": "Docs/plan.pdf", "kind": "doc", "caption": "Kabelplan"},
]


def gaps():
    from foldok_gaps import CompletionSession, Document, default_registry, packs

    doc = Document(id="j", title="Storgata 14", segment="electrical",
                   jurisdiction="NO_IT_230")
    doc.add_subject("board", "DB1", "Hovedtavle")
    return CompletionSession(doc, packs.NO_ELECTRICAL, default_registry(), mode="build").gaps()


def test_photos_in_the_folder_are_found():
    found = {p["file"] for p in photos_in(PHOTOS)}
    assert found == {"Bilder/hovedtavle_ferdig.jpg", "Bilder/kabelbro.jpg"}


def test_a_photo_requirement_is_offered_the_photos_that_exist():
    """The engine reported this missing while the picture sat in the folder."""
    offers = offers_for(gaps(), PHOTOS)
    assert offers and offers[0].has_candidates


def test_the_best_candidate_is_the_one_that_matches_the_requirement():
    offer = offers_for(gaps(), PHOTOS)[0]
    assert offer.candidates[0].name == "hovedtavle_ferdig.jpg"
    assert "hovedtavle" in offer.candidates[0].reasons[0]


def test_nothing_is_bound_automatically():
    """Foldok must not decide that this photo proves that requirement."""
    offer = offers_for(gaps(), PHOTOS)[0]
    assert "bekreft" in offer.message()
    assert "Ingen er bundet automatisk" in __import__("foldok_role").summary([offer])


def test_every_photo_in_the_folder_is_offered_even_without_overlap():
    offer = offers_for(gaps(), PHOTOS)[0]
    names = {c.name for c in offer.candidates}
    assert "kabelbro.jpg" in names
    weak = [c for c in offer.candidates if c.name == "kabelbro.jpg"][0]
    assert "prosjektmappen" in weak.reasons[0]


def test_an_empty_folder_says_take_it_rather_than_pretending():
    offer = offers_for(gaps(), [{"file": "Docs/plan.pdf", "kind": "doc"}])[0]
    assert not offer.has_candidates
    assert "Ta bildet" in offer.message()


def test_photos_are_recognised_by_extension_when_kind_is_missing():
    assert photos_in([{"file": "a/b.HEIC"}])


def test_ranking_is_stable():
    a = rank(photos_in(PHOTOS), requirement_text="photograph of the board")
    b = rank(photos_in(PHOTOS), requirement_text="photograph of the board")
    assert [c.file for c in a] == [c.file for c in b]
