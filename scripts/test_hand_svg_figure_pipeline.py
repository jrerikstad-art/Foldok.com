"""T0 — hand-authored SVG reaches ArtifactEngine page with caption/number; re-issue identical."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import artifact_engine as ae  # noqa: E402

SAMPLE = ROOT / "foldok_diagram" / "wiring_water_heater.svg"
if not SAMPLE.exists():
    SAMPLE = ROOT / ".tmp_foldok7" / "wiring_water_heater.svg"


class HandSvgFigurePipelineTests(unittest.TestCase):
    def test_hand_svg_embeds_with_caption_and_number(self):
        self.assertTrue(SAMPLE.exists(), f"missing sample SVG: {SAMPLE}")
        svg = SAMPLE.read_text(encoding="utf-8")
        self.assertIn("<svg", svg)

        block = ae.diagram_block_from_svg(
            svg,
            title="Water heater wiring",
            caption="Terminal interconnection — hand fixture",
            figure_number="3.1",
            source_citation="WO-0.63 sample",
            diagram_type="wiring",
            revision="A",
        )
        doc = ae.Document(title="Figure pipeline proof", sections=[])
        doc = ae.CompositionEngine().embed_diagram(
            doc,
            block.svg,
            title=block.title,
            caption=block.caption,
            figure_number=block.figure_number,
            source_citation=block.source_citation,
            diagram_type=block.diagram_type,
            revision=block.revision,
            height_pt=block.height_pt,
        )
        html_a = ae.render_document(doc)
        html_b = ae.render_document(doc)
        self.assertEqual(html_a, html_b, "re-issue must be byte-identical")
        self.assertIn("Figure 3.1", html_a)
        self.assertIn("WO-0.63 sample", html_a)
        self.assertIn('data-figure="3.1"', html_a)
        self.assertIn("<svg", html_a)
        # Column-scale figure: width attribute or viewBox present
        self.assertTrue('viewBox="' in html_a or "width=" in html_a)


if __name__ == "__main__":
    unittest.main()
