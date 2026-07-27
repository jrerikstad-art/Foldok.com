"""LEARNING_AND_BOUNDARIES §1 — classify chat drops into existing pipelines."""
from __future__ import annotations

import re
from pathlib import Path

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".tif", ".tiff", ".bmp"}
SHEET_EXT = {".xlsx", ".xls", ".csv"}
DOC_EXT = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"}

FORM_NAME = re.compile(
    r"(sja|skjema|sjekkliste|checklist|blank[\s_-]?form|\bform\b|\bmal\b|template|"
    r"avviksskjema|kontrollskjema|egenkontroll|multipoint|inspection|"
    r"m%C3%B8tereferat|motereferat)",
    re.I,
)
FORM_TEXT = re.compile(
    r"(utfylt\s+av|signatur|dato\s*:|navn\s*:|\[\s*\]|_{3,}|"
    r"skjema|sjekkliste|ikke\s+relevant|avvik|sja\b)",
    re.I,
)
FILLED_SIGNAL = re.compile(
    r"(tegning|rev\.?\s*\d|snitt|plan\s+\d|bom\b|spesifikasjon)",
    re.I,
)


def dest_subdir(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in PHOTO_EXT:
        return "Bilder"
    if ext in {".pdf", ".dwg", ".dxf"} and re.search(r"tegning|plan|snitt|k-\d", name, re.I):
        return "Tegninger"
    if ext in SHEET_EXT or ext in DOC_EXT:
        return "Notater"
    return "Bilder" if ext in PHOTO_EXT else "Notater"


def peek_text_bytes(raw: bytes, name: str, limit: int = 8000) -> str:
    """Cheap text peek for classification — no AI."""
    ext = Path(name).suffix.lower()
    if ext in {".txt", ".md", ".csv", ".json"}:
        try:
            return raw[:limit].decode("utf-8", errors="ignore")
        except Exception:
            return ""
    # PDF/DOCX: try MarkItDown only when classifying ambiguous docs
    if ext in {".pdf", ".docx", ".doc", ".xlsx"}:
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(raw)
                tmp_path = Path(tmp.name)
            try:
                from markitdown import MarkItDown
                return (MarkItDown().convert(str(tmp_path)).text_content or "")[:limit]
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception:
            return ""
    return ""


def classify(name: str, raw: bytes | None = None, text: str | None = None,
             user_choice: str | None = None) -> dict:
    """
    Returns {kind: form_template|project_material|ambiguous, reason}.
    user_choice: 'form' | 'project' forces the route.
    """
    if user_choice in ("form", "form_template", "template"):
        return {"kind": "form_template", "reason": "user_choice"}
    if user_choice in ("project", "project_material", "source"):
        return {"kind": "project_material", "reason": "user_choice"}

    ext = Path(name or "").suffix.lower()
    # WORKORDER_0.30 — skjema.jpg / form photos are templates, not project material
    if FORM_NAME.search(name or ""):
        return {"kind": "form_template", "reason": "filename"}

    if ext in PHOTO_EXT:
        return {"kind": "project_material", "reason": "image"}

    peek = text if text is not None else (
        peek_text_bytes(raw, name) if raw is not None else "")

    if peek:
        form_hits = len(FORM_TEXT.findall(peek))
        filled = len(FILLED_SIGNAL.findall(peek))
        blankish = peek.count("_") + peek.count("[ ]") + peek.count("☐")
        if form_hits >= 2 or (form_hits >= 1 and blankish >= 3 and filled < 2):
            return {"kind": "form_template", "reason": "blank_form_signals"}
        if ext == ".pdf" and form_hits >= 1 and filled < 2:
            return {"kind": "ambiguous", "reason": "pdf_could_be_either"}
        if filled >= 2 and form_hits == 0:
            return {"kind": "project_material", "reason": "filled_doc_signals"}

    if ext == ".pdf":
        return {"kind": "ambiguous", "reason": "pdf_unclassified"}
    if ext in DOC_EXT or ext in SHEET_EXT:
        return {"kind": "project_material", "reason": "document"}
    return {"kind": "project_material", "reason": "default"}


IMPORT_AS_TEMPLATE = re.compile(
    r"(?:"
    r"(?:lag|create|make|bruk|importer?|import)\b.{0,80}\b(?:som\s+mal|as\s+(?:a\s+)?template|til\s+(?:en\s+)?mal)\b|"
    r"\b(?:som\s+mal|as\s+(?:a\s+)?template)\b"
    r")",
    re.I,
)
FILE_MENTION = re.compile(
    r"([\w.\-æøåÆØÅ]+\.(?:jpg|jpeg|png|webp|gif|pdf|docx?|xlsx?|csv))",
    re.I,
)


def is_import_as_template_ask(msg: str) -> bool:
    return bool(IMPORT_AS_TEMPLATE.search(msg or ""))


def mentioned_filename(msg: str) -> str | None:
    m = FILE_MENTION.search(msg or "")
    return m.group(1) if m else None


def find_project_file(folders: list, name: str):
    """Locate a project file by basename (case-insensitive)."""
    if not name:
        return None
    want = name.lower().replace("\\", "/")
    base = Path(want).name.lower()
    for folder in folders or []:
        root = Path(folder)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.name.lower() == base:
                return p
            try:
                rel = str(p.relative_to(root)).replace("\\", "/").lower()
            except ValueError:
                continue
            if rel == want or rel.endswith("/" + base):
                return p
    return None
