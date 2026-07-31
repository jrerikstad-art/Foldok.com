"""A module symbol that grows with its pin count.

The stock ``load_block`` is a fixed 34x26 box with a diagonal through it — right
for a load on a single-line diagram, wrong for a breakout board with six labelled
pins. Rendering an RC excavator's control electronics with it suppressed 14 port
labels, because the engine correctly refuses to overlap text and there was
nowhere to put it.

A module is a plain rectangle sized from the ports it actually has. That is the
whole fix, and it is why board-level wiring was never really out of scope: a
breakout-board diagram is labelled rectangles and lines, which the graph model
already produces.
"""

from __future__ import annotations

from foldok_diagram.symbols import SYMBOLS, Symbol

PORT_PITCH = 22.0          # vertical space one side-port needs for its label
MIN_W, MIN_H = 62.0, 40.0
CHAR_W = 5.4               # rough advance at the label size


def module_symbol(
    component,
    *,
    title: str = "",
) -> Symbol:
    """Size a rectangle to hold this component's ports and its longest label."""
    sides: dict[str, int] = {}
    longest = len(title or component.label or component.id)
    for port in component.ports:
        sides[port.side] = sides.get(port.side, 0) + 1
        longest = max(longest, len(port.label or port.name or port.id))

    vertical = max(sides.get("left", 0), sides.get("right", 0))
    horizontal = max(sides.get("top", 0), sides.get("bottom", 0))

    height = max(MIN_H, vertical * PORT_PITCH + 16)
    width = max(MIN_W, horizontal * PORT_PITCH + 16, longest * CHAR_W)

    return Symbol(
        id=f"module::{component.id}",
        w=round(width, 1),
        h=round(height, 1),
        elements=(
            ("rect", -width / 2, -height / 2, width, height, "equipment"),
            # A thin rule under the top edge reads as a module header without
            # needing text inside the box, which the tag already carries.
            ("line", -width / 2, -height / 2 + 9, width / 2, -height / 2 + 9, "thin"),
        ),
        fill_body=True,
        labels_inside=True,
    )


def register(component, *, title: str = "") -> str:
    """Register a sized symbol and return its id.

    Symbols are per-component because the size is per-component. That is a
    deliberate departure from the shared pack: a symbol pack entry is a shape
    reused everywhere, and a module box is a shape derived from one instance.
    """
    symbol = module_symbol(component, title=title)
    SYMBOLS[symbol.id] = symbol
    return symbol.id
