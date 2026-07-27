"""Guardrails: project-local formlayout cache + vehicle template filter + gap scope."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT / "form_engine"))


def test_formlayout_never_writes_engine_ref_cache():
    from form_engine.layout_extract import resolve_formlayout_cache, extract_layout

    engine_ref = ROOT / ".foldok_ref_cache"
    assert resolve_formlayout_cache("abc", engine_ref) is None
    assert resolve_formlayout_cache("abc", None) is None

    with tempfile.TemporaryDirectory() as td:
        path = resolve_formlayout_cache("deadbeef", td)
        assert path is not None
        assert path.parent == Path(td)
        assert path.name == "formlayout-deadbeef.json"
        pkg = extract_layout(
            {"sha256": "deadbeef", "name": "x.pdf", "text_peek": "Kunde: ____\nDato: ____"},
            cache_dir=td,
        )
        assert path.exists()
        assert pkg.get("sections") or pkg.get("fields") is not None
        # Must not have created a formlayout under engine ref cache
        leaked = list(engine_ref.glob("formlayout-deadbeef.json")) if engine_ref.is_dir() else []
        assert not leaked, f"leaked into ship cache: {leaked}"


def test_vehicle_templates_hidden_unless_tagged():
    import form_model as fm

    locked = {
        "key": "sample_multipoint",
        "file": "sample_multipoint.json",
        "origin": "imported",
        "applies_to": ["vehicle", "sample_fixture"],
        "badge": "Domeneeksempel",
    }
    flexible = {
        "key": "inspection_checklist",
        "file": "inspection_checklist.json",
        "system_default": True,
        "applies_to": ["inspection"],
    }
    assert fm.is_domain_locked_vehicle_template(locked)
    assert not fm.is_domain_locked_vehicle_template(flexible)

    out = fm.filter_templates_for_project([locked, flexible], {"name": "Sandnes renseanlegg"})
    assert [t["key"] for t in out] == ["inspection_checklist"]

    out2 = fm.filter_templates_for_project(
        [locked, flexible], {"name": "Verksted", "tags": ["vehicle"]})
    assert {t["key"] for t in out2} == {"sample_multipoint", "inspection_checklist"}


def test_gaps_scoped_to_active_template():
    import doc_state as ds
    import form_model as fm

    class _Fc:
        def inject_user_facts(self, index, user_facts):
            return index or []

        def template_gaps(self, *a, **k):
            return []

        def map_sections(self, *a, **k):
            return {}, []

        def search_fact_candidates(self, *a, **k):
            return []

        def gap_guide(self, *a, **k):
            return {}

        def allows_reference_suggest(self, *a, **k):
            return True

    vehicle = {
        "file": "sample_multipoint.json",
        "template_key": "sample_multipoint",
        "document_species": "form_fill",
        "sections": [{
            "section_key": "kunde_og_kjoretoy",
            "fields": [
                {"key": "vin", "required": True, "label": "VIN", "type": "text"},
            ],
        }],
    }
    sewage = {
        "file": "sewage.json",
        "template_key": "sewage",
        "document_species": "narrative",
        "sections": [{
            "section_key": "identification",
            "required_facts": [
                {"key": "discharge_permit_no", "severity": "blocking", "label_no": "Tillatelse"},
            ],
        }],
    }
    state = {
        "doc": {
            "template_file": "sewage.json",
            "sections": {
                "identification": {"md": "`[MANGLER: discharge_permit_no]`"},
                # leftover foreign form state must not leak
                "kunde_og_kjoretoy": {"fields": {"vin": {"value": None}}},
            },
        },
        "user_facts": [],
        "dismissed": [],
        "documents": [],
    }
    gaps = ds.gaps_for_document(state, sewage, [], {}, _Fc(), fast=True)
    keys = {g["key"] for g in gaps}
    assert "discharge_permit_no" in keys
    assert "vin" not in keys
    # Wrong template for form_fill → empty
    assert ds.gaps_for_document(state, vehicle, [], {}, _Fc(), fast=True) == []


if __name__ == "__main__":
    test_formlayout_never_writes_engine_ref_cache()
    test_vehicle_templates_hidden_unless_tagged()
    test_gaps_scoped_to_active_template()
    print("ok")
