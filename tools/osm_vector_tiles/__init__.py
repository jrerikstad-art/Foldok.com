"""OpenStreetMap map rendering for Foldok (project-local assets only).

Default backend stitches XYZ raster tiles with Pillow (works out of the box).
Drop your full vector-tile generator beside this package as
`custom_vector_renderer.py` exposing:

    def render_map(lat, lon, out_path, *, width, height, zoom, style,
                   color_overrides, output_format) -> str

If present, HybridKnowledgeEngine prefers that backend.
"""
from __future__ import annotations

from .renderer import render_location_map, geocode_address

__all__ = ["render_location_map", "geocode_address"]
