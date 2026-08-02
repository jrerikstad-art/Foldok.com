"""Evidence + director tests. Synthetic names only.

Run:  python -m pytest foldok_evidence/tests foldok_director/tests -q
"""

from __future__ import annotations

from foldok_director import direct
from foldok_evidence import build_library
from foldok_identity import identify_project

INDEX = [
    {
        "file": "Docs/Kabelplan rev C.pdf",
        "caption": "Kabelplan revisjon C, for construction, SiteAlpha",
        "content_tags": ["cable routing", "cable tray"],
        "doc_role_hints": ["drawing"],
        "facts": [{"id": "f1", "key": "tray_type", "value": "ladder"}],
    },
    {
        "file": "Bilder/hovedtavle.jpg",
        "kind": "photo",
        "caption": "Hovedtavle after installation, labels visible",
        "content_tags": ["installation", "board"],
        "facts": [],
    },
    {
        "file": "Ref/EN 50174-2.pdf",
        "caption": "EN 50174-2 cabling installation planning",
        "doc_role_hints": ["standard"],
        "content_tags": ["standard", "separation"],
    },
    {
        "file": "Ref/oem_brochure.pdf",
        "caption": "VendorCo company profile — our solutions. Follow us. Request a quote.",
        "content_tags": ["marketing"],
    },
    {
        "file": "Ref/scanner_manual.pdf",
        "caption": "AcmeVendor GmbH operating instructions 8027032/2022-07-19",
        "content_tags": ["sensor", "scanner"],
        "doc_role_hints": ["manual"],
    },
]

TEMPLATE = {
    "sections": [
        {"key": "purpose", "title": "Purpose and scope", "position": 1,
         "purpose": "State purpose"},
        {"key": "safety", "title": "Safety", "position": 2},
        {"key": "install", "title": "Installation procedure", "position": 3,
         "purpose": "How the system is installed"},
        {"key": "verify", "title": "Verification", "position": 4},
    ]
}


def test_library_excludes_sales_and_keeps_drawings():
    bp = identify_project(
        artifact={"name": "Installasjonsmanual SiteAlpha"},
        themes=["cable routing", "installation"],
        reference_themes=["sensor", "scanner"],
    )
    lib = build_library(INDEX, identity=bp.identity)
    files = {a.file for a in lib.assets}
    assert "Docs/Kabelplan rev C.pdf" in files
    assert any(a.type == "photo" for a in lib.assets)
    assert any("brochure" in e.get("file", "").lower() for e in lib.excluded) or \
        "Ref/oem_brochure.pdf" not in files


def test_director_builds_checklist_and_sections():
    plan = direct(
        INDEX,
        artifact={"name": "Installasjonsmanual SiteAlpha", "audience": "Felt"},
        template=TEMPLATE,
        project_name="SiteAlpha",
    )
    assert plan.identity.get("document_kind") == "installation"
    assert len(plan.sections) >= 3
    keys = {c.key for c in plan.checklist}
    assert {"purpose", "outline", "evidence", "draft"} <= keys
    assert plan.checklist[0].done  # purpose from artifact name/kind
    install = next(s for s in plan.sections if s.key == "install")
    assert install.arc_stage in ("installation", "body")
    assert install.suggestions


def test_coverage_exposes_weakness():
    plan = direct(INDEX, artifact={"name": "Installation manual"}, template=TEMPLATE)
    assert 0 <= plan.overall_coverage.evidence <= 1
    d = plan.to_dict()
    assert d["schema_version"] == 1
    assert "sections" in d and "knowledge" in d


def test_no_vendor_catalogue_in_director_source():
    from pathlib import Path
    text = Path(__file__).resolve().parents[1].joinpath("__init__.py").read_text(encoding="utf-8").lower()
    for banned in ("sick", "toyota", "legrand", "dogger"):
        assert banned not in text
