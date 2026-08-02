"""Evidence library tests.

Run:  python -m pytest foldok_evidence/tests -q
"""

from __future__ import annotations

from foldok_evidence import build_library
from foldok_identity import identify_project


def test_asset_has_depicts_and_type():
    index = [{
        "file": "Bilder/cleat.jpg",
        "kind": "photo",
        "caption": "Cable cleat mounted on vertical ladder illustrating correct spacing",
        "content_tags": ["cable tray", "installation"],
    }]
    bp = identify_project(
        artifact={"name": "Installation manual"},
        themes=["cable tray", "installation"],
    )
    lib = build_library(index, identity=bp.identity)
    assert len(lib.assets) == 1
    a = lib.assets[0]
    assert a.type == "photo"
    assert "cleat" in a.depicts.lower() or "cleat" in a.caption.lower()
    assert a.id.startswith("A")


def test_for_topic_prefers_matching_tags():
    index = [
        {"file": "a.jpg", "kind": "photo", "caption": "Earthing bar", "content_tags": ["earthing"]},
        {"file": "b.jpg", "kind": "photo", "caption": "Random wall", "content_tags": ["architecture"]},
    ]
    lib = build_library(index)
    hits = lib.for_topic("earthing", limit=2)
    assert hits and hits[0].file.endswith("a.jpg")
