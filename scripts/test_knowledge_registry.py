"""Knowledge pack registry — corrosion profile and loader."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "local_app"))

import knowledge_registry as kr  # noqa: E402


class TestKnowledgeRegistry(unittest.TestCase):
  def setUp(self):
    kr.reload_knowledge()

  def test_list_includes_corrosion(self):
    packs = kr.list_packs()
    ids = [p["id"] for p in packs]
    self.assertIn("corrosion_materials", ids)
    self.assertIn("cable_management_wiring", ids)

  def test_get_pack_loads_fragments(self):
    pack = kr.get_pack("corrosion_materials")
    self.assertIsNotNone(pack)
    frags = pack["fragments"]
    self.assertIn("forms.yaml", frags)
    self.assertEqual(len(frags["forms.yaml"]["forms"]), 7)
    self.assertIn("selection_checklist.yaml", frags)

  def test_blocking_gaps_empty_when_complete(self):
    gaps = kr.blocking_gaps(
        "corrosion_materials",
        {
            "corrosivity_class": "C3",
            "corrosivity_class_confirmed": True,
            "material_family": "zinc_coated_steel",
            "galvanic_review": "not_applicable",
        },
    )
    self.assertEqual(gaps, [])

  def test_blocking_gaps_missing_exposure(self):
    gaps = kr.blocking_gaps("corrosion_materials", {})
    ids = [g["id"] for g in gaps]
    self.assertIn("missing_exposure_class", ids)
    self.assertIn("missing_material_family", ids)

  def test_render_report_block(self):
    text = kr.render_report_block(
        "corrosion_materials",
        {
            "status": "draft",
            "environment_class": "C3",
            "corrosivity_class_confirmed": True,
            "exposure_notes": "urban outdoor, atmospheric",
            "material_family": "zinc-coated carbon steel",
            "protection_system": "hot-dip galvanized",
            "galvanic_review": "reviewed",
            "assumptions": [
                "Atmospheric exposure only; no splash or process chemicals declared",
                "Final suitability confirmed by responsible person",
            ],
            "sources": ["project specs"],
        },
    )
    self.assertIn("Corrosion protection (draft)", text)
    self.assertIn("C3", text)
    self.assertIn("Galvanic: reviewed", text)

  def test_disclaimer_never_claims_compliance(self):
    pack = kr.get_pack("corrosion_materials")
    self.assertFalse(pack["meta"].get("legal_compliance_claimed", True))

  def test_cable_pack_loads_fragments(self):
    pack = kr.get_pack("cable_management_wiring")
    self.assertIsNotNone(pack)
    frags = pack["fragments"]
    self.assertIn("tray_ladder_systems.yaml", frags)
    self.assertIn("wiring_systems.yaml", frags)
    self.assertIn("evidence.yaml", frags)
    self.assertIn("report_blocks.yaml", frags)

  def test_cable_blocking_gaps(self):
    gaps = kr.blocking_gaps("cable_management_wiring", {})
    ids = [g["id"] for g in gaps]
    self.assertIn("tray_class_missing", ids)
    self.assertIn("swl_span_missing", ids)

  def test_cable_render_report_blocks(self):
    support_note = kr.render_report_block(
        "cable_management_wiring",
        {
            "type": "CableSupportSystemNote",
            "status": "draft",
            "system_type": "tray",
            "material_class": "metallic",
            "swl_span_summary": "SWL declared with 2.0 m span basis",
            "support_summary": "Cantilever brackets at 1.5 m",
        },
    )
    self.assertIn("Cable support system (draft)", support_note)
    self.assertIn("System type: tray", support_note)

    wiring_note = kr.render_report_block(
        "cable_management_wiring",
        {
            "type": "WiringSystemSelectionNote",
            "status": "confirmed",
            "wiring_types_used": ["cable_tray", "cable_trunking"],
            "external_influences": ["ambient_temperature", "water_or_humidity"],
            "installation_methods": ["method_of_installation_ref"],
            "ccc_basis": "Project basis sheet CM-12",
            "voltage_drop_reviewed": True,
            "fire_sealing_reviewed": True,
        },
    )
    self.assertIn("Wiring system selection (confirmed)", wiring_note)
    self.assertIn("Voltage drop reviewed: yes", wiring_note)


if __name__ == "__main__":
  unittest.main()
