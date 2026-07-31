"""Foldok — the "get the Capture app" header control.

    python -m foldok_getapp --url https://foldok.com/capture --out snippet.html

Generates a self-contained block: button, popover, QR as inline SVG, platform
detection, bilingual. No runtime dependency and no external requests.
"""

from .qr import QRStyle, module_count, qr_svg
from .widget import Copy, DEFAULT_COPY, landing_note, widget

__all__ = ["Copy", "DEFAULT_COPY", "QRStyle", "landing_note", "module_count", "qr_svg", "widget"]

__version__ = "0.81.0"
