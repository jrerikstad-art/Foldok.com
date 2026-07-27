"""WORKORDER 0.58 §0 — gaps are scoped to the active document only."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))

import doc_state as ds  # noqa: E402
import form_model as fm  # noqa: E402


class _FakeFc:
    def inject_user_facts(self, index, user_facts):
        return index or []

    def template_gaps(self, template, index, artifact, section_files):
        return []

    def map_sections(self, template, index, artifact):
        return {}, []

    def search_fact_candidates(self, index, key):
        return []

    def gap_guide(self, key, section, index, artifact, documents=None):
        return {"action": "manual", "candidates": [], "message": ""}

    def allows_reference_suggest(self, key, severity=None):
        return True


VEHICLE_FORM_KEYS = {"vin", "reg_no", "mileage", "tread_depth", "customer_name", "date"}


def _form_template(file, sections):
    return {
        "file": file,
        "template_key": file.replace(".json", ""),
        "document_species": "form_fill",
        "sections": sections,
    }


def test_gaps_for_document_no_cross_contamination():
    vehicle_form = _form_template("sample_multipoint.json", [
        {
            "section_key": "kunde_og_kjoretoy",
            "fields": [
                {"key": "vin", "required": True, "label_no": "VIN", "type": "text"},
                {"key": "reg_no", "required": True, "label_no": "Reg.nr", "type": "text"},
            ],
        }
    ])
    sewage = {
        "file": "mini_sewage_treatment_plant_connection_diagram.json",
        "template_key": "mini_sewage_treatment_plant_connection_diagram",
        "document_species": "narrative",
        "sections": [
            {
                "section_key": "identification",
                "title_no": "Identifikasjon",
                "notes": "Utslippstillatelse står vanligvis i vedtaksbrevet.",
                "required_facts": [
                    {"key": "discharge_permit_no", "severity": "blocking",
                     "label_no": "Utslippstillatelse nr."},
                ],
            }
        ],
    }
    assert fm.is_form_fill(vehicle_form)

    # Contaminated state: vehicle form still in doc while we ask for sewage gaps
    state = {
        "doc": {
            "template_file": "sample_multipoint.json",
            "sections": {
                "kunde_og_kjoretoy": {"fields": {"vin": {"value": None}, "reg_no": {"value": None}}},
            },
        },
        "user_facts": [],
        "dismissed": [],
        "documents": [],
    }
    fc = _FakeFc()

    # Form gaps for vehicle form work when doc matches
    t_gaps = ds.gaps_for_document(state, vehicle_form, [], {}, fc, fast=True)
    assert {g["key"] for g in t_gaps} >= {"vin", "reg_no"}

    # Asking for sewage while doc is still vehicle form → empty / no vehicle keys
    # (compute refuses foreign form; narrative with empty md still may list required via map)
    state["doc"] = {
        "template_file": sewage["file"],
        "sections": {
            "identification": {"md": "`[MANGLER: discharge_permit_no]`", "files": []},
        },
    }
    s_gaps = ds.gaps_for_document(state, sewage, [], {}, fc, fast=True)
    keys = {g["key"] for g in s_gaps}
    assert "discharge_permit_no" in keys
    assert not (keys & VEHICLE_FORM_KEYS), f"vehicle form keys leaked into sewage gaps: {keys & VEHICLE_FORM_KEYS}"

    # filter_gaps_to_template drops foreign sections even if someone unions
    mixed = t_gaps + s_gaps
    filtered = ds.filter_gaps_to_template(mixed, sewage)
    assert all(g.get("key") not in VEHICLE_FORM_KEYS for g in filtered)

    text = ds.explain_gap_text(s_gaps[0], index_file_count=20)
    assert "Utslippstillatelse" in text or "discharge" in text.lower() or "kreves" in text
    assert len(text.replace("**", "").split()) <= 60


def test_create_shell_does_not_reuse_foreign_sections():
    import template_lifecycle as tl

    state = {
        "doc": {
            "template_file": "sample_multipoint.json",
            "sections": {
                "identification": {"md": "VIN stuff", "fields": {"vin": {"value": "X"}}},
            },
        },
        "documents": [],
        "gaps": [],
    }
    sewage = {
        "template_key": "mini",
        "name_no": "Kobling",
        "sections": [
            {"section_key": "identification", "title_no": "ID"},
        ],
    }
    tl.create_document_shell(state, "mini.json", sewage)
    sec = state["doc"]["sections"]["identification"]
    assert not sec.get("fields"), "must not reuse vehicle-form field bag under shared section key"
    assert sec.get("md") == ""


if __name__ == "__main__":
    test_gaps_for_document_no_cross_contamination()
    test_create_shell_does_not_reuse_foreign_sections()
    print("ok")
