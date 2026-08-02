"""Tests for curation and selection.

Run:  python -m pytest foldok_select/tests -q
"""

from __future__ import annotations

import pytest

from foldok_select import (
    build_context,
    caption_note,
    menu_for,
    parse_reply,
    select_for_section,
)

INDEX = [
    {"file": "Bilder/hovedtavle.jpg", "kind": "photo",
     "caption": "Hovedtavle DB1 med deksel av, merking synlig", "content_tags": ["board"]},
    {"file": "Bilder/kabelbro_gang.jpg", "kind": "photo",
     "caption": "Kabelbro i gangen, festet til betong", "content_tags": ["cable tray"]},
    {"file": "Docs/Kabelplan rev C.pdf", "caption": "Kabelplan revisjon C, for construction",
     "doc_role_hints": ["drawing"]},
    {"file": "Docs/koblingsskjema.pdf", "caption": "Koblingsskjema hovedtavle",
     "content_tags": ["wiring"]},
    {"file": "Docs/kabelliste.xlsx", "caption": "Kabelliste med lengder",
     "doc_role_hints": ["test_report"]},
    {"file": "Ref/EN 50174-2.pdf", "caption": "EN 50174-2 cabling installation planning",
     "doc_role_hints": ["standard"]},
    {"file": "Ref/Legrand brochure.pdf",
     "caption": "Legrand company profile — our solutions. Follow us. Request a quote."},
    {"file": "Ref/SICK product shot.jpg", "kind": "photo",
     "caption": "SICK microScan3 product photo. Subject to change without notice."},
]


def context():
    return build_context(INDEX, project_terms=["Storgata"])


# --- curation ------------------------------------------------------------
def test_sources_are_sorted_into_the_kinds_a_document_is_built_from():
    c = context()
    assert len(c.images) == 2 and c.drawings and c.diagrams and c.tables and c.standards


def test_sales_material_never_reaches_the_document():
    c = context()
    assert any("brochure" in e.file.lower() for e in c.excluded)
    assert not any("brochure" in a.file.lower() for a in c.all())


def test_a_suppliers_product_photo_is_not_evidence_of_this_installation():
    """Putting a catalogue shot in a handover document is a small lie."""
    c = context()
    excluded = [e for e in c.excluded if "SICK" in e.file]
    assert excluded and "not evidence" in excluded[0].reason


def test_reference_images_can_be_admitted_deliberately():
    c = build_context(INDEX, project_terms=["Storgata"], include_reference_images=True)
    assert any("SICK" in a.file for a in c.images)


def test_exclusions_are_recorded_not_dropped():
    """A curation decision nobody can inspect is indistinguishable from a bug —
    and this product already shipped one of those."""
    for excluded in context().excluded:
        assert excluded.reason


def test_a_photographed_drawing_is_a_drawing():
    c = build_context([{"file": "Bilder/plan_foto.jpg", "kind": "photo",
                        "caption": "Foto av installasjonstegning, layout"}])
    assert c.drawings and not c.images


def test_curation_needs_no_narrative():
    """It runs before one exists — that is the whole point of splitting it."""
    import inspect

    assert "narrative" not in inspect.signature(build_context).parameters


def test_every_asset_gets_a_stable_id():
    ids = [a.id for a in context().all()]
    assert len(ids) == len(set(ids))
    assert all(i[:3] in ("IMG", "DWG", "DIA", "TBL", "STD", "DOC") for i in ids)


# --- the menu ------------------------------------------------------------
def test_the_model_is_handed_a_menu_not_asked_to_search():
    prompt = menu_for(context(), section="Montering av kabelbro", kind="image").prompt()
    assert "Tilgjengelige bilder" in prompt
    assert "IMG1" in prompt and "IMG2" in prompt
    assert "finnes det" not in prompt.lower()


def test_the_best_match_is_listed_first_with_its_reason():
    menu = menu_for(context(), section="Montering av kabelbro", kind="image")
    assert menu.items[0].asset.name == "kabelbro_gang.jpg"
    assert "kabelbro" in menu.items[0].hint


def test_an_asset_with_no_overlap_is_still_offered():
    """The engine has no business ruling it out before the model sees the
    section."""
    menu = menu_for(context(), section="Montering av kabelbro", kind="image")
    assert len(menu.items) == 2


def test_an_empty_menu_forbids_rather_than_invites():
    menu = menu_for(context(), section="Erklæringer", kind="diagram")
    context_with_no_diagrams = build_context([INDEX[0]])
    empty = menu_for(context_with_no_diagrams, section="Erklæringer", kind="diagram")
    assert empty.empty
    assert "Ikke vis til noen" in empty.prompt()


def test_the_prompt_forbids_citing_anything_off_the_menu():
    prompt = menu_for(context(), section="x", kind="image").prompt()
    assert "Ikke vis til noe som ikke står i listen" in prompt


# --- reading the reply ---------------------------------------------------
def test_a_chosen_id_becomes_an_asset():
    c = context()
    menu = menu_for(c, section="Kabelbro", kind="image")
    selection = parse_reply("IMG2 er best her.", menu, c)
    assert [a.name for a in selection.chosen] == ["kabelbro_gang.jpg"]


def test_none_is_understood_in_both_languages():
    c = context()
    menu = menu_for(c, section="x", kind="image")
    for reply in ("NONE", "Ingen av dem passer", "INGENTING"):
        assert parse_reply(reply, menu, c).chosen == []


def test_an_invented_id_is_recorded_not_silently_dropped():
    """A model citing IMG7 when two were offered is a signal, not a typo."""
    c = context()
    menu = menu_for(c, section="x", kind="image")
    selection = parse_reply("IMG1 and IMG7", menu, c)
    assert selection.invented == ["IMG7"]
    assert len(selection.chosen) == 1


def test_having_nothing_is_distinguishable_from_choosing_nothing():
    c = context()
    menu = menu_for(c, section="x", kind="image")
    declined = parse_reply("NONE", menu, c)
    nothing = select_for_section(build_context([INDEX[2]]), section="x", kind="image",
                                 ask=lambda p: "NONE")
    assert declined.declined and not declined.had_nothing
    assert nothing.had_nothing and not nothing.declined


def test_the_caption_note_reflects_which_case_it_was():
    """Three outcomes, three different sentences: had nothing, offered and
    declined, chose something. A section that had no images must not read like a
    section that looked and rejected them."""
    c = context()
    menu = menu_for(c, section="x", kind="image")

    no_images = build_context([INDEX[2]])          # a drawing only
    nothing = select_for_section(no_images, section="x", kind="image")
    assert "Ingen illustrasjoner er tilgjengelige" in caption_note(nothing)

    declined = parse_reply("INGEN", menu, c)
    assert "passet ikke" in caption_note(declined)

    chosen = parse_reply("IMG1", menu, c)
    assert chosen.chosen
    assert "Illustrasjoner:" in caption_note(chosen)


# --- the whole loop ------------------------------------------------------
def test_selection_runs_the_bounded_question_through_a_model():
    seen: list[str] = []

    def ask(prompt: str) -> str:
        seen.append(prompt)
        return "IMG2"

    selection = select_for_section(context(), section="Montering av kabelbro",
                                   kind="image", ask=ask)
    assert seen and "IMG2" in seen[0]
    assert [a.name for a in selection.chosen] == ["kabelbro_gang.jpg"]


def test_without_a_model_nothing_is_guessed():
    selection = select_for_section(context(), section="x", kind="image", ask=None)
    assert selection.chosen == [] and selection.offered
