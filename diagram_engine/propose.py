"""Propose / confirm diagram tools — AI may propose graph; engine draws SVG.

Templates give a low skill barrier (Visoid-like UX, deterministic geometry).
User must confirm before document insert.
"""
from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from .electrical import SLD_FIXTURE, WIRING_FIXTURE, render_electrical_diagram
from .engine import DiagramEngine
from .graph import normalize_graph, validate_graph
from .mechanical import HYBRID_FIXTURE, MECHANICAL_FIXTURE, render_hybrid_diagram, render_mechanical_diagram
from .piping import PIPING_FIXTURE, render_piping_diagram
from .visual_qa import visual_qa_svg

# Product templates — pick profile, edit graph, re-render in seconds
TEMPLATES: dict[str, dict[str, Any]] = {
    "panel_sld": {
        "label": "Panel single-line diagram",
        "profile": "single_line",
        "fixture": SLD_FIXTURE,
    },
    "cable_wiring": {
        "label": "Terminal / cable wiring",
        "profile": "wiring",
        "fixture": WIRING_FIXTURE,
    },
    "pipe_run": {
        "label": "Piping schematic",
        "profile": "piping",
        "fixture": PIPING_FIXTURE,
    },
    "drive_train": {
        "label": "Motor–pump–gear arrangement",
        "profile": "mechanical",
        "fixture": MECHANICAL_FIXTURE,
    },
    "pump_skid": {
        "label": "Pump skid hybrid overview",
        "profile": "hybrid",
        "fixture": HYBRID_FIXTURE,
    },
}


def list_diagram_templates() -> list[dict]:
    return [
        {"id": tid, "label": meta["label"], "profile": meta["profile"]}
        for tid, meta in TEMPLATES.items()
    ]


def propose_diagram(
    *,
    template: str | None = None,
    profile: str | None = None,
    graph: dict | None = None,
    title: str | None = None,
    description: str | None = None,
    section_id: str | None = None,
) -> dict[str, Any]:
    """Build a diagram proposal (graph + preview SVG). Does not insert into docs.

    Returns status=proposed — caller must confirm_diagram before embed.
    """
    proposal_id = f"diag_{uuid.uuid4().hex[:10]}"
    tmpl = TEMPLATES.get(template or "")
    if graph:
        g = normalize_graph(deepcopy(graph))
        prof = profile or g.get("type") or (tmpl or {}).get("profile") or "piping"
    elif tmpl:
        g = normalize_graph(deepcopy(tmpl["fixture"]))
        prof = profile or tmpl["profile"]
    elif profile in ("single_line", "wiring", "piping", "mechanical", "hybrid", "pid"):
        # Map profile → default fixture
        fallback = {
            "single_line": SLD_FIXTURE,
            "wiring": WIRING_FIXTURE,
            "piping": PIPING_FIXTURE,
            "pid": PIPING_FIXTURE,
            "mechanical": MECHANICAL_FIXTURE,
            "hybrid": HYBRID_FIXTURE,
        }[profile]
        g = normalize_graph(deepcopy(fallback))
        if profile == "pid":
            g["type"] = "pid"
        prof = profile
    else:
        return {
            "status": "error",
            "error": "Provide template=, profile=, or graph=",
            "templates": list_diagram_templates(),
        }

    if title:
        g["title"] = title
    elif description and not g.get("title"):
        g["title"] = description[:80]

    violations = validate_graph(g)
    svg = _render_profile(g, prof)
    qa = visual_qa_svg(svg, graph=g)

    return {
        "status": "proposed",
        "proposal_id": proposal_id,
        "section_id": section_id,
        "profile": prof,
        "template": template,
        "title": g.get("title") or title or "Diagram",
        "graph": g,
        "svg_preview": svg,
        "validation": {"ok": not violations, "violations": violations},
        "visual_qa": qa,
        "confirm_required": True,
        "note": "User must confirm before insert — engine owns geometry, not the model.",
    }


def confirm_diagram(
    proposal: dict,
    *,
    confirm: bool = True,
    graph_overrides: dict | None = None,
) -> dict[str, Any]:
    """Accept a proposal → final SVG + DiagramBlock-ready payload."""
    if not confirm:
        return {"status": "rejected", "proposal_id": proposal.get("proposal_id")}
    if (proposal or {}).get("status") != "proposed":
        return {"status": "error", "error": "Not a proposed diagram"}

    g = deepcopy(proposal.get("graph") or {})
    if graph_overrides:
        # Shallow merge components/connections if provided
        for k, v in graph_overrides.items():
            if k in ("components", "connections") and isinstance(v, list):
                g[k] = v
            else:
                g[k] = v
        g = normalize_graph(g)

    prof = proposal.get("profile") or g.get("type") or "piping"
    violations = validate_graph(g)
    if violations:
        return {
            "status": "error",
            "error": "Graph validation failed",
            "violations": violations,
            "proposal_id": proposal.get("proposal_id"),
        }

    svg = _render_profile(g, prof)
    qa = visual_qa_svg(svg, graph=g)
    eng = DiagramEngine().load_spec(g, title=g.get("title") or proposal.get("title"))
    return {
        "status": "confirmed",
        "proposal_id": proposal.get("proposal_id"),
        "section_id": proposal.get("section_id"),
        "profile": prof,
        "title": eng.title,
        "graph": g,
        "svg": svg,
        "visual_qa": qa,
        "diagram_block": {
            "type": "diagram",
            "svg": svg,
            "title": eng.title,
            "caption": eng.title,
            "diagram_type": prof,
            "graph_id": g.get("id") or proposal.get("proposal_id"),
            "height_pt": 260.0,
        },
        "ready_to_embed": True,
    }


def generate_diagram(
    template: str | None = None,
    *,
    profile: str | None = None,
    graph: dict | None = None,
    title: str | None = None,
    auto_confirm: bool = False,
) -> dict[str, Any]:
    """Convenience: propose (and optionally confirm) in one call.

    auto_confirm=False by default — keep the trust gate.
    """
    prop = propose_diagram(template=template, profile=profile, graph=graph, title=title)
    if prop.get("status") != "proposed":
        return prop
    if not auto_confirm:
        return prop
    return confirm_diagram(prop, confirm=True)


def _render_profile(g: dict, profile: str) -> str:
    p = (profile or "").lower()
    if p in ("single_line", "sld", "wiring"):
        return render_electrical_diagram(g, mode="wiring" if p == "wiring" else "single_line")
    if p in ("piping", "pid"):
        return render_piping_diagram(g, mode=p)
    if p == "mechanical":
        return render_mechanical_diagram(g, mode=p)
    if p == "hybrid":
        return render_hybrid_diagram(g)
    # Fallback: try DiagramEngine routing
    return DiagramEngine().load_spec(g).render_svg()
