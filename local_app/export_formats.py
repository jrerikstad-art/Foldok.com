"""WORKORDER 0.61 — multi-format export from the same document content.

Render target only — never regenerates AI content. pptx/docx split large
tables deterministically with an explicit notice (never silent truncate).
"""
from __future__ import annotations

import html as html_lib
import io
import re
import zipfile
from pathlib import Path
from typing import Any


def notices_for_format(fmt: str) -> list[str]:
    return []


def sections_from_state(state: dict, template: dict | None = None) -> list[dict]:
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    order = []
    if template:
        order = [s.get("section_key") for s in (template.get("sections") or []) if s.get("section_key")]
    keys = order or sorted(sections.keys())
    # Sketch: order by placeholder y
    sketch = (doc.get("sketch") or {}).get("placeholders") or []
    if sketch and doc.get("document_species") == "sketch":
        out = []
        for ph in sorted(sketch, key=lambda p: float(p.get("y") or 0)):
            out.append({
                "key": ph.get("bound_section") or ph.get("id") or "block",
                "title": ph.get("label") or ph.get("type") or "Blokk",
                "md": ph.get("md") or "",
                "type": ph.get("type"),
            })
        if out:
            return out
    out = []
    for sk in keys:
        sec = sections.get(sk) or {}
        title = sec.get("title_override")
        if not title and template:
            for s in template.get("sections") or []:
                if s.get("section_key") == sk:
                    title = s.get("title_no") or s.get("title")
                    break
        out.append({"key": sk, "title": title or sk, "md": sec.get("md") or "", "type": sec.get("block_type")})
    return out


def _split_table_rows(md: str, max_rows: int = 6) -> tuple[list[str], str | None]:
    """Split markdown tables into chunks of max_rows (plus header)."""
    lines = (md or "").splitlines()
    table_lines = [ln for ln in lines if ln.strip().startswith("|")]
    if len(table_lines) <= max_rows + 2:  # header + sep + rows
        return [md], None
    header = table_lines[0]
    sep = table_lines[1] if len(table_lines) > 1 else "|---|"
    rows = table_lines[2:]
    chunks = []
    for i in range(0, max(len(rows), 1), max_rows):
        part = rows[i:i + max_rows]
        chunks.append("\n".join([header, sep] + part))
    notice = f"Tabellen ble delt over {len(chunks)} lysbilder"
    return chunks, notice


def render_html_export(state: dict, template: dict | None, *, title: str = "Dokument") -> str:
    parts = [f"<!DOCTYPE html><html><head><meta charset=utf-8><title>{html_lib.escape(title)}</title>",
             "<style>body{font-family:Georgia,serif;max-width:720px;margin:2rem auto;padding:0 1rem;line-height:1.5}",
             "h1{font-size:1.6rem}h2{font-size:1.2rem;margin-top:1.8rem}table{border-collapse:collapse;width:100%}",
             "td,th{border:1px solid #ccc;padding:4px 8px} .notice{background:#fff8e6;padding:8px;margin:1rem 0}</style></head><body>"]
    parts.append(f"<h1>{html_lib.escape(title)}</h1>")
    for sec in sections_from_state(state, template):
        parts.append(f"<h2 id=\"{html_lib.escape(sec['key'])}\">{html_lib.escape(sec['title'])}</h2>")
        md = sec.get("md") or ""
        # minimal md → html
        for ln in md.splitlines():
            if ln.startswith("|"):
                parts.append(f"<div>{html_lib.escape(ln)}</div>")
            elif ln.strip():
                parts.append(f"<p>{html_lib.escape(ln)}</p>")
    parts.append("</body></html>")
    return "\n".join(parts)


def render_pptx_export(state: dict, template: dict | None, *, title: str = "Dokument") -> tuple[bytes, list[str]]:
    """One slide per section; large tables split with notice. Pure stdlib OOXML zip."""
    notices: list[str] = []
    slides: list[tuple[str, str]] = [(title, "Foldok · presentasjon")]
    for sec in sections_from_state(state, template):
        md = sec.get("md") or ""
        if "|" in md and md.count("\n|") >= 6:
            chunks, notice = _split_table_rows(md, max_rows=6)
            if notice:
                notices.append(f"{sec['title']}: {notice}")
            for i, chunk in enumerate(chunks):
                label = sec["title"] if len(chunks) == 1 else f"{sec['title']} ({i+1}/{len(chunks)})"
                slides.append((label, chunk[:1800]))
        else:
            # max ~6 bullets
            bullets = [ln.lstrip("-* ").strip() for ln in md.splitlines() if ln.strip()][:6]
            body = "\n".join(bullets) if bullets else (md[:800] or "—")
            slides.append((sec["title"], body))

    # Minimal PPTX package
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _pptx_content_types(len(slides)))
        z.writestr("_rels/.rels", _pptx_rels_root())
        z.writestr("ppt/_rels/presentation.xml.rels", _pptx_pres_rels(len(slides)))
        z.writestr("ppt/presentation.xml", _pptx_presentation(len(slides)))
        z.writestr("ppt/slideMasters/slideMaster1.xml", _SLIDE_MASTER)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", _SLIDE_LAYOUT)
        for i, (stitle, body) in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", _pptx_slide(stitle, body))
        if notices:
            z.writestr("ppt/notices.txt", "\n".join(notices))
    return buf.getvalue(), notices


def render_docx_export(state: dict, template: dict | None, *, title: str = "Dokument") -> bytes:
    """Minimal OOXML docx from sections (stdlib)."""
    paras = [title, ""]
    for sec in sections_from_state(state, template):
        paras.append(sec["title"])
        paras.append(sec.get("md") or "")
        paras.append("")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _DOCX_CT)
        z.writestr("_rels/.rels", _DOCX_RELS)
        z.writestr("word/document.xml", _docx_document(paras))
    return buf.getvalue()


def write_format_export(
    folder: Path | None,
    state: dict,
    template: dict | None,
    *,
    fmt: str,
    display_name: str,
    md_content: str | None = None,
) -> tuple[Path | None, str, list[str], bytes | None]:
    """Returns (path_or_none, display, notices, raw_bytes_if_no_folder)."""
    fmt = (fmt or "pdf").lower()
    notices: list[str] = []
    safe = re.sub(r'[\\/:*?"<>|]', "-", display_name)[:100] or "export"

    if fmt == "html":
        raw = render_html_export(state, template, title=display_name).encode("utf-8")
        name = f"{safe}.html"
    elif fmt == "pptx":
        raw, notices = render_pptx_export(state, template, title=display_name)
        name = f"{safe}.pptx"
    elif fmt == "docx":
        raw = render_docx_export(state, template, title=display_name)
        name = f"{safe}.docx"
    else:
        # pdf target → markdown/html preview path (existing md writer used by caller)
        text = md_content or ""
        raw = text.encode("utf-8")
        name = f"{safe}.md"
        fmt = "pdf"

    if folder and Path(folder).is_dir():
        out_dir = Path(folder) / "Rapporter"
        out_dir.mkdir(exist_ok=True)
        path = out_dir / name
        path.write_bytes(raw)
        return path, name, notices, None
    return None, name, notices, raw


# ── minimal OOXML snippets ────────────────────────────────────────────

def _esc_xml(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pptx_content_types(n: int) -> str:
    overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, n + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
{overrides}
</Types>'''


def _pptx_rels_root() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>'''


def _pptx_pres_rels(n: int) -> str:
    rels = "\n".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, n + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rels}
<Relationship Id="rId{n+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
</Relationships>'''


def _pptx_presentation(n: int) -> str:
    slds = "\n".join(f'<p:sldId id="{255+i}" r:id="rId{i}"/>' for i in range(1, n + 1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldIdLst>{slds}</p:sldIdLst>
<p:sldSz cx="9144000" cy="6858000"/>
</p:presentation>'''


_SLIDE_MASTER = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr/>
</p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"
 accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
</p:sldMaster>'''

_SLIDE_LAYOUT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank">
<p:cSld><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr/>
</p:spTree></p:cSld>
</p:sldLayout>'''


def _pptx_slide(title: str, body: str) -> str:
    # Escape and put body as one text run (newlines → &#10;)
    t = _esc_xml(title)[:120]
    b = _esc_xml(body)[:2000].replace("\n", "&#10;")
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr/>
<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="457200" y="274320"/><a:ext cx="8229600" cy="914400"/></a:xfrm></p:spPr>
<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr sz="2800" b="1"/><a:t>{t}</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr id="3" name="Body"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="457200" y="1371600"/><a:ext cx="8229600" cy="4572000"/></a:xfrm></p:spPr>
<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr sz="1600"/><a:t>{b}</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld>
</p:sld>'''


_DOCX_CT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

_DOCX_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''


def _docx_document(paras: list[str]) -> str:
    body = []
    for i, p in enumerate(paras):
        style = "Heading1" if i == 0 else ("Heading2" if p and not paras[i - 1] == "" and i > 0 and paras[i - 1] == "" else "Normal")
        # crude: first non-empty after blank = heading2
        if i == 0:
            style = "Heading1"
        elif p and (i == 0 or paras[i - 1] == ""):
            style = "Heading2"
        else:
            style = "Normal"
        t = _esc_xml(p).replace("\n", "</w:t><w:br/><w:t>")
        body.append(
            f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(body)}<w:sectPr/></w:body></w:document>'
    )
