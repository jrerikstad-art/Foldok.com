"""Regression: empty installation maps refill; procedure from corpus, not false GAP."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import foldok_compile as fc


def test_ensure_fills_empty_installation():
    index = [
        {
            "file": "Installasjonsmanual.pdf",
            "kind": "pdf",
            "caption": "Installasjon av kabelrenne — montering og jording",
            "doc_role_hints": ["installation_step"],
            "facts": [
                {
                    "id": "f1",
                    "key": "mounting_step",
                    "value": "Mount the tray on supports before connecting bonding straps.",
                }
            ],
        },
        {
            "file": "brochure_marketing.pdf",
            "kind": "pdf",
            "caption": "cable tray wiring systems have 50+ year track record of excellent industrial performance",
            "doc_role_hints": ["overview"],
            "facts": [],
        },
    ]
    secs = [
        {
            "section_key": "installation",
            "title": "Installation / Assembly",
            "roles": ["installation_step"],
            "required_media": {"preferred_roles": ["installation_step"]},
        }
    ]
    fm = fc.ensure_section_file_coverage({"installation": []}, secs, index)
    assert "Installasjonsmanual.pdf" in fm["installation"]
    assert fm["installation"][0] == "Installasjonsmanual.pdf"


def test_compile_procedure_not_gap():
    mapping = {
        "files": ["Installasjonsmanual.pdf"],
        "section": {
            "section_key": "installation",
            "title": "Installation / Assembly",
            "writing_rules": {"structure": "numbered_steps"},
        },
        "template_key": "technical_doc_package",
    }
    index = [
        {
            "file": "Installasjonsmanual.pdf",
            "caption": "Installation steps for cable tray mounting and earthing",
            "doc_role_hints": ["installation_step"],
            "facts": [
                {
                    "id": "t1",
                    "key": "step_1",
                    "value": "Install supports at the specified span before placing tray sections.",
                },
                {
                    "id": "t2",
                    "key": "step_2",
                    "value": "Connect earthing straps between tray lengths and the bonding network.",
                },
            ],
        }
    ]
    md = fc.compile_tech_procedure_md("installation", mapping, index, {}, lang="en")
    assert md
    assert "GAP: claims" not in md
    assert re_search_step(md)
    assert "Install supports" in md or "earthing" in md.lower()


def re_search_step(md: str) -> bool:
    import re
    return bool(re.search(r"(?m)^\s*\d+\.\s+\S", md))


def test_marketing_blurb_filtered():
    assert fc._is_marketing_blurb(
        "cable tray wiring systems have 50+ year track record of excellent industrial performance and dependability."
    )
    assert not fc._is_marketing_blurb("Torque fasteners to 25 Nm after alignment.")


def test_generate_installation_not_false_gap():
    section = {
        "section_key": "installation",
        "title": "Installation / Assembly",
        "title_no": "Installasjon / montering",
        "required_facts": [],
        "required_media": {"preferred_roles": ["installation_step"]},
        "writing_rules": {
            "voice": "imperative",
            "structure": "numbered_steps",
            "fact_citation": "required",
        },
    }
    mapping = {
        "section_key": "installation",
        "files": ["Installasjonsmanual.pdf"],
        "fact_ids": [],
        "section": section,
        "template_key": "technical_doc_package",
    }
    index = [
        {
            "file": "Installasjonsmanual.pdf",
            "kind": "pdf",
            "caption": "Cable tray installation — mount and bond",
            "doc_role_hints": ["installation_step"],
            "facts": [
                {
                    "id": "a1",
                    "key": "install_hint",
                    "value": "Mount tray sections on supports, then tighten splice plates before loading cables.",
                    "confidence": 0.9,
                }
            ],
        }
    ]
    text = fc.generate_section_with_structure(
        "installation", mapping, index, {"name": "EMC", "purpose": "test"}, "en",
    )
    assert "budget 0" not in text
    assert "GAP: claims" not in text
    assert re_search_step(text)


if __name__ == "__main__":
    test_ensure_fills_empty_installation()
    test_compile_procedure_not_gap()
    test_marketing_blurb_filtered()
    test_generate_installation_not_false_gap()
    print("ok")
