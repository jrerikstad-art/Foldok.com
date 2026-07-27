"""Foldok box layout — Word's flow, InDesign's grid, Figma's directness.

    blocks + template + pins
        -> solve()        deterministic geometry, document order preserved
        -> Geometry       consumed by BOTH the canvas and the PDF renderer

The user is in control because every hand edit is a pin in its own layer, and
pins beat the template. The flow survives because a pin says col/span/rows on
the page grid, never raw pixels.
"""

from .flow import BlockInput, Measurer, SimpleMeasurer, order_blocks, pack, paginate, resolve_boxes, solve
from .model import HANDLES, PAGE_SIZES, Box, Geometry, PageGrid, PlacedBox
from .parity import ParityReport, check_layout_tree, compare, fingerprint, payload
from .pins import GLOBAL_SCOPE, Pin, PinStore
from .session import Change, LayoutRefused, LayoutSession
from .snap import DropTarget, SnapResult, block_at, cursor_for, drop_target, ghost, handle_at, resize, snap_rect
from .template import LayoutTemplate, compliance_a4

__all__ = [
    "BlockInput", "Box", "Change", "DropTarget", "GLOBAL_SCOPE", "Geometry", "HANDLES",
    "LayoutRefused", "LayoutSession", "LayoutTemplate", "Measurer", "PAGE_SIZES", "PageGrid",
    "ParityReport", "Pin", "PinStore", "PlacedBox", "SimpleMeasurer", "SnapResult",
    "block_at", "check_layout_tree", "compare", "compliance_a4", "cursor_for", "drop_target",
    "fingerprint", "ghost", "handle_at", "order_blocks", "pack", "paginate", "payload",
    "resize", "resolve_boxes", "snap_rect", "solve",
]

__version__ = "0.73.0"
