"""PDF export: markdown → real PDF bytes, free when pricing unset."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_app"))
sys.path.insert(0, str(ROOT))

import export_formats as expfmt  # noqa: E402
from account_metering import export_entitlement, export_pricing_enabled  # noqa: E402


def test_dev_export_is_free():
    os.environ.pop("FOLDOK_EXPORT_PRICE", None)
    assert export_pricing_enabled() is False
    ent = export_entitlement({}, {})
    assert ent["charge"] is False
    assert ent["reason"] == "dev_free"


def test_render_markdown_pdf_bytes():
    md = """# Oversikt

Tekst med **fet** og æøå.

| A | B |
|---|---|
| 1 | 2 |

- steg en
- steg to

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20" width="40" height="20">
  <rect width="40" height="20" fill="#336"/>
</svg>
"""
    raw = expfmt.render_markdown_pdf(md, title="Testmanual")
    assert raw[:4] == b"%PDF"
    assert len(raw) > 500


def test_write_format_export_returns_download_bytes():
    md = "## Hello\n\nBody text.\n"
    with tempfile.TemporaryDirectory() as td:
        path, name, notices, raw = expfmt.write_format_export(
            Path(td), {}, {"name_no": "Installasjonsmanual"},
            fmt="pdf", display_name="Installasjonsmanual", md_content=md,
        )
        assert name.endswith(".pdf")
        assert raw and raw[:4] == b"%PDF"
        assert path and path.is_file()
        assert (Path(td) / "Rapporter" / "Installasjonsmanual.md").is_file()
        assert notices == []


if __name__ == "__main__":
    test_dev_export_is_free()
    test_render_markdown_pdf_bytes()
    test_write_format_export_returns_download_bytes()
    print("ok")
