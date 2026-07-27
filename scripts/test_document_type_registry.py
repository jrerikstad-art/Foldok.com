"""Document Type Registry unit tests."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import document_type_registry as dtr  # noqa: E402


class DocumentTypeRegistryTest(unittest.TestCase):
    def setUp(self):
        dtr.reload_registry()

    def test_lists_core_and_compliance_types(self):
        types = dtr.list_document_types()
        ids = {t["id"] for t in types}
        self.assertTrue({
            "user_manual", "datasheet", "installation_guide",
            "maintenance_manual", "samsvarserklaring", "inspection_report",
            "industrial_report",
        } <= ids)
        self.assertTrue({
            "technical_file", "declaration_of_conformity", "inspection_package",
            "risk_file", "handover_package", "compliance_matrix", "test_report_package",
        } <= ids)
        self.assertGreaterEqual(len(ids), 14)

    def test_industrial_report_preferred_blocks(self):
        d = dtr.get_document_type("industrial_report")
        self.assertIsNotNone(d)
        pb = d["preferred_blocks"]
        self.assertIn("EvaluationMatrix", pb["evaluation_or_impact"])
        self.assertIn("StakeholderCard", pb["stakeholders"])
        t = dtr.materialise_template("industrial_report", project_id="p1")
        keys = [s["section_key"] for s in t["sections"]]
        self.assertIn("executive_summary", keys)
        self.assertIn("evaluation_or_impact", keys)

    def test_filter_by_industry(self):
        maritime = dtr.list_document_types("maritime")
        self.assertTrue(all("maritime" in t["industries"] for t in maritime))
        self.assertGreaterEqual(len(maritime), 2)

    def test_get_by_alias(self):
        d = dtr.get_document_type("brukermanual")
        self.assertIsNotNone(d)
        self.assertEqual(d["id"], "user_manual")
        self.assertIn("revision_history", d["structure"]["required"])

    def test_match_ranks(self):
        m = dtr.match_document_types("lag en brukermanual for pumper")
        self.assertTrue(m)
        self.assertEqual(m[0]["id"], "user_manual")

    def test_materialise_sections(self):
        t = dtr.materialise_template("installation_guide", project_id="p1")
        keys = [s["section_key"] for s in t["sections"]]
        self.assertIn("installation", keys)
        self.assertIn("identification", keys)
        self.assertEqual(t["document_type"], "installation_guide")
        self.assertEqual(t["workbench_template"], "installation_manual.json")
        # preferred blocks carried
        inst = next(s for s in t["sections"] if s["section_key"] == "installation")
        self.assertIn("Procedure", inst["preferred_blocks"])

    def test_materialise_unknown(self):
        with self.assertRaises(LookupError):
            dtr.materialise_template("not_a_type")

    def test_confidentiality_agreement_type(self):
        d = dtr.get_document_type("confidentiality_agreement")
        self.assertIsNotNone(d)
        self.assertFalse(d.get("legal_compliance_claimed", True))
        self.assertEqual(len(d.get("sections") or []), 6)
        t = dtr.materialise_template("confidentiality_agreement", project_id="p1")
        keys = [s["section_key"] for s in t["sections"]]
        self.assertIn("parties", keys)
        self.assertIn("signatures", keys)
        self.assertEqual(len(t["form_sections"]), 6)
        self.assertEqual(len(t["gaps"]), 5)

    def test_confidentiality_agreement_gaps(self):
        gaps = dtr.document_type_gaps("confidentiality_agreement", {})
        ids = {g["id"] for g in gaps}
        self.assertIn("parties_incomplete", ids)
        self.assertIn("signatures_missing", ids)
        complete = dtr.document_type_gaps(
            "confidentiality_agreement",
            {
                "disclosing_party": "Acme AS",
                "recipient": "Beta Elektro",
                "permitted_purpose": "Installation documentation only",
                "confidential_info_scope": "Project drawings and site photos",
                "care_standard": "Same as own proprietary information",
                "use_limitation": "Permitted purpose only",
                "non_disclosure": "No disclosure to third parties",
                "disclosing_signatory": "Jane Doe",
                "recipient_signatory": "John Smith",
            },
        )
        self.assertEqual(complete, [])

    def test_match_nda_alias(self):
        m = dtr.match_document_types("need an NDA for the project")
        self.assertTrue(m)
        self.assertEqual(m[0]["id"], "confidentiality_agreement")

    def test_opportunity_description_type(self):
        d = dtr.get_document_type("opportunity_description")
        self.assertIsNotNone(d)
        self.assertEqual(len(d.get("sections") or []), 3)
        t = dtr.materialise_template("opportunity_description", project_id="p1")
        keys = [s["section_key"] for s in t["sections"]]
        self.assertEqual(keys, ["industry_background", "competitive_analysis", "market_analysis"])
        self.assertIn("competitor_matrix", t["composition"])
        self.assertEqual(t["summary_block"]["block_type"], "OpportunitySummary")

    def test_opportunity_description_gaps(self):
        gaps = dtr.document_type_gaps("opportunity_description", {})
        ids = {g["id"] for g in gaps}
        self.assertIn("industry_incomplete", ids)
        self.assertIn("competitors_missing", ids)
        self.assertIn("value_proposition_missing", ids)
        complete = dtr.document_type_gaps(
            "opportunity_description",
            {
                "existing_products_services": "Industrial cable trays",
                "industry_size_shape": "Regional market, moderate concentration",
                "industry_trends": "Electrification and modular installs",
                "barriers_to_entry": "Certification and distribution",
                "competitors": [{"name": "Competitor A", "offerings": "Trays"}],
                "differentiation": "Faster site assembly",
                "market_size_growth": "Mid-single-digit growth",
                "target_market": "Nordic contractors",
                "value_proposition": "Lower install time with same SWL class",
                "sources": ["project interview notes"],
            },
        )
        self.assertEqual(complete, [])

    def test_opportunity_market_size_warning_without_sources(self):
        gaps = dtr.document_type_gaps(
            "opportunity_description",
            {
                "existing_products_services": "x",
                "industry_size_shape": "x",
                "industry_trends": "x",
                "barriers_to_entry": "x",
                "competitors": [{"name": "A"}],
                "differentiation": "x",
                "market_size_growth": "Growing market",
                "target_market": "Nordic",
                "value_proposition": "Faster install",
            },
        )
        warn = [g for g in gaps if g["id"] == "market_size_unsupported"]
        self.assertEqual(len(warn), 1)
        self.assertEqual(warn[0]["severity"], "warning")

    def test_product_strategy_type(self):
        d = dtr.get_document_type("product_strategy")
        self.assertIsNotNone(d)
        self.assertEqual(len(d.get("sections") or []), 10)
        t = dtr.materialise_template("product_strategy", project_id="p1", include="all")
        keys = [s["section_key"] for s in t["sections"]]
        self.assertIn("mission_vision", keys)
        self.assertIn("governance", keys)
        self.assertEqual(t["summary_block"]["block_type"], "ProductStrategySummary")

    def test_product_strategy_gaps(self):
        gaps = dtr.document_type_gaps("product_strategy", {})
        ids = {g["id"] for g in gaps}
        self.assertIn("mission_vision_missing", ids)
        self.assertIn("strategy_summary_missing", ids)
        self.assertIn("no_focus_areas", ids)
        complete = dtr.document_type_gaps(
            "product_strategy",
            {
                "mission": "Deliver reliable modular systems",
                "vision": "Lead in sustainable site-ready products",
                "value_for_customers": "Faster install, lower lifecycle cost",
                "value_for_organization": "Platform reuse and margin",
                "strategy_summary": "Product-led with solution bundles for key segments",
                "focus_areas": [{"name": "Modularity", "intent": "Standard interfaces"}],
                "product_definition": "Discrete hardware and software modules",
                "solution_definition": "End-to-end site delivery package",
                "positioning_choice": "hybrid",
            },
        )
        blocking = [g for g in complete if g["severity"] == "blocking"]
        self.assertEqual(blocking, [])

    def test_match_product_strategy_alias(self):
        m = dtr.match_document_types("lag en produktstrategi")
        self.assertTrue(m)
        self.assertEqual(m[0]["id"], "product_strategy")


if __name__ == "__main__":
    unittest.main()
