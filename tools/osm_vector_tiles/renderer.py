"""Unified map render entry — prefers custom vector renderer if present."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional

from .geocode import geocode_address
from .tile_stitch import stitch_map


def _load_custom_renderer():
    """Optional drop-in: tools/osm_vector_tiles/custom_vector_renderer.py"""
    path = Path(__file__).resolve().parent / "custom_vector_renderer.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("foldok_custom_vector_renderer", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "render_map", None)


def render_location_map(
    lat: float,
    lon: float,
    out_path: str,
    *,
    width: int = 1200,
    height: int = 800,
    zoom: int = 16,
    style: str = "default",
    color_overrides: Optional[Dict[str, Any]] = None,
    output_format: str = "png",
) -> str:
    """
    Render a map centered on lat/lon into out_path (project-local).
    Returns absolute path written.
    """
    fmt = (output_format or "png").lower().lstrip(".")
    out = Path(out_path)
    if out.suffix.lower() != f".{fmt}":
        out = out.with_suffix(f".{fmt}")
    out_path = str(out)

    custom = _load_custom_renderer()
    if custom:
        return custom(
            lat, lon, out_path,
            width=width, height=height, zoom=zoom, style=style,
            color_overrides=color_overrides or {},
            output_format=fmt,
        )

    # Built-in: PNG stitch (SVG/PDF → PNG then note; PDF needs extra deps)
    png_path = out_path if fmt == "png" else str(Path(out_path).with_suffix(".png"))
    stitch_map(
        lat, lon, png_path,
        width=width, height=height, zoom=zoom, style=style,
        color_overrides=color_overrides,
    )
    if fmt == "png":
        return png_path
    if fmt == "pdf":
        try:
            from PIL import Image
            img = Image.open(png_path).convert("RGB")
            img.save(out_path, "PDF", resolution=150.0)
            return out_path
        except Exception:
            return png_path
    if fmt == "svg":
        # Minimal SVG wrapper embedding the PNG (keeps everything local)
        rel_name = Path(png_path).name
        svg = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}">\n'
            f'  <image width="{width}" height="{height}" xlink:href="{rel_name}"/>\n'
            f'</svg>\n'
        )
        Path(out_path).write_text(svg, encoding="utf-8")
        return out_path
    return png_path
