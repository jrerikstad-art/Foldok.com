"""QR generation — at build time, into inline SVG.

Two reasons it is not a runtime call to a QR image service:

**Privacy.**  An externally hosted QR image is a request to a third party on
every page view, with the referrer attached.  On a site whose argument is that
nothing leaves the machine, a tracking pixel dressed as a convenience is exactly
the detail someone screenshots.

**Offline.**  The page is one self-contained file.  Adding a network dependency
for a decorative square undoes that for no gain.

So ``segno`` is a build-time dependency, the output is an inline ``<svg>``, and
the shipped page has no new requests and no new scripts.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    import segno
except ImportError:  # pragma: no cover
    segno = None  # type: ignore


@dataclass(frozen=True)
class QRStyle:
    # A literal colour, not var(--ink). CSS variables in SVG presentation
    # attributes are unreliable in older Safari, and a QR that renders with no
    # fill is a square that silently does not scan. Override with CSS if needed.
    dark: str = "#16181D"
    light: str | None = None            # None = transparent, sits on any background
    quiet_zone: int = 2                 # modules; 4 is the spec, 2 scans fine and looks tighter
    size: int = 168                     # rendered px
    radius: float = 0.0                 # module corner rounding, 0..0.5


def qr_svg(
    data: str,
    style: QRStyle | None = None,
    *,
    error: str = "m",
    title: str = "",
) -> str:
    """A self-contained ``<svg>`` string.

    ``error='m'`` gives ~15% recovery, which is the right trade for a code shown
    on a screen: high enough to survive a phone camera at an angle, low enough
    that the code stays coarse and scans fast.
    """
    if segno is None:  # pragma: no cover
        raise RuntimeError(
            "QR generation needs 'segno' at build time (pip install segno). "
            "It is not needed at runtime — the output is a static SVG."
        )
    style = style or QRStyle()
    code = segno.make(data, error=error)
    matrix = [list(row) for row in code.matrix]
    modules = len(matrix)
    span = modules + style.quiet_zone * 2

    rects: list[str] = []
    for y, row in enumerate(matrix):
        run_start: int | None = None
        for x in range(modules + 1):
            on = x < modules and bool(row[x])
            if on and run_start is None:
                run_start = x
            elif not on and run_start is not None:
                # merge horizontal runs into one rect: fewer nodes, smaller file
                rects.append(
                    f'<rect x="{run_start + style.quiet_zone}" y="{y + style.quiet_zone}" '
                    f'width="{x - run_start}" height="1"'
                    + (f' rx="{style.radius:g}"' if style.radius else "")
                    + "/>"
                )
                run_start = None

    background = (
        f'<rect width="{span}" height="{span}" fill="{style.light}"/>' if style.light else ""
    )
    label = f"<title>{_escape(title)}</title>" if title else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {span} {span}" '
        f'width="{style.size}" height="{style.size}" shape-rendering="crispEdges" '
        f'role="img" aria-label="{_escape(title or "QR code")}">'
        f"{label}{background}"
        f'<g class="gc-qr-ink" fill="{style.dark}">{"".join(rects)}</g>'
        "</svg>"
    )


def module_count(data: str, *, error: str = "m") -> int:
    """Useful in tests and for sanity: version 1 is 21 modules, and it grows by
    4 per version. A URL that pushes past ~45 modules gets hard to scan on a
    laptop screen at arm's length."""
    if segno is None:  # pragma: no cover
        raise RuntimeError("segno not installed")
    return len(segno.make(data, error=error).matrix)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )
