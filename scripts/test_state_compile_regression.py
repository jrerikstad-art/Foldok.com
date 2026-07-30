from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "local_app") not in sys.path:
    sys.path.insert(0, str(ROOT / "local_app"))

import editor_chat as edchat  # noqa: E402
import foldok_compile as fc  # noqa: E402


def test_spec_coherence_route_runs_generate():
    r = edchat.route_editor_message(
        "kjør spesifikasjonsgjennomgang nå",
        {"chat_pending": None},
        [],
    )
    ex = r.get("execute") or {}
    assert ex.get("tool") == "run_generate"
    assert ex.get("template_key") == "spec_coherence_review"


def test_abbreviations_section_not_auto_generated():
    mapping = {
        "section_key": "abbreviations",
        "section": {"section_key": "abbreviations", "writing_rules": {"structure": "prose"}},
        "fact_ids": [],
        "files": [],
    }
    out = fc.generate_section_with_structure(
        "abbreviations",
        mapping,
        index=[],
        artifact={},
        lang="no",
    )
    assert out == ""


def test_section_fact_context_filters_contact_noise():
    mapping = {
        "section_key": "method",
        "section": {"section_key": "method", "required_facts": []},
        "fact_ids": ["f1", "f2"],
        "files": ["docs/a.txt"],
    }
    index = [{
        "file": "docs/a.txt",
        "facts": [
            {"id": "f1", "key": "email", "value": "test@example.com"},
            {"id": "f2", "key": "voltage", "value": "5", "unit": "V"},
        ],
    }]
    ctx = fc.build_section_fact_context(mapping, index, artifact={"name": "X", "purpose": "Y"})
    ids = {a["id"] for a in ctx["available"]}
    assert "f1" not in ids
    assert "f2" in ids


def test_research_method_hard_stop_only_mangler_when_required_missing():
    mapping = {
        "section_key": "method",
        "template_key": "research_project_report",
        "section": {
            "section_key": "method",
            "title_no": "Metode",
            "required_facts": [
                {"key": "method_description", "severity": "blocking"},
                {"key": "equipment", "severity": "warning"},
                {"key": "sample_size", "severity": "warning"},
            ],
            "writing_rules": {"structure": "prose"},
        },
        "fact_ids": [],
        "files": ["docs/emc.txt"],
    }
    idx = [{
        "file": "docs/emc.txt",
        "facts": [
            {"id": "f1", "key": "manufacturer", "value": "Legrand"},
            {"id": "f2", "key": "phone", "value": "+1 (248) 848-9100"},
            {"id": "f3", "key": "email", "value": "enquiries@atkore.com"},
        ],
    }]
    out = fc.generate_section_with_structure(
        "method", mapping, idx, artifact={}, lang="no"
    )
    assert "MANGLER: method_description" in out
    assert "MANGLER: equipment" in out
    assert "MANGLER: sample_size" in out
    assert "Legrand" not in out
    assert "+" not in out


def test_postprocess_strips_scope_filler_and_contact_noise_outside_cover():
    idx = [{
        "file": "a.txt",
        "facts": [{"id": "f1", "key": "project_title", "value": "EMC"}],
    }]
    text = (
        "project title er EMC. scope statement er Forskningsprosjekt.\n"
        "manufacturer er Legrand. +1 (248) 848-9100. enquiries@atkore.com"
    )
    out, _, _ = fc.postprocess("method", text, idx, artifact={"name": "EMC", "purpose": "Forskningsprosjekt"})
    assert "project title" not in out.lower()
    assert "scope statement" not in out.lower()
    assert "248" not in out
    assert "@" not in out


def test_metode_hard_stop_blocks_large_unrelated_fact_bag():
    facts = [
        {"id": "doc", "key": "document_number", "value": "ITR-20-006"},
        {"id": "v1", "key": "lv_three_phase_voltage_iter", "value": "400", "unit": "V"},
        {"id": "ph", "key": "phone", "value": "fair rite products phone: +1 (248) 848-9100"},
    ]
    for i in range(47):
        facts.append({"id": f"x{i}", "key": f"misc_{i}", "value": f"value_{i}"})
    idx = [{"file": "emc/source.txt", "facts": facts}]
    mapping = {
        "section_key": "metode",
        "template_key": "research_project_report",
        "section": {
            "section_key": "metode",
            "title_no": "Metode",
            "required_facts": [
                {"key": "method_description", "severity": "blocking"},
                {"key": "equipment", "severity": "warning"},
                {"key": "sample_size", "severity": "warning"},
            ],
            "writing_rules": {"structure": "prose"},
        },
        "fact_ids": [],
        "files": ["emc/source.txt"],
    }
    body = fc.generate_section_with_structure("metode", mapping, idx, artifact={}, lang="no")
    assert "ITR-20-006" not in body
    assert "400 V" not in body
    assert "phone" not in body.lower()
    assert body.count("MANGLER") >= 1
    assert len(body) < 400


def test_research_cover_not_product_dump():
    idx = [{
        "file": "Documents/Chalfant 78411.pdf",
        "caption": "EMI cable tray",
        "facts": [
            {"id": "a", "key": "author_name", "value": "David Beltran"},
            {"id": "p", "key": "product_name", "value": "Marco Steel Wire Cable Tray"},
            {"id": "ph", "key": "phone", "value": "+1 248"},
            {"id": "v", "key": "lv_three_phase_voltage_iter", "value": "400", "unit": "V"},
        ],
    }]
    mapping = {
        "template_key": "research_project_report",
        "section_key": "cover",
        "section": {"section_key": "cover"},
        "fact_ids": [],
        "files": [],
    }
    body = fc.generate_section_with_structure(
        "cover", mapping, idx, artifact={"name": "EMC"}, lang="no"
    )
    assert "Prosjekttittel" in body or "EMC" in body
    assert "Marco Steel" not in body
    assert "400" not in body
    assert "248" not in body
    assert "MANGLER: institution" in body


def test_research_source_register_lists_files():
    idx = [
        {"file": "Documents/a.pdf", "caption": "Dogger Bank", "kind": "doc", "facts": []},
        {"file": "Documents/b.pdf", "caption": "Chalfant", "kind": "doc", "facts": []},
    ]
    mapping = {
        "template_key": "research_project_report",
        "section_key": "source_register",
        "section": {"section_key": "source_register"},
        "fact_ids": [],
        "files": [],
    }
    body = fc.generate_section_with_structure(
        "source_register", mapping, idx, artifact={}, lang="no"
    )
    assert "a.pdf" in body
    assert "Ingen fakta tilgjengelig" not in body


def test_research_observations_has_themed_table_not_empty():
    idx = [{
        "file": "Documents/Chalfant.pdf",
        "facts": [
            {"id": "1", "key": "h_field_attenuation_premium", "value": "70 to 83", "unit": "dB"},
            {"id": "2", "key": "test_standard", "value": "MIL STD 285"},
            {"id": "3", "key": "phone", "value": "1-888"},
        ],
    }]
    mapping = {
        "template_key": "research_project_report",
        "section_key": "observations",
        "section": {"section_key": "observations", "required_facts": []},
        "fact_ids": [],
        "files": ["Documents/Chalfant.pdf"],
    }
    body = fc.generate_section_with_structure(
        "observations", mapping, idx, artifact={}, lang="no"
    )
    assert "MANGLER: measurement" in body
    assert "70 to 83" in body or "70" in body
    assert "1-888" not in body
    assert "phone" not in body.lower()


def test_classify_emc_folder_is_spec_library_not_research():
    idx = [{
        "file": "Documents/Chalfant.pdf",
        "caption": "EMI cable tray shielding MIL STD 285",
        "content_tags": ["emc", "cable_tray", "shielding"],
        "facts": [{"id": "1", "key": "test_standard", "value": "MIL STD 285"}],
    }]
    ct = edchat.classify_corpus("EMC", idx, artifact={"name": "EMC", "research_question": "x"})
    assert ct == "spec_library"
    assert edchat.default_template_for_corpus(ct) == "topic_brief"


def test_topic_brief_zones_or_explicit_gap_never_phones():
    idx = [{
        "file": "Documents/Chalfant.pdf",
        "caption": "EMI shielding zones attenuation cable tray",
        "content_tags": ["emc", "shielding"],
        "facts": [
            {"id": "1", "key": "h_field_attenuation_premium", "value": "70 to 83", "unit": "dB"},
            {"id": "2", "key": "test_standard", "value": "MIL STD 285"},
            {"id": "3", "key": "phone", "value": "+1 (248) 848-9100"},
            {"id": "4", "key": "separation_distance", "value": "300", "unit": "mm"},
            {"id": "5", "key": "cable_class", "value": "Class 4 power"},
        ],
    }]
    mapping = {
        "template_key": "topic_brief",
        "section_key": "overview",
        "section": {"section_key": "overview"},
        "fact_ids": [],
        "files": ["Documents/Chalfant.pdf"],
    }
    body = fc.generate_section_with_structure(
        "overview", mapping, idx, artifact={"name": "EMC"}, lang="no"
    )
    assert "248" not in body
    assert "phone" not in body.lower()

    answers = fc.generate_section_with_structure(
        "answers",
        {**mapping, "section_key": "answers", "section": {"section_key": "answers"}},
        idx, artifact={"name": "EMC"}, lang="no",
    )
    assert "248" not in answers
    assert "phone" not in answers.lower()



def test_research_method_body_under_500_when_missing():
    mapping = {
        "section_key": "method",
        "template_key": "research_project_report",
        "section": {"section_key": "method"},
        "fact_ids": [],
        "files": [],
    }
    idx = [{"file": "x.pdf", "facts": [
        {"id": "1", "key": "lv_three_phase_voltage_iter", "value": "400", "unit": "V"},
        {"id": "2", "key": "phone", "value": "+1 248"},
    ]}]
    body = fc.generate_section_with_structure("method", mapping, idx, artifact={}, lang="no")
    assert len(body) < 500
    assert "400" not in body
    assert "MANGLER: method_description" in body


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print("OK", _name)
    print("ALL PASS")

