"""LayoutTree contract — universal publishing input for renderers."""
from __future__ import annotations

import unittest

from artifact_engine.design_system import ENGINEERING_DS
from artifact_engine.fixtures import demo_ccs_document
from artifact_engine.layout import (
    ComponentLayout,
    ConstraintSolver,
    LayoutTree,
    PageLayout,
    RegionLayout,
    build_print_layout_engine,
)
from artifact_engine.render.base import Renderer
from artifact_engine.render.html import HTMLRenderer


class LayoutTreeContract(unittest.TestCase):
    def test_tree_has_region_hierarchy(self):
        doc = demo_ccs_document()
        tree = build_print_layout_engine(ENGINEERING_DS).layout(doc, compose=True)
        self.assertIsInstance(tree, LayoutTree)
        self.assertEqual(tree.contract_version, "1.0")
        self.assertGreaterEqual(tree.page_count, 1)
        page = tree.pages[0]
        self.assertIsInstance(page, PageLayout)
        self.assertTrue(page.regions)
        region = page.regions[0]
        self.assertIsInstance(region, RegionLayout)
        self.assertEqual(region.role, "main")
        self.assertTrue(region.containers)
        comps = region.containers[0].components
        self.assertTrue(comps)
        self.assertIsInstance(comps[0], ComponentLayout)
        self.assertTrue(comps[0].style.font_family or comps[0].style.color)

    def test_nodes_compat_flattens_components(self):
        doc = demo_ccs_document()
        tree = build_print_layout_engine(ENGINEERING_DS).layout(doc, compose=False)
        page = tree.pages[0]
        flat = page.nodes
        n_comp = sum(len(c.components) for r in page.regions for c in r.containers)
        self.assertEqual(len(flat), n_comp)

    def test_html_renderer_implements_protocol(self):
        self.assertTrue(isinstance(HTMLRenderer(), Renderer))

    def test_html_paint_from_layout_only(self):
        doc = demo_ccs_document()
        tree = build_print_layout_engine(ENGINEERING_DS).layout(doc, compose=False)
        html = HTMLRenderer().render_layout(tree)
        self.assertIn('data-layout="paginated"', html)
        self.assertIn('data-layout-contract="1.0"', html)
        self.assertIn("print-page", html)

    def test_constraint_solver_publishing_checks(self):
        eng = build_print_layout_engine(ENGINEERING_DS)
        checks = eng.solver.publishing_checks()
        self.assertTrue(any("keep_with_next" in c for c in checks))
        self.assertIsInstance(eng.solver, ConstraintSolver)


if __name__ == "__main__":
    unittest.main()
