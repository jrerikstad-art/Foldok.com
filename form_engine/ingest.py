"""Ingest user templates → page rasters for faithful overlay."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp", ".heic"}
PDF_EXT = {".pdf"}
DOC_EXT = {".docx", ".doc", ".rtf", ".txt", ".md"}
HTML_EXT = {".html", ".htm"}


def file_sha256(path: Path | None = None, raw: bytes | None = None) -> str:
    h = hashlib.sha256()
    if raw is not None:
        h.update(raw)
    elif path:
        h.update(Path(path).read_bytes())
    return h.hexdigest()


def _b64_jpeg_from_png_or_jpeg(raw: bytes, ext: str) -> tuple[str, str]:
    """Return (mime, b64). Prefer keeping jpeg/png as-is when possible."""
    ext = (ext or "").lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg", base64.b64encode(raw).decode("ascii")
    if ext == ".png":
        return "image/png", base64.b64encode(raw).decode("ascii")
    if ext == ".webp":
        return "image/webp", base64.b64encode(raw).decode("ascii")
    # Fallback: try pillow → jpeg
    try:
        from io import BytesIO
        from PIL import Image
        im = Image.open(BytesIO(raw)).convert("RGB")
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=88)
        return "image/jpeg", base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return "image/jpeg", base64.b64encode(raw).decode("ascii")


def pdf_pages_as_images(path: Path, *, max_pages: int = 6, dpi: int = 144) -> list[dict]:
    """Rasterize PDF pages via PyMuPDF (fitz)."""
    try:
        import fitz
    except ImportError:
        return []
    doc = fitz.open(path)
    out = []
    scale = dpi / 72.0
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        raw = pix.tobytes("jpeg")
        out.append({
            "page": i,
            "mime": "image/jpeg",
            "data_b64": base64.b64encode(raw).decode("ascii"),
            "width_px": pix.width,
            "height_px": pix.height,
        })
    doc.close()
    return out


def ingest_bytes(raw: bytes, name: str) -> dict:
    """
    Returns {
      kind, sha256, name, backgrounds: [...], text_peek: str, layout_mode_hint
    }
    """
    ext = Path(name or "upload.bin").suffix.lower()
    sha = file_sha256(raw=raw)
    peek = ""
    backgrounds = []
    hint = "structure"
    pdf_native = None

    if ext in PHOTO_EXT:
        mime, b64 = _b64_jpeg_from_png_or_jpeg(raw, ext)
        backgrounds = [{
            "page": 0, "mime": mime, "data_b64": b64,
            "width_px": None, "height_px": None,
        }]
        hint = "overlay"
    elif ext in PDF_EXT:
        # Write temp for fitz — rasters + native text/widget layout
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(raw)
            tpath = Path(tmp.name)
        try:
            backgrounds = pdf_pages_as_images(tpath)
            try:
                from .pdf_layout import extract_form_layout
                pdf_native = extract_form_layout(tpath)
            except Exception:
                pdf_native = None
        finally:
            tpath.unlink(missing_ok=True)
        if backgrounds:
            hint = "overlay"
        # Prefer span text for peek when markitdown unavailable
        if pdf_native and pdf_native.get("raw_fields"):
            peek = "\n".join(
                s.get("text") or "" for s in pdf_native["raw_fields"]
            )[:12000]
        if not peek:
            try:
                from markitdown import MarkItDown
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp2:
                    tmp2.write(raw)
                    p2 = Path(tmp2.name)
                try:
                    peek = (MarkItDown().convert(str(p2)).text_content or "")[:12000]
                finally:
                    p2.unlink(missing_ok=True)
            except Exception:
                peek = peek or ""
    elif ext in HTML_EXT:
        peek = raw.decode("utf-8", errors="ignore")[:12000]
        hint = "structure"  # HTML mock → structure until we parse CSS positions
    elif ext in DOC_EXT:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(raw)
            tpath = Path(tmp.name)
        try:
            from markitdown import MarkItDown
            peek = (MarkItDown().convert(str(tpath)).text_content or "")[:12000]
        except Exception:
            peek = raw[:4000].decode("utf-8", errors="ignore")
        finally:
            tpath.unlink(missing_ok=True)
        hint = "structure"
    else:
        peek = raw[:2000].decode("utf-8", errors="ignore")

    return {
        "kind": "form_template_source",
        "name": Path(name).name,
        "sha256": sha,
        "backgrounds": backgrounds,
        "text_peek": peek,
        "layout_mode_hint": hint,
        "ext": ext,
        "pdf_native": pdf_native,
    }


def ingest_path(path: Path) -> dict:
    path = Path(path)
    return ingest_bytes(path.read_bytes(), path.name)
