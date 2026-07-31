"""Installation manual — locked system, thin corpus, named focus (generic)."""
from __future__ import annotations

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "local_app"))

import install_manual_compile as imc  # noqa: E402
import foldok_compile as fc  # noqa: E402


def _strategy_index():
    return [
        {
            "file": "BoD_workshop.pdf",
            "caption": "Board of directors personas market hypothesis competitive analysis",
            "facts": [
                {"id": "p1", "key": "persona", "value": "Facility buyer"},
                {"id": "h1", "key": "hypothesis", "value": "Wire trays may win"},
                {"id": "r1", "key": "requirement", "value": "Grow market share"},
            ],
            "doc_role_hints": ["overview"],
        },
        {
            "file": "IEC_standards_list.pdf",
            "caption": "IEC 61000 ISO 11452 EN 55011 standards register normsamling kravliste",
            "facts": [
                {"id": "s1", "key": "requirement", "value": "IEC 61000-6-2"},
                {"id": "s2", "key": "standard", "value": "ISO 11452"},
                {"id": "s3", "key": "criterion", "value": "EN 55011"},
            ],
            "doc_role_hints": ["spec"],
        },
    ]


def _vendor_install_entry():
    """Fixture vendor name is local to the test — not an engine constant."""
    return {
        "file": "Acme_Sensor_Install.pdf",
        "caption": "Acme sensor installation mounting torque wiring procedure safety",
        "facts": [
            {"id": "t1", "key": "torque", "value": "2.5", "unit": "Nm"},
            {"id": "m1", "key": "manufacturer", "value": "Acme"},
            {"id": "y1", "key": "system_type", "value": "inductive sensor"},
        ],
        "doc_role_hints": ["manual", "datasheet"],
    }


def test_strategy_corpus_stays_thin():
    idx = _strategy_index()
    art = {"system_under_install": "sensor", "install_system_locked": True, "name": "Demo"}
    assert imc.corpus_shape(idx, art) == "strategy_standards"
    assert imc.should_stay_thin(idx, art)
    assert imc.allowed_install_files(idx, art) == set()


def test_named_focus_unlocks_allowlist_without_builtin_vendors():
    idx = _strategy_index() + [_vendor_install_entry()]
    art = imc.merge_focus_sources(
        {"system_under_install": "sensor", "install_system_locked": True},
        ["acme"],
    )
    assert not imc.should_stay_thin(idx, art)
    allowed = imc.allowed_install_files(idx, art)
    assert allowed == {"Acme_Sensor_Install.pdf"}
    assert "BoD_workshop.pdf" not in allowed


def test_no_vendor_constants_in_module():
    src = Path(imc.__file__).read_text(encoding="utf-8").lower()
    for banned in ("sick", "marco", "ve 2", "ve2", "atkore", "chalfant", "york emc"):
        # Allow only inside comments that say we do NOT hard-code — check code tokens
        assert f'"{banned}"' not in src
        assert f"'{banned}'" not in src


def test_tier_a_does_not_pull_loud_requirements():
    idx = _strategy_index() + [_vendor_install_entry()]
    art = {"system_under_install": "sensor", "install_system_locked": True,
           "install_focus_sources": ["acme"], "name": "Demo"}
    mapping = {
        "template_key": "installation_manual",
        "section_key": "prerequisites",
        "files": ["Acme_Sensor_Install.pdf"],
        "fact_ids": [],
        "section": {
            "section_key": "prerequisites",
            "required_facts": [
                {"key": "requirement", "severity": "warning"},
            ],
            "writing_rules": {"structure": "table"},
        },
    }
    ctx = fc.build_section_fact_context(mapping, idx, art)
    vals = {str(a.get("value")) for a in ctx["available"]}
    assert "Grow market share" not in vals
    assert "IEC 61000-6-2" not in vals


def test_thin_generate_identity_and_sequence():
    idx = _strategy_index()
    art = {"system_under_install": "sensor", "name": "Demo"}
    mapping = {
        "template_key": "installation_manual",
        "section_key": "identification",
        "files": [],
        "fact_ids": [],
        "section": {
            "section_key": "identification",
            "writing_rules": {"structure": "table"},
            "required_facts": [],
        },
    }
    text = fc.generate_section_with_structure(
        "identification", mapping, idx, art, "no",
    )
    assert "system_under_install" in text
    assert "persona" not in text.lower()

    seq = {
        "template_key": "installation_manual",
        "section_key": "sequence",
        "files": [],
        "fact_ids": [],
        "section": {
            "section_key": "sequence",
            "writing_rules": {"structure": "numbered_list", "prescriptive": True},
            "required_content": ["prescriptive_banner"],
        },
    }
    gap = fc.generate_section_with_structure("sequence", seq, idx, art, "no")
    assert "MANGLER" in gap
    assert "bruk" in gap.lower() or "utvid" in gap.lower()
    assert "1." not in gap
    for banned in ("sick", "marco", "ve 2"):
        assert banned not in gap.lower()


def test_parse_focus_sources_generic():
    assert "acme" in imc.parse_focus_sources("bruk Acme i manualen")
    assert "ve-handbook.pdf" in imc.parse_focus_sources("utvid med VE-handbook.pdf")
    assert imc.parse_focus_sources("hello world") == []


def _tech_info_entry():
    """Filename has no install/manual token — body carries mounting/EMC tips."""
    return {
        "file": "technical_information_background_knowledge_on_safety_laser_scanners.pdf",
        "caption": (
            "Background knowledge for safety laser scanners and camera sensors; "
            "covers shielding, earthing, interference suppression, and functional safety."
        ),
        "detail_summary": (
            "Technical information detailing EMC principles: equipotential bonding, "
            "shielding techniques, mains filtering, cable routing, ground loops, "
            "and FE connection guidance for scanners."
        ),
        "facts": [
            {
                "id": "sh1",
                "key": "shield_connection",
                "value": "Always connect the shielding to FE or PE on both sides and over a large area",
            },
            {
                "id": "mf1",
                "key": "mains_filter_installation",
                "value": "must be mounted directly at the entry to the control cabinet",
            },
            {
                "id": "m1",
                "key": "manufacturer",
                "value": "Helios Sensing",
            },
            {
                "id": "pc1",
                "key": "protection_class_iii",
                "value": "operates with safety extra-low voltage",
            },
            {
                "id": "hz1",
                "key": "safety_device_fault_response",
                "value": "Safety components switch all safety outputs to the OFF state on errors",
            },
            {
                "id": "rq1",
                "key": "shield_coverage_requirement",
                "value": "cable shield coverage at least 65%",
            },
            {
                "id": "cr1",
                "key": "selv_ac_voltage_limit",
                "value": "50",
                "unit": "V",
            },
        ],
        "doc_role_hints": ["technical_data", "safety"],
    }


def _tray_catalog_entry():
    return {
        "file": "Wire_Tray_Catalogue.pdf",
        "caption": "Cable tray catalogue load tables and span charts",
        "facts": [
            {"id": "tr1", "key": "product_name", "value": "MegaTray 200"},
            {"id": "tr2", "key": "manufacturer", "value": "TrayCo"},
        ],
        "doc_role_hints": ["catalogue"],
    }


def test_tech_info_pdf_scores_and_fits_sensor_not_tray():
    e = _tech_info_entry()
    assert imc.install_file_score(e, "sensor") >= imc.INSTALL_MIN_SCORE
    assert imc.entry_fits_system(e, "sensor")
    assert not imc.entry_fits_system(e, "cable_tray")
    art = {"system_under_install": "sensor", "install_system_locked": True}
    allowed = imc.allowed_install_files([e, _tray_catalog_entry()], art)
    assert e["file"] in allowed
    assert _tray_catalog_entry()["file"] not in allowed


def test_compile_tips_from_tech_info():
    idx = [_tech_info_entry()]
    art = {"system_under_install": "sensor", "install_system_locked": True}
    # Claim plan → sequence steps (not duplicate tip tables)
    text_plan = imc.compile_install_section_from_plan(
        "sequence", idx, art, mapped_files=[idx[0]["file"]], lang="no",
    )
    assert text_plan
    assert "persona" not in text_plan.lower()

    mapping = {
        "template_key": "installation_manual",
        "section_key": "sequence",
        "files": [idx[0]["file"]],
        "fact_ids": [],
        "section": {
            "section_key": "sequence",
            "writing_rules": {"structure": "numbered_list", "prescriptive": True},
            "required_content": ["prescriptive_banner"],
        },
    }
    text = fc.generate_section_with_structure("sequence", mapping, idx, art, "no")
    # Either ordered steps with cites, or an explicit sequence gap — not tip-table sludge
    assert "{{fact:" in text or "sekvens ikke utledet" in text.lower()
    assert "persona" not in text.lower()
    if "sekvens ikke utledet" not in text.lower():
        assert "1." in text


def test_candidates_listed_when_thin():
    idx = _strategy_index() + [_tech_info_entry()]
    # Without focus, tech info unlocks mixed/install — not thin
    art = {"system_under_install": "sensor"}
    assert not imc.should_stay_thin(idx, art)
    names = imc.candidate_install_filenames(idx, art)
    assert any("laser" in Path(n).name.lower() or "technical" in Path(n).name.lower()
               for n in names)


def test_soft_match_closes_install_gaps_from_tech_info():
    """Folder has tips under extractor keys — not exact template keys."""
    idx = [_tech_info_entry()]
    art = {"system_under_install": "sensor", "install_system_locked": True, "name": "Demo"}
    tpl = json.loads((ROOT / "templates" / "installation_manual.json").read_text(encoding="utf-8"))
    file_map = imc.map_install_files(idx, tpl, art)
    gaps = fc.template_gaps(tpl, idx, art, file_map)
    open_keys = {g["key"] for g in gaps if g.get("severity") in ("blocking", "warning")}
    # Content exists under aliases / soft keys — must not dump as OEM-only misses
    assert "system_type" not in open_keys  # locked system or applicable_products
    assert "hazard" not in open_keys       # safety_device / protection tips
    assert "photos" not in open_keys       # mapped technical PDF counts as media
    # criterion may close via coverage/limit soft match if present; manufacturer present
    table = fc.compile_supplier_manual_gaps(gaps, "no")
    assert "MANGLER:system_type" not in table
    assert "MANGLER:hazard" not in table


def test_focus_overview_is_authored_not_page_copy():
    idx = [_tech_info_entry()]
    idx[0]["detail_summary"] = "Covers shielding, earthing, mains filtering, cable routing."
    idx[0]["extraction_stats"] = {
        "page_count": 40,
        "chars_per_page": {str(i): 2000 for i in range(1, 41)},
        "facts_per_page": {"8": 3, "14": 2},
    }
    idx[0]["file"] = "tech_im0102700_safety_laser.pdf"
    art = {
        "system_under_install": "sensor",
        "install_system_locked": True,
        "install_focus_sources": ["im0102700"],
        "name": "Demo",
    }
    ov = imc.compile_install_overview_md(idx, art, lang="no")
    assert "sensor" in ov or "Demo" in ov
    assert "{{figure:" not in ov
    assert "Sider fra teknisk kilde" not in ov
    # Diagrams once — in overview
    assert "<svg" in ov.lower()
    assert "foldok.diagram.v1" in ov
    assert 'data-profile="wiring"' in ov
    assert "Kanter:" not in ov
    # Sequence from claim plan — numbered steps, no duplicate tip-table sludge
    seq = imc.compile_install_section_from_plan(
        "sequence", idx, art, mapped_files=[idx[0]["file"]], lang="no",
        include_diagrams=False, include_appendix=True,
    )
    assert seq
    assert ("1." in seq) or ("MANGLER: sekvens" in seq) or ("{{fact:" in seq)
    # Single-assignment: no claim id in two buckets
    plan = imc.get_install_claim_plan(idx, art, mapped_files=[idx[0]["file"]])
    seen = set()
    for bucket, rows in (plan.get("buckets") or {}).items():
        for c in rows:
            cid = c.get("id")
            assert cid not in seen, f"claim {cid} in multiple buckets (hit {bucket})"
            seen.add(cid)
    stripped = imc.append_install_figures(
        seq + "\n{{figure:tech_im0102700_safety_laser.pdf:7|side 8}}",
        idx, art, section_key="sequence", limit=4, lang="no",
    )
    assert "{{figure:" not in stripped


def test_claim_partition_sequence_verbs():
    idx = [{
        "file": "Helios_Install.pdf",
        "caption": "sensor installation mounting wiring earthing",
        "facts": [
            {"id": "a1", "key": "mount_bracket", "value": "Mount the sensor on a rigid bracket"},
            {"id": "a2", "key": "shield_connection", "value": "Connect cable shield to FE at cabinet"},
            {"id": "a3", "key": "hazard_laser", "value": "Warning: class 1 laser radiation"},
            {"id": "a4", "key": "verify_earth", "value": "Verify PE continuity before power-up"},
            {"id": "a5", "key": "manufacturer", "value": "Helios"},
            {"id": "a6", "key": "cable_type", "value": "Prepare shielded data cable before install"},
        ],
        "doc_role_hints": ["manual"],
    }]
    art = {
        "system_under_install": "sensor",
        "install_system_locked": True,
        "install_focus_sources": ["helios"],
    }
    plan = imc.build_install_claim_plan(idx, art)
    buckets = plan["buckets"]
    assert any(c["id"] == "a5" for c in buckets["identity"])
    assert any(c["id"] == "a3" for c in buckets["safety"])
    assert any(c["id"] == "a4" for c in buckets["checks"])
    seq_ids = {c["id"] for c in buckets["sequence"]}
    assert "a1" in seq_ids and "a2" in seq_ids
    # exclusivity
    all_ids = []
    for rows in buckets.values():
        all_ids.extend(c["id"] for c in rows)
    assert len(all_ids) == len(set(all_ids))
    steps = imc.compile_sequence_from_plan(plan, lang="en")
    assert "1." in steps and "Mount" in steps
    assert steps.lower().count("{{fact:a1}}") <= 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
