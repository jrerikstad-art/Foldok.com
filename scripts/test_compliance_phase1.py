"""Phase 1 structural profiles + expanded document type registry.

Claim boundary: never assert legal compliance (see COMPLIANCE_POLICY.md).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import compliance_engine as ceng  # noqa: E402
import document_type_registry as dtr  # noqa: E402
from diagram_engine.symbols import list_symbols, get_symbol  # noqa: E402


class CompliancePhase1Test(unittest.TestCase):
    def setUp(self):
        dtr.reload_registry()
        ceng.reload_frameworks()

    def test_registry_has_compliance_types(self):
        ids = {t["id"] for t in dtr.list_document_types()}
        for need in (
            "technical_file", "declaration_of_conformity", "inspection_package",
            "risk_file", "handover_package", "compliance_matrix", "test_report_package",
            "samsvarserklaring", "user_manual",
        ):
            self.assertIn(need, ids)

    def test_existing_types_tagged(self):
        s = dtr.get_document_type("samsvarserklaring")
        self.assertIn("no", s.get("regions") or [])
        self.assertIn("electrical", s.get("domains") or [])
        self.assertIn("declaration", s.get("evidence_types") or [])

    def test_filter_by_region_domain(self):
        no_el = dtr.list_document_types(region="no", domain="electrical")
        ids = {t["id"] for t in no_el}
        self.assertIn("samsvarserklaring", ids)

    def test_frameworks_loaded(self):
        ids = {f["id"] for f in ceng.list_frameworks()}
        self.assertTrue({"eu_machinery", "electrical_installation", "general_inspection"} <= ids)
        for f in ceng.list_frameworks():
            self.assertEqual(f.get("kind"), "structural_profile")
            self.assertIn("disclaimer", f)
            self.assertNotIn("compliant", (f.get("label") or "").lower())

    def test_suggest_and_gaps(self):
        suggested = ceng.suggest_frameworks(["eu"], ["machinery"])
        self.assertIn("eu_machinery", suggested)
        gaps = ceng.evidence_gaps(framework_ids=["eu_machinery"], index=[], state={"doc": {"sections": {}}})
        self.assertGreaterEqual(len(gaps), 4)
        self.assertTrue(all(g["type"] == "evidence" for g in gaps))
        self.assertTrue(all(g.get("legal_claim") is False for g in gaps))
        # satisfy risk via section
        state = {"doc": {"sections": {"risk_assessment": {"md": "Hazards listed."}}}}
        gaps2 = ceng.evidence_gaps(framework_ids=["eu_machinery"], index=[], state=state)
        keys = {g["key"] for g in gaps2}
        self.assertNotIn("risk_assessment", keys)

    def test_package_status_never_claims_compliance(self):
        status = ceng.package_status(
            framework_ids=["eu_machinery"],
            index=[],
            state={"doc": {"sections": {}}},
        )
        self.assertFalse(status["legal_compliance_claimed"])
        self.assertEqual(status["kind"], "structural_profile_coverage")
        self.assertIn("disclaimer", status)
        self.assertIn("NEK", ceng.DISCLAIMER)
        self.assertIn(status["status"], ceng.SAFE_STATUS_LABELS)
        label = status["status_label"].lower()
        for bad in ("compliant", "ce ok", "iso satisfied", "legally"):
            self.assertNotIn(bad, label)
        self.assertEqual(status["coverage_percent"], 0)
        self.assertGreater(status["requirements_total"], 0)
        joined = " ".join(status.get("forbidden_claims") or []).lower()
        self.assertIn("nek compliant", joined)

    def test_package_status_coverage_math(self):
        fw = ceng.get_framework("eu_machinery")
        req_ids = [r["id"] for r in fw["evidence_requirements"]]
        status = ceng.package_status(
            framework_ids=["eu_machinery"],
            index=[],
            state={"doc": {"sections": {}}},
            user_confirmed_requirements=req_ids,
        )
        self.assertEqual(status["coverage_percent"], 100)
        self.assertEqual(status["status"], "ready_for_review")
        self.assertFalse(status["legal_compliance_claimed"])

    def test_default_compliance_has_disclaimer(self):
        d = ceng.default_compliance()
        self.assertEqual(d["kind"], "structural_profiles")
        self.assertEqual(d["disclaimer"], ceng.DISCLAIMER)

    def test_symbols_20(self):
        syms = list_symbols()
        self.assertGreaterEqual(len(syms), 20)
        pump = get_symbol("centrifugal_pump")
        self.assertIsNotNone(pump)
        ports = {p["id"] for p in pump["ports"]}
        self.assertEqual(ports, {"suction", "discharge", "drive"})


if __name__ == "__main__":
    unittest.main()
