"""Regenerate intent must catch typos and not fall through to the model."""
from __future__ import annotations

from local_app.editor_chat import (
    is_regenerate_document_ask,
    looks_like_regenerate_word,
)


def test_typo_tokens():
    assert looks_like_regenerate_word("regenerate")
    assert looks_like_regenerate_word("egaanerate")
    assert looks_like_regenerate_word("regaanerate")
    assert looks_like_regenerate_word("regenarate")
    assert looks_like_regenerate_word("regenerer")
    assert not looks_like_regenerate_word("hello")
    assert not looks_like_regenerate_word("generate")


def test_bare_typo_is_document_regen():
    assert is_regenerate_document_ask("egaanerate")
    assert is_regenerate_document_ask("regaanerate")
    assert is_regenerate_document_ask("regenerate")
    assert is_regenerate_document_ask("regenerate this")
    assert is_regenerate_document_ask("regenerate temabrief")


def test_section_scoped_excluded():
    assert not is_regenerate_document_ask("regenerate section Installation")
    assert not is_regenerate_document_ask("regenerer seksjon Safety")
