"""Foldok select — curation, then narrative, then selection.

    context   = build_context(index, project_terms=[...])      # before narrative
    selection = select_for_section(context, section=..., ask=call_model)  # after

Curation asks whether a source is admissible at all — corpus-level, needs no
narrative. Selection asks which asset supports a given section — and needs one.
Collapsing them breaks the second half.

The model is never asked whether an image exists. It is handed a numbered menu
and asked which entries support the section, which is a bounded choice rather
than a search of a filesystem it cannot see.
"""

from .context import (
    SCHEMA_VERSION,
    Asset,
    AssetKind,
    DocumentContext,
    Excluded,
    build_context,
)
from .select import (
    MAX_MENU,
    Menu,
    MenuItem,
    Selection,
    caption_note,
    menu_for,
    parse_reply,
    select_for_section,
)

__all__ = [
    "Asset", "AssetKind", "DocumentContext", "Excluded", "MAX_MENU", "Menu",
    "MenuItem", "SCHEMA_VERSION", "Selection", "build_context", "caption_note",
    "menu_for", "parse_reply", "select_for_section",
]

__version__ = "0.107.0"
