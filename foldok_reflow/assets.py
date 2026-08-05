"""Figures and tables inside PDFs — the material that was never extracted.

A single 40-page technical PDF contains 23 embedded images. ``foldok_index``'s
extractor does not mention images, figures, tables or XObjects anywhere: it
returns text and nothing else. So a folder of thirty documents full of product
photographs, wiring figures, symbol keys and data tables presents itself to the
engine as prose, and every downstream stage correctly reports that no figures are
available.

That is why "there are pictures in the folder" and "the document has no
illustrations" were both true at once. The pictures are *inside* the PDFs, and
nothing has ever looked in there.

Two things come out here:

``figures``   embedded raster images, with the caption line that sits under them
              in the text — because a figure without its caption is unusable in
              a document, and the caption is what makes it selectable.

``tables``    runs of lines that share a column structure — **when the extractor
              preserves one**. Measured on a real technical PDF: ``pypdf``
              flattens a table to one cell per line, so there are no column runs
              left to detect and this returns nothing. That is reported rather
              than hidden, because "no tables found" and "tables cannot be seen
              by this extractor" are different facts and only the second one
              tells you what to do (use a layout-aware extractor such as
              pdfplumber for table-heavy sources).

Neither is guessed at. A figure with no discoverable caption is still returned,
marked as uncaptioned, because a person can look at it and a heuristic cannot.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = 1

CAPTION = re.compile(
    r"^\s*(figure|fig\.?|figur|illustrasjon|bilde|table|tabell|diagram)\s*"
    r"(\d+[a-z]?)\s*[:.\-–]?\s*(.{0,160})$",
    re.I,
)

# A row of a table: several numeric or short tokens separated by run of spaces.
CELL_SPLIT = re.compile(r"\s{2,}|\t|\s\|\s")
NUMERIC = re.compile(r"^[-+]?\d+(?:[.,]\d+)?(?:\s*[%°]|\s*[a-zA-ZΩµ/²³]{1,6})?$")


@dataclass
class Figure:
    id: str
    page: int
    index: int
    caption: str = ""
    width: int = 0
    height: int = 0
    source: str = ""
    data: bytes | None = field(default=None, repr=False)

    @property
    def captioned(self) -> bool:
        return bool(self.caption.strip())

    @property
    def usable(self) -> bool:
        """Big enough to be content rather than a logo or a bullet glyph."""
        return self.width >= 120 and self.height >= 90

    def menu_line(self) -> str:
        label = self.caption or f"(uncaptioned, page {self.page})"
        return f"{self.id}  {label[:90]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "page": self.page, "caption": self.caption,
            "width": self.width, "height": self.height, "source": self.source,
            "captioned": self.captioned, "usable": self.usable,
        }


@dataclass
class Table:
    id: str
    page: int
    rows: list[list[str]] = field(default_factory=list)
    caption: str = ""
    source: str = ""

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.rows), max((len(r) for r in self.rows), default=0))

    @property
    def usable(self) -> bool:
        rows, cols = self.shape
        return rows >= 2 and cols >= 2

    def menu_line(self) -> str:
        rows, cols = self.shape
        label = self.caption or f"{rows}x{cols} table, page {self.page}"
        return f"{self.id}  {label[:90]}"

    def to_markdown(self) -> str:
        if not self.rows:
            return ""
        width = max(len(r) for r in self.rows)
        padded = [r + [""] * (width - len(r)) for r in self.rows]
        head, *body = padded
        lines = ["| " + " | ".join(head) + " |",
                 "|" + "|".join([" --- "] * width) + "|"]
        lines += ["| " + " | ".join(r) + " |" for r in body]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "page": self.page, "caption": self.caption,
            "rows": len(self.rows), "columns": self.shape[1],
            "source": self.source, "usable": self.usable,
            "markdown": self.to_markdown(),
        }


@dataclass
class AssetHarvest:
    figures: list[Figure] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    source: str = ""
    note: str = ""

    def usable_figures(self) -> list[Figure]:
        return [f for f in self.figures if f.usable]

    def usable_tables(self) -> list[Table]:
        return [t for t in self.tables if t.usable]

    def summary(self, *, lang: str = "no") -> str:
        f, t = len(self.usable_figures()), len(self.usable_tables())
        uncaptioned = sum(1 for x in self.usable_figures() if not x.captioned)
        if lang.startswith("no"):
            line = f"{f} figur(er) og {t} tabell(er) hentet ut av {self.source}"
            if uncaptioned:
                line += f"; {uncaptioned} uten bildetekst"
            return line
        line = f"{f} figure(s) and {t} table(s) from {self.source}"
        if uncaptioned:
            line += f"; {uncaptioned} without a caption"
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "source": self.source,
            "figures": [f.to_dict() for f in self.figures],
            "tables": [t.to_dict() for t in self.tables],
            "note": self.note,
        }


# ----------------------------------------------------------------------
def harvest(
    path: str | Path,
    *,
    text: str = "",
    raw_text: str = "",
    max_figures: int = 60,
) -> AssetHarvest:
    """Figures and tables from one PDF.

    Two text inputs, and the distinction matters. ``text`` is reflowed prose,
    where captions live. ``raw_text`` is the original line-wrapped output, which
    is the **only** place tables can be found — reflow joins short cells into
    sentences, so running table detection afterwards finds nothing. The fix for
    fragmented prose destroys the column structure that makes a table a table.
    """
    p = Path(path)
    result = AssetHarvest(source=p.name)

    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        result.note = "pypdf is not installed; no figures or tables can be read"
        return result

    try:
        reader = PdfReader(str(p))
    except Exception as exc:  # noqa: BLE001
        result.note = f"unreadable: {type(exc).__name__}"
        return result

    captions = _captions(text or "")

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            images = list(page.images)
        except Exception:  # noqa: BLE001 - a damaged image must not stop the page
            images = []
        for i, image in enumerate(images):
            if len(result.figures) >= max_figures:
                break
            width, height = _dimensions(image)
            fid = "FIG" + hashlib.sha1(
                f"{p.name}|{page_no}|{i}".encode()).hexdigest()[:6].upper()
            result.figures.append(Figure(
                id=fid, page=page_no, index=i,
                caption=captions.pop(0) if captions else "",
                width=width, height=height, source=p.name,
                data=getattr(image, "data", None),
            ))

    source_text = raw_text or text or ""
    result.tables = find_tables(source_text, source=p.name)
    if not result.tables and source_text:
        result.note = table_note(source_text)
    return result


def table_note(raw_text: str) -> str:
    """Why no tables were found, when none were.

    Distinguishes three cases a caller cannot otherwise tell apart: the document
    has none, the text was reflowed first, or the extractor flattened them.
    """
    lines = [l for l in raw_text.split("\n") if l.strip()]
    if not lines:
        return "no text to search"
    multi_cell = sum(1 for l in lines if len(CELL_SPLIT.split(l.strip())) >= 3)
    share = multi_cell / len(lines)
    if share < 0.02:
        return (
            "no column structure survives in this text — pypdf flattens tables to one "
            "cell per line, so tables cannot be recovered from it. Use a layout-aware "
            "extractor (pdfplumber) if this source is table-heavy."
        )
    return "column structure is present but no run of rows met the shape test"


def find_tables(text: str, *, source: str = "", min_rows: int = 2) -> list[Table]:
    """Runs of lines that share a column structure.

    pypdf gives no geometry, so a table is recognised by shape: consecutive lines
    that split into the same number of cells on runs of whitespace, with at least
    one numeric column. Prose does not do that.
    """
    tables: list[Table] = []
    page = 1
    run: list[list[str]] = []

    def flush() -> None:
        nonlocal run
        if len(run) >= min_rows:
            width = max(len(r) for r in run)
            if width >= 2 and _has_numeric_column(run):
                tid = "TBL" + hashlib.sha1(
                    f"{source}|{page}|{len(tables)}".encode()).hexdigest()[:6].upper()
                tables.append(Table(id=tid, page=page, rows=list(run), source=source))
        run = []

    for line in (text or "").split("\n"):
        stripped = line.strip()
        mark = re.match(r"^\s*\[page\s+(\d+)\]\s*$", stripped, re.I)
        if mark:
            flush()
            page = int(mark.group(1))
            continue
        cells = [c.strip() for c in CELL_SPLIT.split(stripped) if c.strip()]
        if len(cells) >= 2 and len(stripped) < 200:
            if run and abs(len(cells) - len(run[-1])) > 1:
                flush()
            run.append(cells)
        else:
            flush()
    flush()
    return tables


# ----------------------------------------------------------------------
def _captions(text: str) -> list[str]:
    """Caption lines, in document order. A figure without its caption is
    unusable in a document, and the caption is what makes it selectable."""
    out: list[str] = []
    for line in (text or "").split("\n"):
        m = CAPTION.match(line.strip())
        if m and m.group(3).strip():
            out.append(f"{m.group(1).title()} {m.group(2)}: {m.group(3).strip()}")
    return out


def _dimensions(image: Any) -> tuple[int, int]:
    for attr in ("image", "_image"):
        obj = getattr(image, attr, None)
        size = getattr(obj, "size", None)
        if size and len(size) == 2:
            return (int(size[0]), int(size[1]))
    data = getattr(image, "data", b"") or b""
    # Unknown size: assume usable rather than discard something real.
    return (200, 200) if len(data) > 4096 else (0, 0)


def _has_numeric_column(rows: Sequence[Sequence[str]]) -> bool:
    width = max(len(r) for r in rows)
    for column in range(width):
        values = [r[column] for r in rows if column < len(r)]
        if len(values) >= 2 and sum(1 for v in values if NUMERIC.match(v)) >= len(values) - 1:
            return True
    return False
