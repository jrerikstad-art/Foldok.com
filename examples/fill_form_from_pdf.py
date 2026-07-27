"""Example — fill a form template from PDF layout + facts.

Usage (from foldok-engine root):

    python examples/fill_form_from_pdf.py path/to/form.pdf

Or without a PDF — sample multipoint structure fixture:

    python examples/fill_form_from_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "local_app"))

from form_engine import FormEngine, extract_form_layout, fixture_as_template  # noqa: E402
# Also valid: from layout_extract import extract_form_layout


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    out = ROOT / "filled_form.html"

    engine = FormEngine()
    artifact = {"name": "Service job", "client": {"name": "Eksempel AS"}}
    facts = {"reg_no": "AB 12345", "customer_name": "Ola Nordmann"}

    if pdf and pdf.exists():
        # 1. Extract layout from a PDF form
        layout = extract_form_layout(pdf)
        # 2. Prefer package-from-upload (backgrounds + fields); fall back to template+extract
        raw = pdf.read_bytes()
        engine.load_upload(raw, pdf.name)
        engine.set_layout_from_extract(layout)
        engine.set_mode("overlay" if engine.package and engine.package.get("backgrounds")
                        else "structure")
    else:
        # Demo without PDF — sample multipoint structure sheet
        engine.load_template(fixture_as_template())
        engine.set_mode("structure")

    engine.set_artifact_model(artifact)
    engine.set_project_facts(facts)
    engine.set_company({"name": "VERKSTED AS"})

    html = engine.render(mode=engine.resolve_mode())
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html)} bytes, mode={engine.resolve_mode()})")


if __name__ == "__main__":
    main()
