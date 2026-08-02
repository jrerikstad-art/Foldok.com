"""Wire foldok_corpus into every generated document.

Naming the template first made its section list a ceiling. After the fixed
sections are authored, the folder still proposes what it can support — the same
appendix on installation manuals, topic briefs, research reports, and the rest.

    md = compile_document_corpus_md(index, artifact, lang="no")
    content = inject_corpus_appendix(content, md)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Sequence

from .market import build_offer
from .widen import extract_many

# Already covered by almost every template's end-matter / fixed outline.
_SKIP_KEYS = {
    "sec.fact", "sec.page", "sec.caption", "sec.tag", "sec.claim",
    "sec.rule", "sec.quantity", "sec.reference", "sec.definition",
    "sec.classification",
}
_SKIP_TITLES = {
    "caption", "fact", "page", "tag", "claim", "krav", "requirements",
    "begreper", "definitions", "klassifisering", "classification",
    "tekniske data", "technical data", "referanser", "references",
}

_END_MATTER = re.compile(
    r"(?im)^##\s+("
    r"Kilder|Sources|Kilderegister|Source register|"
    r"Åpne punkter|Open points|Open items|"
    r"Dokumentkontroll|Document control|"
    r"Vedlegg|Appendix|Annex"
    r")\s*$"
)


def docs_from_index(
    index: Sequence[dict] | None,
    artifact: dict | None = None,
    *,
    max_pdfs: int = 5,
    max_pages: int = 40,
) -> list[tuple[str, str]]:
    """(source, text) for extract_many — captions/facts always; top PDFs fully."""
    art = artifact if isinstance(artifact, dict) else {}
    folders = list(art.get("_folders") or [])
    focus_needles = [
        str(x).lower() for x in (art.get("install_focus_sources") or []) if str(x).strip()
    ]

    entries = [
        e for e in (index or [])
        if e.get("file") and e.get("kind") != "skipped"
    ]

    def _is_focus(fn: str) -> bool:
        low = fn.lower().replace("\\", "/")
        return any(n in low for n in focus_needles) if focus_needles else False

    # Rank PDFs: focus first, then by fact/page richness
    pdfs = [e for e in entries if str(e.get("file") or "").lower().endswith(".pdf")]
    pdfs.sort(key=lambda e: (
        0 if _is_focus(str(e.get("file") or "")) else 1,
        -len(e.get("facts") or []),
        -int((e.get("extraction_stats") or {}).get("page_count") or 0),
    ))
    chosen = pdfs[: max(max_pdfs, len([e for e in pdfs if _is_focus(str(e.get("file") or ""))]))]

    docs: list[tuple[str, str]] = []
    seen_src: set[str] = set()

    for e in chosen:
        fn = str(e.get("file") or "")
        text = _pdf_text(fn, folders, max_pages=max_pages)
        if len(text) < 80:
            text = _entry_blob(e)
        if len(text) >= 80:
            src = Path(fn).name
            docs.append((src, text))
            seen_src.add(fn)

    # Captions / facts from the rest of the folder (no full PDF read)
    for e in entries:
        fn = str(e.get("file") or "")
        if fn in seen_src:
            continue
        text = _entry_blob(e)
        if len(text) >= 80:
            docs.append((Path(fn).name, text))

    return docs


def compile_document_corpus_md(
    index: Sequence[dict] | None,
    artifact: dict | None = None,
    *,
    lang: str = "no",
    limit: int = 8,
    exclude_titles: Iterable[str] | None = None,
    max_pdfs: int = 5,
) -> str:
    """Optional «Fra mappen» appendix — same shape for every template."""
    art = artifact if isinstance(artifact, dict) else {}
    cached = art.get("_document_corpus_md")
    if isinstance(cached, str) and cached:
        return cached
    if cached == "":
        return ""

    docs = docs_from_index(index, art, max_pdfs=max_pdfs)
    if not docs:
        art["_document_corpus_md"] = ""
        return ""

    wide = extract_many(docs)
    if len(wide.claims) < 2:
        art["_document_corpus_md"] = ""
        art["_document_corpus_note"] = wide.summary(lang=lang)
        return ""

    n_files = len({src for src, _ in docs})
    min_sources = 1 if n_files <= 1 else 2
    offer = build_offer(
        [c.to_dict() for c in wide.claims],
        lang=lang, min_weight=2, min_sources=min_sources,
    )

    excluded = {t.strip().lower() for t in (exclude_titles or []) if t and t.strip()}
    no = not str(lang or "no").lower().startswith("en")
    kept = []
    for o in offer.ordered():
        if o.key in _SKIP_KEYS:
            continue
        title = (o.title or "").strip()
        if not title or title.lower() in _SKIP_TITLES or title.lower() in excluded:
            continue
        samples = [str(s).strip() for s in (o.samples or []) if str(s).strip()]
        if len(samples) < 2 and o.weight < 4:
            continue
        kept.append((o, samples))
        if len(kept) >= limit:
            break

    if not kept:
        art["_document_corpus_md"] = ""
        art["_document_corpus_note"] = offer.report(lang=lang).split("\n")[0]
        return ""

    lines = [
        "",
        "## " + ("Fra mappen (slett det du ikke vil ha)" if no else "From the folder (delete what you do not want)"),
        "",
        "*" + (
            f"{len(kept)} seksjon(er) foreslått fra {wide.summary(lang=lang)}. "
            "Dokumenttypen avgjør den faste disposisjonen; mappen foreslår resten."
            if no else
            f"{len(kept)} section(s) proposed from {wide.summary(lang=lang)}. "
            "The document type sets the fixed outline; the folder proposes the rest."
        ) + "*",
        "",
    ]
    for o, samples in kept:
        lines.append(f"### {o.title}")
        lines.append("")
        lines.append("*" + o.explain(lang=lang) + "*")
        lines.append("")
        for i, sample in enumerate(samples[:5]):
            src = o.sources[i % len(o.sources)] if o.sources else ""
            cite = f" ({src})" if src else ""
            q = sample if sample.endswith((".", "!", "?")) else sample + "."
            lines.append(f"- {q}{cite}")
        lines.append("")

    md = "\n".join(lines).rstrip() + "\n"
    art["_document_corpus_note"] = f"+{len(kept)} · {wide.summary(lang=lang)}"
    art["_document_corpus_md"] = md
    return md


def inject_corpus_appendix(content: str, appendix: str) -> str:
    """Insert corpus block before end-matter; skip if already present."""
    body = content or ""
    block = (appendix or "").strip()
    if not block:
        return body
    if "Fra mappen (slett det du ikke vil ha)" in body or "From the folder (delete what you do not want)" in body:
        return body
    m = _END_MATTER.search(body)
    if m:
        return body[: m.start()].rstrip() + "\n\n" + block + "\n\n" + body[m.start() :]
    return body.rstrip() + "\n\n" + block + "\n"


def headings_in(content: str) -> list[str]:
    return re.findall(r"(?m)^#{2,3}\s+(.+?)\s*$", content or "")


# ----------------------------------------------------------------------
def _entry_blob(entry: dict) -> str:
    parts: list[str] = []
    for key in ("caption", "detail_summary", "summary", "text"):
        val = str(entry.get(key) or "").strip()
        if len(val) >= 25:
            parts.append(val)
    for f in entry.get("facts") or []:
        if isinstance(f, dict):
            val = str(f.get("value") or "").strip()
            if len(val) >= 25:
                parts.append(val)
    return "\n".join(parts)


def _pdf_text(rel: str, folders: Iterable[str], *, max_pages: int = 40) -> str:
    path = _resolve(rel, folders)
    if not path:
        return ""
    try:
        from foldok_compile import extract_pdf_pages
        pages = extract_pdf_pages(path) or []
    except Exception:
        return ""
    return "\n".join(str(p.get("text") or "") for p in pages[:max_pages])


def _resolve(rel: str, folders: Iterable[str]) -> Path | None:
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if not rel:
        return None
    for folder in folders or []:
        base = Path(folder)
        cand = base / rel
        if cand.is_file():
            return cand
        parts = Path(rel).parts
        if len(parts) > 1:
            cand2 = base / Path(*parts[1:])
            if cand2.is_file():
                return cand2
        name = Path(rel).name
        for p in list(base.rglob(name))[:3]:
            if p.is_file():
                return p
    return None
