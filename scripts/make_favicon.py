"""Generate Foldok favicon PNG/ICO assets from the […] brand mark."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "public"
INK = (22, 24, 29, 255)  # #16181D
SIGNAL = (245, 196, 0, 255)  # #F5C400


def make(size: int, radius_ratio: float = 0.18) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = max(2, int(size * radius_ratio))
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=INK)
    font = None
    for path in (
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\CascadiaMono.ttf",
        r"C:\Windows\Fonts\lucon.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ):
        if Path(path).exists():
            font = ImageFont.truetype(path, size=int(size * 0.46))
            break
    if font is None:
        font = ImageFont.load_default()
    text = "[…]"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1] - size * 0.02
    draw.text((x, y), text, font=font, fill=SIGNAL)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make(32).save(OUT / "favicon-32.png")
    make(16).save(OUT / "favicon-16.png")
    make(180, radius_ratio=0.2).save(OUT / "apple-touch-icon.png")
    make(32).save(OUT / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print("ok", sorted(p.name for p in OUT.glob("favicon*")), "apple-touch-icon.png")


if __name__ == "__main__":
    main()
