"""Tests for page addressing.

Run:  python -m pytest foldok_pages/tests -q
"""

from __future__ import annotations

import pytest

from foldok_pages import Block, PageIndex, order_pin, resolve


def index() -> PageIndex:
    return PageIndex([
        Block("h1", page=1, order=0, section="scope", section_title="1 Omfang", label="Omfang"),
        Block("t1", page=1, order=1, section="scope", section_title="1 Omfang"),
        Block("h2", page=5, order=2, section="verify", section_title="4 Verifikasjon"),
        Block("tbl_iso", page=6, order=3, section="verify", section_title="4 Verifikasjon",
              label="isolasjonstabellen", role="table"),
        Block("h3", page=8, order=4, section="handover", section_title="6 Overlevering"),
    ])


# --- pages exist and are shown -------------------------------------------
def test_the_outline_shows_page_numbers_that_already_existed():
    text = index().outline("no")
    assert "Side 1: 1 Omfang" in text
    assert "Side 6: 4 Verifikasjon" in text


def test_page_count_comes_from_the_geometry():
    assert index().page_count == 8


# --- a page resolves to a stable anchor ----------------------------------
def test_page_six_resolves_to_the_section_it_falls_in():
    anchor = resolve("legg inn koblingsskjema på side 6", index())
    assert anchor.kind == "page"
    assert anchor.section_title == "4 Verifikasjon"
    assert anchor.after_block == "tbl_iso"
    assert anchor.page_seen == 6


def test_the_resolution_is_shown_back_before_acting():
    """The user gets to see whether it understood them."""
    sentence = resolve("side 6", index()).describe("koblingsskjemaet", lang="no")
    assert "Side 6 er seksjon «4 Verifikasjon»" in sentence
    assert "etter isolasjonstabellen" in sentence   # the human name, not the id
    assert "festet til seksjonen, ikke til siden" in sentence


def test_english_addresses_work_the_same():
    anchor = resolve("add a wiring diagram to page 6", index())
    assert anchor.after_block == "tbl_iso"
    assert "anchored to the section" in anchor.describe("the diagram", lang="en")


def test_short_forms_are_understood():
    for phrasing in ("s. 6", "p.6", "på side 6", "page 6"):
        assert resolve(phrasing, index()).page_seen == 6, phrasing


# --- other address forms -------------------------------------------------
def test_a_section_address_is_more_stable_and_scores_higher():
    page = resolve("side 6", index())
    section = resolve("i kapittel 4", index())
    assert section.confidence > page.confidence


def test_after_a_named_block_is_the_strongest_address():
    anchor = resolve("etter isolasjonstabellen", index())
    assert anchor.kind == "after" and anchor.after_block == "tbl_iso"
    assert anchor.confidence >= 0.9


def test_before_a_named_block_works_too():
    anchor = resolve("before isolasjonstabellen", index())
    assert anchor.before_block == "tbl_iso" and anchor.after_block is None


def test_the_end_and_the_start_are_addresses():
    assert resolve("bakerst i dokumentet", index()).kind == "end"
    assert resolve("first page", index()).kind == "start"


# --- refusing well -------------------------------------------------------
def test_a_page_that_does_not_exist_says_how_many_there_are():
    anchor = resolve("side 40", index())
    assert not anchor.resolved
    assert "8 side(r)" in anchor.note


def test_an_address_it_cannot_read_asks_rather_than_guesses():
    anchor = resolve("legg den et fint sted", index())
    assert not anchor.resolved
    assert "Si hvilken seksjon" in anchor.describe("figuren", lang="no")


def test_an_empty_page_is_reported_not_guessed():
    idx = PageIndex([Block("a", page=1), Block("b", page=3)])
    assert "tom" in resolve("side 2", idx).note


# --- turning an anchor into an edit --------------------------------------
def test_an_anchor_becomes_an_order_pin():
    idx = index()
    pin = order_pin(resolve("side 6", idx), idx)
    assert pin and pin["after"] == "tbl_iso"
    assert pin["index"] == 4


def test_an_unresolved_anchor_produces_no_edit():
    idx = index()
    assert order_pin(resolve("somewhere nice", idx), idx) is None


# --- built from real geometry --------------------------------------------
def test_it_builds_from_foldok_boxes_geometry():
    from foldok_boxes import BlockInput, LayoutSession

    blocks = [BlockInput(f"t{i}", "text", text="x" * 1500) for i in range(60)]
    session = LayoutSession(blocks)
    geometry = session.geometry()
    idx = PageIndex.from_geometry(
        geometry, [{"id": b.id, "section": "body", "section_title": "Body"} for b in blocks]
    )
    assert idx.page_count == geometry.page_count
    assert idx.page_count > 1
    anchor = resolve(f"page {idx.page_count}", idx)
    assert anchor.resolved
