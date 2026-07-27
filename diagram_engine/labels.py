"""Deterministic component label placement from DiagramStyle rules.

Never changes connectivity — only label anchors / optional leader lines.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .graph import SYM_H, SYM_W


@dataclass
class LabelBox:
    x: float  # center x of text
    y: float  # baseline-ish y used for SVG text
    w: float
    h: float
    side: str
    offset: bool = False  # True when forced out with leader
    hidden: bool = False

    @property
    def left(self) -> float:
        return self.x - self.w / 2

    @property
    def right(self) -> float:
        return self.x + self.w / 2

    @property
    def top(self) -> float:
        return self.y - self.h

    @property
    def bottom(self) -> float:
        return self.y


def _estimate_size(text: str, style: Any) -> tuple[float, float]:
    L = style.labels
    char_w = max(4.0, L.tag_size * 0.55)
    w = min(float(L.max_width), max(12.0, len(text or "") * char_w))
    h = float(L.tag_size) + float(L.padding) * 2
    return w, h


def _candidate(
    cx: float, cy: float, w: float, h: float, side: str, gap: float, *, offset: float = 0.0,
) -> LabelBox:
    half_w, half_h = SYM_W / 2, SYM_H / 2
    if side == "above":
        return LabelBox(cx + offset, cy - half_h - gap - h * 0.25, w, h, side, offset=bool(offset))
    if side == "below":
        return LabelBox(cx + offset, cy + half_h + gap + h * 0.75, w, h, side, offset=bool(offset))
    if side == "left":
        return LabelBox(cx - half_w - gap - w / 2, cy + h * 0.25 + offset, w, h, side, offset=bool(offset))
    # right
    return LabelBox(cx + half_w + gap + w / 2, cy + h * 0.25 + offset, w, h, side, offset=bool(offset))


def _intersects(a: LabelBox, b: LabelBox, pad: float) -> bool:
    return not (
        a.right + pad < b.left
        or a.left - pad > b.right
        or a.bottom + pad < b.top
        or a.top - pad > b.bottom
    )


def _hits_symbol(box: LabelBox, cx: float, cy: float, pad: float) -> bool:
    left, right = cx - SYM_W / 2 - pad, cx + SYM_W / 2 + pad
    top, bottom = cy - SYM_H / 2 - pad, cy + SYM_H / 2 + pad
    return not (box.right < left or box.left > right or box.bottom < top or box.top > bottom)


def place_component_label(
    text: str,
    cx: float,
    cy: float,
    style: Any,
    *,
    occupied: Iterable[LabelBox] | None = None,
    symbol_centers: Iterable[tuple[float, float]] | None = None,
) -> LabelBox:
    """Try preferred → right → left → below; then offset with leader flag."""
    preferred = style.label_preferred() if hasattr(style, "label_preferred") else "above"
    order = [preferred] + [s for s in ("above", "right", "left", "below") if s != preferred]
    w, h = _estimate_size(text, style)
    gap = float(style.gaps.min_label if hasattr(style, "gaps") else style.grid.min_label_gap)
    pad = float(style.labels.padding)
    occupied_list = list(occupied or [])
    symbols = list(symbol_centers or [(cx, cy)])

    def ok(box: LabelBox) -> bool:
        for scx, scy in symbols:
            if _hits_symbol(box, scx, scy, pad):
                return False
        for other in occupied_list:
            if _intersects(box, other, gap):
                return False
        return True

    for side in order:
        box = _candidate(cx, cy, w, h, side, gap)
        if ok(box):
            return box

    # Offset pass on preferred side
    for delta in (16.0, 28.0, -16.0, -28.0, 40.0, -40.0):
        box = _candidate(cx, cy, w, h, preferred, gap, offset=delta)
        box.offset = True
        if ok(box):
            return box

    # Last resort
    box = _candidate(cx, cy, w, h, preferred, gap, offset=48.0)
    box.offset = True
    if style.labels.hide_if_overlap:
        box.hidden = True
    return box


def label_svg(
    text: str,
    box: LabelBox,
    style: Any,
    *,
    symbol_xy: tuple[float, float] | None = None,
    paint_attrs: str = "",
) -> str:
    if box.hidden or not text:
        return ""
    from .paint import esc

    parts = []
    if box.offset and style.labels.leader_when_offset and symbol_xy:
        sx, sy = symbol_xy
        # Short leader from symbol top/side toward label
        parts.append(
            f'<line x1="{sx:.1f}" y1="{sy - SYM_H/2:.1f}" x2="{box.x:.1f}" y2="{box.y:.1f}" '
            f'stroke="{esc(style.colors.muted)}" stroke-width="{style.labels.leader_stroke}" '
            f'data-leader="1"/>'
        )
    attrs = paint_attrs or (
        f'font-family="{esc(style.labels.font)}" font-size="{style.labels.tag_size}" '
        f'font-weight="{style.labels.tag_weight}" fill="{esc(style.labels.color)}"'
    )
    parts.append(
        f'<text x="{box.x:.1f}" y="{box.y:.1f}" text-anchor="middle" {attrs}>'
        f'{esc(str(text))}</text>'
    )
    return "\n".join(parts)
