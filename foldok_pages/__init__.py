"""Foldok pages — accept "page 6", anchor to something that survives reflow.

    index  = PageIndex.from_geometry(geometry, blocks)
    anchor = resolve("legg diagrammet på side 6", index)
    print(anchor.describe("koblingsskjemaet"))
    #  Side 6 er seksjon «4 Verifikasjon», etter isolasjonstabellen.
    #  Legger koblingsskjemaet der. Sidetallet flytter seg når innholdet
    #  endres, så den er festet til seksjonen, ikke til siden.

The page numbers already existed — foldok_boxes stamps `page` on every placed
box. Nothing ever surfaced them.
"""

from .resolve import Anchor, Block, PageIndex, order_pin, resolve

__all__ = ["Anchor", "Block", "PageIndex", "order_pin", "resolve"]

__version__ = "0.85.0"
