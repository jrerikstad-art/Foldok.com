"""XYZ tile stitcher — default map backend (Pillow + OSM/Carto tiles)."""
from __future__ import annotations

import io
import math
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

USER_AGENT = "FoldokEngine/0.52 (local documentation maps)"

# Style → tile URL template ({z}/{x}/{y})
STYLE_TILES = {
    "default": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "minimal": "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "technical": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    # Attribution required when used commercially; fine for local project docs
    "satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
}

MARKER_COLORS = {
    "default": (200, 40, 40, 230),
    "minimal": (40, 80, 160, 230),
    "technical": (20, 20, 20, 240),
    "satellite": (255, 220, 40, 240),
}


def _latlon_to_tile(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def _fetch_tile(url: str) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.read()
    except Exception:
        return None


def stitch_map(
    lat: float,
    lon: float,
    out_path: str,
    *,
    width: int = 1200,
    height: int = 800,
    zoom: int = 16,
    style: str = "default",
    color_overrides: Optional[Dict] = None,
) -> str:
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps

    style_key = (style or "default").lower()
    template = STYLE_TILES.get(style_key, STYLE_TILES["default"])
    tile_size = 256

    cx, cy = _latlon_to_tile(lat, lon, zoom)
    tiles_x = max(1, math.ceil(width / tile_size) + 1)
    tiles_y = max(1, math.ceil(height / tile_size) + 1)
    x0 = int(math.floor(cx - tiles_x / 2))
    y0 = int(math.floor(cy - tiles_y / 2))

    canvas = Image.new("RGB", (tiles_x * tile_size, tiles_y * tile_size), (240, 240, 240))
    n = 2 ** zoom
    for dx in range(tiles_x):
        for dy in range(tiles_y):
            tx = (x0 + dx) % n
            ty = y0 + dy
            if ty < 0 or ty >= n:
                continue
            url = template.format(z=zoom, x=tx, y=ty)
            raw = _fetch_tile(url)
            if not raw:
                continue
            try:
                tile = Image.open(io.BytesIO(raw)).convert("RGB")
                canvas.paste(tile, (dx * tile_size, dy * tile_size))
            except Exception:
                continue

    # Crop centered on lat/lon
    px = (cx - x0) * tile_size
    py = (cy - y0) * tile_size
    left = int(max(0, px - width / 2))
    top = int(max(0, py - height / 2))
    right = int(min(canvas.width, left + width))
    bottom = int(min(canvas.height, top + height))
    img = canvas.crop((left, top, right, bottom))
    if img.size != (width, height):
        pad = Image.new("RGB", (width, height), (240, 240, 240))
        pad.paste(img, (0, 0))
        img = pad

    if style_key == "technical":
        img = ImageOps.grayscale(img).convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(1.25)

    # Color overrides: tint / contrast / marker color
    ov = color_overrides or {}
    if ov.get("grayscale"):
        img = ImageOps.grayscale(img).convert("RGB")
    if ov.get("contrast"):
        try:
            img = ImageEnhance.Contrast(img).enhance(float(ov["contrast"]))
        except (TypeError, ValueError):
            pass
    if ov.get("brightness"):
        try:
            img = ImageEnhance.Brightness(img).enhance(float(ov["brightness"]))
        except (TypeError, ValueError):
            pass
    if ov.get("tint"):
        # Soft color wash (R,G,B) 0-255
        try:
            r, g, b = ov["tint"][:3]
            wash = Image.new("RGB", img.size, (int(r), int(g), int(b)))
            img = Image.blend(img, wash, float(ov.get("tint_strength", 0.15)))
        except Exception:
            pass

    # Marker
    draw = ImageDraw.Draw(img, "RGBA")
    mx, my = width // 2, height // 2
    marker = ov.get("marker_color") or MARKER_COLORS.get(style_key, MARKER_COLORS["default"])
    if isinstance(marker, str) and marker.startswith("#") and len(marker) == 7:
        marker = tuple(int(marker[i:i + 2], 16) for i in (1, 3, 5)) + (230,)
    r = int(ov.get("marker_radius", 14))
    draw.ellipse([mx - r, my - r, mx + r, my + r], fill=tuple(marker)[:4], outline=(255, 255, 255, 255), width=3)
    draw.ellipse([mx - 3, my - 3, mx + 3, my + 3], fill=(255, 255, 255, 255))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    return out_path
