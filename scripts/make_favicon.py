"""Generate Foldok favicon — tab-readable ellipsis on signal yellow."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "public"
INK = (22, 24, 29, 255)
SIGNAL = (245, 196, 0, 255)


def make_16() -> Image.Image:
    """Pixel-aware 16×16: solid yellow tile + three 3×3 dots with 1px gaps."""
    img = Image.new("RGBA", (16, 16), SIGNAL)
    draw = ImageDraw.Draw(img)
    # Dots as 3×3 blocks at y=6..8; x slots leave clear yellow between
    for x0 in (2, 6, 10):
        draw.rectangle([x0, 6, x0 + 3, 9], fill=INK)
    return img


def make(size: int) -> Image.Image:
    if size == 16:
        return make_16()
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Soft squircle for larger sizes (circular on tabs)
    pad = max(0, int(size * 0.02))
    draw.ellipse([pad, pad, size - 1 - pad, size - 1 - pad], fill=SIGNAL)
    cy = (size - 1) / 2
    rad = size * 0.10
    gap = size * 0.28  # center-to-center
    for i in (-1, 0, 1):
        cx = (size - 1) / 2 + i * gap
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=INK)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    images = {sz: make(sz) for sz in (16, 32, 48, 180)}
    images[16].save(OUT / "favicon-16.png")
    images[32].save(OUT / "favicon-32.png")
    images[180].save(OUT / "apple-touch-icon.png")
    images[16].save(
        OUT / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[images[32], images[48]],
    )
    # Keep SVG as circle + dots (browsers that prefer SVG)
    (OUT / "favicon.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="Foldok">
  <title>Foldok</title>
  <circle cx="16" cy="16" r="16" fill="#F5C400"/>
  <circle cx="7.5" cy="16" r="3.2" fill="#16181D"/>
  <circle cx="16" cy="16" r="3.2" fill="#16181D"/>
  <circle cx="24.5" cy="16" r="3.2" fill="#16181D"/>
</svg>
""",
        encoding="utf-8",
    )
    print("ok")


if __name__ == "__main__":
    main()
