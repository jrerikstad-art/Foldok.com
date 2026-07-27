"""Print parity, as a test rather than a habit.

EDITOR_SPEC §6 says: "Weekly check: export the demo doc, hold it next to the
canvas. If they diverge, the canvas lies."  That is a good rule and a bad
mechanism — it finds the divergence a week late, by eye, on one document.

The mechanism here is that both sides consume the *same* Geometry object.  The
canvas draws ``geometry.to_dict()``; the renderer places from the same boxes.
Parity then is not something to maintain, it is something to assert:

    fingerprint(geometry_from_canvas) == fingerprint(geometry_from_renderer)

``check_layout_tree`` adapts artifact_engine's LayoutTree so the assertion can
run against the real PDF path in CI, on every document in the fixture set,
rather than on one demo once a week.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .model import Geometry, PlacedBox

TOLERANCE_PT = 0.5           # half a point: below the resolution of any printer


@dataclass
class Mismatch:
    block_id: str
    field: str
    canvas: Any
    renderer: Any

    def __str__(self) -> str:
        return f"{self.block_id}.{self.field}: canvas {self.canvas} vs renderer {self.renderer}"


@dataclass
class ParityReport:
    mismatches: list[Mismatch]
    missing_in_renderer: list[str]
    missing_in_canvas: list[str]

    @property
    def ok(self) -> bool:
        return not (self.mismatches or self.missing_in_renderer or self.missing_in_canvas)

    def __str__(self) -> str:
        if self.ok:
            return "parity ok"
        lines = ["PARITY BROKEN — the canvas is showing something the PDF will not print"]
        lines += [f"  {m}" for m in self.mismatches[:40]]
        if self.missing_in_renderer:
            lines.append(f"  only on canvas: {', '.join(self.missing_in_renderer[:10])}")
        if self.missing_in_canvas:
            lines.append(f"  only in PDF: {', '.join(self.missing_in_canvas[:10])}")
        return "\n".join(lines)


def payload(geometry: Geometry) -> dict[str, Any]:
    """The one wire format.  Canvas and renderer both take this and nothing else."""
    return geometry.to_dict()


def fingerprint(geometry: Geometry) -> str:
    """Stable hash of the geometry.  A golden test on this catches any drift in
    the solver, the grid, or the pin resolution, in one assertion."""
    blob = json.dumps(
        [b.to_dict() for b in sorted(geometry.boxes, key=lambda b: (b.page, b.y, b.col, b.block_id))],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def compare(
    canvas: Sequence[PlacedBox] | Geometry,
    renderer: Sequence[PlacedBox] | Geometry,
    tolerance: float = TOLERANCE_PT,
) -> ParityReport:
    a = {b.block_id: b for b in (canvas.boxes if isinstance(canvas, Geometry) else canvas)}
    b = {x.block_id: x for x in (renderer.boxes if isinstance(renderer, Geometry) else renderer)}

    mismatches: list[Mismatch] = []
    for block_id in sorted(set(a) & set(b)):
        left, right = a[block_id], b[block_id]
        if left.page != right.page:
            mismatches.append(Mismatch(block_id, "page", left.page, right.page))
        for field in ("x", "y", "width", "height"):
            lv, rv = getattr(left, field), getattr(right, field)
            if abs(lv - rv) > tolerance:
                mismatches.append(Mismatch(block_id, field, round(lv, 2), round(rv, 2)))
    return ParityReport(
        mismatches=mismatches,
        missing_in_renderer=sorted(set(a) - set(b)),
        missing_in_canvas=sorted(set(b) - set(a)),
    )


def boxes_from_layout_tree(tree: Any) -> list[PlacedBox]:
    """Adapter for artifact_engine's LayoutTree.

    Kept deliberately forgiving about attribute names: the point is to make the
    parity assertion runnable against the real renderer today, not to freeze the
    tree's shape.  If the tree changes, this adapter is the one place to fix.
    """
    out: list[PlacedBox] = []
    for page_no, page in enumerate(_iter(tree, "pages"), start=1):
        for node in _walk(page):
            block_id = _get(node, "block_id", "id", "source_id")
            if not block_id:
                continue
            frame = _get(node, "frame", "rect", "box") or node
            x = _num(_get(frame, "x", "left"))
            y = _num(_get(frame, "y", "top"))
            w = _num(_get(frame, "width", "w"))
            h = _num(_get(frame, "height", "h"))
            if w <= 0 or h <= 0:
                continue
            out.append(
                PlacedBox(
                    block_id=str(block_id), page=int(_num(_get(node, "page")) or page_no),
                    row=0, col=0, span=0, rows=0,
                    x=x, y=y, width=w, height=h,
                    role=str(_get(node, "role", "kind", "type") or "text"),
                )
            )
    return out


def check_layout_tree(geometry: Geometry, tree: Any, tolerance: float = TOLERANCE_PT) -> ParityReport:
    return compare(geometry, boxes_from_layout_tree(tree), tolerance)


# ----------------------------------------------------------------------
def _iter(obj: Any, *names: str) -> Iterable[Any]:
    for name in names:
        value = _get(obj, name)
        if value:
            return value
    return []


def _get(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _walk(node: Any) -> Iterable[Any]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        for key in ("children", "nodes", "items", "components", "regions", "containers"):
            kids = _get(current, key)
            if isinstance(kids, (list, tuple)):
                stack.extend(kids)
