"""Foldok diagram engine.

    graph + pins + style + profile
        -> layout()        deterministic geometry
        -> render_svg()    byte-stable SVG, also the canvas surface
        -> EngineeringFigure (ArtifactEngine)

Public surface is deliberately small.  Everything a user can adjust by hand goes
through ``DiagramSession``; everything the engine decides goes through
``layout``.
"""

from .editing import ConnectRefused, DiagramSession, Edit
from .layout import Layout, layout
from .model import (
    SCHEMA_VERSION,
    Component,
    Connection,
    Endpoint,
    Graph,
    Port,
    Provenance,
    Segment,
)
from .overrides import (
    GLOBAL_SCOPE,
    Pin,
    PinStore,
    target_component,
    target_connection,
    target_port_label,
)
from .profile import PROFILES, Profile
from .render import RenderResult, render_svg
from .style import DiagramStyle, Encoding
from .validate import Issue, Report, validate

__all__ = [
    "SCHEMA_VERSION",
    "Component",
    "ConnectRefused",
    "Connection",
    "DiagramSession",
    "DiagramStyle",
    "Edit",
    "Encoding",
    "Endpoint",
    "GLOBAL_SCOPE",
    "Graph",
    "Issue",
    "Layout",
    "PROFILES",
    "Pin",
    "PinStore",
    "Port",
    "Profile",
    "Provenance",
    "RenderResult",
    "Report",
    "Segment",
    "figure",
    "layout",
    "render_svg",
    "target_component",
    "target_connection",
    "target_port_label",
    "validate",
]

__version__ = "0.63.0"


def figure(
    graph: Graph,
    profile,
    style: DiagramStyle | None = None,
    pins: PinStore | None = None,
    *,
    target_width_pt: float | None = None,
    title: str | None = None,
    subtitle: str | None = None,
) -> RenderResult:
    """One call from graph to publishable SVG."""
    style = style or DiagramStyle()
    lay = layout(graph, profile, style, pins)
    return render_svg(
        lay,
        style,
        target_width_pt=target_width_pt,
        title=title if title is not None else (graph.title or None),
        subtitle=subtitle if subtitle is not None else (graph.subtitle or None),
    )
