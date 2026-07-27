"""Layout strategies — place nodes; never invent edges."""
from __future__ import annotations

import re

POWER_EDGE = re.compile(
    r"\b(v\+?|vin|vout|gnd|ground|5v|3,?\s*3v|7,?\s*4v|12v|24v|power|strøm)\b",
    re.I,
)
SIGNAL_EDGE = re.compile(
    r"\b(i2c|sda|scl|spi|uart|gpio|pwm|csi|can|signal|data)\b", re.I,
)


def compute_layers(spec: dict, *, kind: str = "wiring") -> tuple[dict, dict]:
    """
    Returns (nodes_by_id, columns: {layer_int: [ids]}).
    kind: wiring|power|signal|process|star|overview
    """
    nodes = {c["id"]: c for c in (spec.get("components") or []) if c.get("id")}
    if not nodes:
        return {}, {}

    if kind == "star":
        return nodes, _star_columns(nodes, spec)
    if kind == "overview" and not (spec.get("connections") or []):
        return nodes, _grid_columns(nodes)

    # Weighted topological layering
    weight = _edge_weight_fn(kind)
    layer = {i: 0 for i in nodes}
    # Seed: power sources / inlets at 0
    for cid, n in nodes.items():
        role = (n.get("role") or n.get("type") or "").lower()
        if role in ("power", "source", "inlet") or cid in ("lipo", "batt", "inlet"):
            layer[cid] = 0

    edges = spec.get("connections") or []
    for _ in range(len(nodes) + 2):
        changed = False
        for e in edges:
            a = (e.get("from") or "").split(".")[0]
            b = (e.get("to") or "").split(".")[0]
            if a not in nodes or b not in nodes or a == b:
                continue
            step = weight(e)
            if layer[b] < layer[a] + step:
                layer[b] = layer[a] + step
                changed = True
        if not changed:
            break

    # Compress layer numbers to 0..n contiguous
    ranks = sorted(set(layer.values()))
    remap = {r: i for i, r in enumerate(ranks)}
    layer = {k: remap[v] for k, v in layer.items()}

    cols: dict[int, list] = {}
    for cid in sorted(nodes, key=lambda x: (layer[x], x)):
        cols.setdefault(layer[cid], []).append(cid)

    # Within column: prefer focus / role order
    role_rank = {
        "power": 0, "converter": 1, "logic": 2, "peripheral": 3,
        "actuator": 4, "process": 2, "other": 5,
    }
    for c, ids in cols.items():
        cols[c] = sorted(
            ids,
            key=lambda i: (
                role_rank.get((nodes[i].get("role") or nodes[i].get("type") or "other").lower(), 5),
                i,
            ),
        )
    return nodes, cols


def _edge_weight_fn(kind: str):
    def w(e: dict) -> int:
        lab = e.get("label") or ""
        if kind == "power":
            return 1 if POWER_EDGE.search(lab) else 2
        if kind == "signal":
            return 1 if SIGNAL_EDGE.search(lab) else 2
        if kind == "process":
            return 1
        return 1
    return w


def _star_columns(nodes: dict, spec: dict) -> dict:
    edges = spec.get("connections") or []
    deg = {i: 0 for i in nodes}
    for e in edges:
        a = (e.get("from") or "").split(".")[0]
        b = (e.get("to") or "").split(".")[0]
        if a in deg:
            deg[a] += 1
        if b in deg:
            deg[b] += 1
    hub = max(deg, key=lambda i: (deg[i], i)) if deg else next(iter(nodes))
    spoke = [i for i in sorted(nodes) if i != hub]
    mid = max(1, len(spoke) // 2)
    left, right = spoke[:mid], spoke[mid:]
    cols = {0: left, 1: [hub], 2: right}
    return {k: v for k, v in cols.items() if v}


def _grid_columns(nodes: dict) -> dict:
    ids = sorted(nodes)
    cols: dict[int, list] = {}
    per = max(1, (len(ids) + 2) // 3)
    for i, cid in enumerate(ids):
        cols.setdefault(i // per, []).append(cid)
    return cols
