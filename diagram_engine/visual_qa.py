"""Visual QA for deterministic engineering SVGs (print-safe, not photoreal).

Checks clarity rules: SVG present, min stroke, legend when connections
exist, tags/labels, margins, basic collision heuristics.
"""
from __future__ import annotations

import re
from typing import Any


def visual_qa_svg(
    svg: str,
    *,
    graph: dict | None = None,
    min_stroke: float = 1.0,
    require_legend: bool | None = None,
) -> dict[str, Any]:
    """Return {ok, issues[], checks{}}.

    issues severity: error | warn.
    """
    issues: list[dict] = []
    checks: dict[str, bool] = {}
    text = svg or ""

    checks["has_svg"] = "<svg" in text.lower()
    if not checks["has_svg"]:
        issues.append({"severity": "error", "code": "no_svg", "msg": "No SVG markup"})
        return {"ok": False, "issues": issues, "checks": checks}

    checks["has_viewbox"] = bool(re.search(r'viewBox\s*=', text, re.I))
    if not checks["has_viewbox"]:
        issues.append({"severity": "warn", "code": "no_viewbox", "msg": "Missing viewBox (print scaling)"})

    # Stroke weights
    strokes = [float(m) for m in re.findall(r'stroke-width\s*=\s*"([0-9.]+)"', text)]
    strokes += [float(m) for m in re.findall(r"stroke-width\s*:\s*([0-9.]+)", text)]
    if strokes:
        checks["min_stroke_ok"] = min(strokes) >= min_stroke - 1e-6
        if not checks["min_stroke_ok"]:
            issues.append({
                "severity": "warn",
                "code": "thin_stroke",
                "msg": f"Stroke below {min_stroke} (min found {min(strokes)})",
            })
    else:
        checks["min_stroke_ok"] = True

    # Legend
    has_legend = bool(re.search(
        r"(Wire colors|Pipe media|Connections|Drives|diagram-legend|wire-legend)",
        text, re.I,
    ))
    n_conn = len((graph or {}).get("connections") or []) if graph else 0
    # Heuristic: data-wire / data-connection / data-medium paths
    path_conn = len(re.findall(r"data-(?:wire|connection|medium)=", text))
    expect_legend = require_legend if require_legend is not None else (
        n_conn >= 2 or path_conn >= 2
    )
    checks["legend_present"] = has_legend or not expect_legend
    if expect_legend and not has_legend:
        issues.append({
            "severity": "warn",
            "code": "no_legend",
            "msg": "Connections present but no color/media legend",
        })

    # Tags / component labels
    has_tags = bool(re.search(r'data-component=', text)) or bool(
        re.search(r"font-weight=\"600\"", text)
    )
    checks["has_labels"] = has_tags
    if graph and (graph.get("components") or []) and not has_tags:
        issues.append({
            "severity": "warn",
            "code": "no_tags",
            "msg": "Graph has components but SVG lacks component markers/labels",
        })

    # Print margin: first rect background shouldn't be the only content;
    # prefer padding — check title text exists near top
    checks["has_title_band"] = bool(re.search(r"<text[^>]*y=\"2[0-9]\"", text))
    if not checks["has_title_band"]:
        issues.append({
            "severity": "warn",
            "code": "no_title_band",
            "msg": "No title text near top margin",
        })

    # Very rough label collision: many text elements with identical x,y
    coords = re.findall(
        r'<text[^>]*\bx="([0-9.]+)"[^>]*\by="([0-9.]+)"',
        text,
    )
    if len(coords) >= 4:
        from collections import Counter
        c = Counter((round(float(x), 0), round(float(y), 0)) for x, y in coords)
        collisions = sum(1 for _, n in c.items() if n > 1)
        checks["label_collision_ok"] = collisions == 0
        if collisions:
            issues.append({
                "severity": "warn",
                "code": "label_collision",
                "msg": f"{collisions} shared text coordinates (possible overlap)",
            })
    else:
        checks["label_collision_ok"] = True

    # Foldok markers
    checks["deterministic_marker"] = bool(re.search(
        r'data-foldok="(electrical_diagram|domain_diagram|connection_spec)"',
        text,
    )) or bool(re.search(r'data-graph=', text))

    errors = [i for i in issues if i["severity"] == "error"]
    return {
        "ok": len(errors) == 0,
        "issues": issues,
        "checks": checks,
        "n_issues": len(issues),
        "n_errors": len(errors),
    }


def visual_qa_engine(diagram_engine: Any) -> dict[str, Any]:
    """QA a DiagramEngine instance (render + optional graph)."""
    svg = diagram_engine.render_svg() if hasattr(diagram_engine, "render_svg") else str(diagram_engine)
    graph = getattr(diagram_engine, "spec", None) if hasattr(diagram_engine, "spec") else None
    return visual_qa_svg(svg, graph=graph if isinstance(graph, dict) else None)
