"""Foldok route — the branch hub_chat was missing.

    if diagram_route.is_diagram_request(message):
        result = diagram_route.handle(message, spec=..., components=...)

hub_chat is a keyword router with no model and no tool loop in that path, so a
drawing capability needs a route beside the other routes, not a tool
registration. Also narrows the CAD refusal that was answering these questions.
"""

from .diagram_route import (
    DIAGRAM_WORDS,
    ROUTE_SNIPPET,
    RouteResult,
    apply_patch,
    handle,
    is_diagram_request,
)

__all__ = [
    "DIAGRAM_WORDS", "ROUTE_SNIPPET", "RouteResult", "apply_patch", "handle",
    "is_diagram_request",
]

__version__ = "0.85.0"
