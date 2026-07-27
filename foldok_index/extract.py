"""Extraction.

One rule: **zero text is never a success.**

The most common cause of "I indexed it and the agent can't see it" is a scanned
PDF or an unsupported format going through a pipeline that catches the exception,
logs a warning nobody reads, writes a document row with zero chunks, and returns
"indexed: ok".  Every layer downstream then behaves correctly on nothing.

So extraction returns a status, and the caller cannot mistake empty for fine.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

TEXT_SUFFIXES = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".py", ".js", ".ts", ".dart",
    ".java", ".c", ".h", ".cpp", ".sql", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".html", ".htm", ".xml", ".svg",
}

MIN_USEFUL_CHARS = 24


@dataclass
class Extraction:
    text: str
    status: str                 # "ok" | "empty" | "unsupported" | "failed"
    detail: str = ""
    fix: str = ""
    title: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def extract(path: str | Path) -> Extraction:
    p = Path(path)
    if not p.exists():
        return Extraction("", "failed", f"{p} does not exist", "check the path")
    suffix = p.suffix.lower()
    try:
        handler = _HANDLERS.get(suffix)
        if handler is None:
            if suffix in TEXT_SUFFIXES:
                handler = _plain
            else:
                return Extraction(
                    "", "unsupported",
                    f"no extractor for '{suffix}'",
                    "add an extractor, or convert the file to text/PDF before indexing",
                )
        result = handler(p)
    except Exception as exc:                       # noqa: BLE001 - report, never swallow
        return Extraction(
            "", "failed", f"{type(exc).__name__}: {exc}",
            "the file may be corrupt, encrypted, or not what its extension claims",
        )

    text = _tidy(result.text)
    if len(text.strip()) < MIN_USEFUL_CHARS:
        return Extraction(
            text, "empty",
            f"only {len(text.strip())} characters of text came out",
            "if this is a scanned document it needs OCR before it can be indexed; "
            "an empty extraction is never indexed, because it would look like a "
            "successful upload that the assistant can never find",
            title=result.title or p.stem,
        )
    return Extraction(text, "ok", title=result.title or p.stem)


# ----------------------------------------------------------------------
def _plain(p: Path) -> Extraction:
    raw = p.read_text(encoding="utf-8", errors="replace")
    title = ""
    for line in raw.splitlines():
        if line.strip():
            title = line.lstrip("# ").strip()[:120]
            break
    return Extraction(raw, "ok", title=title)


def _csvish(p: Path) -> Extraction:
    delim = "\t" if p.suffix.lower() == ".tsv" else ","
    rows = []
    with p.open(newline="", encoding="utf-8", errors="replace") as fh:
        for i, row in enumerate(csv.reader(fh, delimiter=delim)):
            rows.append(" | ".join(c.strip() for c in row))
            if i > 20000:
                rows.append("... (truncated)")
                break
    return Extraction("\n".join(rows), "ok", title=p.stem)


def _jsonish(p: Path) -> Extraction:
    data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    return Extraction(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), "ok", title=p.stem)


def _docx(p: Path) -> Extraction:
    """No dependency: a .docx is a zip with XML inside."""
    with zipfile.ZipFile(p) as zf:
        names = [n for n in zf.namelist() if n.startswith("word/") and n.endswith(".xml")]
        if "word/document.xml" not in names:
            return Extraction("", "failed", "no word/document.xml inside the archive")
        xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return Extraction(text, "ok", title=p.stem)


def _pdf(p: Path) -> Extraction:
    try:
        from pypdf import PdfReader                      # type: ignore
    except ImportError:
        return Extraction(
            "", "unsupported",
            "no PDF text extractor is installed",
            "pip install pypdf — and note that a scanned PDF will still need OCR",
        )
    reader = PdfReader(str(p))
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:                                 # noqa: BLE001
            return Extraction("", "failed", "the PDF is encrypted", "supply the password")
    pages = []
    for i, page in enumerate(reader.pages):
        pages.append(f"[page {i + 1}]\n" + (page.extract_text() or ""))
    title = ""
    try:
        title = (reader.metadata or {}).get("/Title", "") or ""
    except Exception:                                     # noqa: BLE001
        title = ""
    return Extraction("\n\n".join(pages), "ok", title=str(title) or p.stem)


_HANDLERS: dict[str, Callable[[Path], Extraction]] = {
    ".csv": _csvish,
    ".tsv": _csvish,
    ".json": _jsonish,
    ".jsonl": _plain,
    ".docx": _docx,
    ".pdf": _pdf,
}


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def supported_suffixes() -> list[str]:
    return sorted(TEXT_SUFFIXES | set(_HANDLERS))
