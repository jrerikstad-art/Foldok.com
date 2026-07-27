"""Renderer protocol — LayoutTree is the only allowed input for paint."""
from __future__ import annotations

from typing import Protocol, runtime_checkable, Union

from artifact_engine.layout.tree import LayoutTree

# bytes for PDF/DOCX/SVG packages; str for HTML
RenderOutput = Union[bytes, str]


@runtime_checkable
class Renderer(Protocol):
    """
    Universal renderer contract.

    Implementations MUST:
      - accept only LayoutTree (final geometry + resolved styles)
      - make no layout / page-break / typography decisions
      - not inspect Document, Section, or Block models for placement

    Convenience wrappers that accept Document must compose→measure→solve→tree
    first, then call render_layout / render_tree.
    """

    def render_layout(self, layout: LayoutTree) -> RenderOutput:
        ...
