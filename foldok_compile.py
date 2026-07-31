#!/usr/bin/env python3
"""
FOLDOK headless compiler — engine contract v1 reference implementation.

    python foldok_compile.py ./my-project-folder \
        --template templates/technical_doc_package.json \
        --lang no --out ./draft.md

Proves the engine on a real folder BEFORE any UI is wired to it:
  index once → checkpoint A (confirm) → checkpoint B (map + gaps)
  → checkpoint C (generate with citation rule) → markdown draft + reports.

Requirements:
    pip install anthropic markitdown pillow
    export ANTHROPIC_API_KEY=sk-ant-...

Contract rules enforced here (see ENGINE_CONTRACT.md):
  * every file indexed exactly once (sha256 cache in .foldok_cache/)
  * nothing right of the index reads original files
  * every factual claim in generated prose must cite {{fact:ID}};
    missing values render as [MANGLER: key], never invented
  * every API call logged to the token ledger with purpose + cost
"""

import argparse, base64, hashlib, io, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bom_engine import ELEMENT_PROMPT_ADDON, aggregate_bom, render_bom_markdown, detect_suggestions

ENGINE_ROOT = Path(__file__).resolve().parent

# Windows consoles default to cp1252, which cannot print ◆/⚠/✗/→
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

# ── models & pricing (EUR per 1M tokens, approximate) ────────────────
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"
PRICE = {  # (input, output)
    HAIKU: (0.90, 4.50),
    SONNET: (2.70, 13.50),
}

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff", ".bmp", ".svg"}
DOC_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".rtf"}
CAD_EXT = {".step", ".stp", ".iges", ".igs", ".fcstd", ".dxf", ".dwg", ".stl", ".obj", ".brep"}
FIGURE_MARK = re.compile(r"\{\{figure:([^}|]+):(\d+)(?:\|([^}]*))?\}\}")
FIG_SHORT_MARK = re.compile(r"\{\{fig:([^}|]+)\}\}")
ILLUST_BLOCK = re.compile(
    r"\n*###\s*Illustrasjoner\s*\n(?:.*?)(?=\n###\s|\n##\s|\Z)", re.S | re.I)

client = anthropic.Anthropic()
LEDGER = []


def log_call(purpose, model, usage):
    i, o = usage.input_tokens, usage.output_tokens
    pin, pout = PRICE[model]
    cost = (i * pin + o * pout) / 1_000_000
    LEDGER.append({"purpose": purpose, "model": model, "in": i, "out": o, "eur": round(cost, 5)})
    return cost


def ask(purpose, model, messages, system=None, max_tokens=1500):
    kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    log_call(purpose, model, resp.usage)
    return resp.content[0].text


def parse_json(text):
    """Tolerant JSON extraction from a model reply."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"[\[{].*[\]}]", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def ask_json(purpose, model, messages, system=None, max_tokens=1500):
    """ask() + parse_json with one retry when the reply is malformed or
    truncated (large projects can overflow the token budget mid-JSON)."""
    raw = ask(purpose, model, messages, system=system, max_tokens=max_tokens)
    try:
        return parse_json(raw)
    except json.JSONDecodeError:
        print(f"  ⚠ JSON parse failed ({purpose}), retrying…")
        retry_system = ((system + "\n\n") if system else "") + \
            "IMPORTANT: Reply with COMPLETE valid JSON only. Keep lists brief so the whole reply fits."
        raw = ask(purpose, model, messages, system=retry_system, max_tokens=max_tokens)
        return parse_json(raw)


def load_template_catalog():
    """All system templates for intent resolution — key, name, description, applies_to."""
    out = []
    for p in sorted((ENGINE_ROOT / "templates").glob("*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        out.append({
            "key": t.get("template_key"),
            "file": p.name,
            "name_no": t.get("name_no") or t.get("name"),
            "description": (t.get("description") or "")[:400],
            "applies_to": t.get("applies_to") or [],
        })
    return out


def resolve_template_intent(story, artifact, lang="no", project_context=None):
    """One Haiku call: choose template from catalog or honest no_fit."""
    catalog = load_template_catalog()
    valid_keys = {t["key"] for t in catalog if t.get("key")}
    art_json = json.dumps(artifact or {}, ensure_ascii=False)[:2500]
    cat_json = json.dumps(catalog, ensure_ascii=False)
    ctx_block = (project_context.strip() + "\n\n") if project_context else ""
    prompt = f"""{ctx_block}User describes what they need from this documentation project.
Choose the best matching template from the catalog ONLY — never invent template keys.

ARTIFACT MODEL (checkpoint A):
{art_json}

TEMPLATE CATALOG (all {len(catalog)} templates):
{cat_json}

USER STORY:
{story.strip()}

Reply ONLY JSON:
{{
  "choice": "<template_key from catalog>",
  "confidence": 0.0-1.0,
  "why_no": "1-2 setninger på norsk som siterer brukerens egne ord",
  "alternatives": [{{"key": "<template_key>", "why_no": "..."}}],
  "no_fit": false
}}

If nothing fits honestly, set no_fit to an object (not false):
{{"suggested_name": "...", "suggested_outline": ["section 1", "section 2", ...]}}
and omit choice or set choice to null. alternatives max 2.
Never invent keys outside the catalog."""
    raw = ask_json("template_intent", HAIKU, [{"role": "user", "content": prompt}], max_tokens=900)
    choice = raw.get("choice")
    no_fit = raw.get("no_fit")
    if choice and choice not in valid_keys:
        choice = None
        no_fit = no_fit or {
            "suggested_name": raw.get("suggested_name") or "Tilpasset dokument",
            "suggested_outline": raw.get("suggested_outline") or [],
        }
    if no_fit and choice:
        choice = None
    alts = []
    for a in (raw.get("alternatives") or [])[:2]:
        k = a.get("key")
        if k in valid_keys:
            t = next(x for x in catalog if x["key"] == k)
            alts.append({"key": k, "file": t["file"], "name_no": t["name_no"],
                         "why_no": a.get("why_no") or ""})
    result = {
        "choice": choice,
        "confidence": raw.get("confidence", 0),
        "why_no": raw.get("why_no") or "",
        "alternatives": alts,
        "no_fit": no_fit if no_fit else False,
        "cost_eur": round(LEDGER[-1]["eur"], 4) if LEDGER else 0,
    }
    if choice:
        t = next(x for x in catalog if x["key"] == choice)
        result["file"] = t["file"]
        result["name_no"] = t["name_no"]
    return result


# ── 1. INDEXING ──────────────────────────────────────────────────────
INDEX_SYSTEM = """You index project files for a technical documentation compiler.
Reply ONLY with JSON:
{
 "caption": "<=40 words, dense, factual, in %LANG%",
 "detail_summary": "<=200 words or null (documents only)",
 "content_tags": ["snake_case", ...],
 "doc_role_hints": ["overview|installation_step|technical_data|safety|maintenance|test_result|certificate|wiring|nameplate|damage|packaging|environment|drawing|site_plan|schematic|sketch|contract_clause|tender_requirement|deliverable|obligation|penalty|scope"],
 "quality_flags": ["blurry|dark|screenshot|irrelevant"],
 "facts": [
   {"fact_type":"spec|measurement|identifier|date|material|rating|standard_ref|instruction|warning|contact|decision|assumption|load|criterion|obligation|deliverable|deadline|penalty|right|requirement|element",
    "key":"canonical_snake_case. Physical: swl, weight, serial_no, test_standard, dimensions. Contracts/permits/correspondence: party, obligation, deliverable, deadline, penalty, right, requirement, contract_ref, case_ref, scope_statement, issuer. PREFER these canonical keys over invented compounds (use key=deadline + descriptive source_excerpt, NOT documentation_submission_deadline). For fact_type=element: key=beam|stud|column|…, value=profile as written, optional props {qty,length_mm,material}",
    "value":"...", "unit":"t|kg|mm|A|MΩ|null",
    "confidence":0.0-1.0,
    "source_excerpt":"verbatim snippet",
    "source_location":"nameplate in photo | page N | cell ref"}
 ]
}
For technical/architectural drawings: role=drawing (or site_plan/schematic/sketch), and extract title-block facts: drawing_no, revision, scale, drawing_title — these make the drawings register (tegningsliste) build itself.
Files whose path or name contains PLANTEGNING, FASADETEGNING, SNITT, SITUASJON, PERSPEKTIV, or TEGNING are drawings — tag role=drawing even when the file is a PDF.
Building area / tilbygg size: use canonical key floor_area or gross_area (unit m²) — NOT invented keys like new_building_area or new_area_total.
Extract ONLY facts explicitly present. Partially legible → lower confidence.
Never infer. Never compute. Never complete a value.
Cap the facts array at 25 entries — prioritize parties, obligations,
deadlines, deliverables, and requirements over minor details.""" + ELEMENT_PROMPT_ADDON


def shrink_image(path, max_px=1024):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("pip install pillow")
    img = Image.open(path)
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=82)
    return base64.standard_b64encode(buf.getvalue()).decode()


def shrink_image_bytes(jpeg_bytes: bytes, max_px=1024) -> str:
    """Base64 JPEG from raw image bytes (PDF page rasters)."""
    try:
        from PIL import Image
    except ImportError:
        sys.exit("pip install pillow")
    img = Image.open(io.BytesIO(jpeg_bytes))
    img.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=82)
    return base64.standard_b64encode(buf.getvalue()).decode()


# Thin-page threshold for technical manuals (scanned / image-only pages)
THIN_PAGE_CHARS = 80
MAX_VISION_PAGES = 12  # cost cap per PDF


def extract_pdf_pages(path: Path) -> list[dict]:
    """Per-page text extraction via PyMuPDF. Returns [{page, text, chars}, …]."""
    try:
        import fitz
    except ImportError:
        return []
    doc = fitz.open(path)
    try:
        out = []
        for i in range(len(doc)):
            text = doc[i].get_text("text") or ""
            out.append({"page": i + 1, "text": text, "chars": len(text.strip())})
        return out
    finally:
        doc.close()


def render_pdf_page_jpeg(path: Path, page_1based: int, scale: float = 1.5) -> bytes | None:
    """Rasterize one PDF page to JPEG bytes (1-based page index)."""
    try:
        import fitz
    except ImportError:
        return None
    doc = fitz.open(path)
    try:
        idx = max(0, min(page_1based - 1, len(doc) - 1))
        pix = doc[idx].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pix.tobytes("jpeg")
    finally:
        doc.close()


def page_extraction_stats(pages: list[dict], facts: list | None = None) -> dict:
    """Instrument chars-per-page and facts-per-page for technical manuals."""
    chars_per_page = {str(p["page"]): p["chars"] for p in pages}
    thin_pages = [p["page"] for p in pages if p["chars"] < THIN_PAGE_CHARS]
    facts_per_page: dict[str, int] = {str(p["page"]): 0 for p in pages}
    for f in facts or []:
        loc = (f.get("source_location") or "").lower()
        m = re.search(r"page\s*(\d+)", loc)
        if m:
            key = m.group(1)
            facts_per_page[key] = facts_per_page.get(key, 0) + 1
    return {
        "page_count": len(pages),
        "chars_per_page": chars_per_page,
        "facts_per_page": facts_per_page,
        "thin_pages": thin_pages,
        "thin_page_threshold": THIN_PAGE_CHARS,
        "total_chars": sum(p["chars"] for p in pages),
        "vision_pages": [],
    }


def index_pdf_with_depth(path: Path, lang: str, rel_name: str, system: str) -> tuple[str, dict, list]:
    """Index a PDF with per-page instrumentation + vision fallback for thin pages.

    Returns (raw_json_from_text_index, extraction_stats, extra_vision_facts).
    """
    pages = extract_pdf_pages(path)
    partial = False
    if pages and len(pages) > 200:
        # WORKORDER 0.55 D1 — first 60 pages + leave TOC-ish early pages
        pages = pages[:60]
        partial = True
    stats = page_extraction_stats(pages) if pages else {
        "page_count": 0, "chars_per_page": {}, "facts_per_page": {},
        "thin_pages": [], "thin_page_threshold": THIN_PAGE_CHARS,
        "total_chars": 0, "vision_pages": [], "fallback": "no_fitz",
    }
    if partial:
        stats["partial_index"] = True
        stats["partial_note"] = "delvis indeksert — PDF >200 sider; første 60 sider"

    # Dense text for the primary Haiku text pass
    dense_parts = []
    for p in pages:
        if p["chars"] >= THIN_PAGE_CHARS:
            dense_parts.append(f"--- page {p['page']} ---\n{p['text']}")
    dense_text = "\n\n".join(dense_parts).strip()

    if not dense_text:
        # Whole PDF thin (scanned) — try MarkItDown then fall back to filename stub
        try:
            from markitdown import MarkItDown
            dense_text = (MarkItDown().convert(str(path)).text_content or "").strip()
        except Exception as e:
            dense_text = f"(thin PDF extraction; MarkItDown: {e}) filename: {path.name}"
        if not dense_text:
            dense_text = f"(scanned or image-only PDF) filename: {path.name}"

    raw = ask("index_doc", HAIKU,
              [{"role": "user", "content":
                f"Index this document. Path (folder names are role hints): {rel_name}\n\n"
                f"{dense_text[:24000]}"}],
              system=system, max_tokens=4096)

    # Vision fallback for thin pages (canonical for technical manuals)
    vision_facts = []
    visioned = []
    thin = stats.get("thin_pages") or []
    for page_no in thin[:MAX_VISION_PAGES]:
        jpeg = render_pdf_page_jpeg(path, page_no)
        if not jpeg:
            continue
        b64 = shrink_image_bytes(jpeg)
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": (
                f"This is page {page_no} of PDF '{rel_name}'. "
                f"Text extraction yielded under {THIN_PAGE_CHARS} characters — "
                f"likely a scanned technical-manual page. Extract all readable "
                f"specs, identifiers, ratings, warnings, and part numbers. "
                f"Set source_location to 'page {page_no}' on every fact."
            )},
        ]
        try:
            vraw = ask("index_pdf_page_vision", HAIKU,
                       [{"role": "user", "content": content}], system=system, max_tokens=2048)
            vdata = parse_json(vraw)
            for f in vdata.get("facts") or []:
                if not isinstance(f, dict):
                    continue
                f = dict(f)
                if not f.get("source_location"):
                    f["source_location"] = f"page {page_no}"
                vision_facts.append(f)
            visioned.append(page_no)
        except Exception as e:
            print(f"  ⚠ vision fallback failed for {path.name} p{page_no}: {e}")

    stats["vision_pages"] = visioned
    stats["vision_fact_count"] = len(vision_facts)
    return raw, stats, vision_facts


def read_json_file(path: Path):
    """Read a JSON file as UTF-8, falling back to cp1252 for cache files
    written by older versions on Windows (write_text without encoding)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="cp1252"))


def index_file(path: Path, lang: str, cache_dir: Path, rel_name: str = None):
    # file identity is the RELATIVE PATH — same filename in two subfolders
    # must not collide, and folder names ("Tegninger/") are role signal
    rel_name = rel_name or path.name
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    # WORKORDER 0.55 D1 — oversize skipped by default
    if size > 25 * 1024 * 1024:
        entry = {
            "file": rel_name, "kind": "skipped", "caption": f"Oversize ({size} bytes) — hoppet over",
            "facts": [], "quality_flags": ["oversize"], "cached": False,
        }
        return entry

    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    cache = cache_dir / f"{sha}.json"
    if cache.exists():
        entry = read_json_file(cache)
        entry["cached"] = True
        return entry

    ext = path.suffix.lower()
    system = INDEX_SYSTEM.replace("%LANG%", {"no": "Norwegian", "en": "English", "pl": "Polish"}[lang])
    extraction_stats = None
    vision_facts = []

    if ext in PHOTO_EXT:
        b64 = shrink_image(path)
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": f"Index this project photo. Path (folder names are role hints): {rel_name}"},
        ]
        raw = ask("index_photo", HAIKU, [{"role": "user", "content": content}], system=system)
        kind = "photo"
    elif ext == ".pdf":
        # Technical manuals: per-page chars + vision fallback on thin pages
        raw, extraction_stats, vision_facts = index_pdf_with_depth(path, lang, rel_name, system)
        kind = "doc"
        md_text = None  # unused; kept for retry branch compatibility
    elif ext in DOC_EXT:
        try:
            from markitdown import MarkItDown
            md_text = MarkItDown().convert(str(path)).text_content[:24000]
        except Exception as e:
            md_text = f"(extraction failed: {e}) filename: {path.name}"
        raw = ask("index_doc", HAIKU,
                  [{"role": "user", "content": f"Index this document. Path (folder names are role hints): {rel_name}\n\n{md_text}"}],
                  system=system, max_tokens=4096)
        kind = "doc"
    else:
        entry = {"file": rel_name, "sha": sha, "kind": "skipped", "caption": rel_name,
                 "content_tags": [], "doc_role_hints": [], "quality_flags": [], "facts": []}
        cache.write_text(json.dumps(entry), encoding="utf-8")
        return entry

    last_err = None
    for attempt in range(2):
        try:
            data = parse_json(raw)
            break
        except json.JSONDecodeError as e:
            last_err = e
            if attempt == 0:
                print(f"  ⚠ JSON parse failed for {path.name}, retrying index…")
                if kind == "photo":
                    raw = ask("index_photo", HAIKU, [{"role": "user", "content": content}],
                              system=system + "\nKeep facts ≤15. Reply with COMPLETE valid JSON only.", max_tokens=4096)
                elif ext == ".pdf":
                    raw = ask("index_doc", HAIKU,
                              [{"role": "user", "content":
                                f"Index this document. Path: {rel_name}\n\n"
                                f"(retry — return complete JSON only)"}],
                              system=system + "\nKeep facts ≤15. Reply with COMPLETE valid JSON only.",
                              max_tokens=4096)
                else:
                    raw = ask("index_doc", HAIKU,
                              [{"role": "user", "content": f"Index this document. Path (folder names are role hints): {rel_name}\n\n{md_text[:12000]}"}],
                              system=system + "\nKeep facts ≤15. Reply with COMPLETE valid JSON only.", max_tokens=4096)
            else:
                raise last_err
    # Merge vision-page facts (dedupe by key+value)
    facts = list(data.get("facts") or [])
    seen = {(f.get("key"), str(f.get("value"))) for f in facts if isinstance(f, dict)}
    for vf in vision_facts:
        key = (vf.get("key"), str(vf.get("value")))
        if key in seen:
            continue
        seen.add(key)
        facts.append(vf)
    # Cap at 25 after merge (prefer vision facts that carry page locations)
    data["facts"] = facts[:25]
    entry = {"file": rel_name, "sha": sha, "kind": kind, **data}
    if extraction_stats is not None:
        # Recompute facts_per_page from merged facts
        fpp = {str(k): 0 for k in (extraction_stats.get("chars_per_page") or {})}
        for f in entry.get("facts") or []:
            loc = (f.get("source_location") or "").lower()
            m = re.search(r"page\s*(\d+)", loc)
            if m:
                fpp[m.group(1)] = fpp.get(m.group(1), 0) + 1
        extraction_stats["facts_per_page"] = fpp
        entry["extraction_stats"] = extraction_stats
        if extraction_stats.get("thin_pages"):
            flags = list(entry.get("quality_flags") or [])
            if "thin_text_pages" not in flags:
                flags.append("thin_text_pages")
            if extraction_stats.get("vision_pages"):
                flags.append("vision_fallback")
            entry["quality_flags"] = flags
    # assign stable fact ids
    for n, f in enumerate(entry.get("facts", [])):
        f["id"] = f"{sha[:8]}-{n}"
    cache.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
    return entry


def index_project_name(name: str, cache_dir: Path, lang: str = "no"):
    """Synthesize one index entry from the project/folder name (WORKORDER 0.19B §1).

    Cached against the name hash — free after first Haiku call.
    Citation source renders as 'prosjektnavn'.
    """
    name = (name or "").strip()
    if not name:
        return None
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(exist_ok=True)
    h = hashlib.sha256(name.encode("utf-8")).hexdigest()
    sha = f"projname:{h}"
    cache = cache_dir / f"projname-{h}.json"
    if cache.exists():
        entry = read_json_file(cache)
        entry["cached"] = True
        return entry
    raw = ask_json("index_project_name", HAIKU, [{"role": "user", "content":
        f"""Extract identifier facts explicitly present in this project name.
Only what is literally in the string — never infer from world knowledge.
key examples: make, model, model_year, address, case_ref, kommune, gnr_bnr, drawing_no, party.

Project name: {name}

Reply ONLY JSON:
{{"facts":[{{"fact_type":"identifier","key":"snake_case","value":"...","unit":null,
"confidence":0.0-1.0,"source_excerpt":"verbatim substring","source_location":"prosjektnavn"}}]}}
Language for values when needed: {lang}. Empty facts array is fine if nothing is explicit."""}],
        max_tokens=800)
    facts = []
    for n, f in enumerate(raw.get("facts") or []):
        if not isinstance(f, dict) or not f.get("key") or f.get("value") in (None, ""):
            continue
        f = dict(f)
        f["id"] = f"{h[:8]}-{n}"
        f["source_location"] = "prosjektnavn"
        f.setdefault("source_excerpt", name)
        f.setdefault("fact_type", "identifier")
        facts.append(f)
    entry = {
        "file": "(prosjektnavn)",
        "sha": sha,
        "kind": "project_name",
        "caption": name,
        "content_tags": ["project_name"],
        "doc_role_hints": [],
        "quality_flags": [],
        "facts": facts,
    }
    cache.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
    return entry


# Keys that must never get an AI reference suggestion (compliance / safety)
COMPLIANCE_NO_REFERENCE = {
    "test_standard", "swl", "safe_working_load", "working_load_limit", "wll",
    "proof_load", "design_load", "break_load", "certificate_no", "cert_no",
    "ce_mark", "ce_marking", "notified_body", "inspection_class", "inspection_interval",
    "calibration_standard", "safety_factor", "rated_capacity",
}


def allows_reference_suggest(key, severity=None):
    """HARD RULE: no reference offer on compliance/safety-critical keys."""
    k = (key or "").strip().lower()
    if k in COMPLIANCE_NO_REFERENCE:
        return False
    return True


def reference_suggest(key, artifact, lang="no", project_context=None):
    """One Haiku call: commonly known reference value, or NOT_CONFIDENT.

    NEVER auto-inserted — caller must require user action.
    """
    if not allows_reference_suggest(key):
        return None
    art = {
        "name": (artifact or {}).get("name"),
        "purpose": (artifact or {}).get("purpose"),
        "artifact_type": (artifact or {}).get("artifact_type"),
        "main_components": (artifact or {}).get("main_components"),
    }
    art_h = hashlib.sha256(json.dumps(art, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    cache_dir = __import__("foldok_paths").ref_cache_dir(ENGINE_ROOT)
    cache_dir.mkdir(exist_ok=True)
    cache = cache_dir / f"ref-{key}-{art_h}.json"
    if cache.exists():
        data = read_json_file(cache)
        return None if data.get("not_confident") else data
    ctx_block = (project_context.strip() + "\n\n") if project_context else ""
    raw = ask("reference_suggest", HAIKU, [{"role": "user", "content":
        f"""{ctx_block}Suggest the commonly known value for fact key '{key}' for this artifact.
Reply EXACTLY one of:
  VALUE|<value>|<unit or empty>|<one-line basis in Norwegian>
  NOT_CONFIDENT

Do not invent project-specific measurements (serial numbers, addresses, test results).
Only well-known type/class defaults (e.g. oil grade for a car model/year).

Artifact summary: {json.dumps(art, ensure_ascii=False)[:1200]}
Language: {lang}"""}], max_tokens=200)
    text = (raw or "").strip()
    if not text or text.upper().startswith("NOT_CONFIDENT"):
        cache.write_text(json.dumps({"not_confident": True}), encoding="utf-8")
        return None
    if text.upper().startswith("VALUE|"):
        parts = text.split("|", 3)
        if len(parts) < 4:
            cache.write_text(json.dumps({"not_confident": True}), encoding="utf-8")
            return None
        _, value, unit, basis = parts[0], parts[1].strip(), parts[2].strip() or None, parts[3].strip()
        if not value:
            cache.write_text(json.dumps({"not_confident": True}), encoding="utf-8")
            return None
        data = {"value": value, "unit": unit, "basis": basis, "key": key,
                "not_confident": False}
        cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    cache.write_text(json.dumps({"not_confident": True}), encoding="utf-8")
    return None


IDENTITY_RULE = """
HARD REQUIREMENT — identification section:
The drafted template MUST begin with an identification/data section listing the
standard identity fields for this artifact type as required_facts (severity: warning).
Examples — vehicle: reg_no, vin, model_year, mileage, owner;
building: address, gnr_bnr, kommune;
machine/product: manufacturer, model_no, serial_no;
contract: party, contract_ref.
Choose fields a professional in the domain would expect on page one.
All drafted required_facts MUST use severity "warning" — NEVER "blocking".
Never draft legal/boilerplate declaration text.
"""


def _count_first_section_required_facts(template):
    secs = sorted(template.get("sections") or [], key=lambda s: s.get("position", 99))
    if not secs:
        return 0, None
    first = secs[0]
    rfs = [rf for rf in (first.get("required_facts") or []) if rf.get("key")]
    return len(rfs), first


def _inject_generic_identity(template, artifact=None):
    """Fallback identification section when draft validation fails twice."""
    art_type = ((artifact or {}).get("artifact_type") or "").lower()
    name = ((artifact or {}).get("name") or "").lower()
    blob = art_type + " " + name
    if any(w in blob for w in ("vehicle", "bil", "car", "toyota", "rav4", "auto", "service")):
        fields = [
            ("reg_no", "Registreringsnummer"),
            ("vin", "Chassisnummer (VIN)"),
            ("model_year", "Årsmodell"),
            ("mileage", "Kilometerstand"),
            ("owner", "Eier"),
        ]
        title_no = "Kjøretøydata"
    elif any(w in blob for w in ("building", "bygg", "tilbygg", "kommune", "rense")):
        fields = [
            ("address", "Adresse"),
            ("gnr_bnr", "Gnr/bnr"),
            ("kommune", "Kommune"),
        ]
        title_no = "Eiendomsdata"
    elif any(w in blob for w in ("contract", "kontrakt", "avtale")):
        fields = [
            ("party", "Part"),
            ("contract_ref", "Kontraktreferanse"),
            ("case_ref", "Saksnummer"),
        ]
        title_no = "Avtaleparter"
    else:
        fields = [
            ("manufacturer", "Produsent"),
            ("model_no", "Modell"),
            ("serial_no", "Serienummer"),
        ]
        title_no = "Identifikasjon"
    identity = {
        "section_key": "identification",
        "title": "Identification",
        "title_no": title_no,
        "position": 1,
        "required": True,
        "gap_severity": "warning",
        "required_facts": [
            {"key": k, "severity": "warning", "label_no": lab, "cardinality": "one"}
            for k, lab in fields
        ],
        "required_media": {},
        "required_content": ["no_uncited_specs"],
        "writing_rules": {"structure": "prose", "fact_citation": "required"},
        "ai_proposed_banner": True,
    }
    sections = list(template.get("sections") or [])
    for s in sections:
        pos = s.get("position", 99)
        if isinstance(pos, int) and pos >= 1:
            s["position"] = pos + 1
    template["sections"] = [identity] + sections
    return template


def _normalize_drafted_template(raw, story):
    """Force warning severity; strip blocking; ensure keys."""
    t = dict(raw) if isinstance(raw, dict) else {}
    key = t.get("template_key") or "drafted_" + hashlib.sha256(
        (story or "").encode()).hexdigest()[:10]
    t["template_key"] = re.sub(r"[^a-z0-9_]+", "_", key.lower()).strip("_") or "drafted"
    t.setdefault("name_no", t.get("name") or "AI-foreslått mal")
    t.setdefault("name", t.get("name_no"))
    t["origin"] = "ai_drafted"
    t["ai_drafted"] = True
    t["badge"] = "AI-foreslått struktur"
    t.setdefault("version", 1)
    t.setdefault("language_default", "no")
    sections = []
    for i, s in enumerate(t.get("sections") or []):
        if not isinstance(s, dict):
            continue
        s = dict(s)
        s.setdefault("section_key", f"section_{i+1}")
        s.setdefault("position", i + 1)
        s.setdefault("title_no", s.get("title") or s["section_key"])
        s.setdefault("title", s["title_no"])
        s["gap_severity"] = "warning"
        rfs = []
        for rf in s.get("required_facts") or []:
            if not isinstance(rf, dict) or not rf.get("key"):
                continue
            rf = dict(rf)
            rf["severity"] = "warning"  # NEVER blocking on rung-3
            rf.setdefault("cardinality", "one")
            rfs.append(rf)
        s["required_facts"] = rfs
        s.setdefault("required_media", {})
        s.setdefault("required_content", ["no_uncited_specs"])
        s.setdefault("writing_rules", {"structure": "prose", "fact_citation": "required"})
        s.pop("boilerplate", None)
        s.pop("boilerplate_no", None)
        sections.append(s)
    t["sections"] = sections
    return t


def draft_template(story, artifact, lang="no", project_context=None):
    """Rung-3 AI-drafted template (TEMPLATE_LIFECYCLE) with identity validation."""
    story = (story or "").strip()
    if not story:
        raise ValueError("Tom beskrivelse")
    desc_h = hashlib.sha256(story.encode("utf-8")).hexdigest()
    cache = __import__("foldok_paths").ref_cache_dir(ENGINE_ROOT) / f"tpldraft-{desc_h}.json"
    cache.parent.mkdir(exist_ok=True)
    if cache.exists():
        return read_json_file(cache)

    art_json = json.dumps(artifact or {}, ensure_ascii=False)[:2500]
    ctx_block = (project_context.strip() + "\n\n") if project_context else ""
    prompt = f"""{ctx_block}Draft a documentation template as JSON matching Foldok's sections schema.
Informed by the artifact model and document conventions for this need.
{IDENTITY_RULE}

ARTIFACT:
{art_json}

USER NEED:
{story}

Reply ONLY JSON:
{{
  "template_key": "snake_case",
  "name": "English name",
  "name_no": "Norsk navn",
  "description": "short",
  "applies_to": [],
  "version": 1,
  "language_default": "{lang}",
  "sections": [
    {{
      "section_key": "identification",
      "title": "Identification",
      "title_no": "...",
      "position": 1,
      "required": true,
      "gap_severity": "warning",
      "required_facts": [
        {{"key":"...","severity":"warning","label_no":"...","cardinality":"one"}}
      ],
      "required_media": {{}},
      "required_content": ["no_uncited_specs"],
      "writing_rules": {{"structure":"prose","fact_citation":"required"}}
    }}
  ]
}}
Add 3–7 further sections after identification as appropriate. No boilerplate fields.
All required_facts severity must be "warning"."""

    raw = ask_json("template_import", SONNET, [{"role": "user", "content": prompt}], max_tokens=4000)
    t = _normalize_drafted_template(raw, story)
    n, _ = _count_first_section_required_facts(t)
    if n < 3:
        raw2 = ask_json("template_import", SONNET, [{"role": "user", "content":
            prompt + "\n\nPREVIOUS DRAFT FAILED VALIDATION: first section must have ≥3 "
            "required_facts for identification. Fix and reply with complete JSON only."}],
            max_tokens=4000)
        t = _normalize_drafted_template(raw2, story)
        n, _ = _count_first_section_required_facts(t)
        if n < 3:
            t = _inject_generic_identity(t, artifact)
    cache.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    return t


# ── 2. CHECKPOINT A — artifact model ─────────────────────────────────
def build_artifact_model(index, lang):
    captions = "\n".join(f"[{e['file']}] {e['caption']}" for e in index)
    facts = "\n".join(f"({f['id']}) {f['key']}={f['value']}{f.get('unit') or ''}"
                      for e in index for f in e.get("facts", []))
    return ask_json("artifact_model", SONNET, [{"role": "user", "content": f"""From these indexed project files, form a model of what physical artifact this project is about. Reply ONLY JSON:
{{"artifact_type":"snake_case e.g. lifting_tool","name":"...","purpose":"one sentence",
"main_components":[{{"name":"...","seen_in":["filename",...]}}],
"hazards":[{{"hazard":"...","source":"filename or inferred"}}],
"lifecycle_stages":["transport","install","operate","maintain","inspect","dispose"],
"confidence":0.0-1.0}}
Language for text values: {lang}.

CAPTIONS:
{captions}

FACTS:
{facts}"""}], max_tokens=2500)


# ── 3. CHECKPOINT B — mapping + gaps (mapping=1 haiku call, gaps=pure code) ──
def _augment_facts_from_reports(index, all_facts):
    """Synthetic spec_ref / design_basis_ref from indexed report files (zero tokens)."""
    for e in index or []:
        if e.get("kind") == "skipped":
            continue
        fn = e.get("file", "").replace("\\", "/").lower()
        if not any(x in fn for x in ("designgrunnlag", "design_basis", "design basis")):
            continue
        fd = _facts_dict(e)
        ref = fd.get("drawing_no") or fd.get("document_number") or Path(e["file"]).stem
        rev = fd.get("revision") or _rev_from_name(e["file"]) or ""
        val = f"{ref} rev {rev}".strip() if rev and rev != "—" else str(ref)
        synth = {"id": f"synth-spec-{hash(e['file']) & 0xFFFFFF}", "key": "spec_ref",
                 "value": val, "unit": None, "source_location": e["file"]}
        if not all_facts.get("spec_ref"):
            all_facts.setdefault("spec_ref", []).append(synth)
        basis = {"id": f"synth-basis-{hash(e['file']) & 0xFFFFFF}", "key": "design_basis_ref",
                 "value": val, "unit": None, "source_location": e["file"]}
        if not all_facts.get("design_basis_ref"):
            all_facts.setdefault("design_basis_ref", []).append(basis)


def _augment_synthetic_facts(index, all_facts, artifact):
    """Close template gaps when code-built sections already know the answer."""
    _augment_facts_from_reports(index, all_facts)
    issuer = _best_issuer_from_index(index, artifact)
    if issuer and not all_facts.get("issuer"):
        all_facts.setdefault("issuer", []).append({
            "id": "synth-issuer", "key": "issuer", "value": issuer,
            "source_location": "indekserte tegninger"})
    if artifact:
        import re as _re
        m = _re.search(r"(\d+)\s*m\s*[²2]", artifact.get("purpose") or "")
        if m:
            for area_key in ("floor_area", "gross_area", "new_building_area"):
                if not all_facts.get(area_key):
                    all_facts.setdefault(area_key, []).append({
                        "id": f"synth-{area_key}", "key": area_key, "value": m.group(1),
                        "unit": "m²", "source_location": "artefaktmodell"})


def template_gaps(template, index, artifact, section_files=None):
    """Fact and media gaps without LLM file→section mapping."""
    all_facts = {}
    by_type = {}
    for e in index:
        for f in e.get("facts", []):
            all_facts.setdefault(f["key"], []).append(f)
            by_type.setdefault(f.get("fact_type"), []).append(f)
    _augment_synthetic_facts(index, all_facts, artifact)
    gaps = []
    for s in template["sections"]:
        cond = s.get("condition")
        if cond:
            holds, recognized = _condition_holds(cond, artifact)
            if recognized and not holds:
                continue
        fkeys = [rf for rf in s.get("required_facts", []) if _fact_applies(rf, artifact)]
        for rf in fkeys:
            if rf.get("severity") == "info":
                continue
            rf["_section_key"] = s["section_key"]
            key = rf["key"]
            matched_facts = _facts_for_key(key, all_facts, artifact)
            if matched_facts:
                gaps.extend(_fact_gaps(rf, all_facts, artifact))
            else:
                cands = by_type.get(rf.get("fact_type"), [])
                noisy = rf.get("fact_type") == "identifier" or len(cands) > 8
                if cands and not noisy:
                    gaps.append({"section": s["section_key"], "type": "matched_by_type",
                                 "key": key,
                                 "label": (rf.get("label_no") or rf.get("label", "")) +
                                 f" — {len(cands)} kandidat(er) via fact_type, bekreft",
                                 "severity": "info"})
                else:
                    gaps.extend(_fact_gaps(rf, all_facts, artifact))
        sk = s["section_key"]
        files = (section_files or {}).get(sk, [])
        minp = s.get("required_media", {}).get("min_photos", 0)
        if minp:
            # Prefer mapped section files; if map missing, don't pretend supplier must
            # invent photos when the index already has overview/drawing media.
            if section_files is not None:
                have = _section_media_count(files, index)
            else:
                have = _section_media_count(
                    [e.get("file") for e in (index or []) if e.get("file")],
                    index,
                )
            if have < minp:
                gaps.append({"section": sk, "type": "missing_media",
                             "key": "photos", "label": f"min {minp} photo(s)", "severity": "warning"})
    return gaps


def map_sections(template, index, artifact):
    # ── inbound guard (foldok_intake): personal docs out before Haiku sees them ──
    intake_notice = ""
    intake_gate = None
    try:
        from foldok_intake import prepare, gate as intake_gate_fn, sensitive_summary
        safe_index, intake_report = prepare(index)
        intake_gate = intake_gate_fn
        held_back = [
            {"file": c.file, "class": c.doc_class, "reasons": list(c.reasons)}
            for c in intake_report.excluded
        ]
        intake_notice = sensitive_summary(intake_report, "no") or ""
        if held_back:
            print(f"  ⚠ Held back {len(held_back)} personal/sensitive file(s) before mapping: "
                  + ", ".join(h["file"] for h in held_back))
    except Exception as e:
        print(f"  ⚠ foldok_intake unavailable ({e}) — using legacy personal-doc filter")
        index = tag_personal_documents(list(index))
        safe_index, held_entries = filter_personal_documents(index)
        held_back = [{"file": e["file"], "class": "personal", "reasons": ["legacy classifier"]}
                     for e in held_entries]
        if held_back:
            print(f"  ⚠ Held back {len(held_back)} personal document(s) before mapping: "
                  + ", ".join(h["file"] for h in held_back))

    caps = "\n".join(
        f"[{e['file']}] roles={e.get('doc_role_hints', [])} :: {e['caption']}"
        for e in safe_index
    )
    secs = [{"section_key": s["section_key"], "title": s.get("title_no") or s.get("title"),
             "title_no": s.get("title_no"), "title_en": s.get("title"),
             "roles": s.get("required_media", {}).get("preferred_roles", []),
             "required_media": s.get("required_media") or {},
             "notes": s.get("notes") or ""}
            for s in template["sections"]]

    tpl_key = str(template.get("template_key") or "").strip().lower()
    is_research_report = (
        tpl_key == "research_project_report"
        or Path(str(template.get("_file") or "")).name.lower() == "research_project_report.json"
    )
    is_topic_brief = (
        tpl_key == "topic_brief"
        or Path(str(template.get("_file") or "")).name.lower() == "topic_brief.json"
    )
    is_install_manual = (
        tpl_key == "installation_manual"
        or Path(str(template.get("_file") or "")).name.lower() == "installation_manual.json"
    )
    if is_research_report or is_topic_brief:
        # Deterministic map — compilers own bodies; no Haiku file-routing cost/sludge.
        all_files = [e.get("file") for e in safe_index if e.get("file")]
        fig_files = [
            e.get("file") for e in safe_index
            if e.get("file") and (
                e.get("kind") in ("image", "slide", "drawing")
                or str(e.get("file") or "").lower().endswith((".png", ".jpg", ".jpeg", ".pdf", ".pptx"))
            )
        ][:12]
        if is_topic_brief:
            file_map = {
                "overview": all_files[:6],
                "answers": all_files[:12],
                "gaps": [],
                "source_register": all_files,
            }
        else:
            file_map = {
                "cover": [],
                "objective": [],
                "method": [],
                "data_collected": all_files[:20],
                "observations": fig_files[:8] or all_files[:6],
                "deviations": [],
                "next_steps": [],
                "source_register": all_files,
                "signature": [],
            }
    elif is_install_manual:
        from install_manual_compile import map_install_files, corpus_shape, allowed_install_files
        file_map = map_install_files(safe_index, template, artifact)
        allowed = allowed_install_files(safe_index, artifact)
        shape = corpus_shape(safe_index, artifact)
        print(f"  · installation_manual: shape={shape} allowlist={len(allowed)} files")
    else:
        file_map = ask_json("section_mapping", HAIKU, [{"role": "user", "content":
            f"Map project files to document sections. Reply ONLY JSON: "
            f'{{"<section_key>": ["filename", ...], ...}}. A file may appear in several sections; '
            f"omit irrelevant files.\n\nSECTIONS:\n{json.dumps(secs)}\n\nFILES:\n{caps}"}], max_tokens=2500)

    # ── relevance gate: computed score (foldok_intake) then role overlap ────────
    dropped: dict[str, list[str]] = {}
    if not (is_research_report or is_topic_brief or is_install_manual):
        if intake_gate is not None:
            gate_report = intake_gate(file_map, safe_index, secs)
            file_map = dict(gate_report.kept)
            for m in gate_report.dropped:
                dropped.setdefault(m.section, []).append(m.file)
            if gate_report.dropped:
                print(f"  ⚠ {gate_report.explain()}")
        file_map, role_dropped = gate_mapped_files(file_map, safe_index, template)
        for sk, files in role_dropped.items():
            dropped.setdefault(sk, []).extend(files)
            print(f"  ⚠ Role gate dropped from [{sk}]: {', '.join(files)}")
    else:
        if is_install_manual:
            label = "installation_manual"
        elif is_topic_brief:
            label = "topic_brief"
        else:
            label = "research_project_report"
        print(f"  · {label}: skipping relevance gate (deterministic compilers)")

    gaps = template_gaps(template, safe_index, artifact, file_map)
    all_facts = {}
    # Install manuals: never harvest required-key facts from the whole loud corpus.
    fact_index = safe_index
    if is_install_manual:
        from install_manual_compile import filter_index_for_install
        fact_index = filter_index_for_install(safe_index, artifact)
        # Gaps must use the same allowlist — otherwise supplier_manual_gaps lists
        # exact-key misses that soft-match on allowlisted technical PDFs.
        gaps = template_gaps(template, fact_index or safe_index, artifact, file_map)
    for e in fact_index:
        for f in e.get("facts", []):
            all_facts.setdefault(f["key"], []).append(f)
    _augment_synthetic_facts(fact_index if is_install_manual else safe_index, all_facts, artifact)
    mappings = {}
    for s in template["sections"]:
        cond = s.get("condition")
        if cond:
            holds, recognized = _condition_holds(cond, artifact)
            if not recognized:
                print(f"  ⚠ [{s['section_key']}] unrecognized condition {cond!r} — including section")
                holds = True
            if not holds:
                continue
        if s.get("repeat_for"):
            print(f"  ⚠ [{s['section_key']}] repeat_for={s['repeat_for']!r} — "
                  f"grammar v2 not implemented in CLI; section runs once")
        fkeys = [rf for rf in s.get("required_facts", []) if _fact_applies(rf, artifact)]
        matched = []
        for rf in fkeys:
            if rf.get("severity") == "info":
                continue
            matched_facts = _facts_for_key(rf["key"], all_facts, artifact)
            if matched_facts:
                matched.extend(f["id"] for f in matched_facts)
        files = file_map.get(s["section_key"], [])
        mappings[s["section_key"]] = {
            "files": files,
            "fact_ids": matched,
            "section": s,
            "template_key": template.get("template_key") or "",
        }
    return mappings, gaps, {
        "held_back": held_back,
        "dropped": dropped,
        "intake_notice": intake_notice,
        "file_map": file_map,
    }


def _condition_holds(cond, artifact):
    """Tiny evaluator for the template condition mini-language.

    Returns (holds, recognized). recognized=False means the condition uses
    syntax this evaluator does not understand — the caller must not treat
    that as an evaluated False.
    """
    if "lifecycle_stages" in cond:
        stages = artifact.get("lifecycle_stages", [])
        return any(f"'{st}'" in cond for st in stages), True
    if "hazards" in cond:
        return len(artifact.get("hazards", [])) > 0, True
    if "artifact_type" in cond:
        m = re.search(r"artifact_type\s+in\s+\(([^)]+)\)", cond)
        if m:
            types = [t.strip().strip("'\"") for t in m.group(1).split(",")]
            return artifact.get("artifact_type", "") in types, True
        return artifact.get("artifact_type", "") in cond, True
    return False, False


def _fact_applies(rf, artifact):
    """Skip a required_fact row when its per-fact condition does not hold."""
    cond = rf.get("condition")
    if not cond:
        return True
    holds, recognized = _condition_holds(cond, artifact)
    return holds if recognized else True


def _fact_gaps(rf, all_facts, artifact):
    """Return gap dicts for one required_facts row (cardinality-aware)."""
    key = rf["key"]
    card = rf.get("cardinality", "one")
    severity = rf.get("severity", "warning")
    label = rf.get("label_no") or rf.get("label") or key
    section = rf.get("_section_key", "?")
    facts = _facts_for_key(key, all_facts, artifact)

    if card in ("one_or_more", "one"):
        if not facts:
            return [{"section": section, "type": "missing_fact", "key": key,
                     "label": label, "severity": severity}]
        return []

    if card == "one_per_hazard":
        hazards = artifact.get("hazards", [])
        if not hazards:
            return []
        shortfall = len(hazards) - len(facts)
        if shortfall <= 0:
            return []
        return [{"section": section, "type": "missing_fact", "key": key,
                 "label": f"{label} ({shortfall} hazard(s) uncovered)",
                 "severity": severity} for _ in range(shortfall)]

    # unknown cardinality — treat like one_or_more
    if not facts:
        return [{"section": section, "type": "missing_fact", "key": key,
                 "label": label, "severity": severity}]
    return []


# ── 4. CHECKPOINT C — generation with citation rule ──────────────────
GEN_SYSTEM = """You write ONE section of professional technical documentation. Output clean Markdown.

CITATION / TRUTH (non-negotiable):
- Do NOT output a section heading (# or ##) — the assembler adds it.
- Every factual claim (number, rating, standard, dimension, name, address)
  must cite a provided fact as {{fact:ID}}. Example: "Tilbygget er {{fact:ab12cd34-0}}."
- If a required value has no fact, write {{missing:key}} — never invent, estimate, or use "typical" values.
- Key meaning: floor_area / gross_area = size in m²; property_address = site address;
  criterion = acceptance limit (e.g. UR ≤ 1.0). NEVER use {{missing:criterion}} for area in m² —
  use {{fact:…}} for floor_area, or {{missing:floor_area}}.
- NEVER write {{missing:ukjent_kilde}} or any non-canonical key. A missing marker is a VALUE
  slot with a real fact key (reg_no, oil_type, …). If a clause depends on an unknown fact,
  restructure the sentence and put {{missing:canonical_key}} as its own short clause.
- Do NOT invent images without a listed file; insert available photos as
  {{fig:filename}} on its own line (with a one-line caption beneath).
  The assembler also inserts {{figure:file:page|cap}} markers.

TEXT QUALITY (always):
- Clear, concise, professional Norwegian (or the requested language). Natural flowing sentences —
  not raw AI tone, not list-of-facts pasted as prose.
- Never repeat the same number, dimension, address, or project name in the same section.
  Mention a value once; rephrase with pronouns or "tilbygget" / "tiltaker" thereafter.
  Bad: "Tilbygget er 25 m². Arealet er 25 m². Tilbygget har 25 m²."
  Good: "Tiltaket omfatter oppføring av et nytt tilbygg på ca. {{fact:ID}} i samsvar med godkjente tegninger."
- Prefer active or neutral professional tone. Short paragraphs. Consistent terms
  (tilbygg, fasadeendringer, plantegning, snitt, situasjonsplan).
- Structure when the section is prose: (1) one overview sentence, (2) scope, (3) explicit
  limitations/avgrensninger when relevant. Use bullets only when they aid scanning.
- Write for building authorities, engineers, and craftsmen — precision without padding.
- Follow the section writing_rules (voice, structure, max_words).
- Warnings: signal word + hazard + consequence + avoidance."""


DRAWING_ROLES = {"drawing", "site_plan", "schematic", "sketch", "overview", "nameplate", "photo"}
# filename/path heuristics — root PDFs often get role=technical_data from the
# indexer even though they ARE the tegningsunderlag (0.10.1 gap on this project)
DRAWING_NAME = re.compile(
    r"plantegning|fasadetegning|snitt|situasjon|perspektiv|tegning|plan_|elevation|section|"
    r"presentasjon|presentation|erikstad|\.pptx$",
    re.I)


# ── Personal-document classification ──────────────────────────────────────────
# Deterministic — no model call.  Keyed on the indexed caption / content_tags /
# doc_role_hints AND the filename itself.  Two actions:
#   quality_flag: "personal_document"   → visible in the UI "Holdt tilbake" log
#   doc_role_hints appended with "personal_document" → excluded before mapping

_PERSONAL_CAPTION_RE = re.compile(
    r"\b(insuran|forsikring|polise|policy\s+no|policy\s+number|prf\d|premium|"
    r"payslip|l[øo]nnsslipp|salary|salary\s+slip|national\s+id|f[øo]dselsnummer|"
    r"ssn|passport\s+no|personnummer|medical\s+rec|legejournal|journal\s+no|"
    r"tax\s+return|selvangivelse|skattemelding|bank\s+statement|kontoutskrift|"
    r"credit\s+card|kredittkort|mortgage|boliglån)\b",
    re.I,
)
_PERSONAL_FILENAME_RE = re.compile(
    r"(forsikring|insurance|polise|policy|payslip|l[øo]nn|salary|passport|"
    r"personnummer|skatt|legejournal|bank.?statement|kontoutskrift)",
    re.I,
)
_PERSONAL_TAGS = {
    "insurance_document", "policy_document", "payslip", "salary_document",
    "personal_id", "medical_record", "tax_document", "bank_statement",
}


def classify_personal(entry: dict) -> bool:
    """Return True if this index entry looks like a personal document.

    The caller is responsible for tagging it; we only classify."""
    caption = (entry.get("caption") or "") + " " + (entry.get("detail_summary") or "")
    if _PERSONAL_CAPTION_RE.search(caption):
        return True
    tags = set(entry.get("content_tags") or [])
    if tags & _PERSONAL_TAGS:
        return True
    if _PERSONAL_FILENAME_RE.search(entry.get("file") or ""):
        return True
    return False


def tag_personal_documents(index: list[dict]) -> list[dict]:
    """Add quality_flag='personal_document' and role 'personal_document' in-place.

    Returns the same list (mutated) for chaining.  Already-tagged entries are
    skipped so the function is safe to call multiple times.
    """
    for entry in index:
        flags = list(entry.get("quality_flags") or [])
        if "personal_document" in flags:
            continue
        if classify_personal(entry):
            flags.append("personal_document")
            entry["quality_flags"] = flags
            hints = list(entry.get("doc_role_hints") or [])
            if "personal_document" not in hints:
                hints.append("personal_document")
            entry["doc_role_hints"] = hints
    return index


def filter_personal_documents(index: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split index into (safe, held_back) by personal_document flag.

    held_back entries are NOT passed to map_sections or generation.
    """
    safe, held = [], []
    for entry in index:
        if "personal_document" in (entry.get("quality_flags") or []):
            held.append(entry)
        else:
            safe.append(entry)
    return safe, held


# ── Relevance gate ─────────────────────────────────────────────────────────────
# Section templates declare required_media.preferred_roles.  Files whose
# doc_role_hints share no token with a section's accepted roles are dropped
# from that section's mapped files — before any model receives them.
#
# Fallback: if a section has NO preferred_roles declared (older templates),
# no filtering is applied so nothing silently disappears.

_SECTION_ROLE_OVERRIDE: dict[str, set[str]] = {
    # section_key → additional accepted roles beyond what the template declares
    "certificates": {"certificate", "test_result"},
    "declaration":  {"certificate", "deliverable", "contract_clause"},
    "bom":          {"overview", "technical_data", "nameplate"},
}


def gate_mapped_files(
    file_map: dict[str, list[str]],
    index: list[dict],
    template: dict,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Remove files from each section bucket that share no role with that section.

    Returns (gated_map, dropped_map) where dropped_map records what was removed
    and why (for the "Holdt tilbake" log).
    """
    entry_by_file = {e["file"]: e for e in index}
    section_roles: dict[str, set[str]] = {}
    for s in template.get("sections") or []:
        sk = s["section_key"]
        declared = set((s.get("required_media") or {}).get("preferred_roles") or [])
        declared |= _SECTION_ROLE_OVERRIDE.get(sk, set())
        section_roles[sk] = declared

    gated: dict[str, list[str]] = {}
    dropped: dict[str, list[str]] = {}
    for sk, files in file_map.items():
        accepted_roles = section_roles.get(sk, set())
        if not accepted_roles:
            # No role constraint declared — pass all through
            gated[sk] = files
            continue
        keep, drop = [], []
        for f in files:
            entry = entry_by_file.get(f)
            file_roles = set((entry or {}).get("doc_role_hints") or [])
            if file_roles & accepted_roles:
                keep.append(f)
            else:
                drop.append(f)
        gated[sk] = keep
        if drop:
            dropped[sk] = drop
    return gated, dropped


# ── Markdown normaliser ────────────────────────────────────────────────────────
# Model output occasionally puts headings and blockquotes mid-paragraph without
# the preceding blank line that CommonMark requires.  One deterministic pass
# fixes every section without touching the content.

_MD_HEADING_RE = re.compile(r"(?<!\n)(\n)(#{1,6} )")
_MD_BLOCKQUOTE_RE = re.compile(r"(?<!\n)(\n)(> )")


def normalise_markdown(text: str) -> str:
    """Ensure a blank line precedes every heading and block-quote."""
    if not text:
        return text
    try:
        from foldok_intake import normalise as intake_normalise
        return intake_normalise(text)
    except ImportError:
        pass
    text = _MD_HEADING_RE.sub(r"\n\n\2", text)
    text = _MD_BLOCKQUOTE_RE.sub(r"\n\n\2", text)
    return text


def is_visual_source(rel_name, entry=None):
    ext = Path(rel_name).suffix.lower()
    if ext in PHOTO_EXT:
        return True
    if ext in (".pdf", ".pptx"):
        roles = set((entry or {}).get("doc_role_hints") or [])
        if roles & DRAWING_ROLES:
            return True
        if DRAWING_NAME.search(rel_name):
            return True
    return False


def figure_page_budget(rel_name, entry=None, total_pages=1):
    """How many pages/slides to cut into the document."""
    if Path(rel_name).suffix.lower() in PHOTO_EXT:
        return 1
    if DRAWING_NAME.search(rel_name) or "site_plan" in ((entry or {}).get("doc_role_hints") or []):
        return min(total_pages, 6)
    if is_visual_source(rel_name, entry):
        return min(total_pages, 3)
    return 0


def strip_illustration_block(md):
    if not md:
        return ""
    md = ILLUST_BLOCK.sub("", md)
    md = FIGURE_MARK.sub("", md)
    return md.rstrip() + "\n"


def inject_illustration_markers(md, file_entries, page_counts):
    """Append ### Illustrasjoner with {{figure:file:page|caption}} markers.

    file_entries: list of (rel_name, entry_dict_or_None)
    page_counts: dict rel_name -> page count
    """
    md = strip_illustration_block(md or "")
    lines = []
    for rel, entry in file_entries:
        total = page_counts.get(rel, 1)
        n = figure_page_budget(rel, entry, total)
        if n <= 0:
            continue
        cap = (entry or {}).get("caption") or Path(rel).name
        for p in range(n):
            label = f"{cap} — side {p + 1}" if n > 1 else cap
            lines.append(f"{{{{figure:{rel}:{p}|{label}}}}}")
    if not lines:
        return md
    block = "\n\n### Illustrasjoner\n\n" + "\n\n".join(lines) + "\n"
    return md.rstrip() + block


def expand_figures_to_markdown_images(md, media_url_fn):
    """Turn {{figure:file:page|cap}} into markdown images via media_url_fn(file, page)->url."""
    def repl(m):
        rel, page, cap = m.group(1), int(m.group(2)), (m.group(3) or m.group(1)).strip()
        url = media_url_fn(rel, page)
        return f"![{cap}]({url})"
    return FIGURE_MARK.sub(repl, md or "")


# templates ask for scope_statement; indexer often emits new_building_area etc.
FACT_ALIASES = {
    "scope_statement": ["floor_area", "gross_area", "new_building_area", "new_area",
                        "new_area_total", "terrace_area", "building_area"],
    "floor_area": ["gross_area", "new_building_area", "new_area", "new_area_total", "terrace_area", "building_area"],
    "gross_area": ["floor_area", "new_building_area", "new_area", "new_area_total", "terrace_area", "building_area"],
    "dimensions": ["floor_area", "gross_area", "new_building_area", "width", "length"],
    "project_title": ["drawing_title", "property_address", "thesis_title", "product_name", "project_name"],
    "project_name": ["project_title", "drawing_title", "product_name", "thesis_title"],
    "thesis_title": ["project_title", "product_name", "drawing_title"],
    "author_name": ["author", "researcher", "client_name"],
    "doc_no": ["drawing_no", "drawing_number", "document_number", "document_no", "sheet_number"],
    "drawing_no": ["drawing_number", "document_number", "doc_no", "sheet_number"],
    "revision": ["drawing_revision", "rev", "document_revision"],
    "design_basis_ref": ["design_basis", "basis_document", "basis_reference"],
    "issuer": ["architect_name", "prepared_by", "author_name", "project_manager", "reviewer_or_approver", "issuer_name"],
    "spec_ref": ["document_number", "drawing_no", "revision"],
    "property_address": ["address", "site_address", "project_location", "eiendomsadresse"],
    # Installation manual — extractor keys rarely match template required_facts verbatim
    "system_type": [
        "applicable_products", "product_type", "equipment_type", "device_type",
        "type_designation", "anleggstype", "system_under_install",
    ],
    "hazard": [
        "warning", "danger", "risk", "fare", "safety_warning",
        "safety_device_fault_response", "fault_response",
    ],
    "requirement": [
        "krav", "shall_requirement", "mandatory_requirement",
        "installation_requirement", "emc_requirement",
    ],
    "criterion": [
        "acceptance_criterion", "acceptance_criteria", "akseptkriterium",
        "threshold", "limit", "cable_shield_coverage",
    ],
    "manufacturer": ["supplier", "leverandør", "vendor", "producer"],
}

# Soft key match when exact + alias miss (vocabulary drift in extracted keys)
SOFT_KEY_RX = {
    "system_type": re.compile(
        r"(?i)^(system_type|applicable_products|product_type|equipment_type|"
        r"device_type|type_designation|anleggstype)$"
    ),
    "hazard": re.compile(
        r"(?i)(hazard|fare|danger|warning|fault_response|safety_device|risk)"
    ),
    "requirement": re.compile(r"(?i)(requirement|krav)"),
    "criterion": re.compile(
        r"(?i)(criterion|acceptance|aksept|threshold|_limit$|limit$|_coverage$)"
    ),
    "manufacturer": re.compile(r"(?i)^(manufacturer|supplier|leverand|vendor|producer)"),
}


GAP_LABELS_NO = {
    "issuer": "Utsteder (arkitekt)",
    "spec_ref": "Spesifikasjonsreferanse + revisjon",
    "design_basis_ref": "Styrende designgrunnlag",
    "doc_no": "Dokumentnummer",
    "drawing_no": "Tegningsnummer",
    "revision": "Revisjon",
    "floor_area": "Gulvareal",
    "gross_area": "Bruttoareal",
    "project_title": "Prosjekttittel",
    "prepared_by": "Utarbeidet av",
}

CREATE_DOC_FOR_KEY = {
    "design_basis_ref": ("design_basis.json", "Opprett Designgrunnlag i Foldok"),
    "spec_ref": ("design_basis.json", "Opprett Designgrunnlag i Foldok"),
}

REFRESH_SECTION_FOR_KEY = {
    "issuer": ("spec_overview", "Oppdater tabell fra indekserte tegninger"),
    "doc_no": ("doc_control", "Oppdater dokumentkontroll fra kilder"),
    "drawing_no": ("drawings_register", "Oppdater tegningsliste"),
}


def gap_guide(key, section, index, artifact, documents=None):
    """Return guided next step for one open gap — zero tokens."""
    documents = documents or []
    label = GAP_LABELS_NO.get(key, key.replace("_", " "))
    cands = search_fact_candidates(index, key)
    artifact = artifact or {}

    def pack(action, message, **extra):
        return {"key": key, "section": section, "label": label, "action": action,
                "message": message, "candidates": cands[:8], **extra}

    if key in CREATE_DOC_FOR_KEY:
        has_basis_file = any("designgrunnlag" in e.get("file", "").lower()
                             or "design_basis" in e.get("file", "").lower() for e in index)
        has_basis_doc = any(d.get("template") == "design_basis.json" for d in documents)
        tpl, btn = CREATE_DOC_FOR_KEY[key]
        if not has_basis_doc and not has_basis_file:
            return pack("create_document",
                          "Designgrunnlag finnes ikke i prosjektet ennå — opprett det som eget Foldok-dokument.",
                          create_template=tpl, create_label=btn)
        if has_basis_file and cands:
            best = cands[0]
            return pack("apply_value",
                        f"Designgrunnlag finnes i kildene ({best['file'].split('/')[-1]}).",
                        suggested=best)
        if has_basis_file:
            return pack("refresh_section",
                        "Designgrunnlag ligger i Rapporter/ — oppdater tabellen.",
                        refresh_section="spec_overview")
        return pack("create_document",
                    "Generer designgrunnlag for å lukke denne referansen.",
                    create_template=tpl, create_label=btn)

    if key in REFRESH_SECTION_FOR_KEY:
        sec, msg = REFRESH_SECTION_FOR_KEY[key]
        if cands:
            return pack("apply_value", f"{msg}. Verdi funnet i kildene.", suggested=cands[0],
                        refresh_section=sec)
        return pack("refresh_section", msg, refresh_section=sec)

    if cands:
        best = cands[0]
        return pack("apply_value",
                      f"Funnet i {best['file'].split('/')[-1]}: {best['excerpt'][:80]}",
                      suggested=best)

    # Sovereign artifact fields
    if key in ("project_title", "thesis_title", "product_name", "project_name") and artifact.get("name"):
        return pack("apply_value", "Fra artefaktmodellen (sjekkpunkt A).",
                      suggested={"fact_id": "artifact-name", "key": key, "value": artifact["name"],
                                   "unit": None, "source": "artefaktmodell", "file": "artefaktmodell"})
    if key == "scope_statement" and artifact.get("purpose"):
        return pack("apply_value", "Fra artefaktmodellen.",
                      suggested={"fact_id": "artifact-purpose", "key": key, "value": artifact["purpose"],
                                   "unit": None, "source": "artefaktmodell", "file": "artefaktmodell"})
    if key in ("floor_area", "gross_area", "new_building_area"):
        import re as _re
        m = _re.search(r"(\d+)\s*m\s*[²2]", artifact.get("purpose") or "")
        if m:
            return pack("apply_value", f"Areal nevnt i artefaktformål ({m.group(1)} m²).",
                          suggested={"fact_id": "artifact-area", "key": key, "value": m.group(1),
                                       "unit": "m²", "source": "artefaktmodell", "file": "artefaktmodell"})

    return pack("manual", "Verdien finnes ikke i kildene ennå. Legg til fil, pek på riktig tegning, eller skriv inn.")


def _facts_dict(entry):
    """Flatten entry facts; merge known alias keys onto canonical names."""
    raw = {f["key"]: f["value"] for f in entry.get("facts", [])}
    merges = [
        ("drawing_no", ["drawing_number", "document_number", "doc_no", "sheet_number"]),
        ("revision", ["drawing_revision", "rev", "document_revision"]),
        ("drawing_title", ["sheet_title", "title", "drawing_type"]),
        ("property_address", ["project_location", "address", "site_address"]),
    ]
    for canon, aliases in merges:
        if raw.get(canon):
            continue
        for a in aliases:
            if raw.get(a):
                raw[canon] = raw[a]
                break
    return raw


def _rev_from_name(name):
    m = re.search(r"rev\s*(\d+)", name, re.I)
    return f"REV{m.group(1)}" if m else None


def _rev_score(rev, filename=""):
    """Numeric rank for revision comparison — higher = newer."""
    s = str(rev or _rev_from_name(filename) or "").upper()
    m = re.search(r"REV\s*(\d+)", s)
    if m:
        return 1000 + int(m.group(1))
    m = re.search(r"\bREV\s*([A-Z])\b", s)
    if m:
        return 100 + ord(m.group(1))
    m = re.search(r"rev\s*(\d+)", filename or "", re.I)
    if m:
        return 1000 + int(m.group(1))
    return 0


def _file_mtime(folders, file):
    """Newest mtime among project folders for a relative file path."""
    best = 0
    for folder in folders or []:
        p = Path(folder) / file.replace("/", os.sep)
        try:
            if p.is_file():
                best = max(best, p.stat().st_mtime)
        except OSError:
            pass
    return best


def detect_revision_supersede(index, excluded_files=None, folders=None):
    """Same drawing_no with lower revision → suggest toggle-off (zero tokens)."""
    excluded = set(excluded_files or [])
    by_dno = {}
    for e in index or []:
        if not _is_drawing_entry(e) or e.get("file") in excluded:
            continue
        fd = _facts_dict(e)
        dno = fd.get("drawing_no") or fd.get("drawing_number") or fd.get("document_number")
        if not dno or str(dno).strip() in ("—", "-", "?"):
            continue
        rev = fd.get("revision") or _rev_from_name(e["file"]) or ""
        by_dno.setdefault(str(dno).strip(), []).append({
            "file": e["file"], "rev": rev or "?",
            "score": _rev_score(rev, e["file"]),
            "mtime": _file_mtime(folders, e["file"]),
        })
    out = []
    for dno, entries in by_dno.items():
        if len(entries) < 2:
            continue
        best = max(entries, key=lambda x: (x["score"], x["mtime"]))
        for ent in entries:
            if ent["file"] == best["file"]:
                continue
            if ent["score"] > best["score"] or (
                    ent["score"] == best["score"] and ent["mtime"] >= best["mtime"]):
                continue
            fname = Path(ent["file"]).name
            bname = Path(best["file"]).name
            hint_name = f"supersede|{dno}|{ent['file']}"
            out.append({
                "type": "supersede_revision",
                "name": hint_name,
                "label": f"{dno} rev {ent['rev']} erstattet av rev {best['rev']}",
                "reason": (f"{dno} rev {ent['rev']} ser ut til å være erstattet av "
                           f"rev {best['rev']}"),
                "evidence": f"{fname} → {bname}",
                "file": ent["file"],
                "superseded_by": best["file"],
                "drawing_no": dno,
                "old_rev": ent["rev"],
                "new_rev": best["rev"],
            })
    return out[:8]


def superseded_files_map(index, excluded_files=None, folders=None):
    """Map older-revision files → supersede metadata (for KILDER hints + table ⚠)."""
    excluded = set(excluded_files or [])
    m = {}
    for s in detect_revision_supersede(index, excluded_files=excluded, folders=folders):
        if s.get("file"):
            m[s["file"]] = s
    return m


def _doc_no_cell(facts, filename, lang="no"):
    """Prefer title-block number; fall back to traceable filename (not a false MANGLER)."""
    bogus = re.compile(r"not\s+(clearly\s+)?visible|ukjent|unknown|n/?a|—|-", re.I)
    for k in ("drawing_no", "drawing_number", "document_number", "doc_no"):
        v = facts.get(k)
        if v and not bogus.fullmatch(str(v).strip()):
            return f"**{v}**"
    stem = Path(filename).stem
    if lang == "no":
        return f"**{stem}** *(filnavn — bekreft dok.nr. mot tittelblokk)*"
    return f"**{stem}** *(filename — confirm doc no. against title block)*"


def _pick_doc_control_drawings(index, max_n=8):
    """One row per drawing type — prefer Til Søknad / REV2 / PNG cutouts."""
    kinds = [
        ("plantegning", re.compile(r"plantegning", re.I)),
        ("fasade", re.compile(r"fasade", re.I)),
        ("situasjon", re.compile(r"situasjon|situvasjon", re.I)),
        ("snitt", re.compile(r"snitt", re.I)),
    ]
    visuals = [e for e in index if _is_drawing_entry(e)]
    by_kind = {}
    for e in visuals:
        name = e["file"]
        ext = Path(name).suffix.lower()
        score = 0
        if ext in PHOTO_EXT:
            score += 80
        if re.search(r"s[øo]knad", name, re.I):
            score += 25
        rev_m = re.search(r"rev\s*(\d+)", name, re.I)
        if rev_m:
            score += 40 + int(rev_m.group(1)) * 10
        if re.search(r"\btopp\b", name, re.I) and not rev_m:
            score -= 30
        kind = "annet"
        for kid, rx in kinds:
            if rx.search(name):
                kind = kid
                break
        prev = by_kind.get(kind)
        if not prev or score > prev[0]:
            by_kind[kind] = (score, e)
    picked = [by_kind[k][1] for k in ("plantegning", "fasade", "situasjon", "snitt") if k in by_kind]
    seen = {e["file"] for e in picked}
    for e in sorted(visuals, key=lambda x: -len(x.get("facts") or [])):
        if e["file"] not in seen and len(picked) < max_n:
            name = e["file"]
            if not (DRAWING_NAME.search(name) or Path(name).suffix.lower() in PHOTO_EXT | {".pdf", ".svg"}):
                continue
            picked.append(e)
            seen.add(e["file"])
    return picked


# ── structured table model (SOURCE_INTERACTION_SPEC S2/S4) ──────────
# Cell: {"v": str|None, "mangler": key?, "cited": bool?, "verified": bool?,
#        "note": str?, "plain": bool?, "fact_id": str?}
# Row:  {"row_key": "slot|source", "source_file": str|None, "cells": {col_id: cell}}
#       or {"row_key": "group|…", "group": "label"} for group header rows.

DOC_CONTROL_COLUMNS = [
    {"id": "doc", "label": "Dokument", "label_en": "Document", "key": "doc_no", "editable": True},
    {"id": "title", "label": "Tittel", "label_en": "Title", "key": "drawing_title", "editable": True},
    {"id": "rev", "label": "Revisjon", "label_en": "Revision", "key": "revision", "editable": True},
    {"id": "addr", "label": "Adresse", "label_en": "Address", "key": "property_address", "editable": True},
    {"id": "purpose", "label": "Formål", "label_en": "Purpose", "key": "purpose", "editable": True},
]

SPEC_OVERVIEW_COLUMNS = [
    {"id": "kind", "label": "Dokumenttype", "label_en": "Document type", "key": None, "editable": False},
    {"id": "title", "label": "Betegnelse", "label_en": "Title", "key": "drawing_title", "editable": True},
    {"id": "issuer", "label": "Utgiver", "label_en": "Issuer", "key": "issuer", "editable": True},
    {"id": "rev", "label": "Revisjon", "label_en": "Revision", "key": "revision", "editable": True},
    {"id": "status", "label": "Status", "label_en": "Status", "key": None, "editable": False},
]

TABLE_COLUMNS = {"doc_control": DOC_CONTROL_COLUMNS, "spec_overview": SPEC_OVERVIEW_COLUMNS}


def _dedupe_title_value(v, note=None):
    """ONE_AGENT_SPEC B1 — collapse name+cited concatenation duplicates."""
    if v is None:
        return None, note
    s = str(v).strip()
    s = re.sub(r"\b(.{6,80}?)\s+\1\b", r"\1", s)
    if note:
        n = str(note).strip()
        if s.lower() == n.lower() or n.lower() in s.lower() or s.lower() in n.lower():
            note = None
    return s, note


def _cell(v=None, mangler=None, cited=True, note=None, plain=False):
    v, note = _dedupe_title_value(v, note)
    c = {"v": None if v is None else str(v)}
    if mangler:
        c["mangler"] = mangler
    if note:
        c["note"] = note
    if plain:
        c["plain"] = True
    elif v is not None and cited:
        c["cited"] = True
    return c


def _cell_md(cell):
    if cell.get("mangler"):
        return f"`[MANGLER: {cell['mangler']}]`"
    v, note = _dedupe_title_value(cell.get("v"), cell.get("note"))
    if v is None or v == "":
        return "—"
    if cell.get("verified"):
        s = f"**{v} ✓**"
    elif cell.get("cited"):
        s = f"**{v}**"
    else:
        s = str(v)
    if note:
        s += f" *({note})*"
    return s


def render_table_md(data, lang="no"):
    """Rows → markdown table (identical shape to the old string builders)."""
    if data.get("empty_message"):
        return data["empty_message"]
    cols = data["columns"]
    lab = "label" if lang == "no" else "label_en"
    header = "| " + " | ".join(c.get(lab) or c["label"] for c in cols) + " |"
    sep = "|" + "---|" * len(cols)
    lines = [header, sep]
    for row in data["rows"]:
        if row.get("group"):
            lines.append(f"| **{row['group']}** |" + " |" * (len(cols) - 1))
            continue
        cells = row.get("cells") or {}
        lines.append("| " + " | ".join(_cell_md(cells.get(c["id"], {})) for c in cols) + " |")
    md = "\n".join(lines)
    if data.get("note"):
        md += "\n\n" + data["note"]
    return md


def apply_cell_overrides(data, overrides, section):
    """User cell edits are sovereign — applied after compile, before render."""
    by = {(o.get("row_key"), o.get("column")): o
          for o in overrides or [] if o.get("section") == section}
    if not by:
        return data
    for row in data.get("rows", []):
        cells = row.get("cells") or {}
        for col_id, cell in cells.items():
            o = by.get((row.get("row_key"), col_id))
            if not o:
                continue
            cell["v"] = str(o.get("value") or "")
            cell.pop("mangler", None)
            cell.pop("note", None)
            cell["verified"] = bool(o.get("verified_by_user"))
            cell["cited"] = bool(o.get("fact_id")) and not cell["verified"]
            if o.get("fact_id"):
                cell["fact_id"] = o["fact_id"]
    return data


def _doc_no_val(facts, filename, lang="no"):
    """(value, note) — prefer title-block number; fall back to traceable filename."""
    bogus = re.compile(r"not\s+(clearly\s+)?visible|ukjent|unknown|n/?a|—|-", re.I)
    for k in ("drawing_no", "drawing_number", "document_number", "doc_no"):
        v = facts.get(k)
        if v and not bogus.fullmatch(str(v).strip()):
            return str(v), None
    stem = Path(filename).stem
    note = ("filnavn — bekreft dok.nr. mot tittelblokk" if lang == "no"
            else "filename — confirm doc no. against title block")
    return stem, note


def compile_doc_control_data(index, artifact, lang="no"):
    """Dokumentkontroll as structured rows — zero tokens."""
    artifact = artifact or {}
    address = None
    for e in index:
        fd = _facts_dict(e)
        address = fd.get("property_address") or fd.get("project_location") or address

    def addr_cell():
        return (_cell(address) if address
                else _cell(mangler="property_address"))

    rows = []
    proj = artifact.get("name")
    purpose = (artifact.get("purpose") or "")[:120]
    rows.append({"row_key": "report|__artifact__", "source_file": None, "cells": {
        "doc": _cell("KR-001"),
        "title": _cell(proj) if proj else _cell(mangler="project_title"),
        "rev": _cell("REV 0"),
        "addr": addr_cell(),
        "purpose": _cell(purpose or ("Konstruksjonsrapport" if lang == "no"
                                     else "Structural design report"), plain=True),
    }})

    basis_entry = None
    for e in index:
        fn = e["file"].replace("\\", "/").lower()
        if "designgrunnlag" in fn or "design_basis" in fn or "design basis" in fn:
            basis_entry = e
            break
    if basis_entry:
        fd = _facts_dict(basis_entry)
        bno = fd.get("drawing_no") or fd.get("document_number") or Path(basis_entry["file"]).stem
        brev = fd.get("revision") or _rev_from_name(basis_entry["file"]) or None
        cap = basis_entry.get("caption") or "Designgrunnlag"
        rows.append({"row_key": f"basis|{basis_entry['file']}", "source_file": basis_entry["file"], "cells": {
            "doc": _cell(bno),
            "title": _cell(cap[:60]),
            "rev": _cell(brev) if brev else _cell("—", plain=True),
            "addr": addr_cell(),
            "purpose": _cell("Styrende designgrunnlag", plain=True),
        }})
    else:
        rows.append({"row_key": "basis|__missing__", "source_file": None, "cells": {
            "doc": _cell(mangler="design_basis_ref"),
            "title": _cell("Designgrunnlag", plain=True),
            "rev": _cell("—", plain=True),
            "addr": addr_cell(),
            "purpose": _cell("Legg Designgrunnlag.md i Rapporter/ eller pek på kilden", plain=True),
        }})

    for e in _pick_doc_control_drawings(index):
        fd = _facts_dict(e)
        doc_v, doc_note = _doc_no_val(fd, e["file"], lang)
        title = fd.get("drawing_title") or e.get("caption") or Path(e["file"]).stem
        rev = fd.get("revision") or _rev_from_name(e["file"]) or None
        cap = (e.get("caption") or "")[:100]
        rows.append({"row_key": f"drawing|{e['file']}", "source_file": e["file"], "cells": {
            "doc": _cell(doc_v, note=doc_note),
            "title": _cell(str(title)[:70]),
            "rev": _cell(rev) if rev else _cell("—", plain=True),
            "addr": addr_cell(),
            "purpose": _cell(cap, plain=True),
        }})

    data = {"section": "doc_control", "columns": DOC_CONTROL_COLUMNS, "rows": rows}
    if len(rows) <= 2:
        data["empty_message"] = (
            "Ingen tegninger funnet i kildene — legg tegninger i prosjektmappen og indekser."
            if lang == "no" else "No drawings in sources.")
    else:
        data["note"] = (
            "*Dokumentnummer hentet fra tittelblokk når lesbart; ellers vises filnavn som sporbar referanse "
            "(klikk MANGLER kun hvis du vil overstyre).*"
            if lang == "no" else
            "*Doc numbers from title blocks when legible; otherwise filename shown as traceable reference.*")
    return data


def compile_doc_control(index, artifact, lang="no"):
    """Dokumentkontroll — markdown view of compile_doc_control_data. Zero tokens."""
    return render_table_md(compile_doc_control_data(index, artifact, lang), lang)


def _best_issuer_from_index(index, artifact=None):
    """Pick the fullest architect/issuer name seen across sources."""
    candidates = []
    for e in index or []:
        fd = _facts_dict(e)
        for k in ("architect_name", "issuer", "prepared_by", "author_name", "project_manager"):
            v = fd.get(k)
            if v and len(str(v).strip()) > 3:
                candidates.append(str(v).strip())
    if candidates:
        return max(candidates, key=len)
    return _author_from_artifact(artifact)


def _issuer_cell(entry, default_issuer=None):
    fd = _facts_dict(entry)
    for k in ("issuer", "architect_name", "prepared_by", "author_name"):
        v = fd.get(k)
        if v and len(str(v).strip()) > 2:
            return f"**{v}**"
    if default_issuer:
        return f"**{default_issuer}**"
    return "`[MANGLER: issuer]`"


def _standards_from_index(index):
    """Collect invoked standards/specs from index facts."""
    rows, seen = [], set()
    std_keys = {"building_code", "load_standard", "load_standard_series", "test_standard",
                "room_height_standard", "invoked_document", "governing_standard"}
    skip_keys = {"drawing_scale", "scale", "drawing_number", "drawing_no"}
    scale_like = re.compile(r"^\d+\s*:\s*\d+$")
    for e in index or []:
        for f in e.get("facts", []):
            key = f.get("key")
            if key in skip_keys:
                continue
            if f.get("fact_type") != "standard_ref" and key not in std_keys:
                continue
            val = str(f.get("value") or "").strip()
            if not val or scale_like.match(val) or val.lower() in seen:
                continue
            seen.add(val.lower())
            src = Path(e["file"]).name
            rows.append((val, src))
    return rows


def _issuer_val(entry, default_issuer=None):
    """(value, mangler?) for the Utgiver cell."""
    fd = _facts_dict(entry)
    for k in ("issuer", "architect_name", "prepared_by", "author_name"):
        v = fd.get(k)
        if v and len(str(v).strip()) > 2:
            return str(v), None
    if default_issuer:
        return default_issuer, None
    return None, "issuer"


def compile_spec_overview_data(index, artifact, lang="no"):
    """Spesifikasjonsoversikt as structured rows — zero tokens."""
    artifact = artifact or {}
    default_issuer = _best_issuer_from_index(index, artifact)
    rows = []

    def issuer_cell(entry):
        v, mangler = _issuer_val(entry, default_issuer)
        return _cell(v) if v else _cell(mangler=mangler)

    rows.append({"row_key": "group|provided",
                 "group": "Gitt dokumentasjon" if lang == "no" else "Provided documentation"})

    basis_entry = None
    for e in index or []:
        fn = e["file"].replace("\\", "/").lower()
        if any(x in fn for x in ("designgrunnlag", "design_basis", "design basis")):
            basis_entry = e
            break
    if basis_entry:
        fd = _facts_dict(basis_entry)
        title = basis_entry.get("caption") or "Designgrunnlag"
        rev = fd.get("revision") or _rev_from_name(basis_entry["file"]) or None
        ref = fd.get("drawing_no") or fd.get("document_number") or Path(basis_entry["file"]).stem
        rows.append({"row_key": f"basis|{basis_entry['file']}", "source_file": basis_entry["file"], "cells": {
            "kind": _cell("Spesifikasjon" if lang == "no" else "Specification", plain=True),
            "title": _cell(f"{str(title)[:50]} ({ref})"),
            "issuer": issuer_cell(basis_entry),
            "rev": _cell(rev) if rev else _cell("—", plain=True),
            "status": _cell("Referert" if lang == "no" else "Referenced", plain=True),
        }})

    for e in _pick_doc_control_drawings(index, max_n=6):
        fd = _facts_dict(e)
        kind = "Tegning"
        name = e["file"]
        if re.search(r"plantegning", name, re.I):
            kind = "Plantegning"
        elif re.search(r"fasade", name, re.I):
            kind = "Fasadetegning"
        elif re.search(r"situasjon|situvasjon", name, re.I):
            kind = "Situasjonskart"
        elif re.search(r"snitt", name, re.I):
            kind = "Snitt"
        title = fd.get("drawing_title") or e.get("caption") or Path(name).stem
        rev = fd.get("revision") or _rev_from_name(name) or None
        rows.append({"row_key": f"drawing|{name}", "source_file": name, "cells": {
            "kind": _cell(kind, plain=True),
            "title": _cell(str(title)[:65], plain=True),
            "issuer": issuer_cell(e),
            "rev": _cell(rev) if rev else _cell("—", plain=True),
            "status": _cell("Fremlagt" if lang == "no" else "Provided", plain=True),
        }})

    for e in index or []:
        if basis_entry and e.get("file") == basis_entry.get("file"):
            continue
        fn = e["file"].replace("\\", "/").lower()
        if not any(x in fn for x in ("designgrunnlag", "design_basis", "teknisk dokumentasjon", "konstruksjonsrapport")):
            continue
        if "rapporter/" not in fn and "rapport" not in fn:
            continue
        title = e.get("caption") or Path(e["file"]).stem
        fd = _facts_dict(e)
        rev = fd.get("revision") or _rev_from_name(e["file"]) or None
        rows.append({"row_key": f"report|{e['file']}", "source_file": e["file"], "cells": {
            "kind": _cell("Rapport", plain=True),
            "title": _cell(str(title)[:65], plain=True),
            "issuer": issuer_cell(e),
            "rev": _cell(rev) if rev else _cell("—", plain=True),
            "status": _cell("Referert" if lang == "no" else "Referenced", plain=True),
        }})

    rows.append({"row_key": "group|standards",
                 "group": "Påberopte standarder" if lang == "no" else "Invoked standards"})
    standards = _standards_from_index(index)
    if standards:
        for val, src in standards[:12]:
            rows.append({"row_key": f"standard|{val[:40]}", "source_file": src, "cells": {
                "kind": _cell("Standard", plain=True),
                "title": _cell(str(val)[:60]),
                "issuer": _cell(default_issuer) if default_issuer else _cell("—", plain=True),
                "rev": _cell("—", plain=True),
                "status": _cell(src, plain=True),
            }})
    else:
        hint = ("Ingen standarder ekstrahert — sjekk Designgrunnlag.md" if lang == "no"
                else "No standards extracted — check design basis")
        rows.append({"row_key": "standard|__none__", "source_file": None, "cells": {
            "kind": _cell("—", plain=True), "title": _cell(hint, plain=True),
            "issuer": _cell("—", plain=True), "rev": _cell("—", plain=True),
            "status": _cell("—", plain=True),
        }})

    note = ("*Utgiver hentet fra arkitektnavn på tegninger når ikke angitt per dokument. "
            "Standarder listes kun når funnet i indekserte kilder.*"
            if lang == "no" else
            "*Issuer from drawing title blocks when not stated per document.*")
    return {"section": "spec_overview", "columns": SPEC_OVERVIEW_COLUMNS, "rows": rows, "note": note}


def compile_spec_overview(index, artifact, lang="no"):
    """Spesifikasjonsoversikt — markdown view of compile_spec_overview_data."""
    return render_table_md(compile_spec_overview_data(index, artifact, lang), lang)


def _author_from_artifact(artifact):
    """Pull a person name from checkpoint-A purpose when sources omit author_name."""
    purpose = (artifact or {}).get("purpose") or ""
    # e.g. "... for Jan Rune Erikstad." / "... by Ada Lovelace"
    m = re.search(
        r"(?:\bfor|\bby|av)\s+([A-ZÆØÅ][a-zæøåA-ZÆØÅ\-]+(?:\s+[A-ZÆØÅ][a-zæøåA-ZÆØÅ\-]+){1,3})\s*[.\)]?\s*$",
        purpose.strip(),
        re.I,
    )
    if m:
        return m.group(1).strip(" .")
    return None


def _facts_for_key(key, all_facts, artifact=None):
    """Lookup required_fact key plus known alias keys (vocabulary drift).
    Falls back to confirmed artifact model fields when no indexed fact exists.
    Reference-provenance facts never close a gap (WORKORDER 0.19B §3)."""
    out = list(all_facts.get(key, []))
    for alias in FACT_ALIASES.get(key, []):
        out.extend(all_facts.get(alias, []))
    # Soft match: keys like safety_device_fault_response close ``hazard``
    if not out:
        rx = SOFT_KEY_RX.get(key)
        if rx:
            for fk, facts in (all_facts or {}).items():
                if fk == key:
                    continue
                if rx.search(str(fk or "")):
                    out.extend(facts)
    out = [f for f in out if f.get("provenance") != "reference"]
    if out or not artifact:
        return out
    # checkpoint A name/purpose are sovereign — use them when index has no title/author
    if key in ("project_title", "thesis_title", "product_name", "project_name") and artifact.get("name"):
        return [{"id": "artifact-name", "key": key, "value": artifact["name"], "unit": None,
                 "source_location": "artefaktmodell (sjekkpunkt A)"}]
    if key == "scope_statement" and artifact.get("purpose"):
        return [{"id": "artifact-purpose", "key": "scope_statement", "value": artifact["purpose"], "unit": None,
                 "source_location": "artefaktmodell (sjekkpunkt A)"}]
    if key == "author_name":
        author = _author_from_artifact(artifact)
        if author:
            return [{"id": "artifact-author", "key": "author_name", "value": author, "unit": None,
                     "source_location": "artefaktmodell (sjekkpunkt A)"}]
    if key == "system_type":
        locked = str(artifact.get("system_under_install") or "").strip()
        if locked:
            return [{"id": "artifact-system", "key": "system_type", "value": locked, "unit": None,
                     "source_location": "artefaktmodell (system_under_install)"}]
    if key in ("floor_area", "gross_area", "new_building_area"):
        m = re.search(r"(\d+)\s*m\s*[²2]", artifact.get("purpose") or "")
        if m:
            return [{"id": "artifact-area", "key": key, "value": m.group(1), "unit": "m²",
                     "source_location": "artefaktmodell (sjekkpunkt A)"}]
    return out


def _section_media_count(files, index) -> int:
    """How many mapped files can satisfy a min_photos / overview media need."""
    by = {e.get("file"): e for e in (index or []) if e.get("file")}
    n = 0
    for fn in files or []:
        e = by.get(fn) or {}
        ext = Path(str(fn)).suffix.lower()
        roles = set(e.get("doc_role_hints") or [])
        kind = e.get("kind") or ""
        if ext in PHOTO_EXT or kind in ("image", "slide", "drawing"):
            n += 1
        elif ext in (".pdf", ".pptx") and roles & {
            "drawing", "schematic", "site_plan", "overview",
            "technical_data", "manual", "datasheet",
        }:
            n += 1
        elif ext in (".pdf", ".pptx", ".png", ".jpg", ".jpeg"):
            # Mapped visual/source page — counts for overview media
            n += 1
    return n


def pick_best_area_fact(index, artifact=None):
    """Best floor/tilbygg area fact already in the index (or artifact purpose)."""
    prefer = ("floor_area", "gross_area", "new_building_area", "new_area",
              "new_area_total", "building_area", "terrace_area")
    best = None
    for e in index or []:
        for f in e.get("facts", []):
            if f.get("key") not in prefer:
                continue
            try:
                val = float(str(f.get("value", "")).replace(",", ".").split()[0])
            except (TypeError, ValueError):
                continue
            if val <= 0:
                continue
            cand = {**f, "source_location": e.get("file"), "file": e.get("file")}
            if not best or (f.get("key") == "floor_area" and best.get("key") != "floor_area"):
                best = cand
            elif f.get("key") == best.get("key") and (f.get("confidence") or 0) > (best.get("confidence") or 0):
                best = cand
    if best:
        return best
    m = re.search(r"(\d+)\s*m\s*[²2]", (artifact or {}).get("purpose") or "")
    if m:
        return {"id": "artifact-area", "key": "floor_area", "value": m.group(1), "unit": "m²",
                "source_location": "artefaktmodell"}
    return None


# Model sometimes writes {{missing:criterion}} for tilbygg m² — criterion is UR limit, not area.
_MISKEYED_AREA = re.compile(
    r"`?\[MANGLER:\s*criterion\]`?(\s*m\s*[²2])",
    re.I,
)


def repair_miskeyed_area_mangler(state, index, artifact=None):
    """Zero-token: replace [MANGLER: criterion] m² with cited area from index."""
    area = pick_best_area_fact(index, artifact)
    if not area:
        return []
    unit = area.get("unit") or "m²"
    val = str(area.get("value"))
    rendered = f"**{val} {unit}**" if unit and unit not in str(val) else f"**{val}**"
    # Keep trailing " m²" from the match group so we don't double the unit awkwardly
    def repl(m):
        # If prose already has " m²" after, just insert the number as bold
        return f"**{val}**{m.group(1)}"

    fixed = []
    doc = state.get("doc") or {}
    for sk, sec in (doc.get("sections") or {}).items():
        md = sec.get("md") or ""
        if not _MISKEYED_AREA.search(md):
            continue
        new_md = _MISKEYED_AREA.sub(repl, md, count=1)
        if new_md != md:
            sec["md"] = new_md
            cited = list(sec.get("cited_fact_ids") or sec.get("cited") or [])
            if area.get("id") and area["id"] not in cited:
                cited.append(area["id"])
            sec["cited"] = cited
            sec["cited_fact_ids"] = cited
            fixed.append(sk)
    return fixed


def _is_drawing_entry(entry):
    if entry.get("kind") == "skipped":
        return False
    if DRAWING_ROLES.intersection(entry.get("doc_role_hints", [])):
        return True
    name = entry.get("file", "")
    return bool(DRAWING_NAME.search(name))


def compile_drawings_register(index, lang):
    """Tegningsliste — pure code, zero tokens (template notes promise this).
    One row per drawing file; title-block facts fill the cells,
    illegible title blocks surface as [MANGLER] cells for the user."""
    rows = []
    seen = set()
    for e in index:
        if not _is_drawing_entry(e):
            continue
        if e["file"] in seen:
            continue
        seen.add(e["file"])
        facts = _facts_dict(e)

        def cell(key):
            v = facts.get(key)
            if v:
                return f"**{v}**"
            if key in ("drawing_no", "revision"):
                return _doc_no_cell(facts, e["file"], lang) if key == "drawing_no" else (
                    f"**{facts.get('revision') or _rev_from_name(e['file']) or '—'}**"
                    if facts.get("revision") or _rev_from_name(e["file"]) else f"`[MANGLER: {key}]`")
            return f"`[MANGLER: {key}]`"

        title = facts.get("drawing_title")
        title_cell = f"**{title}**" if title else (e.get("caption") or "")[:80]
        rev = facts.get("revision") or _rev_from_name(e["file"]) or ""
        rev_cell = f"**{rev}**" if rev else cell("revision")
        rows.append(f"| {cell('drawing_no')} | {title_cell} | {rev_cell} | {cell('scale')} | {e['file']} |")
    if not rows:
        return ("Ingen tegninger identifisert i kildene. `[MANGLER: drawing_no]`" if lang == "no"
                else "No drawings identified in the sources. `[MANGLER: drawing_no]`")
    header = ("| Tegningsnr. | Tittel | Rev. | Målestokk | Kildefil |" if lang == "no"
              else "| Drawing no | Title | Rev | Scale | Source file |")
    return "\n".join([header, "|---|---|---|---|---|"] + rows)


def inject_user_facts(index, user_facts):
    """Append sovereign user-entered facts as a synthetic index entry."""
    if not user_facts:
        return index
    synth = {
        "file": "brukeroppgitt",
        "sha": "user",
        "kind": "user",
        "caption": "Verdier oppgitt manuelt av bruker",
        "doc_role_hints": [],
        "quality_flags": [],
        "facts": user_facts,
    }
    return index + [synth]


def compile_supplier_manual_gaps(gaps, lang="no"):
    """WORKORDER_0.27 §B — manufacturer-only [MANGLER] honesty table (zero tokens)."""
    rows = [g for g in (gaps or [])
            if g.get("severity") in ("blocking", "warning") and g.get("key")]
    if lang == "no":
        lines = ["| Tema | Kun leverandør kan levere |", "|---|---|"]
        if not rows:
            lines.append("| (ingen åpne mangler registrert) | — |")
        else:
            for g in rows:
                label = g.get("label") or g.get("key", "").replace("_", " ")
                lines.append(f"| {label} | `[MANGLER:{g['key']}]` |")
        return "\n".join(lines)
    lines = ["| Topic | Supplier must provide |", "|---|---|"]
    if not rows:
        lines.append("| (no open gaps recorded) | — |")
    else:
        for g in rows:
            label = g.get("label") or g.get("key", "").replace("_", " ")
            lines.append(f"| {label} | `[MANGLER:{g['key']}]` |")
    return "\n".join(lines)


# ── Section fact context + structure enforcement (WORKORDER 0.48) ─────

def _fact_confidence(f):
    try:
        return float(f.get("confidence") if f.get("confidence") is not None else 0.7)
    except (TypeError, ValueError):
        return 0.7


def _format_fact_line(fid, f):
    unit = f.get("unit") or ""
    conf = _fact_confidence(f)
    return (
        f"{fid}: {f.get('key')} = {f.get('value')}{unit} "
        f"(src: {f.get('source_location', '')}; conf={conf:.2f})"
    )


def build_section_fact_context(mapping, index, artifact, cap=120, exclude_ids=None):
    """Two-tier facts for generate_section (WORKORDER 0.48 Bug 1).

    PRIMARY   = mapping fact_ids (mapper-selected)
    AVAILABLE = required-key matches + facts from mapped files + synth
                artifact facts, capped and confidence-sorted.
    """
    exclude_ids = set(exclude_ids or [])
    section = mapping.get("section") or {}
    sec_key = (mapping.get("section_key") or section.get("section_key") or "").strip().lower()
    by_id = {f["id"]: f for e in index for f in e.get("facts", [])}

    # Noise filters: contact/marketing tokens do not belong in technical prose.
    NOISE_KEYS = {
        "email", "e_mail", "mail", "phone", "telephone", "mobile",
        "contact_person", "contact_name", "website", "url", "linkedin",
        "instagram", "facebook", "slogan", "tagline", "marketing_text",
        "promo_text", "token_count", "word_count",
        "persona", "personas", "hypothesis", "hypotese", "market_size",
        "market_segment", "buyer_persona", "competitive", "swot",
        "investor", "opportunity", "board", "ceo", "cfo",
    }
    install_mode = str(mapping.get("template_key") or "").strip().lower() == "installation_manual"
    for fid in list(by_id.keys()):
        f = by_id.get(fid) or {}
        key = str(f.get("key") or "").strip().lower()
        if key in NOISE_KEYS:
            by_id.pop(fid, None)
            continue
        val = str(f.get("value") or "")
        if re.search(r"@\w+\.\w+|https?://|www\.", val, re.I):
            by_id.pop(fid, None)
            continue
        if re.search(r"\b(follow|subscribe|call now|limited offer)\b", val, re.I):
            by_id.pop(fid, None)
            continue
        if install_mode and re.search(
            r"(?i)\b(persona|hypotese|hypothesis|markedspotensial|"
            r"market\s*size|konkurrent|investor|styre)\b",
            f"{key} {val}",
        ):
            by_id.pop(fid, None)

    # Keep project title/scope only in true overview/identity homes.
    # Install manuals: title only — not purpose/author (BoD sludge magnets).
    allow_project_meta = sec_key in {
        "identification", "system_overview", "summary", "executive_summary",
        "scope", "spec_overview", "doc_control",
    }
    if allow_project_meta and artifact.get("name"):
        by_id["artifact-name"] = {
            "id": "artifact-name", "key": "project_title",
            "value": artifact["name"], "unit": None,
            "confidence": 1.0,
            "source_location": "artefaktmodell (sjekkpunkt A)",
        }
    if allow_project_meta and artifact.get("purpose") and not install_mode:
        by_id["artifact-purpose"] = {
            "id": "artifact-purpose", "key": "scope_statement",
            "value": artifact["purpose"], "unit": None,
            "confidence": 1.0,
            "source_location": "artefaktmodell (sjekkpunkt A)",
        }
    author = _author_from_artifact(artifact)
    if allow_project_meta and author and not install_mode:
        by_id["artifact-author"] = {
            "id": "artifact-author", "key": "author_name",
            "value": author, "unit": None, "confidence": 1.0,
            "source_location": "artefaktmodell (sjekkpunkt A)",
        }
    if install_mode:
        system_val = str(artifact.get("system_under_install") or "").strip()
        if system_val:
            by_id["artifact-system"] = {
                "id": "artifact-system", "key": "system_under_install",
                "value": system_val, "unit": None, "confidence": 1.0,
                "source_location": "artefaktmodell (system_under_install)",
            }

    primary_ids = [fid for fid in (mapping.get("fact_ids") or []) if fid in by_id]
    for synth in ("artifact-name", "artifact-purpose", "artifact-author", "artifact-system"):
        if synth in by_id and synth not in primary_ids:
            primary_ids.append(synth)

    required_keys = set()
    for rf in section.get("required_facts") or []:
        if not _fact_applies(rf, artifact) or rf.get("severity") == "info":
            continue
        key = rf.get("key")
        if key:
            required_keys.add(key)
            required_keys.update(FACT_ALIASES.get(key, []))

    mapped_files = set(mapping.get("files") or [])
    scored = []  # (priority, -confidence, fid, fact)
    seen = set()

    # Install manuals: hard allowlist — never Tier-A from the whole project.
    install_allowed = None
    if install_mode:
        from install_manual_compile import (
            allowed_install_files,
            should_stay_thin,
            filter_identity_fact_ids,
        )
        install_allowed = allowed_install_files(index, artifact)
        mapped_files = {f for f in mapped_files if f in install_allowed}
        # Stay thin: only synth system (+ project name) — no loud fact harvest
        if should_stay_thin(index, artifact):
            primary_ids = [fid for fid in primary_ids if fid.startswith("artifact-")]
            for synth in ("artifact-system", "artifact-name"):
                if synth in by_id and synth not in primary_ids:
                    primary_ids.append(synth)
            available = []
            for fid in primary_ids:
                if fid in by_id and fid not in exclude_ids:
                    f = by_id[fid]
                    available.append({"id": fid, **{k: v for k, v in f.items() if k != "id"}})
            available_ids = {a["id"] for a in available}
            return {
                "by_id": by_id,
                "primary_ids": primary_ids,
                "available": available,
                "available_ids": available_ids,
                "primary_txt": "\n".join(
                    _format_fact_line(fid, by_id[fid]) for fid in primary_ids if fid in by_id
                ) or "(thin — no install sources)",
                "available_txt": "(thin — no install sources)",
                "required_keys": required_keys,
                "install_stay_thin": True,
                "install_allowed_files": sorted(install_allowed),
            }

    def _add(fid, f, priority):
        if not fid or fid in seen or fid not in by_id or fid in exclude_ids:
            return
        seen.add(fid)
        scored.append((priority, -_fact_confidence(f), fid, f))

    # Tier A: required-key matches — install: only from allowlisted files
    for e in index or []:
        fn = e.get("file") or ""
        if install_allowed is not None and fn not in install_allowed:
            continue
        for f in e.get("facts") or []:
            if f.get("provenance") == "reference":
                continue
            if f.get("key") in required_keys:
                _add(f.get("id"), f, 0)

    # Tier B: all facts from mapped files
    for e in index or []:
        if e.get("file") not in mapped_files:
            continue
        for f in e.get("facts") or []:
            if f.get("provenance") == "reference":
                continue
            _add(f.get("id"), f, 1)

    # Tier C: synth / primary leftovers
    for fid in primary_ids:
        if fid in by_id:
            _add(fid, by_id[fid], 2)

    scored.sort()
    available = []
    # Section-specific cap (keeps prose from becoming fact sludge)
    if install_mode:
        section_cap = min(cap, 12 if sec_key == "identification" else 16)
    elif sec_key in ("technical_data", "spec_overview", "bom"):
        section_cap = min(cap, 80)
    elif sec_key in ("method", "results", "discussion", "conclusion"):
        section_cap = min(cap, 28)
    else:
        section_cap = min(cap, 42)
    for _p, _c, fid, f in scored:
        if len(available) >= section_cap:
            break
        available.append({"id": fid, **{k: v for k, v in f.items() if k != "id"}})

    if install_mode and sec_key == "identification":
        available = [
            a for a in available
            if a["id"] in filter_identity_fact_ids([a["id"]], by_id)
            or str(a["id"]).startswith("artifact-")
        ]

    available_ids = {a["id"] for a in available}
    primary_txt = "\n".join(
        _format_fact_line(fid, by_id[fid]) for fid in primary_ids
    ) or "(no priority facts mapped)"
    available_txt = "\n".join(
        _format_fact_line(a["id"], by_id[a["id"]]) for a in available
        if a["id"] in by_id
    ) or "(no available facts)"

    out = {
        "by_id": by_id,
        "primary_ids": primary_ids,
        "available": available,
        "available_ids": available_ids,
        "primary_txt": primary_txt,
        "available_txt": available_txt,
        "required_keys": required_keys,
    }
    if install_mode:
        out["install_allowed_files"] = sorted(install_allowed or [])
        out["install_stay_thin"] = False
    return out


# Structures that must produce narrative / list text — never a bare fact dump.
PROSE_LIKE_STRUCTURES = (
    "prose", "numbered_list", "numbered_steps", "checklist", "list", "bullet_list",
)
TABLE_STRUCTURES = ("table", "bom_table")


def _structure_kind(section):
    wr = (section or {}).get("writing_rules") or {}
    return (wr.get("structure") or "prose").lower()


def _wants_fact_table(section, structure):
    """Only emit a parameter table when the template asked for one."""
    if structure in TABLE_STRUCTURES:
        return True
    req = (section or {}).get("required_content") or []
    return "table_format" in req


def structure_ok(text, structure):
    """Return True if markdown satisfies the required writing_rules.structure."""
    structure = (structure or "prose").lower()
    t = text or ""
    if structure in TABLE_STRUCTURES:
        lines = t.splitlines()
        has_row = any(ln.strip().startswith("|") and ln.count("|") >= 2 for ln in lines)
        has_rule = any(re.match(r"^\s*\|?\s*[-:]+", ln) for ln in lines)
        return has_row and has_rule
    if structure in ("numbered_list", "numbered_steps"):
        return bool(re.search(r"(?m)^\s*\d+\.\s+\S", t))
    if structure in ("checklist",):
        return ("□" in t) or bool(re.search(r"(?m)^\s*-\s*\[[ xX]\]\s+", t))
    if structure in ("list", "bullet_list"):
        return bool(re.search(r"(?m)^\s*[-*•]\s+\S", t)) or structure_ok(t, "numbered_list")
    return True


def build_generic_fact_table(mapping, index, artifact, lang="no", ctx=None, fact_ids=None):
    """Zero-token table from facts using B1 column vocabulary (WORKORDER 0.49)."""
    import editorial_layer as ed

    ctx = ctx or build_section_fact_context(mapping, index, artifact)
    by_id = ctx["by_id"]
    section = mapping.get("section") or {}
    sec_key = mapping.get("section_key") or section.get("section_key") or ""
    vocab_key = ed.vocab_key_for_section(sec_key, section)
    if vocab_key == "bom":
        return render_bom_markdown(aggregate_bom(index), lang)

    ids = list(fact_ids) if fact_ids is not None else list(ctx["primary_ids"])
    if fact_ids is None:
        primary_set = set(ctx["primary_ids"])
        for a in ctx["available"]:
            if a["id"] not in primary_set:
                ids.append(a["id"])

    # Research data table allowlist by theme + contact denylist
    sk = (sec_key or "").strip().lower()
    tpl_key = str(mapping.get("template_key") or "").strip().lower()
    if sk == "identification" and tpl_key == "installation_manual":
        from install_manual_compile import filter_identity_fact_ids
        ids = filter_identity_fact_ids(ids, by_id)[:16]
    if sk == "data_collected":
        allow_prefix = ("attenuation", "measurement", "test_", "standard", "frequency", "shield", "emc")
        allow_exact = {"manufacturer", "product_name", "part_number", "sample_size", "data_location"}
        deny_exact = {"phone", "email", "website", "url", "address", "fax", "linkedin"}
        kept = []
        for fid in ids:
            f = by_id.get(fid) or {}
            k = str(f.get("key") or "").strip().lower()
            if k in deny_exact:
                continue
            if k in allow_exact or any(k.startswith(p) for p in allow_prefix):
                kept.append(fid)
        ids = kept[:20]

    rows = []
    seen_keys = set()

    def _row_tech(fid):
        f = by_id.get(fid)
        if not f:
            return None
        key = f.get("key") or ""
        if key in seen_keys:
            return None
        seen_keys.add(key)
        unit = f.get("unit") or ""
        return {
            "row_key": key or fid,
            "cells": {
                "param": _cell(key.replace("_", " "), cited=False, plain=True),
                "value": _cell(f.get("value"), cited=True),
                "unit": _cell(unit or "—", cited=False, plain=True),
                "source": _cell(f"{{{{fact:{fid}}}}}", cited=False, plain=True),
            },
        }

    def _row_components(fid, nr):
        f = by_id.get(fid)
        if not f:
            return None
        return {
            "row_key": f.get("id") or fid,
            "cells": {
                "nr": _cell(str(nr), cited=False, plain=True),
                "component": _cell(f.get("value"), cited=True),
                "function": _cell(f.get("key", "").replace("_", " "), cited=False, plain=True),
                "source": _cell(f"{{{{fact:{fid}}}}}", cited=False, plain=True),
            },
        }

    if vocab_key == "components":
        # Cap lookup-heavy ID/component rows to keep reports readable.
        ids = ids[:20]
        for i, fid in enumerate(ids, 1):
            r = _row_components(fid, i)
            if r:
                rows.append(r)
    else:
        for fid in ids:
            r = _row_tech(fid)
            if r:
                rows.append(r)
        for rf in section.get("required_facts") or []:
            if not _fact_applies(rf, artifact) or rf.get("severity") == "info":
                continue
            key = rf.get("key")
            if not key or key in seen_keys:
                continue
            alias_keys = {key, *FACT_ALIASES.get(key, [])}
            present = any(
                by_id.get(fid, {}).get("key") in alias_keys
                for fid in (fact_ids if fact_ids is not None else ctx["available_ids"])
            )
            if present:
                continue
            seen_keys.add(key)
            rows.append({
                "row_key": key,
                "cells": {
                    "param": _cell(key.replace("_", " "), cited=False, plain=True),
                    "value": _cell(mangler=key),
                    "unit": _cell("—", cited=False, plain=True),
                    "source": _cell("—", cited=False, plain=True),
                },
            })

    if not rows:
        empty = (
            "Ingen fakta tilgjengelig for denne tabellen."
            if lang == "no" else "No facts available for this table."
        )
        return empty

    cols = ed.columns_for(vocab_key if vocab_key != "bom" else "technical_data", lang)
    # Normalize cell ids to vocab
    data = {"columns": cols, "rows": rows}
    return render_table_md(data, lang=lang)


def resolve_fig_markers(text, index):
    """{{fig:filename}} → {{figure:filename:0|caption}} when file is indexed."""
    known = {e.get("file"): e for e in (index or []) if e.get("file")}

    def repl(m):
        name = (m.group(1) or "").strip()
        if not name:
            return ""
        # Allow basename match
        entry = known.get(name)
        if not entry:
            for f, e in known.items():
                if Path(f).name == name or f.endswith("/" + name) or f.endswith("\\" + name):
                    entry = e
                    name = f
                    break
        if not entry:
            return ""  # drop unknown — never a broken ref
        cap = (entry.get("caption") or Path(name).name).strip()
        return f"{{{{figure:{name}:0|{cap}}}}}"

    return FIG_SHORT_MARK.sub(repl, text or "")


def count_figures(text):
    t = text or ""
    return len(FIGURE_MARK.findall(t)) + len(FIG_SHORT_MARK.findall(t))


# Registers / declarations / signatures stay figure-free even with default-on.
NO_FIGURE_SECTIONS = frozenset({
    "declaration", "source_register", "drawings_register", "doc_control",
    "revision_history", "abbreviations", "toc", "signature", "erklaering",
    "kilderegister", "supplier_manual_gaps", "ambiguities", "risk_flags",
    "standards_declaration", "conflict_register", "requirements_register",
    "kommentarer_og_signatur",
})


def _section_opts_out_of_figures(mapping):
    """True when the section must not auto-receive figures."""
    section = mapping.get("section") or {}
    media = section.get("required_media") or {}
    if section.get("no_figures") or media.get("no_figures"):
        return True
    if section.get("boilerplate"):
        return True
    if (section.get("writing_rules") or {}).get("structure") == "boilerplate":
        return True
    sk = (mapping.get("section_key") or section.get("section_key") or "").strip()
    if sk in NO_FIGURE_SECTIONS:
        return True
    if sk.endswith("_register") or sk.endswith("_declaration"):
        return True
    if "signature" in sk or sk == "declaration":
        return True
    return False


def ensure_min_figures(text, mapping, index, max_n=4):
    """Insert top-N visuals when the section has too few figures.

    Default-on: any section with usable visuals gets ≥1 figure unless opted
    out. Pool = mapped files + every other visual in the index, ranked by
    caption relevance to the section (fixes mapper-starved boat-photo bug).

    Installation manuals: never auto-insert supplier PDF page rasters (copyright).
    """
    if str(mapping.get("template_key") or "").strip().lower() == "installation_manual":
        return text
    section = mapping.get("section") or {}
    media = section.get("required_media") or {}
    if _section_opts_out_of_figures(mapping):
        return text

    preferred = set(media.get("preferred_roles") or [])
    mapped = list(mapping.get("files") or [])
    by_file = {e.get("file"): e for e in (index or []) if e.get("file")}

    def _is_usable_visual(rel):
        e = by_file.get(rel) or {}
        if is_visual_source(rel, e):
            return True
        return Path(rel).suffix.lower() in PHOTO_EXT | {".pdf", ".pptx"}

    visual_mapped = [rel for rel in mapped if _is_usable_visual(rel)]
    min_photos = int(media.get("min_photos") or 0)
    if min_photos <= 0:
        if not visual_mapped:
            return text
        min_photos = 1
    if count_figures(text) >= min_photos:
        return text

    def score(rel):
        e = by_file.get(rel) or {}
        roles = set(e.get("doc_role_hints") or [])
        s = 0
        if preferred & roles:
            s += 10
        if roles & {"drawing", "site_plan", "schematic", "overview"}:
            s += 5
        if Path(rel).suffix.lower() in PHOTO_EXT:
            s += 3
        sk = mapping.get("section_key") or section.get("section_key") or ""
        if sk in ("system_overview", "scope", "description", "cover") and (
            roles & {"drawing", "site_plan", "overview"} or DRAWING_NAME.search(rel or "")
        ):
            s += 8
        return s

    # Widen pool: mapped first, then every other visual in the index
    mapped_set = set(mapped)
    extra = [
        e.get("file") for e in (index or [])
        if e.get("file") and e.get("file") not in mapped_set
        and _is_usable_visual(e.get("file"))
    ]
    candidates = mapped + extra

    sec_text = (
        (section.get("title_no") or "") + " " + (section.get("title") or "")
        + " " + (section.get("notes") or "") + " "
        + (section.get("section_key") or "").replace("_", " ")
    )[:500].lower()
    sec_words = {w[:6] for w in re.findall(r"[a-zæøå]{4,}", sec_text)}

    def relevance(rel):
        e = by_file.get(rel) or {}
        cap = ((e.get("caption") or "") + " "
               + " ".join(e.get("content_tags") or [])).lower()
        if not cap:
            return 0
        hits = sum(1 for w in sec_words if w in cap)
        return min(hits * 6, 24)

    def total(rel):
        rel_score = relevance(rel)
        s = score(rel) + rel_score
        if rel in mapped_set:
            s += 4  # mapper tiebreak, never overrides relevance
        e = by_file.get(rel) or {}
        cap = ((e.get("caption") or "") + " "
               + " ".join(e.get("content_tags") or [])).lower()
        if rel_score == 0 and cap:
            s -= 8  # captioned but irrelevant to this section
        return s

    ranked = sorted(candidates, key=total, reverse=True)
    ranked = [r for r in ranked if total(r) > 6 or r in mapped_set]
    need = max(min_photos, 1)
    n = min(max_n, max(need, int(media.get("max_photos") or need)))
    lines = []
    for rel in ranked:
        if len(lines) >= n:
            break
        e = by_file.get(rel) or {}
        if not _is_usable_visual(rel):
            continue
        cap = (e.get("caption") or Path(rel).name).strip()
        lines.append(f"{{{{fig:{rel}}}}}")
        lines.append(cap)
    if not lines:
        return text
    block = "\n".join(lines)
    return (text or "").rstrip() + "\n\n" + block + "\n"


def _prose_ok(text):
    """Validator for write_prose contract — no tables, headings, or figure markup."""
    t = text or ""
    if re.search(r"(?m)^\s{0,3}#{1,6}\s+", t):
        return False
    if re.search(r"(?m)^\s*\|.+\|", t):
        return False
    if FIG_SHORT_MARK.search(t) or FIGURE_MARK.search(t):
        return False
    return bool(t.strip())


def _clean_prose_noise(text):
    """Remove known sludge voice/repetition patterns."""
    t = text or ""
    # ban findings-ledger voice
    t = re.sub(r"(?im)^\s*(finding|funn)\s*:\s*", "", t)
    t = re.sub(r"(?i)the following documents indicate[^.]*\.", "", t)
    # ban repeated project_title/scope filler sentence pattern
    t = re.sub(
        r"(?i)\b(project title|prosjekttittel)\s+er\s+[^.]{1,120}\.\s*"
        r"(scope statement|omfang)\s+er\s+[^.]{1,160}\.",
        "",
        t,
    )
    return re.sub(r"\n{3,}", "\n\n", t).strip()


CONTACT_NOISE_RX = re.compile(
    r"(?i)([\w.+-]+@[\w-]+\.[\w.-]+|https?://\S+|www\.\S+|"
    r"\+?\d[\d\s().-]{7,}\d|"
    r"\b(address|adresse|phone|telefon|mobile|fax|website|url|linkedin)\b)"
)


def _strip_contact_noise_preserving_svg(text: str) -> str:
    """Drop contact/URL noise lines without destroying engine SVG diagrams.

    SVG opening tags include ``xmlns=\"http://www.w3.org/2000/svg\"`` which
    would otherwise match CONTACT_NOISE_RX and strip the whole ``<svg>`` line.
    """
    if not text:
        return text
    parts = re.split(r"(?is)(<svg\b[^>]*>.*?</svg>)", text)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
            continue
        kept = []
        for ln in part.splitlines():
            # Keep orphaned svg openers / markup even if URL-like attrs appear
            s = (ln or "").lstrip()
            if s.startswith("<svg") or s.startswith("</svg") or s.startswith("<"):
                # Still drop pure contact lines that happen to start with <
                if s.startswith("<svg") or s.startswith("</svg"):
                    kept.append(ln)
                    continue
                # Inner SVG children (<rect>, <text>, …) — keep
                if re.match(r"^</?(?:svg|g|rect|text|path|line|circle|ellipse|"
                            r"polyline|polygon|defs|use|title|desc|tspan)\b", s, re.I):
                    kept.append(ln)
                    continue
            if CONTACT_NOISE_RX.search(ln or ""):
                continue
            kept.append(ln)
        out.append("\n".join(kept))
    return "\n".join(out)


def _is_contact_section(sec_key: str) -> bool:
    sk = (sec_key or "").strip().lower()
    return sk in {"contact", "contacts", "kontakt", "kontaktinfo"}


def _is_research_template(mapping: dict) -> bool:
    """True only for research_project_report (not every section named method)."""
    return str(mapping.get("template_key") or "").strip().lower() == "research_project_report"


def _research_required_missing(sec_key: str, artifact: dict, by_id: dict, available_ids: set[str]) -> list[str]:
    """Hard-stop keys per section when research framing is incomplete."""
    sk = (sec_key or "").strip().lower()
    sec_keys = {
        "objective": ("research_question",),
        "method": ("method_description", "equipment", "sample_size"),
        "observations": ("measurement",),
    }
    req = list(sec_keys.get(sk, ()))
    if not req:
        return []
    missing = []
    for key in req:
        from_artifact = str((artifact or {}).get(key) or "").strip()
        from_facts = any(
            str((by_id.get(fid) or {}).get("key") or "").strip().lower() == key
            for fid in (available_ids or set())
        )
        if not from_artifact and not from_facts:
            missing.append(key)
    return missing


def _mangler_lines(keys: list[str], *, lang: str = "no", max_n: int = 5) -> str:
    if not keys:
        return ""
    if (lang or "no").lower().startswith("no"):
        lines = [f"MANGLER: {k} - oppgi" for k in keys[:max_n]]
    else:
        lines = [f"MISSING: {k} - provide value" for k in keys[:max_n]]
    return "\n".join(lines)


STRICT_MISSING_ONLY_ROLES = {
    "method", "methods", "metode", "forsok", "forsøk",
    "results", "resultater", "observations", "discussion",
    "goals", "goal", "mål", "objective", "avvik", "deviations",
    "status", "next_steps",
}


def _section_role_tokens(sec_key: str, section: dict) -> set[str]:
    vals = [
        str(sec_key or ""),
        str(section.get("section_key") or ""),
        str(section.get("title_no") or ""),
        str(section.get("title") or ""),
    ]
    tokens = set()
    for v in vals:
        vv = v.strip().lower()
        if not vv:
            continue
        tokens.add(vv)
        for part in re.split(r"[^a-z0-9æøå]+", vv):
            if part:
                tokens.add(part)
    return tokens


def _strict_missing_keys_for_section(section: dict, by_id: dict, available_ids: set[str]) -> list[str]:
    out = []
    for rf in section.get("required_facts") or []:
        if rf.get("severity") == "info":
            continue
        key = str(rf.get("key") or "").strip()
        if not key:
            continue
        alias = {key.lower(), *(k.lower() for k in FACT_ALIASES.get(key, []))}
        has_fact = any(
            str((by_id.get(fid) or {}).get("key") or "").strip().lower() in alias
            for fid in (available_ids or set())
        )
        if not has_fact:
            out.append(key)
    return out


def _strict_missing_keys_for_research(section: dict, artifact: dict, by_id: dict, available_ids: set[str]) -> list[str]:
    """Research template: force core fields to be explicitly present."""
    sk = str(section.get("section_key") or "").strip().lower()
    require_artifact_only = {
        "objective": {"research_question"},
        "method": {"method_description", "equipment", "sample_size"},
        "next_steps": {"next_step"},
    }
    out = []
    for rf in section.get("required_facts") or []:
        if rf.get("severity") == "info":
            continue
        key = str(rf.get("key") or "").strip()
        if not key:
            continue
        kl = key.lower()
        if kl in require_artifact_only.get(sk, set()):
            if not str((artifact or {}).get(key) or "").strip():
                out.append(key)
            continue
        # default: fact presence in section context
        alias = {kl, *(k.lower() for k in FACT_ALIASES.get(key, []))}
        has_fact = any(
            str((by_id.get(fid) or {}).get("key") or "").strip().lower() in alias
            for fid in (available_ids or set())
        )
        if not has_fact:
            out.append(key)
    return out


def _looks_like_fact_dump(text: str) -> bool:
    t = text or ""
    # key:value walls and repeated "X er Y" tuples
    kv = re.findall(r"(?im)\b[a-z0-9_æøå][a-z0-9_æøå .-]{1,40}:\s+[^.\n]{1,80}", t)
    er = re.findall(r"(?im)\b[a-z0-9_æøå][a-z0-9_æøå .-]{1,40}\s+er\s+[^.\n]{1,80}", t)
    return len(kv) >= 2 or len(er) >= 3


def _is_research_report_mapping(mapping: dict) -> bool:
    return str(mapping.get("template_key") or "").strip().lower() == "research_project_report"


def _is_topic_brief_mapping(mapping: dict) -> bool:
    return str(mapping.get("template_key") or "").strip().lower() == "topic_brief"


def _is_install_manual_mapping(mapping: dict) -> bool:
    return str(mapping.get("template_key") or "").strip().lower() == "installation_manual"


def _index_usable(index):
    return [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]


def _fact_pairs(index, allow_keys=None, allow_prefixes=None, deny_keys=None, limit=12):
    """Collect (label, value, source) for themed research tables."""
    allow_keys = {k.lower() for k in (allow_keys or [])}
    allow_prefixes = tuple(p.lower() for p in (allow_prefixes or ()))
    deny_keys = {k.lower() for k in (deny_keys or (
        "phone", "email", "website", "url", "address", "fax", "linkedin",
        "author_email", "publisher_website",
    ))}
    out, seen = [], set()
    for e in _index_usable(index):
        src = Path(e.get("file") or "").name
        for f in e.get("facts") or []:
            key = str(f.get("key") or "").strip().lower()
            if not key or key in deny_keys:
                continue
            if allow_keys and key not in allow_keys and not any(key.startswith(p) for p in allow_prefixes):
                continue
            val = str(f.get("value") or "").strip()
            if not val or CONTACT_NOISE_RX.search(val):
                continue
            unit = f.get("unit") or ""
            shown = f"{val} {unit}".strip() if unit else val
            sig = (key, shown.lower())
            if sig in seen:
                continue
            seen.add(sig)
            label = key.replace("_", " ")
            out.append((label, shown, src))
            if len(out) >= limit:
                return out
    return out


def _md_table(headers, rows):
    if not rows:
        return ""
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _research_theme_bits(index, artifact=None):
    art = artifact or {}
    hay = " ".join(
        [str(art.get("name") or ""), str(art.get("purpose") or "")]
        + [str(e.get("caption") or "") for e in _index_usable(index)[:40]]
        + [" ".join(e.get("content_tags") or []) for e in _index_usable(index)[:40]]
    ).lower()
    themes = []
    for needle, label in (
        ("emc", "elektromagnetisk kompatibilitet (EMC)"),
        ("cable tray", "cable tray / cable management"),
        ("cable management", "cable tray / cable management"),
        ("shield", "skjermingseffektivitet"),
        ("shielding", "skjermingseffektivitet"),
    ):
        if needle in hay and label not in themes:
            themes.append(label)
    return themes or ["teknisk kildesamling"]


def _research_section_alias(sec_key: str) -> str:
    sk = (sec_key or "").strip().lower()
    aliases = {
        "metode": "method",
        "methods": "method",
        "forsok": "method",
        "forsøk": "method",
        "mal": "objective",
        "mål": "objective",
        "goals": "objective",
        "goal": "objective",
        "resultater": "observations",
        "results": "observations",
        "avvik": "deviations",
        "status": "next_steps",
        "kilderegister": "source_register",
        "innsamede_data": "data_collected",
        "innsamlede_data": "data_collected",
    }
    return aliases.get(sk, sk)


def compile_research_section(sec_key, mapping, index, artifact, lang="no"):
    """Deterministic research_project_report bodies.

    Empty research core → short MANGLER.
    Rich sources → few thematic tables + register — never a full-graph dump.
    """
    sk = _research_section_alias(sec_key)
    art = artifact or {}
    no = (lang or "no").lower().startswith("no")
    usable = _index_usable(index)
    n = len(usable)
    themes = _research_theme_bits(index, art)
    theme_txt = ", ".join(themes[:3])

    if sk == "cover":
        title = art.get("name") or Path((usable[0] or {}).get("file") or "project").stem if usable else "—"
        authors = []
        for e in usable:
            for f in e.get("facts") or []:
                if str(f.get("key") or "").lower() in ("author_name", "author", "prepared_by"):
                    v = str(f.get("value") or "").strip()
                    if v and len(v) > 2 and "@" not in v and v not in authors:
                        authors.append(v)
        author_cell = (", ".join(authors[:3]) + (" m.fl." if len(authors) > 3 else "")) if authors else (
            f"MANGLER: author_name - {'oppgi' if no else 'provide'}"
        )
        inst = str(art.get("institution") or "").strip() or f"MANGLER: institution - {'oppgi' if no else 'provide'}"
        period = str(art.get("report_period") or "").strip() or f"MANGLER: report_period - {'oppgi' if no else 'provide'}"
        material = ("Spesifikasjoner, standarder, produktunderlag, notater"
                    if no else "Specifications, standards, product data, notes")
        headers = ["Parameter", "Verdi", "Kilde"] if no else ["Parameter", "Value", "Source"]
        rows = [
            ["Prosjekttittel" if no else "Project title", title, "Prosjekt" if no else "Project"],
            ["Tema" if no else "Theme", theme_txt, f"Indeks ({n} filer)" if no else f"Index ({n} files)"],
            ["Type materiale" if no else "Material type", material, "Indeks" if no else "Index"],
            ["Institution", inst, "—"],
            ["Rapportperiode" if no else "Report period", period, "—"],
            ["Rapportforfatter (i kilder)" if no else "Authors in sources", author_cell,
             "Sitater i register" if no else "Source register"],
        ]
        note = ("Ikke blande produktnavn, telefonnummer eller ITER-spenninger inn her."
                if no else "Do not mix product names, phone numbers, or ITER voltages here.")
        return _md_table(headers, rows) + "\n\n*" + note + "*"

    if sk == "objective":
        lead = (
            f"Denne mappen er en kildesamling om {theme_txt}, ikke et ferdig laboratorieforsøk."
            if no else
            f"This folder is a source collection on {theme_txt}, not a completed laboratory study."
        )
        rq = str(art.get("research_question") or "").strip()
        if rq:
            body = f"{lead}\n\n**Forskningsspørsmål:** {rq}" if no else f"{lead}\n\n**Research question:** {rq}"
        else:
            body = lead + "\n\n" + _mangler_lines(["research_question"], lang=lang)
            body += (
                "\n\nForeslåtte spørsmål (må bekreftes av bruker før de blir «fakta»):\n\n"
                "- Hvilke skjermingskrav (dB / frekvens) gjelder for cable tray i prosjektets referanser?\n"
                "- Hvilke standarder overlapper eller konflikter (f.eks. MIL-STD-285 vs IEEE 299)?\n"
                "- Hva er relevant for offshore/HVDC-kontekst (Dogger Bank-underlag)?"
                if no else
                "\n\nSuggested questions (must be confirmed before becoming facts):\n\n"
                "- Which shielding requirements (dB / frequency) apply to cable tray in the references?\n"
                "- Which standards overlap or conflict (e.g. MIL-STD-285 vs IEEE 299)?\n"
                "- What is relevant for offshore/HVDC context?"
            )
        return body

    if sk == "method":
        miss = [k for k in ("method_description", "equipment", "sample_size")
                if not str(art.get(k) or "").strip()]
        if miss:
            return _mangler_lines(miss, lang=lang)
        # Explicit research method present — short prose only from artifact fields
        bits = []
        if art.get("method_description"):
            bits.append(str(art["method_description"]))
        if art.get("equipment"):
            bits.append(("Utstyr: " if no else "Equipment: ") + str(art["equipment"]))
        if art.get("sample_size"):
            bits.append(("Utvalg: " if no else "Sample size: ") + str(art["sample_size"]))
        return "\n\n".join(bits)

    if sk == "observations":
        has_meas = any(
            str(f.get("key") or "").lower() in ("measurement", "measured_value", "test_result")
            and str(f.get("value") or "").strip()
            for e in usable for f in (e.get("facts") or [])
        )
        parts = []
        if not has_meas and not str(art.get("measurement") or "").strip():
            parts.append(_mangler_lines(["measurement"], lang=lang))
            parts.append(
                "Det finnes ikke egne måleserier i prosjektet ennå. Under er utdrag fra kildemateriale "
                "(produkt-/standarddata), ikke prosjektets forsøksresultater:"
                if no else
                "No project measurement series yet. Below are extracts from source material "
                "(product/standard data), not the project's experimental results:"
            )
        shield = _fact_pairs(
            index,
            allow_keys={"test_standard", "manufacturer", "navy_project_test_result"},
            allow_prefixes=("attenuation", "h_field", "e_field", "plane_wave", "shield"),
            limit=8,
        )
        if shield:
            headers = ["Størrelse", "Verdi", "Kilde"] if no else ["Item", "Value", "Source"]
            parts.append(("**Skjerming (eksempel fra produktunderlag)**"
                          if no else "**Shielding (examples from product data)**"))
            parts.append(_md_table(headers, [[a, b, c] for a, b, c in shield]))
        return "\n\n".join(p for p in parts if p) or (
            "Ingen observasjoner registrert ennå." if no else "No observations recorded yet."
        )

    if sk == "deviations":
        rows = []
        if not str(art.get("research_question") or "").strip():
            rows.append([
                "Ingen definert research_question" if no else "No research_question defined",
                "Rapporten kan ikke konkludere forskningsmessig" if no else "Report cannot conclude scientifically",
            ])
        if not all(str(art.get(k) or "").strip() for k in ("method_description", "equipment", "sample_size")):
            rows.append([
                "Ingen egen metode / utstyr / utvalg" if no else "No method / equipment / sample",
                "Resultater = kun litteratur/produkt, ikke forsøk" if no else "Results = literature/product only, not experiment",
            ])
        rows.append([
            "Blandede kildetyper" if no else "Mixed source types",
            "Standard, katalog og håndbok i samme mappe — må skilles i analyse"
            if no else "Standards, catalogues and handbooks in one folder — separate in analysis",
        ])
        headers = ["Avvik", "Betydning"] if no else ["Issue", "Meaning"]
        return _md_table(headers, rows)

    if sk == "next_steps":
        status = (
            f"Status: Kildesamling indeksert ({n} filer). Rapportstruktur opprettet; forskningskjernen er ufullstendig."
            if no else
            f"Status: Source collection indexed ({n} files). Report structure created; research core incomplete."
        )
        parts = [status]
        if not str(art.get("next_step") or "").strip():
            parts.append(_mangler_lines(["next_step"], lang=lang))
        else:
            parts.append(str(art["next_step"]))
        parts.append(
            "Mulige neste steg (valg):\n\n"
            "- Formulér research_question\n"
            "- Kjør spesifikasjonsgjennomgang (konflikt/overlapp mellom EN/IEC/NEK/MIL)\n"
            "- Bygg kravmatrise for cable tray / skjerming\n"
            "- Først deretter: egen testplan hvis målinger skal inn i rapporten"
            if no else
            "Possible next steps:\n\n"
            "- State research_question\n"
            "- Run Spec Coherence Review\n"
            "- Build requirements matrix for cable tray / shielding\n"
            "- Only then: own test plan if measurements enter the report"
        )
        return "\n\n".join(parts)

    if sk == "data_collected":
        parts = []
        mech = _fact_pairs(
            index,
            allow_keys={
                "test_standard", "material_standard", "max_span", "manufacturer",
                "load_depth_standard", "radius_fittings_standard",
            },
            allow_prefixes=("max_load", "nec_ground", "splice", "tray_", "cover_"),
            limit=10,
        )
        if mech:
            headers = ["Parameter", "Verdi", "Kilde"] if no else ["Parameter", "Value", "Source"]
            parts.append(("**A. Cable tray / mekanikk (utvalg)**"
                          if no else "**A. Cable tray / mechanics (selection)**"))
            parts.append(_md_table(headers, [[a, b, c] for a, b, c in mech]))
        stds = _fact_pairs(
            index,
            allow_keys={"test_standard", "material_standard", "governing_standard", "building_code"},
            allow_prefixes=("en_", "iec_", "mil_", "nek_", "ieee_", "astm_", "ul_", "hd_", "nema_"),
            limit=12,
        )
        if stds:
            headers = ["Standard", "Merknad"] if no else ["Standard", "Note"]
            rows, seen = [], set()
            std_id = re.compile(
                r"(?i)\b((?:EN|IEC|ISO|NEK|HD)\s*\d[\d\-:/]*|"
                r"MIL[-\s]?STD[-\s]?\d[\w\-]*|"
                r"IEEE\s*(?:Std\s*)?\d[\w\-]*|"
                r"ASTM\s*[A-Z]?\d[\w\-]*|"
                r"UL\s*\d[\w\-]*|"
                r"NEMA\s*[A-Z]?\d?[\w\-]*)\b"
            )
            for label, val, src in stds:
                m = std_id.search(val) or std_id.search(label.replace("_", " "))
                if not m:
                    continue
                shown = m.group(1).strip()
                sig = shown.lower()
                if sig in seen:
                    continue
                seen.add(sig)
                rows.append([shown, src])
            if rows:
                parts.append(("**B. Standarder nevnt i korpus (utvalg)**"
                              if no else "**B. Standards in corpus (selection)**"))
                parts.append(_md_table(headers, rows[:10]))
        miss = []
        if not any(str(f.get("key") or "").lower() == "measurement" for e in usable for f in (e.get("facts") or [])):
            if not str(art.get("measurement") or "").strip():
                miss.append("measurement")
        if not any(str(f.get("key") or "").lower() == "data_location" for e in usable for f in (e.get("facts") or [])):
            if not str(art.get("data_location") or "").strip():
                miss.append("data_location")
        if miss:
            parts.append(_mangler_lines(miss, lang=lang))
        note = ("Ikke telefon, e-post, forlagsadresse eller ITER-spenningslister i denne seksjonen."
                if no else "No phone, email, publisher address, or ITER voltage lists in this section.")
        if parts:
            parts.append("*" + note + "*")
        return "\n\n".join(parts) if parts else (
            "Ingen tematiske måledata funnet ennå." if no else "No thematic measurement data yet."
        )

    if sk == "source_register":
        rows = []
        for e in usable[:40]:
            fn = e.get("file") or ""
            name = Path(fn).name
            if not name or name.startswith("(") or name.lower() in ("prosjektnavn", "project"):
                continue
            roles = e.get("doc_role_hints") or []
            kind = (
                "Produktkatalog" if any(r in roles for r in ("catalogue", "datasheet")) else
                "Produkt / testreferanser" if any(r in roles for r in ("technical_data", "test_result")) else
                "Faglig/prosjektunderlag" if any(r in roles for r in ("overview", "drawing", "site_plan")) else
                "Standard / guide" if any(r in roles for r in ("standard", "spec")) else
                "Dokument"
            )
            if not no:
                kind = {
                    "Produktkatalog": "Product catalogue",
                    "Produkt / testreferanser": "Product / test refs",
                    "Faglig/prosjektunderlag": "Technical / project brief",
                    "Standard / guide": "Standard / guide",
                    "Dokument": "Document",
                }.get(kind, kind)
            use = (e.get("caption") or "")[:70] or ("Bakgrunn" if no else "Background")
            rows.append([name, kind, use])
        if n > 40:
            rows.append([
                (f"Øvrige {n - 40} filer" if no else f"Remaining {n - 40} files"),
                ("Standarder, guider, notater" if no else "Standards, guides, notes"),
                ("Bakgrunn; ikke alle sitert linje for linje"
                 if no else "Background; not all cited line-by-line"),
            ])
        headers = (["Dokument", "Type", "Bruk i rapport"]
                   if no else ["Document", "Type", "Use in report"])
        return _md_table(headers, rows) if rows else (
            "Ingen kilder i indeksen." if no else "No sources in index."
        )

    return None


def _partition_ok(obj, known_ids):
    if not isinstance(obj, dict):
        return False
    prose = obj.get("prose_facts")
    table = obj.get("table_facts")
    if not isinstance(prose, list) or not isinstance(table, list):
        return False
    for fid in list(prose) + list(table):
        if fid not in known_ids:
            return False
    return True


def partition_section_facts(ctx, section, structure, lang="no"):
    """Step 2 — model partitions facts; fallback: all → table (or all → prose)."""
    from call_contracts import CallContract, run_contracted, register

    known = set(ctx["available_ids"]) | set(ctx["primary_ids"])
    ids = [a["id"] for a in ctx["available"]]
    # Computation over validation: structure dictates when possible
    if structure in TABLE_STRUCTURES:
        return {"prose_facts": [], "table_facts": ids}
    if structure in PROSE_LIKE_STRUCTURES and structure != "prose":
        # Lists / steps: all facts feed the narrative — never a side table.
        return {"prose_facts": ids, "table_facts": []}
    if structure == "prose" and not _wants_fact_table(section, structure):
        # Prose without table_format: write narrative from all facts.
        return {"prose_facts": ids, "table_facts": []}
    if not ids:
        return {"prose_facts": [], "table_facts": []}

    def fallback():
        # Prose-like: prefer narrative. Table-like: prefer table.
        if structure in PROSE_LIKE_STRUCTURES:
            return {"prose_facts": list(ids), "table_facts": []}
        return {"prose_facts": [], "table_facts": list(ids)}

    contract = register(CallContract(
        purpose="partition_facts",
        shape='JSON {"prose_facts":[id…], "table_facts":[id…]} — ids from provided set only',
        validate=lambda o: _partition_ok(o, known),
        fallback=fallback,
        model=HAIKU,
        max_tokens=250,
        parse="json",
    ))
    title = section.get("title_no") or section.get("title") or ""
    fact_lines = ctx["available_txt"][:3500]
    messages = [{"role": "user", "content": (
        f"Partition facts for section \"{title}\" ({lang}).\n"
        "Return JSON only: {\"prose_facts\": [ids for narrative], "
        "\"table_facts\": [ids for a parameter table]}.\n"
        "Every id must appear in exactly one list when possible; "
        "numeric specs and ratings prefer table_facts.\n"
        f"FACTS:\n{fact_lines}"
    )}]
    try:
        result = run_contracted(contract, ask, messages, parse_json_fn=parse_json)
        part = result.value
    except Exception:
        part = fallback()
    # Deduplicate / filter
    prose = [i for i in (part.get("prose_facts") or []) if i in known]
    table = [i for i in (part.get("table_facts") or []) if i in known]
    for i in ids:
        if i not in prose and i not in table:
            # Orphans follow the section's structure, not a silent table dump.
            if structure in PROSE_LIKE_STRUCTURES and not _wants_fact_table(section, structure):
                prose.append(i)
            else:
                table.append(i)
    # Prose sections without table_format: collapse any model table preference into prose.
    if structure in PROSE_LIKE_STRUCTURES and not _wants_fact_table(section, structure):
        prose = list(dict.fromkeys(prose + table))
        table = []
    return {"prose_facts": prose, "table_facts": table}


def write_section_prose(sec_key, mapping, index, artifact, lang, fact_ids, ctx,
                        instruction=None):
    """Step 3 — intent-authored prose (foldok_author 0.86).

    Fact-shaped intents: deterministic compose (or model for describe/summarize),
    then verify. Procedural intents are refused — keep the safe fact ledger
    rather than inventing steps/hazards.
    """
    from call_contracts import CallContract, run_contracted, register
    from foldok_author import (
        AUTHORED_NOT_GENERATED,
        AuthoringEngine,
        IntentRefused,
        facts_from_foldok,
        inject_fact_citations,
        resolve_intent,
        verify,
    )

    s = mapping["section"]
    by_id = ctx["by_id"]
    req_missing = []
    for rf in s.get("required_facts", []):
        if not _fact_applies(rf, artifact) or rf.get("severity") == "info":
            continue
        key = rf["key"]
        alias_keys = {key, *FACT_ALIASES.get(key, [])}
        got = [
            fid for fid in ctx["available_ids"]
            if fid in by_id and by_id[fid].get("key") in alias_keys
        ]
        if not got:
            req_missing.append(key)

    role_tokens = _section_role_tokens(sec_key, s)
    if role_tokens & STRICT_MISSING_ONLY_ROLES and req_missing:
        return _mangler_lines(req_missing, lang=lang, max_n=5)

    title = s.get("title_no" if lang == "no" else "title") or s.get("title") or sec_key
    req_content = s.get("required_content") or []
    content_hints = []
    prescriptive = bool(s.get("writing_rules", {}).get("prescriptive"))
    if prescriptive or "prescriptive_banner" in req_content:
        content_hints.append(
            "Start with banner: > **AI-foreslått rekkefølge — bekreft mot "
            "leverandørens anvisning**")
    if "ai_proposed_banner" in req_content:
        content_hints.append(
            "Start the section with a clear banner line: "
            "> **AI-foreslått struktur** — bekreft/endre før bruk.")
    if prescriptive or "author_placeholder_per_phase" in req_content:
        content_hints.append(
            "End the section with: `[AUTHOR: bekreft rekkefølge mot leverandøranvisning]`")
    if "author_placeholder_for_sequencing" in req_content:
        content_hints.append(
            "After each phase heading, include the placeholder "
            "`[AUTHOR: bekreft rekkefølge og ansvar]`.")
    if "checklist_format" in req_content:
        content_hints.append(
            "Use checklist rows: □ check — criterion (cite fact id). "
            "Rows without a cited criterion are marked AI-foreslått.")
    if instruction:
        content_hints.append(f"Additional instruction: {instruction}")
    if req_missing:
        content_hints.append(
            "Required keys with no fact — emit {{missing:key}} for: "
            + ", ".join(req_missing)
        )

    # Hard stop for research sections: if mandatory keys are missing,
    # emit ONLY MANGLER lines (no extra facts, no filler prose).
    if _is_research_template(mapping):
        miss = _research_required_missing(sec_key, artifact or {}, by_id, ctx.get("available_ids") or set())
        if miss:
            return _mangler_lines(miss, lang=lang)

    intent = resolve_intent(
        s,
        sec_key=sec_key,
        document_species=(mapping.get("document_species") or ""),
    )
    facts = facts_from_foldok(list(fact_ids or []), by_id)

    def fallback_safe():
        if req_missing:
            return _mangler_lines(req_missing, lang=lang)
        if intent in AUTHORED_NOT_GENERATED:
            return (
                "[AUTHOR: skriv prosedyre / advarsel her — genereres ikke fra fakta.]"
                if lang == "no" else
                "[AUTHOR: write procedure / warning here — not generated from facts.]"
            )
        return ""

    # 0.86: procedural intents are authored, not generated
    if intent in AUTHORED_NOT_GENERATED:
        # Install manuals: never pad with hollow phase shells / banner walls.
        if _is_install_manual_mapping(mapping):
            bits = []
            if facts:
                bits.append(
                    ("**Siterte forutsetninger / farer (ikke en ferdig prosedyre):**"
                     if lang == "no" else
                     "**Cited constraints / hazards (not a finished procedure):**")
                )
                for f in facts[:12]:
                    cite = f"{{{{fact:{f.id}}}}}" if getattr(f, "id", None) else ""
                    bits.append(f"- {f.key}: {f.value}{(' ' + f.unit) if f.unit else ''} {cite}".rstrip())
            bits.append(fallback_safe())
            return "\n".join(bits)
        text = fallback_safe()
        if content_hints and "[AUTHOR:" not in text:
            text = text + "\n\n" + "\n".join(content_hints[:2])
        return text

    engine = AuthoringEngine(lang=lang or "en")

    # Prefer deterministic compose (zero tokens) when it verifies
    try:
        authored = engine.author(intent, facts, title=title)
    except IntentRefused:
        return fallback_safe()

    if authored.prose and authored.grounded:
        text = inject_fact_citations(_clean_prose_noise(authored.prose), facts)
        for hint in content_hints:
            if hint.startswith("Start") and hint not in text:
                text = hint.replace("Start with banner: ", "").replace(
                    "Start the section with a clear banner line: ", ""
                ) + "\n\n" + text
                break
        if req_missing:
            text += " " + " ".join(f"{{{{missing:{k}}}}}." for k in req_missing)
        if _prose_ok(text):
            if re.search(r"(?im)\b[a-z0-9_]{2,}\s*:\s*\*\*.+\*\*", text):
                return fallback_safe()
            return text

    # Varied phrasing intents may call the model (still verified)
    if intent in ("describe_component", "summarize_system") and facts:
        system = (
            "You write ONE documentation section as clean Markdown prose.\n"
            "RULES: Follow the INTENT. No markdown tables (|), no figure markup. "
            "Cite facts as {{fact:ID}}. Never invent values. No 'Finding:' voice. "
            "No procedures, hazards, or steps that are not in the facts."
        )
        user_prompt = engine.prompt(intent, facts, title=title)
        if content_hints:
            user_prompt += "\n\nEXTRA:\n" + "\n".join(content_hints)
        user_prompt += f"\n\nARTIFACT: {artifact.get('name')} — {artifact.get('purpose')}"

        contract = register(CallContract(
            purpose="generate_section_prose",
            shape="Markdown prose citing {{fact:id}}; no tables, figures, or headings",
            validate=_prose_ok,
            fallback=fallback_safe,
            model=SONNET,
            max_tokens=900,
            parse="text",
        ))
        try:
            result = run_contracted(
                contract, ask,
                [{"role": "user", "content": user_prompt}],
                system=system,
            )
            text = _clean_prose_noise(result.value)
        except Exception:
            return fallback_safe()
        if not _prose_ok(text):
            return fallback_safe()
        if re.search(r"(?im)\b[a-z0-9_]{2,}\s*:\s*\*\*.+\*\*", text):
            return fallback_safe()
        plan = engine.plan(intent, facts, title=title)
        check = verify(text, plan, facts)
        if facts and not check.grounded:
            return fallback_safe()
        return text

    return fallback_safe()


def place_section_figures(text, mapping, index):
    """Step 5 — code figure placement (required_media + caption relevance)."""
    text = resolve_fig_markers(text or "", index)
    return ensure_min_figures(text, mapping, index)


def generate_section(sec_key, mapping, index, artifact, lang, instruction=None, pre_gaps=None,
                     exclude_fact_ids=None):
    """Legacy entry + code-compiled sections. Prefer generate_section_with_structure.

    Code-compiled branches must call place_section_figures — same as
    generate_section_with_structure — because server.py still dispatches here.
    """
    s = mapping["section"]
    if (sec_key or "").strip().lower() in ("abbreviations", "forkortelser"):
        # Glossary is authored from real terms only; never auto-generated from token frequency.
        return ""
    req_content = s.get("required_content") or []
    if sec_key == "supplier_manual_gaps" or "gap_list_from_engine" in req_content:
        gaps = pre_gaps
        if gaps is None:
            gaps = template_gaps({"sections": [s]}, index, artifact)
        text = compile_supplier_manual_gaps(gaps, lang)
        return place_section_figures(text, mapping, index)
    if sec_key == "drawings_register":
        return place_section_figures(compile_drawings_register(index, lang), mapping, index)
    if sec_key == "doc_control":
        return place_section_figures(
            compile_doc_control(index, artifact, lang), mapping, index,
        )
    if sec_key == "spec_overview":
        return place_section_figures(
            compile_spec_overview(index, artifact, lang), mapping, index,
        )
    if sec_key == "bom" or s.get("writing_rules", {}).get("structure") == "bom_table":
        return place_section_figures(
            render_bom_markdown(aggregate_bom(index), lang), mapping, index,
        )
    if s.get("boilerplate"):
        text = s.get(f"boilerplate_{lang}") or s["boilerplate"]
        return place_section_figures(text, mapping, index)

    if _is_topic_brief_mapping(mapping):
        from topic_brief_compile import compile_topic_brief_section
        compiled = compile_topic_brief_section(sec_key, mapping, index, artifact, lang=lang)
        if compiled is not None:
            if (sec_key or "").strip().lower() in ("gaps", "standards_register", "source_register"):
                return normalise_markdown(compiled)
            return place_section_figures(compiled, mapping, index)

    if _is_research_report_mapping(mapping):
        compiled = compile_research_section(sec_key, mapping, index, artifact, lang=lang)
        if compiled is not None:
            if _research_section_alias(sec_key) in ("method", "cover"):
                return normalise_markdown(compiled)
            return place_section_figures(compiled, mapping, index)

    # Non-compiled: run full contracted pipeline
    return generate_section_with_structure(
        sec_key, mapping, index, artifact, lang,
        instruction=instruction, pre_gaps=pre_gaps, exclude_fact_ids=exclude_fact_ids,
    )


def generate_section_with_structure(
    sec_key, mapping, index, artifact, lang, instruction=None, pre_gaps=None,
    exclude_fact_ids=None,
):
    """Six-step section pipeline (WORKORDER 0.49).

    1 SELECT FACTS     code
    2 PARTITION        model (JSON) — skipped when structure is decisive
    3 WRITE PROSE      model (contracted)
    4 BUILD TABLE      code (B1 vocab)
    5 PLACE FIGURES    code
    6 COMPOSE/PAGINATE code (LayoutTree — caller / assemble)
    """
    s = mapping.get("section") or {}
    if (sec_key or "").strip().lower() in ("abbreviations", "forkortelser"):
        # Kill auto-abbreviation-by-count behaviour.
        return ""
    structure = _structure_kind(s)
    req_content = s.get("required_content") or []

    # Code-compiled paths — zero model calls
    def _ret(t): return normalise_markdown(place_section_figures(t, mapping, index))

    if sec_key == "supplier_manual_gaps" or "gap_list_from_engine" in req_content:
        gaps = pre_gaps
        if gaps is None:
            gaps = template_gaps({"sections": [s]}, index, artifact)
        return _ret(compile_supplier_manual_gaps(gaps, lang))
    if sec_key == "drawings_register":
        return _ret(compile_drawings_register(index, lang))
    if sec_key == "doc_control":
        return _ret(compile_doc_control(index, artifact, lang))
    if sec_key == "spec_overview":
        return _ret(compile_spec_overview(index, artifact, lang))
    if sec_key == "bom" or structure == "bom_table":
        return _ret(render_bom_markdown(aggregate_bom(index), lang))
    if s.get("boilerplate"):
        text = s.get(f"boilerplate_{lang}") or s["boilerplate"]
        return _ret(text)

    # Topic brief — facet retrieve + AuthoringEngine (cited pack)
    if _is_topic_brief_mapping(mapping):
        from topic_brief_compile import compile_topic_brief_section
        compiled = compile_topic_brief_section(sec_key, mapping, index, artifact, lang=lang)
        if compiled is not None:
            if (sec_key or "").strip().lower() in (
                "gaps", "standards_register", "source_register", "overview"
            ):
                return normalise_markdown(compiled)
            return _ret(compiled)

    # Installation manual — thin corpus + procedure evidence + deferred register
    if _is_install_manual_mapping(mapping):
        from install_manual_compile import (
            PROCEDURE_SECTION_KEYS,
            append_install_figures,
            candidate_install_filenames,
            compile_install_identity_md,
            compile_install_overview_md,
            compile_install_section_from_plan,
            dedupe_index_by_file,
            focus_needles,
            get_install_claim_plan,
            has_procedure_evidence,
            procedure_gap_md,
            should_stay_thin,
            system_under_install,
            thin_identity_md,
            thin_overview_md,
        )
        index = dedupe_index_by_file(index)
        # Fresh claim plan per generate section batch (shared via artifact cache)
        if isinstance(artifact, dict) and "_install_claim_plan" not in artifact:
            pass  # built lazily on first section
        sk_l = (sec_key or "").strip().lower()
        stay_thin = should_stay_thin(index, artifact)
        candidates = candidate_install_filenames(index, artifact)
        if sk_l == "source_register":
            return normalise_markdown(
                "*(Kilderegister fylles etter generering fra siterte filer.)*"
                if lang == "no" else
                "*(Source register filled after generate from cited files.)*"
            )
        if sk_l == "identification":
            if stay_thin:
                text = thin_identity_md(artifact, lang, candidates=candidates)
            else:
                text = compile_install_identity_md(index, artifact, lang=lang)
                text = append_install_figures(
                    text, index, artifact, section_key=sk_l, limit=2, lang=lang,
                )
            return normalise_markdown(text)
        if sk_l == "system_overview":
            if stay_thin:
                return normalise_markdown(
                    thin_overview_md(artifact, lang, candidates=candidates)
                )
            # Diagrams live only here (claim plan + overview)
            if isinstance(artifact, dict):
                artifact.pop("_install_claim_plan", None)
            return normalise_markdown(
                compile_install_overview_md(index, artifact, lang=lang)
            )
        if sk_l in PROCEDURE_SECTION_KEYS:
            mapped = mapping.get("files") or []
            if stay_thin or not has_procedure_evidence(index, mapped, artifact=artifact):
                if sk_l == "sequence":
                    return normalise_markdown(procedure_gap_md(
                        lang,
                        system=system_under_install(artifact),
                        section_key=sk_l,
                        stay_thin=stay_thin,
                        focus=focus_needles(artifact),
                        candidates=candidates,
                    ))
                return normalise_markdown(
                    "[MANGLER: installasjonsprosedyre] — se seksjonen Installasjonssekvens "
                    "(ingen monteringskilder i tillatt sett; holdes tynn)."
                    if lang == "no" else
                    "[GAP: installation procedure] — see Installation Sequence "
                    "(no mounting sources in allowlist; staying thin)."
                )
            # Shared partitioned claim plan — one assignment across sections
            get_install_claim_plan(index, artifact, mapped_files=mapped)
            text = compile_install_section_from_plan(
                sk_l, index, artifact, mapped_files=mapped, lang=lang,
                include_diagrams=False,  # diagrams only in overview
                include_appendix=(sk_l == "sequence"),
            )
            if text:
                text = append_install_figures(
                    text, index, artifact, section_key=sk_l, limit=4, lang=lang,
                )
                return normalise_markdown(text)
            if sk_l == "sequence":
                return normalise_markdown(procedure_gap_md(
                    lang,
                    system=system_under_install(artifact),
                    section_key=sk_l,
                    stay_thin=False,
                    focus=focus_needles(artifact),
                    candidates=candidates,
                ))
            return normalise_markdown(
                "[MANGLER: installasjonsprosedyre] — se seksjonen Installasjonssekvens."
                if lang == "no" else
                "[GAP: installation procedure] — see Installation Sequence."
            )

    # Research project report — deterministic section contracts (no fact walls)
    if _is_research_report_mapping(mapping):
        compiled = compile_research_section(sec_key, mapping, index, artifact, lang=lang)
        if compiled is not None:
            # Method: MANGLER-only, no figures. Cover: ID table only.
            if _research_section_alias(sec_key) in ("method", "cover"):
                return normalise_markdown(compiled)
            return _ret(compiled)

    # 1. SELECT FACTS
    ctx = build_section_fact_context(
        mapping, index, artifact, exclude_ids=exclude_fact_ids
    )
    role_tokens = _section_role_tokens(sec_key, s)
    # Only hard-stop generic prose sections outside research compiler
    if not _is_research_report_mapping(mapping):
        strict_missing = _strict_missing_keys_for_section(
            s, ctx.get("by_id") or {}, ctx.get("available_ids") or set()
        )
        if role_tokens & STRICT_MISSING_ONLY_ROLES and strict_missing:
            return normalise_markdown(_mangler_lines(strict_missing, lang=lang, max_n=5))
    else:
        strict_missing = []

    # 2. PARTITION
    partition = partition_section_facts(ctx, s, structure, lang=lang)
    prose_ids = partition.get("prose_facts") or []
    table_ids = partition.get("table_facts") or []

    # 3. WRITE PROSE — always for prose-like structures (even if partition preferred tables)
    prose = ""
    want_prose = structure in PROSE_LIKE_STRUCTURES or bool(prose_ids)
    if want_prose:
        ids_for_prose = prose_ids or list(ctx["available_ids"])
        # Prose sections must still run with zero facts (placeholders / structure).
        if ids_for_prose or structure in PROSE_LIKE_STRUCTURES:
            prose = write_section_prose(
                sec_key, mapping, index, artifact, lang,
                ids_for_prose, ctx, instruction=instruction,
            )
            if not _prose_ok(prose):
                # one more attempt already inside contract; redact bare numbers later
                prose = re.sub(r"(?m)^\s*\|.*\|.*$", "", prose or "")
                prose = re.sub(r"(?m)^\s{0,3}#{1,6}\s+.*$", "", prose)
                prose = FIG_SHORT_MARK.sub("", prose)
                prose = FIGURE_MARK.sub("", prose)

    # 4. BUILD TABLE — only when the template asked for a table
    table = ""
    if _wants_fact_table(s, structure):
        table = build_generic_fact_table(
            mapping, index, artifact, lang=lang, ctx=ctx,
            fact_ids=table_ids or None,
        )
        if structure in TABLE_STRUCTURES and not structure_ok(table, "table"):
            table = build_generic_fact_table(
                mapping, index, artifact, lang=lang, ctx=ctx,
            )

    # 5. PLACE FIGURES + compose
    parts = [p for p in (prose.strip(), table.strip()) if p]
    text = "\n\n".join(parts) if parts else (
        build_generic_fact_table(mapping, index, artifact, lang=lang, ctx=ctx)
        if structure in TABLE_STRUCTURES
        else (prose or "")
    )
    text = place_section_figures(text, mapping, index)
    # Default prose safety: never ship fact-dump walls.
    if structure in PROSE_LIKE_STRUCTURES and _looks_like_fact_dump(text):
        if strict_missing:
            return normalise_markdown(_mangler_lines(strict_missing, lang=lang, max_n=5))
        return normalise_markdown("")
    return normalise_markdown(text)


def regenerate_one_section(sec_key, mapping, index, artifact, lang, instruction=None):
    """Re-run one section only. No writes — caller decides after accept."""
    text = generate_section_with_structure(
        sec_key, mapping, index, artifact, lang, instruction=instruction,
    )
    text, cited, violations = postprocess(sec_key, text, index, artifact)
    if violations:
        text2 = generate_section_with_structure(
            sec_key, mapping, index, artifact, lang, instruction=instruction,
        )
        text2, cited2, violations2 = postprocess(sec_key, text2, index, artifact)
        if len(violations2) < len(violations):
            text, cited, violations = text2, cited2, violations2
        if violations:
            text = redact_uncited(text)
    return {"md": text, "cited": cited, "violations": violations}


SPEC_SECTIONS = {"technical_data", "tech", "circuit_schedule", "test_results", "test_documentation"}
BARE_NUM = re.compile(r"\b\d+[.,]?\d*\b")
# spans exempt from the bare-number rule: resolved facts (bold), MANGLER
# placeholders, markdown headers, table separator rows
PROTECTED_SPAN = re.compile(r"\*\*[^*]+\*\*|`\[MANGLER[^\]]*\]`|^#+ .*$|^\|[-: |]+\|$", re.M)


def redact_uncited(text):
    """Contract §4: after a failed regeneration, uncited numbers become
    placeholders instead of shipping unverified values."""
    out, last = [], 0
    for m in PROTECTED_SPAN.finditer(text):
        out.append(BARE_NUM.sub("`[MANGLER: uverifisert verdi]`", text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(BARE_NUM.sub("`[MANGLER: uverifisert verdi]`", text[last:]))
    return "".join(out)


def strip_duplicate_heading(text):
    """Remove a leading heading the model echoed — main() already adds ## title."""
    return re.sub(r"^\s{0,3}#{1,6}\s+.+\n+", "", text.lstrip(), count=1)


def postprocess(sec_key, text, index, artifact=None, excluded_fact_ids=None, known_keys=None):
    """Resolve citations, convert missing markers, enforce bare-number rule.
    ONE_AGENT_SPEC B3: never emit [MANGLER: ukjent kilde]; drop sentences
    that depend on unknown fact ids; reject non-canonical MANGLER keys.
    WORKORDER 0.48: resolve {{fig:filename}} markers."""
    text = strip_duplicate_heading(text)
    text = resolve_fig_markers(text, index)
    try:
        from install_manual_compile import dedupe_index_by_file
        index = dedupe_index_by_file(index)
    except Exception:
        pass
    by_id = {}
    for e in index or []:
        for f in e.get("facts", []):
            fid = f.get("id")
            if fid and fid not in by_id:
                by_id[fid] = f
    excluded_fact_ids = set(excluded_fact_ids or [])
    known = set(known_keys or [])
    for e in index or []:
        for f in e.get("facts") or []:
            if f.get("key"):
                known.add(f["key"])
    if artifact:
        if artifact.get("name"):
            by_id["artifact-name"] = {"id": "artifact-name", "key": "project_title", "value": artifact["name"], "unit": None}
            known.add("project_title")
        if artifact.get("purpose"):
            by_id["artifact-purpose"] = {"id": "artifact-purpose", "key": "scope_statement", "value": artifact["purpose"], "unit": None}
            known.add("scope_statement")
    cited = []
    unknown_cites = []

    def sub_fact(m):
        fid = m.group(1)
        f = by_id.get(fid)
        if not f:
            if fid in excluded_fact_ids:
                return "`[MANGLER: kilde ekskludert]`"
            unknown_cites.append(fid)
            return "⟦DROP_UNKNOWN_CITE⟧"
        cited.append(f["id"])
        unit = f" {f['unit']}" if f.get("unit") else ""
        # Tables break if resolved values contain pipe characters
        val = str(f.get("value") or "").replace("|", "/")
        if f.get("provenance") == "reference":
            return f"**{val}{unit} ~**"
        if str(f.get("id", "")).startswith("user-"):
            return f"**{val}{unit} ✓**"
        return f"**{val}{unit}**"

    text = re.sub(r"\{\{fact:([\w-]+)\}\}", sub_fact, text)
    text = re.sub(r"\{\{missing:([\w_]+)\}\}", r"`[MANGLER: \1]`", text)

    # Scope/meta may only live in project identification/header sections.
    sk = (sec_key or "").strip().lower()
    if sk not in {"cover", "project_identification", "identification", "header"}:
        text = re.sub(r"(?i)\b(project title|prosjekttittel)\b[^.\n]{0,180}[.\n]?", "", text)
        text = re.sub(r"(?i)\b(scope statement|omfang)\b[^.\n]{0,220}[.\n]?", "", text)
        text = re.sub(r"(?i)\b(author name|forfatter)\b[^.\n]{0,140}[.\n]?", "", text)

    # Contact/publishing noise never belongs outside explicit contact sections.
    # Preserve engine-generated <svg>…</svg> (xmlns URLs are not contact spam).
    if not _is_contact_section(sec_key):
        text = _strip_contact_noise_preserving_svg(text or "")

    def _drop_marked_chunks(blob, marker):
        """Drop prose sentences with marker; for tables, drop lines only."""
        if marker not in blob:
            return blob
        if structure_ok(blob, "table") or any(
            ln.strip().startswith("|") for ln in blob.splitlines()
        ):
            lines = [
                ln for ln in blob.splitlines()
                if marker not in ln
            ]
            return "\n".join(lines).replace(marker, "").strip()
        chunks = re.split(r"(?<=[.!?])\s+", blob)
        return " ".join(c for c in chunks if marker not in c).replace(marker, "").strip()

    # Drop sentences that still depend on an unknown citation
    text = _drop_marked_chunks(text, "⟦DROP_UNKNOWN_CITE⟧")

    # Forbidden junk MANGLER keys → drop the whole sentence (never leave "ukjent kilde")
    def scrub_mangler(m):
        key = m.group(1).strip()
        if key.lower() in ("ukjent kilde", "ukjent_kilde", "ukjent", "unknown"):
            return "⟦DROP_JUNK_MANGLER⟧"
        if " " in key:
            return "⟦DROP_JUNK_MANGLER⟧"
        if known and key not in known and not re.match(r"^[a-z][a-z0-9_]*$", key):
            return "⟦DROP_JUNK_MANGLER⟧"
        return m.group(0)

    text = re.sub(r"`?\[MANGLER:\s*([^\]]+)\]`?", scrub_mangler, text)
    text = _drop_marked_chunks(text, "⟦DROP_JUNK_MANGLER⟧")
    # Collapse repeated spaces/tabs only — never newlines (tables + {{fig}} lines)
    text = "\n".join(
        re.sub(r"[^\S\n]{2,}", " ", ln).rstrip() for ln in (text or "").splitlines()
    ).strip()
    # Collapse accidental duplicated phrases in a cell/line ("Toyota X Toyota X")
    text = "\n".join(
        re.sub(r"\b(.{8,80}?)\s+\1\b", r"\1", ln) for ln in text.splitlines()
    )

    violations = []
    if unknown_cites:
        violations.append(f"unknown_cite:{','.join(unknown_cites[:5])}")
    if sec_key in SPEC_SECTIONS:
        stripped = PROTECTED_SPAN.sub("", text)
        stripped = re.sub(r"\{\{[^}]+\}\}", "", stripped)
        for m in BARE_NUM.finditer(stripped):
            violations.append(m.group(0))
    return text, cited, violations


def append_fact_to_entry(entry, fact, cache_path):
    """Append an extracted fact to a cache entry and persist."""
    facts = entry.setdefault("facts", [])
    sha = entry.get("sha", "x")[:8]
    fact["id"] = f"{sha}-{len(facts)}"
    facts.append(fact)
    cache_path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
    return fact


def _file_text_for_extract(path: Path, rel_name: str):
    ext = path.suffix.lower()
    if ext in DOC_EXT:
        try:
            from markitdown import MarkItDown
            return MarkItDown().convert(str(path)).text_content[:12000]
        except Exception as e:
            return f"(extraction failed: {e})"
    if ext in PHOTO_EXT:
        return None  # image path handled separately
    return ""


def extract_targeted(path: Path, rel_name: str, entry, cache_path, key, hint, lang):
    """One Haiku call to extract a single fact from one file. Returns fact dict or None."""
    ext = path.suffix.lower()
    hint_txt = hint or "ingen"
    if ext in PHOTO_EXT:
        b64 = shrink_image(path)
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": (
                f"Extract ONLY fact key '{key}' from this image. File: {rel_name}. "
                f"Location hint: {hint_txt}. Reply ONLY JSON: "
                f'{{"found":true,"value":"...","unit":null,"fact_type":"spec","source_location":"..."}} '
                f'or {{"found":false}}. If not visible, found=false. Never infer.')},
        ]
        raw = ask("extract_targeted", HAIKU, [{"role": "user", "content": content}], max_tokens=400)
    else:
        md_text = _file_text_for_extract(path, rel_name) or entry.get("caption", "")
        raw = ask("extract_targeted", HAIKU, [{"role": "user", "content":
            f"Extract ONLY fact key '{key}' from this document. File: {rel_name}. "
            f"Location hint: {hint_txt}.\n\n{md_text[:10000]}\n\n"
            f'Reply ONLY JSON: {{"found":true,"value":"...","unit":null,"fact_type":"spec","source_location":"..."}} '
            f'or {{"found":false}}. If not present, found=false. Never infer.'}], max_tokens=400)
    data = parse_json(raw)
    cost = LEDGER[-1]["eur"] if LEDGER else 0
    if not data.get("found"):
        return None, cost
    fact = {"key": key, "value": data["value"], "unit": data.get("unit"),
            "fact_type": data.get("fact_type", "spec"),
            "source_location": data.get("source_location") or rel_name}
    fact = append_fact_to_entry(entry, fact, cache_path)
    return fact, cost


def search_fact_candidates(index, key):
    """Code-only search for candidate facts matching an open gap key (0 tokens)."""
    alias_keys = {key, *FACT_ALIASES.get(key, [])}
    cands = []
    for e in index:
        if e.get("kind") == "skipped":
            continue
        for f in e.get("facts", []):
            if f.get("key") in alias_keys:
                cands.append({
                    "file": e["file"], "fact_id": f["id"], "key": f["key"],
                    "value": f["value"], "unit": f.get("unit"),
                    "excerpt": f"{f['key']} = {f['value']}{f.get('unit') or ''}",
                    "source": f.get("source_location") or e["file"],
                })
        cap = (e.get("caption") or "").lower()
        if key.replace("_", " ") in cap or key in cap:
            for f in e.get("facts", []):
                if f["id"] not in {c["fact_id"] for c in cands}:
                    cands.append({
                        "file": e["file"], "fact_id": f["id"], "key": f["key"],
                        "value": f["value"], "unit": f.get("unit"),
                        "excerpt": e.get("caption", "")[:120],
                        "source": e["file"],
                    })
    return cands[:12]


def gap_assist_search(index, key, lang, project_context=None):
    """Step 2: Haiku over file summaries when code search finds nothing."""
    caps = "\n".join(f"[{e['file']}] {e.get('caption','')}" for e in index if e.get("kind") != "skipped")[:8000]
    ctx_block = (project_context.strip() + "\n\n") if project_context else ""
    raw = ask("gap_assist", HAIKU, [{"role": "user", "content":
        f"{ctx_block}Gap key '{key}' not found in indexed facts. Search these file summaries and reply ONLY JSON:\n"
        f'{{"action":"propose","file":"filename","hint":"where to look","key":"{key}"}} OR '
        f'{{"action":"absent","message":"Finnes ikke i kildene"}}\n\nFILES:\n{caps}'}], max_tokens=500)
    return parse_json(raw)


def fill_known_gaps(state, template, index, artifact, fc, keys_only=None, documents=None):
    """Apply index/artifact values to every gap key we can already resolve — zero tokens."""
    repaired = repair_miskeyed_area_mangler(state, index, artifact)
    keys_only = set(keys_only) if keys_only else None
    gaps = state.get("gaps") or []
    documents = documents if documents is not None else (state.get("documents") or [])
    key_facts = {}
    for g in gaps:
        key = g.get("key")
        if not key or key in key_facts:
            continue
        if keys_only is not None and key not in keys_only:
            continue
        # Mis-tagged area already fixed above — don't try to fill real criterion with m²
        if key == "criterion" and repaired:
            continue
        guide = gap_guide(key, g.get("section", ""), index, artifact, documents)
        if guide["action"] != "apply_value" or not guide.get("suggested"):
            continue
        s = guide["suggested"]
        fid = s.get("fact_id")
        if fid and str(fid).startswith("artifact-"):
            fact = {"id": fid, "key": key, "value": s["value"], "unit": s.get("unit"),
                    "source_location": s.get("source", "artefaktmodell")}
        elif fid:
            fact = None
            for e in index:
                for f in e.get("facts", []):
                    if f.get("id") == fid:
                        fact = {**f, "source_location": e["file"]}
                        break
            if not fact:
                continue
        else:
            continue
        key_facts[key] = fact
    # Also apply floor_area if summary still has MANGLER:floor_area
    if keys_only is None or "floor_area" in (keys_only or set()):
        area = pick_best_area_fact(index, artifact)
        if area and "floor_area" not in key_facts:
            open_keys = {g.get("key") for g in gaps}
            if "floor_area" in open_keys or repaired:
                key_facts.setdefault("floor_area", {**area, "key": "floor_area"})
    if not key_facts and not repaired:
        return {"applied": [], "gaps": state.get("gaps", []), "repaired_sections": []}
    import doc_state as ds
    result = {"applied": [], "gaps": state.get("gaps", []), "repaired_sections": repaired}
    if key_facts:
        result = ds.apply_multiple_cited(state, key_facts, template, index, artifact, fc)
        result["repaired_sections"] = repaired
    else:
        state["gaps"] = ds.compute_all_gaps(state, template, index, artifact, fc)
        result["gaps"] = state["gaps"]
    return result


def count_fillable_gaps(state, index, artifact, documents=None):
    """How many open gaps have a known value ready to apply (zero tokens)."""
    gaps = state.get("gaps") or []
    documents = documents if documents is not None else (state.get("documents") or [])
    seen, n = set(), 0
    for g in gaps:
        key = g.get("key")
        if not key or key in seen:
            continue
        seen.add(key)
        guide = gap_guide(key, g.get("section", ""), index, artifact, documents)
        if guide["action"] == "apply_value" and guide.get("suggested"):
            n += 1
    return n


def open_gap_keys_from_gaps(gaps):
    return {g["key"] for g in gaps if g.get("type") == "missing_fact" or g.get("key")}


def match_new_facts_to_gaps(index_entry, open_keys, aliases=None):
    """After indexing a new file, which open gap keys does it cover?
    aliases defaults to FACT_ALIASES; pass merged local_learning aliases from the workbench."""
    alias_map = aliases if aliases is not None else FACT_ALIASES
    found = {}
    for f in index_entry.get("facts", []):
        for gk in open_keys:
            if f.get("key") == gk or f.get("key") in alias_map.get(gk, []):
                found[gk] = f
    return found


# ── MAIN ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="+", help="one or more project folders")
    ap.add_argument("--template", required=True)
    ap.add_argument("--lang", default="no", choices=["no", "en", "pl"])
    ap.add_argument("--out", default=None, help="output path (default: <folder>/draft.md)")
    ap.add_argument("--yes", action="store_true", help="skip checkpoint A confirmation")
    ap.add_argument("--dump-mapping", action="store_true", help="write mapping.json for eval harness")
    args = ap.parse_args()

    folders = [Path(f) for f in args.folder]
    if args.out is None:
        args.out = str(folders[0] / "draft.md")
    template = json.loads(Path(args.template).read_text(encoding="utf-8"))

    # recursive: subfolders (Bilder/, Tegninger/, Rapporter/) are sources too;
    # hidden dirs (incl. .foldok_cache) excluded at every level. Per-folder
    # cache so a folder shared between projects indexes once, free everywhere.
    SKIP_DIRS = {"capture", "foldok-engine", "feltdok-engine", "node_modules", "__pycache__",
                 "releases", ".git", ".cursor"}
    tasks = []  # (path, rel_name, cache_dir)
    for folder in folders:
        cache_dir = __import__("foldok_paths").cache_dir(folder)
        cache_dir.mkdir(exist_ok=True)
        prefix = f"{folder.name}/" if len(folders) > 1 else ""
        for p in sorted(folder.rglob("*")):
            if not p.is_file():
                continue
            rel_parts = p.relative_to(folder).parts
            if any(part.startswith(".") for part in rel_parts):
                continue
            if any(part in SKIP_DIRS for part in rel_parts[:-1]):
                continue
            tasks.append((p, prefix + p.relative_to(folder).as_posix(), cache_dir))

    print(f"◆ Indexing {len(tasks)} files across {len(folders)} folder(s) — cached files are free…")
    index, done, t0 = [None] * len(tasks), 0, time.time()
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(index_file, p, args.lang, cd, rel): i
                for i, (p, rel, cd) in enumerate(tasks)}
        for fut in as_completed(futs):
            i = futs[fut]
            e = fut.result()
            index[i] = e
            done += 1
            el = time.time() - t0
            eta = int(el / done * (len(tasks) - done)) if done else 0
            tag = "cache" if e.get("cached") else e["kind"]
            print(f"  [{done}/{len(tasks)} · ~{eta}s igjen] [{tag:>6}] {e['file']}: {e['caption'][:60]}")
    index = [e for e in index if e["kind"] != "skipped"]
    # Project/folder name is always a source (WORKORDER 0.19B §1)
    for folder in folders:
        synth = index_project_name(folder.name, __import__("foldok_paths").cache_dir(folder), args.lang)
        if synth:
            index = [synth] + [e for e in index if e.get("kind") != "project_name"]
            break

    print("\n◆ Checkpoint A — artifact model")
    artifact = build_artifact_model(index, args.lang)
    print(json.dumps(artifact, indent=2, ensure_ascii=False))
    if not args.yes:
        if input("\nIs this correct? [y/N] ").strip().lower() != "y":
            sys.exit("Corrections flow not implemented in CLI — edit captions in cache or rerun. Aborting.")

    print("\n◆ Checkpoint B — mapping + gap detection")
    mappings, gaps, guard_report = map_sections(template, index, artifact)
    for held in (guard_report.get("held_back") or []):
        name = held["file"] if isinstance(held, dict) else held
        print(f"  [personal_doc] held back: {name}")
    if guard_report.get("intake_notice"):
        print(f"  {guard_report['intake_notice']}")
    for g in gaps:
        print(f"  [{g['severity']:>8}] {g['section']}: {g['type']} → {g['label']}")
    blocking = [g for g in gaps if g["severity"] == "blocking"]

    if args.dump_mapping:
        dump = {k: {"files": v["files"], "fact_ids": v["fact_ids"]} for k, v in mappings.items()}
        (folders[0] / "mapping.json").write_text(json.dumps(dump, indent=2))
        print("  mapping.json written for eval harness")

    print("\n◆ Checkpoint C — generating sections")
    out, all_violations = [f"# {artifact['name']}\n"], []
    for sec_key, mapping in mappings.items():
        s = mapping["section"]
        title = s["title_no"] if args.lang == "no" else s["title"]
        print(f"  → {title}")
        text = generate_section_with_structure(sec_key, mapping, index, artifact, args.lang)
        text, cited, violations = postprocess(sec_key, text, index, artifact)
        if violations:
            print(f"    ⚠ uncited numbers in spec section: {violations} — regenerating once")
            text2 = generate_section_with_structure(sec_key, mapping, index, artifact, args.lang)
            text2, cited2, violations2 = postprocess(sec_key, text2, index, artifact)
            if len(violations2) < len(violations):
                text, cited, violations = text2, cited2, violations2
            if violations:
                # contract §4: still failing after one retry → replace the
                # uncited numbers with placeholders and flag for the user
                print(f"    ⚠ still uncited after retry: {violations} — redacted to [MANGLER]")
                text = redact_uncited(text)
                all_violations.append((sec_key, violations))
        out.append(f"\n## {title}\n\n{text}\n")
        if mapping["files"]:
            out.append("*Kilder: " + ", ".join(mapping["files"]) + "*\n")

    Path(args.out).write_text("\n".join(out), encoding="utf-8")

    # ── reports ──────────────────────────────────────────────────
    total = sum(l["eur"] for l in LEDGER)
    print(f"\n◆ Done → {args.out}")
    print(f"\n  TOKEN LEDGER ({len(LEDGER)} calls, €{total:.3f} total)")
    by_p = {}
    for l in LEDGER:
        by_p.setdefault(l["purpose"], [0, 0.0])
        by_p[l["purpose"]][0] += 1
        by_p[l["purpose"]][1] += l["eur"]
    for p, (n, c) in by_p.items():
        print(f"    {p:<18} {n:>3} calls  €{c:.3f}")
    print(f"\n  GAPS: {len(blocking)} blocking, {len(gaps)-len(blocking)} warning/info")
    for g in blocking:
        print(f"    ✗ BLOCKING [{g['section']}] {g['label']}")
    sugg = detect_suggestions(index, artifact, current_template_key=template.get("template_key"))
    if sugg:
        print("\n  FORSLAG (valgfritt — prosjektet ser ut til å trenge):")
        for s in sugg:
            print(f"    · {s['name']}  — {s['reason']} (funn: {s['evidence']})")
    if all_violations:
        print(f"\n  ⚠ CITATION VIOLATIONS (redacted to [MANGLER], review these sections): {all_violations}")
    print("\n  Evaluate against definition of done:")
    print("    1. artifact model ≥80% correct unedited?")
    print("    2. ≥80% of photos in the right section?")
    print("    3. zero specs without fact citation?")
    print("    4. every genuine gap visible as [MANGLER]?")


if __name__ == "__main__":
    main()
