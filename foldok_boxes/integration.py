"""Integration with the existing build.

Three jobs, all of them about not throwing away what 0.72 already has:

1.  ``grid_from_theme`` — take the page geometry from artifact_engine's Theme so
    the box grid is the same grid the renderer already uses.
2.  ``blocks_from`` — adapt whatever block objects the document engine hands over
    into BlockInput, forgivingly, so this can be wired in before either side is
    refactored.
3.  ``migrate_layout`` — turn the existing ``layout jsonb`` (``full|half|third``
    from migration_004) into col/span pins.  Every document already in the
    database keeps the layout it has; nobody opens a saved job to find it
    reshaped.

The migration is the part to get right.  Three named widths map cleanly onto a
12-column grid, and because they arrive as pins at the ``template`` layer rather
than the ``user`` layer, a later "reset layout" still returns to the template
instead of back to a value someone picked in 2025.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from .flow import BlockInput
from .model import PageGrid
from .pins import PinStore

WIDTH_FRACTIONS: dict[str, float] = {
    "full": 1.0,
    "half": 0.5,
    "third": 1 / 3,
    "two_thirds": 2 / 3,
    "quarter": 0.25,
    "auto": 1.0,
}

ROLE_MAP: dict[str, str] = {
    "paragraph": "text", "p": "text", "prose": "text", "markdown": "text",
    "h1": "heading", "h2": "heading", "h3": "heading", "title": "heading",
    "figure": "image", "photo": "image", "img": "image",
    "svg": "diagram", "schematic": "diagram",
    "grid": "table", "datatable": "table",
    "warning_box": "callout", "warning": "callout", "note": "callout",
    "page_break": "spacer", "spacer": "spacer",
}


def grid_from_theme(theme: Any, page_size: str = "A4", columns: int = 12) -> PageGrid:
    return PageGrid.from_theme(theme, page_size=page_size, columns=columns)


def blocks_from(source: Iterable[Any]) -> list[BlockInput]:
    """Adapt existing block objects or dicts.  Unknown types become text, which
    is the safe default: full width, height from content."""
    out: list[BlockInput] = []
    for i, raw in enumerate(source):
        bid = str(_get(raw, "id", "block_id", "key") or f"block_{i}")
        raw_role = str(_get(raw, "role", "type", "kind", "block_type") or "text").lower()
        role = ROLE_MAP.get(raw_role, raw_role if raw_role in
                            ("text", "heading", "image", "diagram", "table", "callout", "spacer")
                            else "text")
        text = _get(raw, "text", "content", "body", "markdown") or ""
        if not isinstance(text, str):
            text = str(text)
        rows_hint = _get(raw, "row_count", "rows")
        aspect = _get(raw, "aspect", "aspect_ratio")
        out.append(
            BlockInput(
                id=bid,
                role=role,
                section=str(_get(raw, "section_key", "section") or ""),
                text=text,
                rows_hint=int(rows_hint) if isinstance(rows_hint, (int, float)) else None,
                aspect=float(aspect) if isinstance(aspect, (int, float)) else None,
                locked=bool(_get(raw, "locked", "is_locked", "boilerplate") or False),
            )
        )
    return out


def migrate_layout(
    rows: Sequence[dict[str, Any]],
    grid: PageGrid,
    pins: PinStore | None = None,
    *,
    layer: str = "template",
) -> tuple[PinStore, list[str]]:
    """``[{block_id, layout:{width, align, group_id, group_slot}}]`` -> pins.

    Grouped blocks (migration_004's two-column pairing) become adjacent columns
    in the same band, which is what a group always meant geometrically — the
    group_id was only ever a way to say "these two sit side by side" without a
    column model to say it in.
    """
    pins = pins or PinStore()
    scope = grid.scoped()
    notes: list[str] = []

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        layout = row.get("layout") or {}
        gid = layout.get("group_id")
        if gid:
            groups.setdefault(str(gid), []).append(row)

    handled: set[str] = set()
    for gid, members in sorted(groups.items()):
        members.sort(key=lambda r: int((r.get("layout") or {}).get("group_slot") or 0))
        share = grid.columns // max(1, len(members))
        col = 0
        for member in members:
            bid = str(member["block_id"])
            pins.pin(bid, "col", col, layer=layer, scope=scope, note=f"from group {gid}")
            pins.pin(bid, "span", share, layer=layer, scope=scope, note=f"from group {gid}")
            handled.add(bid)
            col += share
        notes.append(f"group {gid}: {len(members)} block(s) became adjacent columns")

    for row in rows:
        bid = str(row["block_id"])
        if bid in handled:
            continue
        layout = row.get("layout") or {}
        width = str(layout.get("width") or "full").lower()
        fraction = WIDTH_FRACTIONS.get(width)
        if fraction is None:
            notes.append(f"block {bid}: unknown width '{width}', treated as full")
            fraction = 1.0
        span = max(1, min(grid.columns, round(grid.columns * fraction)))
        pins.pin(bid, "span", span, layer=layer, scope=scope, note=f"migrated from '{width}'")
        pins.pin(bid, "col", 0, layer=layer, scope=scope, note=f"migrated from '{width}'")
        align = layout.get("align")
        if align in ("left", "center", "right", "justify"):
            pins.pin(bid, "align", align, layer=layer, scope=scope)

    notes.append(
        f"{len(rows)} block(s) migrated to a {grid.columns}-column grid at layer '{layer}' — "
        "'reset layout' will return to the template, not to these values"
    )
    return pins, notes


def layout_jsonb(block_id: str, pins: PinStore, grid: PageGrid) -> dict[str, Any]:
    """Write pins back out in a shape the existing ``layout jsonb`` column can
    hold, so the new model can ship before the schema changes."""
    scope = grid.scoped()
    out: dict[str, Any] = {"grid": {"columns": grid.columns, "page_size": grid.page_size}}
    for prop in ("col", "span", "rows", "align", "break_before", "keep_with_next"):
        value = pins.value(block_id, prop, scope, None)
        if value is not None:
            out[prop] = value
    span = out.get("span")
    if isinstance(span, int):
        ratio = span / grid.columns
        out["width"] = (
            "full" if ratio > 0.9 else
            "two_thirds" if ratio > 0.58 else
            "half" if ratio > 0.42 else
            "third" if ratio > 0.29 else "quarter"
        )
    return out


def _get(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None
