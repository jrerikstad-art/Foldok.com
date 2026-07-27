"""Editorial layer — professional document furniture (WORKORDER 0.49 Part B).

All code, zero model calls. Ledger purposes are computation-only.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Optional

# ── B1 TABLE COLUMN VOCABULARY ───────────────────────────────────────
# One dictionary, used everywhere. Labels: (id, no, en)

TABLE_COLUMN_VOCAB: dict[str, list[dict[str, str]]] = {
    "technical_data": [
        {"id": "param", "label": "Parameter", "label_en": "Parameter"},
        {"id": "value", "label": "Verdi", "label_en": "Value"},
        {"id": "unit", "label": "Enhet", "label_en": "Unit"},
        {"id": "source", "label": "Kilde", "label_en": "Source"},
    ],
    "components": [
        {"id": "nr", "label": "Nr", "label_en": "No."},
        {"id": "component", "label": "Komponent", "label_en": "Component"},
        {"id": "function", "label": "Funksjon", "label_en": "Function"},
        {"id": "source", "label": "Kilde", "label_en": "Source"},
    ],
    "drawings": [
        {"id": "dwg", "label": "Tegn.nr", "label_en": "Dwg no."},
        {"id": "title", "label": "Tittel", "label_en": "Title"},
        {"id": "rev", "label": "Rev", "label_en": "Rev"},
        {"id": "scale", "label": "Målestokk", "label_en": "Scale"},
        {"id": "source", "label": "Kilde", "label_en": "Source"},
    ],
    "requirements": [
        {"id": "id", "label": "ID", "label_en": "ID"},
        {"id": "req", "label": "Krav", "label_en": "Requirement"},
        {"id": "type", "label": "Type", "label_en": "Type"},
        {"id": "clause", "label": "Klausul", "label_en": "Clause"},
    ],
    "checks": [
        {"id": "point", "label": "Kontrollpunkt", "label_en": "Check point"},
        {"id": "criterion", "label": "Kriterium", "label_en": "Criterion"},
        {"id": "result", "label": "Resultat", "label_en": "Result"},
        {"id": "source", "label": "Kilde", "label_en": "Source"},
    ],
    "revisions": [
        {"id": "rev", "label": "Rev", "label_en": "Rev"},
        {"id": "date", "label": "Dato", "label_en": "Date"},
        {"id": "issued", "label": "Utstedt", "label_en": "Issued"},
        {"id": "prepared", "label": "Utarbeidet", "label_en": "Prepared"},
        {"id": "approved", "label": "Godkjent", "label_en": "Approved"},
    ],
    # BOM uses bom_engine columns — alias for lookup only
    "bom": [],
}

# Map section_key / structure hints → vocab key
_SECTION_VOCAB_ALIASES = {
    "technical_data": "technical_data",
    "tech": "technical_data",
    "spec_overview": "technical_data",
    "specifications": "technical_data",
    "main_components": "components",
    "components": "components",
    "product_description": "components",
    "drawings_register": "drawings",
    "drawings": "drawings",
    "requirements": "requirements",
    "acceptance_criteria": "checks",
    "checks": "checks",
    "test_results": "checks",
    "test_documentation": "checks",
    "revision_history": "revisions",
    "doc_control": "revisions",
    "bom": "bom",
}


def vocab_key_for_section(sec_key: str, section: Optional[dict] = None) -> str:
    sk = (sec_key or "").lower()
    if sk in _SECTION_VOCAB_ALIASES:
        return _SECTION_VOCAB_ALIASES[sk]
    wr = (section or {}).get("writing_rules") or {}
    structure = (wr.get("structure") or "").lower()
    if structure in ("table", "bom_table"):
        if "bom" in sk:
            return "bom"
        if "draw" in sk or "tegning" in sk:
            return "drawings"
        if "component" in sk or "komponent" in sk:
            return "components"
        if "revis" in sk:
            return "revisions"
        if "check" in sk or "kontroll" in sk or "test" in sk:
            return "checks"
        return "technical_data"
    title = (
        (section or {}).get("title_no")
        or (section or {}).get("title")
        or ""
    ).lower()
    for key, aliases in (
        ("components", ("komponent", "component")),
        ("drawings", ("tegning", "drawing")),
        ("revisions", ("revisjon", "revision")),
        ("checks", ("kontroll", "test", "sjekk")),
        ("requirements", ("krav", "requirement")),
    ):
        if any(a in title or a in sk for a in aliases):
            return key
    return "technical_data"


def columns_for(vocab_key: str, lang: str = "no") -> list[dict[str, str]]:
    cols = TABLE_COLUMN_VOCAB.get(vocab_key) or TABLE_COLUMN_VOCAB["technical_data"]
    return list(cols)


# ── B3 SECTION RHYTHM ────────────────────────────────────────────────
# identification → overview → technical data → procedure → maintenance →
# storage → declarations → registers/appendices. Template position = tiebreak.

EDITORIAL_RHYTHM: list[tuple[str, list[str]]] = [
    ("identification", [
        "cover", "title", "identif", "nameplate", "producer", "doc_control",
    ]),
    ("overview", [
        "overview", "summary", "scope", "intro", "description", "system",
        "parties",
    ]),
    ("technical_data", [
        "technical", "tech", "spec", "data", "parameter", "rating",
    ]),
    ("procedure", [
        "install", "assembl", "operat", "commission", "procedure", "use",
        "betjening", "montage",
    ]),
    ("maintenance", [
        "maintenance", "vedlikehold", "service", "spare", "troubleshoot",
        "fault", "feils",
    ]),
    ("storage", [
        "storage", "transport", "disposal", "lagring", "avfall", "packing",
    ]),
    ("declarations", [
        "declaration", "compliance", "legal", "warranty", "certificate",
        "samsvar",
    ]),
    ("registers", [
        "bom", "drawing", "tegning", "register", "appendix", "vedlegg",
        "glossary", "abbreviation", "revision", "illustrasjon", "toc",
        "contents", "innhold",
    ]),
]


def rhythm_bucket(title_or_key: str) -> str:
    t = (title_or_key or "").lower()
    for name, keys in EDITORIAL_RHYTHM:
        if any(k in t for k in keys):
            return name
    return "overview"


def sort_sections_editorial(section_defs: list[dict]) -> list[dict]:
    """Bind CompositionEngine-style buckets; template position is tiebreak."""
    order = {name: i for i, (name, _) in enumerate(EDITORIAL_RHYTHM)}

    def key(s: dict):
        sk = s.get("section_key") or s.get("key") or ""
        title = s.get("title_no") or s.get("title") or sk
        bucket = rhythm_bucket(f"{sk} {title}")
        return (order.get(bucket, 50), int(s.get("position") or 99), sk)

    return sorted(section_defs or [], key=key)


# ── B2 FIGURES ───────────────────────────────────────────────────────
FIGURE_MARK = re.compile(r"\{\{figure:([^}|]+):(\d+)(?:\|([^}]*))?\}\}")
FIG_SHORT = re.compile(r"\{\{fig:([^}|]+)\}\}")
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

_ACRONYM = re.compile(r"\b([A-ZÆØÅ]{2,}[A-ZÆØÅ0-9]{0,6})\b")


def number_figures(md: str, *, lang: str = "no", start: int = 1) -> tuple[str, list[dict]]:
    """Auto-number {{figure:…}} markers. Caption below as italic line.

    Returns (rewritten_md, [{n, file, page, caption}]).
    """
    label = "Illustrasjon" if lang != "en" else "Illustration"
    figures: list[dict] = []
    n = start

    def repl(m: re.Match) -> str:
        nonlocal n
        fname, page, cap = m.group(1), m.group(2), (m.group(3) or "").strip()
        if not cap:
            cap = Path(fname).name
        entry = {"n": n, "file": fname, "page": int(page or 0), "caption": cap}
        figures.append(entry)
        # Keep machine marker + human caption below (AKVA: italic caption)
        out = f"{{{{figure:{fname}:{page}|{cap}}}}}\n*{label} {n}: {cap}*"
        n += 1
        return out

    # Avoid double-numbering if already numbered
    if re.search(rf"\*{label} \d+:", md or ""):
        # Still collect for appendix
        for m in FIGURE_MARK.finditer(md or ""):
            figures.append({
                "n": len(figures) + start,
                "file": m.group(1),
                "page": int(m.group(2) or 0),
                "caption": (m.group(3) or Path(m.group(1)).name).strip(),
            })
        return md or "", figures

    return FIGURE_MARK.sub(repl, md or ""), figures


def build_illustration_appendix(figures: list[dict], *, lang: str = "no") -> str:
    """AKVA Appendix B style — auto-compiled, zero tokens."""
    if not figures:
        return ""
    title = "Illustrasjoner og tabeller" if lang != "en" else "Illustrations and tables"
    lines = [f"## {title}\n"]
    hdr = (
        "| Nr | Illustrasjon | Kilde |"
        if lang != "en"
        else "| No. | Illustration | Source |"
    )
    lines.append(hdr)
    lines.append("|---|---|---|")
    for f in figures:
        cap = (f.get("caption") or "").replace("|", "/")
        src = f.get("file") or ""
        lines.append(f"| {f.get('n')} | {cap} | {src} |")
    return "\n".join(lines) + "\n"


# ── B4 DOCUMENT FURNITURE ────────────────────────────────────────────

def build_title_page_md(
    artifact: dict,
    template: Optional[dict] = None,
    *,
    lang: str = "no",
    doc_no: str = "",
    revision: str = "A",
    export_date: Optional[str] = None,
    company: str = "",
    cover_figure: Optional[str] = None,
) -> str:
    """Title page markdown (structure only — logo via cover figure if present)."""
    artifact = artifact or {}
    template = template or {}
    title = artifact.get("name") or template.get("name_no") or template.get("name") or "Dokument"
    subtitle = (
        template.get("name_no") or template.get("name") or artifact.get("purpose") or ""
    )
    doc_no = doc_no or (template.get("document_no") or template.get("template_key") or "")
    export_date = export_date or date.today().isoformat()
    company = company or (artifact.get("manufacturer") or artifact.get("company") or "")
    lines = [
        "<!-- TITLE_PAGE -->",
        f"# {title}",
        "",
    ]
    if subtitle and subtitle != title:
        lines.append(f"**{subtitle}**")
        lines.append("")
    meta_rows = [
        ("Dokumentnr." if lang != "en" else "Document no.", doc_no or "—"),
        ("Revisjon" if lang != "en" else "Revision", revision or "—"),
        ("Dato" if lang != "en" else "Date", export_date),
    ]
    if company:
        meta_rows.append(("Selskap" if lang != "en" else "Company", company))
    lines.append("| | |")
    lines.append("|---|---|")
    for k, v in meta_rows:
        lines.append(f"| **{k}** | {v} |")
    lines.append("")
    if cover_figure:
        lines.append(f"{{{{figure:{cover_figure}:0|{title}}}}}")
        lines.append("")
    lines.append("---\n")
    return "\n".join(lines)


def build_toc_md(section_defs: list[dict], *, lang: str = "no", page_map: Optional[dict] = None) -> str:
    title = "Innhold" if lang != "en" else "Contents"
    lines = [f"## {title}\n"]
    page_map = page_map or {}
    for i, s in enumerate(section_defs or [], 1):
        st = s.get("title_no") or s.get("title") or s.get("section_key")
        sk = s.get("section_key") or ""
        pg = page_map.get(sk) or page_map.get(st) or ""
        if pg:
            lines.append(f"{i}. {st} …… {pg}")
        else:
            lines.append(f"{i}. {st}")
    lines.append("")
    return "\n".join(lines)


def compile_glossary_from_index(index: list, *, lang: str = "no", min_count: int = 2) -> str:
    """Abbreviations/glossary from repeated acronyms in captions/facts."""
    counts: dict[str, int] = {}
    stop = {
        "PDF", "JPG", "PNG", "DOC", "DOCX", "XLSX", "SVG", "HTML", "HTTP",
        "JSON", "API", "ID", "OK", "NO", "EN", "REV", "MM", "KG", "NM",
        "THE", "AND", "FOR", "MED", "TIL", "AV", "OG",
    }
    for e in index or []:
        blob = " ".join([
            e.get("caption") or "",
            e.get("detail_summary") or "",
            " ".join(str(f.get("value") or "") for f in (e.get("facts") or [])),
        ])
        for m in _ACRONYM.finditer(blob):
            tok = m.group(1)
            if tok in stop or len(tok) < 2:
                continue
            counts[tok] = counts.get(tok, 0) + 1
    items = sorted(
        ((k, c) for k, c in counts.items() if c >= min_count),
        key=lambda x: (-x[1], x[0]),
    )[:40]
    if not items:
        return ""
    title = "Forkortelser" if lang != "en" else "Abbreviations"
    lines = [f"## {title}\n", "| Forkortelse | Forekomster |" if lang != "en" else "| Abbreviation | Count |", "|---|---|"]
    for k, c in items:
        lines.append(f"| {k} | {c} |")
    lines.append("")
    return "\n".join(lines)


def empty_revision_table(lang: str = "no") -> str:
    cols = columns_for("revisions", lang)
    lab = "label" if lang != "en" else "label_en"
    header = "| " + " | ".join(c.get(lab) or c["label"] for c in cols) + " |"
    sep = "|" + "---|" * len(cols)
    empty = "| " + " | ".join("—" for _ in cols) + " |"
    title = "Revisjonshistorikk" if lang != "en" else "Revision history"
    return f"## {title}\n\n{header}\n{sep}\n{empty}\n"


# ── B6 CROSS-REFERENCES ──────────────────────────────────────────────
_SEE_REF = re.compile(
    r"(?i)\bse\s+avsnitt\s+(\d+(?:\.\d+)*)\b"
    r"|\bsee\s+section\s+(\d+(?:\.\d+)*)\b"
    r"|\{\{ref:([^}]+)\}\}"
)


def resolve_cross_refs(md: str, section_numbers: dict[str, str]) -> str:
    """Resolve «se avsnitt 3.1» / {{ref:key}} using numbered section map.

    Unresolved refs are dropped (never left dangling).
    section_numbers: {"3.1": "Technical data", "technical_data": "3.1", ...}
    """
    if not md:
        return md

    def repl(m: re.Match) -> str:
        num = m.group(1) or m.group(2)
        key = m.group(3)
        if key:
            target = section_numbers.get(key) or section_numbers.get(key.lower())
            if not target:
                return ""
            # If map stores number for key
            if re.match(r"^\d", str(target)):
                return f"[se avsnitt {target}](#sec-{target.replace('.', '-')})"
            return f"[se avsnitt {key}](#sec-{key})"
        if num and (num in section_numbers or any(
            str(v) == num for v in section_numbers.values()
        )):
            return f"[se avsnitt {num}](#sec-{num.replace('.', '-')})"
        return ""  # drop unresolved

    return _SEE_REF.sub(repl, md)


def build_section_number_map(section_defs: list[dict]) -> dict[str, str]:
    """1-based section numbers from editorial order."""
    out: dict[str, str] = {}
    for i, s in enumerate(section_defs or [], 1):
        num = str(i)
        sk = s.get("section_key") or ""
        title = s.get("title_no") or s.get("title") or sk
        out[sk] = num
        out[title] = num
        out[num] = title
    return out


# ── Compose full editorial markdown ──────────────────────────────────

def apply_editorial_furniture(
    body_md: str,
    *,
    artifact: dict,
    template: dict,
    section_defs: list[dict],
    index: Optional[list] = None,
    lang: str = "no",
    cover_figure: Optional[str] = None,
    doc_meta: Optional[dict] = None,
) -> str:
    """Wrap body with title page, TOC, revision table, glossary, illustration index.

    Adds ZERO model calls.
    """
    meta = doc_meta or {}
    numbered, figures = number_figures(body_md, lang=lang)
    numbered = resolve_cross_refs(
        numbered, build_section_number_map(section_defs),
    )
    parts = [
        build_title_page_md(
            artifact,
            template,
            lang=lang,
            doc_no=meta.get("document_no") or "",
            revision=meta.get("revision") or "A",
            export_date=meta.get("export_date"),
            company=meta.get("company") or "",
            cover_figure=cover_figure,
        ),
        build_toc_md(section_defs, lang=lang, page_map=meta.get("page_map")),
        empty_revision_table(lang),
    ]
    gloss = compile_glossary_from_index(index or [], lang=lang)
    if gloss:
        parts.append(gloss)
    parts.append(numbered)
    appendix = build_illustration_appendix(figures, lang=lang)
    if appendix:
        parts.append(appendix)
    return "\n".join(parts)
