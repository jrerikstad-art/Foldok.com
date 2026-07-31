"""Measure structure and page design from a document — never keep body text."""

from __future__ import annotations

import re
from pathlib import Path

from .model import DesignProfile, Skeleton

HEADING_MD = re.compile(r"^(#{1,6})\s+(.+)$", re.M)
HEADING_NUM = re.compile(
    r"^(\d{1,2}(?:\.\d{1,3}){0,4})\s+([A-ZÆØÅ][^\n]{2,80})$", re.M
)
HEADING_ALLCAPS = re.compile(r"^([A-ZÆØÅ][A-ZÆØÅ0-9 /&\-]{3,60})$", re.M)
TABLE_HINT = re.compile(r"(?i)\b(table|tabell)\s+\d")
FIGURE_HINT = re.compile(r"(?i)\b(figure|figur|fig\.)\s+\d")


def skeleton(text: str) -> Skeleton:
    """Section titles from local text. Bodies are never stored on the Skeleton."""
    headings: list[tuple[int, str]] = []
    seen: set[str] = set()

    for m in HEADING_MD.finditer(text):
        title = m.group(2).strip()
        key = title.lower()
        if key not in seen and len(title) > 1:
            seen.add(key)
            headings.append((len(m.group(1)), title))

    if not headings:
        for m in HEADING_NUM.finditer(text):
            title = m.group(2).strip()
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            level = m.group(1).count(".") + 1
            headings.append((level, title))

    if not headings:
        for m in HEADING_ALLCAPS.finditer(text):
            title = m.group(1).strip()
            key = title.lower()
            if key in seen or len(title.split()) > 8:
                continue
            seen.add(key)
            headings.append((1, title.title() if title.isupper() else title))

    numbering = "decimal" if any(
        HEADING_NUM.match(line) for line in text.splitlines()[:200]
    ) else ("markdown" if HEADING_MD.search(text) else "none")

    return Skeleton(
        headings=headings[:40],
        numbering=numbering,
        tables=len(TABLE_HINT.findall(text)),
        figures=len(FIGURE_HINT.findall(text)),
    )


def design_from_pdf(path: str | Path) -> DesignProfile:
    path = Path(path)
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        if not reader.pages:
            return DesignProfile(measured_from="pdf", confidence=0.0)
        page = reader.pages[0]
        box = page.mediabox
        w = float(box.width)
        h = float(box.height)
        page_size = _page_name(w, h)
        # PDF has no reliable margin without layout analysis — report page only.
        return DesignProfile(
            page_size=page_size,
            body_size_pt=11.0,
            columns=1,
            measured_from="pdf",
            confidence=0.55 if page_size else 0.3,
            margin_left_pt=72.0,
            margin_right_pt=72.0,
            margin_top_pt=72.0,
            margin_bottom_pt=72.0,
        )
    except Exception:  # noqa: BLE001
        return DesignProfile(measured_from="pdf", confidence=0.0)


def design_from_docx(path: str | Path) -> DesignProfile:
    path = Path(path)
    try:
        import docx  # type: ignore

        document = docx.Document(str(path))
        section = document.sections[0]
        w = float(section.page_width.pt) if section.page_width else 0.0
        h = float(section.page_height.pt) if section.page_height else 0.0
        page_size = _page_name(w, h)
        body = 11.0
        for style_name in ("Normal", "Body Text"):
            try:
                style = document.styles[style_name]
                if style.font and style.font.size:
                    body = float(style.font.size.pt)
                    break
            except Exception:  # noqa: BLE001
                continue
        return DesignProfile(
            page_size=page_size,
            margin_left_pt=float(section.left_margin.pt) if section.left_margin else 0.0,
            margin_right_pt=float(section.right_margin.pt) if section.right_margin else 0.0,
            margin_top_pt=float(section.top_margin.pt) if section.top_margin else 0.0,
            margin_bottom_pt=float(section.bottom_margin.pt) if section.bottom_margin else 0.0,
            body_size_pt=body,
            columns=1,
            measured_from="docx",
            confidence=0.75 if page_size else 0.4,
        )
    except Exception:  # noqa: BLE001
        return DesignProfile(measured_from="docx", confidence=0.0)


def _page_name(width_pt: float, height_pt: float) -> str:
    if width_pt <= 0 or height_pt <= 0:
        return ""
    # A4 ≈ 595 × 842, Letter ≈ 612 × 792
    for name, w, h in (("A4", 595, 842), ("Letter", 612, 792), ("A3", 842, 1191)):
        if abs(width_pt - w) < 8 and abs(height_pt - h) < 8:
            return name
        if abs(width_pt - h) < 8 and abs(height_pt - w) < 8:
            return f"{name}-landscape"
    return f"{width_pt:.0f}x{height_pt:.0f}pt"
