"""Diagram intent — what the user wants to show (not how to draw it)."""
from __future__ import annotations

import re

KINDS = ("wiring", "power", "signal", "process", "star", "overview")

POWER_RE = re.compile(
    r"\b(power|strøm|spenning|forsyning|batteri|battery|vin|vout|gnd|lipo)\b", re.I)
SIGNAL_RE = re.compile(
    r"\b(signal|i2c|spi|uart|gpio|pwm|csi|can|bus|data)\b", re.I)
PROCESS_RE = re.compile(
    r"(process|prosess|flow|flyt|funksjon|renseanlegg|rense|pipeline|trinn|"
    r"inlet|outlet|avløp)",
    re.I)

STAR_RE = re.compile(
    r"\b(star|hub|sentral|overview|oversikt|system\s*overview)\b", re.I)
WIRING_RE = re.compile(
    r"\b(wiring|kobling|tilkobling|schematic|blokk|block\s*diagram)\b", re.I)


def _endpoint_component(ep) -> str:
    """Support 'a.b' strings and {component_id, port_id} dicts."""
    if isinstance(ep, dict):
        return str(ep.get("component_id") or ep.get("component") or ep.get("id") or "")
    if isinstance(ep, str):
        return ep.split(".", 1)[0] if ep else ""
    return ""


def classify_intent(
    *,
    ask: str = "",
    title: str = "",
    artifact: dict | None = None,
    spec: dict | None = None,
) -> dict:
    """
    Returns {kind, focus: list[str], reason}.
    kind drives layout; never invents components.
    """
    art = artifact or {}
    blob = " ".join([
        ask or "",
        title or "",
        art.get("title") or "",
        art.get("purpose") or "",
        art.get("name") or "",
        " ".join(art.get("tags") or []) if isinstance(art.get("tags"), list) else "",
    ])
    # Edge-label hint from existing graph
    if spec:
        labels = " ".join(
            (e.get("label") or "")
            or ((e.get("attributes") or {}).get("designation") or "")
            for e in (spec.get("connections") or [])
        )
        blob = f"{blob} {labels}"
        # Domain diagram types skip block-intent heuristics
        t = (spec.get("type") or "").lower().replace("-", "_")
        if t in ("single_line", "sld", "wiring", "piping", "pid", "mechanical", "hybrid"):
            # Only treat as domain profile when domain/symbols say so —
            # bare type=wiring on block diagrams still uses heuristics below
            # unless domain is set.
            domain = (spec.get("domain") or "").lower()
            if domain or t in ("single_line", "sld", "piping", "pid", "mechanical", "hybrid"):
                mapped = {
                    "single_line": "power", "sld": "power",
                    "wiring": "wiring",
                    "piping": "process", "pid": "process",
                    "mechanical": "overview", "hybrid": "overview",
                }
                return {
                    "kind": mapped.get(t, "wiring"),
                    "focus": [],
                    "reason": f"diagram type {t}",
                }

    if PROCESS_RE.search(blob):
        kind, reason = "process", "process/flow language"
    elif POWER_RE.search(blob) and not SIGNAL_RE.search(blob):
        kind, reason = "power", "power path"
    elif SIGNAL_RE.search(blob) and not POWER_RE.search(blob):
        kind, reason = "signal", "signal path"
    elif STAR_RE.search(blob):
        kind, reason = "star", "hub/overview"
    elif WIRING_RE.search(blob):
        kind, reason = "wiring", "wiring/block ask"
    else:
        # Heuristic from graph shape
        kind, reason = _kind_from_graph(spec), "graph heuristic"

    focus = _focus_ids(kind, spec)
    return {"kind": kind, "focus": focus, "reason": reason}


def _kind_from_graph(spec: dict | None) -> str:
    if not spec:
        return "wiring"
    comps = spec.get("components") or []
    edges = spec.get("connections") or []
    if not edges:
        return "overview"
    # Long chain + few branches → process
    ids = {c["id"] for c in comps if c.get("id")}
    out_deg = {i: 0 for i in ids}
    in_deg = {i: 0 for i in ids}
    for e in edges:
        a = _endpoint_component(e.get("from"))
        b = _endpoint_component(e.get("to"))
        if a in out_deg:
            out_deg[a] += 1
        if b in in_deg:
            in_deg[b] += 1
    hubs = [i for i in ids if out_deg[i] + in_deg[i] >= 4]
    if len(hubs) == 1 and len(edges) >= 4:
        return "star"
    chainish = sum(1 for i in ids if out_deg[i] <= 1 and in_deg[i] <= 1)
    if chainish >= max(3, len(ids) - 1):
        return "process"
    return "wiring"


def _focus_ids(kind: str, spec: dict | None) -> list:
    if not spec:
        return []
    edges = spec.get("connections") or []
    if kind == "power":
        return [
            _endpoint_component(e.get("from"))
            for e in edges
            if POWER_RE.search(e.get("label") or "")
        ]
    if kind == "signal":
        return [
            _endpoint_component(e.get("from"))
            for e in edges
            if SIGNAL_RE.search(e.get("label") or "")
        ]
    return []
