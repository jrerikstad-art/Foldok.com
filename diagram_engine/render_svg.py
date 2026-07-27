"""connection_spec → deterministic SVG block diagram.

CONTRACT: the model proposes the GRAPH (user confirms); THIS CODE draws.
Same input → byte-identical SVG. Provenance: extracted / user / reference.
Positions from LayeredGraphLayout (Sugiyama-style); pins + provenance intact.
"""
from __future__ import annotations

import hashlib
import re

from artifact_engine.layout.graph import LayeredGraphLayout

from .style import (
    BOX_H_BASE, BOX_W, COL_GAP, PAD, PIN_H, PROV, ROW_GAP,
    tokens_from_theme,
)

TITLE_BAND = 54
LEGEND_BAND = 40


def _escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _norm_prov(p) -> str:
    p = (p or "reference").strip().lower()
    if p in ("verified_by_user", "user", "confirmed"):
        return "user"
    if p in ("extracted", "cited", "sitert"):
        return "extracted"
    return "reference"


def _label_lines(label: str) -> list:
    """D3 — flatten embedded newlines to a second SVG text line."""
    raw = (label or "").replace("\\n", "\n")
    parts = [ln.strip() for ln in re.split(r"[\n\r]+", raw) if ln.strip()]
    return parts or [""]


def _node_height(n: dict) -> float:
    label_extra = max(0, len(_label_lines(n.get("label") or "")) - 1) * 12
    return float(BOX_H_BASE + PIN_H * len(n.get("pins") or []) + label_extra)


def _default_orientation(kind: str) -> str:
    if kind in ("process",):
        return "TB"
    return "LR"


def compute_graph_layout(
    spec: dict,
    *,
    kind: str = "wiring",
    orientation: str | None = None,
) -> tuple[dict, dict, dict, float, float]:
    """
    Returns (nodes_by_id, pos{id:(x,y)}, heights, width, height).
    Uses LayeredGraphLayout; falls back to empty if no components.
    """
    comps = [c for c in (spec.get("components") or []) if c.get("id") or c.get("name")]
    nodes = {}
    layout_nodes = []
    for c in comps:
        cid = c.get("id") or c.get("name")
        nodes[cid] = c
        layout_nodes.append({
            "id": cid,
            "name": cid,
            "label": c.get("label") or cid,
            "width": BOX_W,
            "height": _node_height(c),
            "type": c.get("type") or c.get("role") or "component",
        })

    if not layout_nodes:
        return {}, {}, {}, 400.0, 200.0

    orient = (orientation or _default_orientation(kind)).upper()
    if orient not in ("TB", "LR"):
        orient = "LR"

    if orient == "LR":
        rank_sep, node_sep = float(COL_GAP), float(ROW_GAP)
    else:
        rank_sep, node_sep = float(ROW_GAP + 46), float(COL_GAP * 0.45)

    engine = LayeredGraphLayout(
        node_width=float(BOX_W),
        node_height=float(BOX_H_BASE),
        rank_sep=rank_sep,
        node_sep=node_sep,
        margin=float(PAD),
        orientation=orient,
    )
    result = engine.layout(layout_nodes, list(spec.get("connections") or []))

    pos = {n.id: (n.x, n.y + TITLE_BAND) for n in result.nodes}
    heights = {n.id: n.height for n in result.nodes}
    W = max(result.width, 400.0)
    H = max(result.height + TITLE_BAND + LEGEND_BAND, 200.0)
    return nodes, pos, heights, W, H


def render_block_diagram(
    spec,
    title=None,
    *,
    kind: str | None = None,
    theme=None,
    orientation: str | None = None,
):
    """
    Draw SVG. kind tags intent (wiring|power|signal|process|star|overview).
    Positions from LayeredGraphLayout. Provenance edge colors unchanged.
    """
    kind = kind or "wiring"
    tok = tokens_from_theme(theme)
    ink, paper, sheet = tok["ink"], tok["paper"], tok["sheet"]
    signal, steel, line = tok["signal"], tok["steel"], tok["line"]
    font = tok["font"]

    nodes, pos, heights, W, H = compute_graph_layout(
        spec, kind=kind, orientation=orientation,
    )

    def pin_y(cid, pin):
        pins = nodes[cid].get("pins", [])
        i = pins.index(pin) if pin in pins else -1
        _x, y = pos[cid]
        return y + BOX_H_BASE - 8 + (i + 1) * PIN_H if i >= 0 else y + heights[cid] / 2

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="{_escape(font)}" data-foldok="connection_spec" '
        f'data-layout="{_escape(kind)}" data-graph="layered">',
        f'<rect width="{W}" height="{H}" fill="{paper}"/>',
    ]
    if title:
        s.append(
            f'<text x="{PAD}" y="{PAD + 6}" font-size="17" font-weight="800" '
            f'fill="{ink}">{_escape(title)}</text>'
        )
        s.append(
            f'<rect x="{PAD}" y="{PAD + 14}" width="150" height="4" fill="{signal}"/>'
        )

    for e in spec.get("connections") or []:
        a, ap = (e["from"].split(".") + [""])[:2]
        b, bp = (e["to"].split(".") + [""])[:2]
        if a not in pos or b not in pos:
            continue
        x1 = pos[a][0] + BOX_W
        y1 = pin_y(a, ap)
        x2 = pos[b][0]
        y2 = pin_y(b, bp)
        if x2 + BOX_W / 2 < pos[a][0] + BOX_W / 2:
            x1 = pos[a][0]
            x2 = pos[b][0] + BOX_W
        mx = (x1 + x2) / 2
        prov = _norm_prov(e.get("provenance"))
        color, dash = PROV.get(prov, PROV["reference"])
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s.append(
            f'<path d="M{x1},{y1} L{mx},{y1} L{mx},{y2} L{x2},{y2}" '
            f'fill="none" stroke="{color}" stroke-width="2"{d} '
            f'data-from="{_escape(e.get("from"))}" data-to="{_escape(e.get("to"))}" '
            f'data-provenance="{prov}" '
            f'data-fact-id="{_escape(str(e.get("fact_id") or ""))}"/>'
        )
        s.append(f'<circle cx="{x2}" cy="{y2}" r="3.4" fill="{color}"/>')
        lbl_lines = _label_lines(e.get("label") or "")
        base_y = min(y1, y2) + abs(y2 - y1) / 2 - 5
        for li, ln in enumerate(lbl_lines):
            s.append(
                f'<text x="{mx}" y="{base_y + li * 11}" '
                f'font-size="10" font-weight="700" fill="{color}" '
                f'text-anchor="middle">{_escape(ln)}</text>'
            )

    for cid, (x, y) in sorted(pos.items()):
        n, h = nodes[cid], heights[cid]
        s.append(
            f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{h}" rx="8" '
            f'fill="{sheet}" stroke="{line}" data-component="{_escape(cid)}"/>'
        )
        s.append(
            f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="2" fill="{signal}"/>'
        )
        lines = _label_lines(n.get("label") or cid)
        for li, ln in enumerate(lines):
            s.append(
                f'<text x="{x + 14}" y="{y + 22 + li * 12}" font-size="12.5" '
                f'font-weight="800" fill="{ink}">{_escape(ln)}</text>'
            )
        label_extra = max(0, len(lines) - 1) * 12
        if n.get("image"):
            s.append(
                f'<text x="{x + 14}" y="{y + 37 + label_extra}" font-size="8.5" '
                f'fill="{steel}">{_escape(str(n["image"]))}</text>'
            )
        for i, p in enumerate(n.get("pins", [])):
            s.append(
                f'<text x="{x + 14}" '
                f'y="{y + BOX_H_BASE - 4 + label_extra + (i + 1) * PIN_H}" '
                f'font-size="9.5" font-family="monospace" fill="{steel}">'
                f'▸ {_escape(p)}</text>'
            )

    ly = H - 26
    s.append(
        f'<text x="{PAD}" y="{ly}" font-size="10" font-weight="700" '
        f'fill="{steel}">Kanter:</text>'
    )
    for i, (name, key) in enumerate([
        ("sitert fra kilde", "extracted"),
        ("bekreftet av bruker", "user"),
        ("AI-foreslått — verifiser", "reference"),
    ]):
        color, dash = PROV[key]
        x0 = PAD + 60 + i * 190
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s.append(
            f'<line x1="{x0}" y1="{ly - 4}" x2="{x0 + 26}" y2="{ly - 4}" '
            f'stroke="{color}" stroke-width="2"{d}/>'
        )
        s.append(
            f'<text x="{x0 + 32}" y="{ly}" font-size="10" fill="{ink}">{name}</text>'
        )
    s.append("</svg>")
    return "\n".join(s)


def svg_fingerprint(svg: str) -> str:
    return hashlib.sha256((svg or "").encode("utf-8")).hexdigest()


EXCAVATORBRAIN_FIXTURE = {
    "components": [
        {"id": "lipo", "label": "7,4V LiPo-batteri", "pins": ["+7,4V", "GND"],
         "image": "20260622_202841.jpg"},
        {"id": "fuse", "label": "3A polyfuse", "pins": ["inn", "ut"]},
        {"id": "buck", "label": "Pololu D24V50F5 (5V/5A)", "pins": ["VIN", "VOUT 5V", "GND"],
         "image": "20260612_124408.jpg"},
        {"id": "pi5", "label": "Raspberry Pi 5",
         "pins": ["5V", "GPIO2/SDA (pin 3)", "GPIO3/SCL (pin 5)", "CSI-2", "GND"],
         "image": "20260605_140447.jpg"},
        {"id": "cam", "label": "Pi Camera Module 3", "pins": ["CSI"]},
        {"id": "pca", "label": "PCA9685 PWM (I2C 0x40)",
         "pins": ["VCC 5V", "SDA", "SCL", "CH0–CH5"], "image": "20260615_124715.jpg"},
        {"id": "shift", "label": "BSS138 nivåskiftere", "pins": ["HV 5V", "LV 3,3V", "A1–A6"],
         "image": "20260612_124415.jpg"},
        {"id": "rc", "label": "RC-mottaker TL-HUINA S4G", "pins": ["CH1–CH6", "5V"]},
        {"id": "srv", "label": "Servoer ×6 (lift/reach/grab/rot/L/R)", "pins": ["PWM inn"]},
    ],
    "connections": [
        {"from": "lipo.+7,4V", "to": "fuse.inn", "label": "7,4V", "provenance": "extracted"},
        {"from": "fuse.ut", "to": "buck.VIN", "label": "7,4V", "provenance": "extracted"},
        {"from": "buck.VOUT 5V", "to": "pi5.5V", "label": "5V", "provenance": "user"},
        {"from": "buck.VOUT 5V", "to": "pca.VCC 5V", "label": "5V", "provenance": "user"},
        {"from": "pi5.GPIO2/SDA (pin 3)", "to": "pca.SDA", "label": "I2C SDA",
         "provenance": "reference"},
        {"from": "pi5.GPIO3/SCL (pin 5)", "to": "pca.SCL", "label": "I2C SCL",
         "provenance": "reference"},
        {"from": "cam.CSI", "to": "pi5.CSI-2", "label": "CSI-2", "provenance": "extracted"},
        {"from": "rc.CH1–CH6", "to": "shift.A1–A6", "label": "6 kanaler 5V",
         "provenance": "reference"},
        {"from": "shift.LV 3,3V", "to": "pca.CH0–CH5", "label": "3,3V logikk",
         "provenance": "reference"},
        {"from": "pca.CH0–CH5", "to": "srv.PWM inn", "label": "PWM 50 Hz",
         "provenance": "user"},
    ],
}

RENSEANLEGG_FIXTURE = {
    "components": [
        {"id": "inlet", "label": "Innkommende\\navløpsvann", "pins": ["ut"]},
        {"id": "screen", "label": "Rist / sil", "pins": ["inn", "ut"]},
        {"id": "eq", "label": "Utligningsbasseng", "pins": ["inn", "ut"]},
        {"id": "bio", "label": "Biologisk trinn\\n(integrert modul)",
         "pins": ["inn", "ut", "slam"]},
        {"id": "settle", "label": "Sedimentering", "pins": ["inn", "klarvann", "slam"]},
        {"id": "out", "label": "Utløp til resipient", "pins": ["inn"]},
        {"id": "sludge", "label": "Slamhåndtering", "pins": ["inn"]},
    ],
    "connections": [
        {"from": "inlet.ut", "to": "screen.inn", "label": "råvann", "provenance": "extracted"},
        {"from": "screen.ut", "to": "eq.inn", "label": "silstrøm", "provenance": "extracted"},
        {"from": "eq.ut", "to": "bio.inn", "label": "jevn tilførsel", "provenance": "reference"},
        {"from": "bio.ut", "to": "settle.inn", "label": "biomasse", "provenance": "reference"},
        {"from": "settle.klarvann", "to": "out.inn", "label": "klarvann",
         "provenance": "extracted"},
        {"from": "bio.slam", "to": "sludge.inn", "label": "overskuddsslam",
         "provenance": "reference"},
        {"from": "settle.slam", "to": "sludge.inn", "label": "bunnslam",
         "provenance": "reference"},
    ],
}

FIXTURE = EXCAVATORBRAIN_FIXTURE
