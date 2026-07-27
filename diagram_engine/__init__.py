"""Diagram Engine v2 — intent-aware layout + multi-domain deterministic SVG.

One engine, three symbol packs (electrical / piping / mechanical),
shared Component–Port–Connection graph. Canvas edits the graph; engine draws.
"""
from __future__ import annotations

from .editor import DiagramCanvasEditor, DiagramDocument
from .electrical import (
    SLD_FIXTURE,
    WATER_HEATER_240V_FIXTURE,
    WIRING_FIXTURE,
    normalize_electrical_graph,
    render_electrical_diagram,
    resolve_wire_color,
)
from .engine import DiagramEngine
from .graph import normalize_graph, validate_graph
from .hit_test import AFFORDANCES, build_hit_index, snap_port_at
from .intent import classify_intent
from .layout import compute_layers
from .manual_layout import auto_spread_positions, ensure_positions, render_manual_diagram
from .mechanical import (
    HYBRID_FIXTURE,
    MECHANICAL_FIXTURE,
    render_hybrid_diagram,
    render_mechanical_diagram,
)
from .piping import PID_FIXTURE, PIPING_FIXTURE, render_piping_diagram
from .propose import (
    confirm_diagram,
    generate_diagram,
    list_diagram_templates,
    propose_diagram,
)
from .render_svg import (
    EXCAVATORBRAIN_FIXTURE,
    FIXTURE,
    RENSEANLEGG_FIXTURE,
    compute_graph_layout,
    render_block_diagram,
    svg_fingerprint,
)
from .symbols import get_symbol, list_symbols, load_symbols
from .visual_qa import visual_qa_engine, visual_qa_svg

__all__ = [
    "DiagramEngine",
    "DiagramCanvasEditor",
    "DiagramDocument",
    "render_block_diagram",
    "render_electrical_diagram",
    "render_piping_diagram",
    "render_mechanical_diagram",
    "render_hybrid_diagram",
    "render_manual_diagram",
    "ensure_positions",
    "auto_spread_positions",
    "normalize_graph",
    "validate_graph",
    "normalize_electrical_graph",
    "resolve_wire_color",
    "svg_fingerprint",
    "classify_intent",
    "compute_layers",
    "compute_graph_layout",
    "list_symbols",
    "get_symbol",
    "load_symbols",
    "propose_diagram",
    "confirm_diagram",
    "generate_diagram",
    "list_diagram_templates",
    "visual_qa_svg",
    "visual_qa_engine",
    "build_hit_index",
    "snap_port_at",
    "AFFORDANCES",
    "FIXTURE",
    "EXCAVATORBRAIN_FIXTURE",
    "RENSEANLEGG_FIXTURE",
    "SLD_FIXTURE",
    "WIRING_FIXTURE",
    "WATER_HEATER_240V_FIXTURE",
    "PIPING_FIXTURE",
    "PID_FIXTURE",
    "MECHANICAL_FIXTURE",
    "HYBRID_FIXTURE",
]
