"""Bridge foldok_pages into the workbench — accept "side 6", anchor to section."""
from __future__ import annotations

from typing import Any


def page_index_from_layout(state: dict | None) -> Any | None:
    """Build a PageIndex from foldok_boxes geometry when a layout session exists."""
    try:
        from foldok_pages import PageIndex
    except ImportError:
        return None
    layout = (state or {}).get("layout") or (state or {}).get("box_layout") or {}
    geometry = layout.get("geometry")
    blocks_meta = layout.get("blocks") or layout.get("block_meta") or []
    if geometry is None:
        return None
    try:
        return PageIndex.from_geometry(geometry, blocks_meta)
    except Exception:
        return None


def resolve_page_in_message(
    message: str,
    state: dict | None = None,
    *,
    what: str = "figuren",
    lang: str = "no",
) -> dict | None:
    """If the message names a page/section, return describe + anchor dict (zero tokens)."""
    try:
        from foldok_pages import resolve
    except ImportError:
        return None
    idx = page_index_from_layout(state)
    if idx is None or not getattr(idx, "blocks", None):
        return None
    anchor = resolve(message or "", idx)
    if not anchor.resolved and not getattr(anchor, "page_seen", 0):
        return None
    return {
        "describe": anchor.describe(what, lang=lang),
        "anchor": anchor.to_dict() if hasattr(anchor, "to_dict") else {
            "section": anchor.section,
            "section_title": anchor.section_title,
            "page_seen": anchor.page_seen,
            "after_block": anchor.after_block,
            "kind": anchor.kind,
            "confidence": anchor.confidence,
        },
        "section": anchor.section or None,
    }
