"""Project identity — primary topics beat OEM density.

Run:  python -m pytest foldok_identity/tests -q
"""

from __future__ import annotations

from foldok_corpus import build_offer
from foldok_identity import identify_project, score_offer, score_topic


def test_install_artifact_sets_kind_and_arc():
    bp = identify_project(
        artifact={"name": "Installasjonsmanual SiteAlpha", "audience": "Felt"},
        themes=["cable routing", "earthing", "verification"],
        reference_themes=["sensor", "scanner", "product range"],
    )
    assert bp.identity.document_kind == "installation"
    assert bp.preferred_arc[0] == "purpose"
    assert "cable routing" in bp.identity.primary_topics
    assert "sensor" in bp.identity.secondary_topics or "sensor" in bp.identity.excluded_topics


def test_reference_only_theme_is_not_primary():
    bp = identify_project(
        artifact={"name": "Installation handover"},
        themes=["installation", "cable tray"],
        reference_themes=["laser scanner", "safety sensor"],
    )
    assert "laser scanner" not in bp.identity.primary_topics
    assert score_topic("laser scanner", bp.identity) in ("somewhat", "background", "ignore")
    assert score_topic("cable tray", bp.identity) == "relevant"


def test_market_drops_ignored_offers_when_identity_present():
    claims = [
        {"type": "practice", "text": "Mount tray after earthing", "source": "a.pdf"},
        {"type": "practice", "text": "Torque fasteners", "source": "b.pdf"},
        {"type": "quantity", "text": "Scanner range 5 m laser scanner", "source": "oem.pdf"},
        {"type": "quantity", "text": "Scanner resolution laser scanner", "source": "oem2.pdf"},
    ]
    bp = identify_project(
        artifact={"name": "Installation manual"},
        themes=["installation", "earthing", "tray"],
        reference_themes=["laser scanner"],
    )
    # Force scanner into excluded so quantity samples hit ignore.
    bp.identity.excluded_topics = ["laser scanner"]
    offer = build_offer(claims, identity=bp)
    by_key = {o.key: o for o in offer.offers}
    assert by_key["sec.practice"].kept is True
    assert by_key["sec.quantity"].relevance == "ignore"
    assert by_key["sec.quantity"].kept is False


def test_score_offer_keeps_frame_relevant():
    bp = identify_project(artifact={"name": "Installasjonsdokument"}, themes=["routing"])
    rel = score_offer({"key": "sec.definition", "title": "Begreper", "band": "frame"}, bp.identity)
    assert rel == "relevant"


def test_no_hardcoded_real_vendors_in_identity_module():
    from pathlib import Path
    text = Path(__file__).resolve().parents[1].joinpath("blueprint.py").read_text(encoding="utf-8").lower()
    for banned in ("sick", "toyota", "legrand", "dogger", "siemens", "phoenix contact"):
        assert banned not in text
