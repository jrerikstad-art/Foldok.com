"""python -m artifact_engine — self-test + write artifact_demo.html."""
from pathlib import Path

from . import demo_ccs_document, render_document

if __name__ == "__main__":
    doc = demo_ccs_document()
    a = render_document(doc, theme="datasheet")
    b = render_document(doc, theme="datasheet")
    assert a == b, "determinism broken"
    assert "Demo CCS Feed System" in a
    assert "feature-grid" in a and "spec-table" in a
    assert "Akvasmart" not in a
    assert 'data-foldok="artifact_document"' in a
    # Layout path
    from . import layout_document, render_document as rd
    lay = layout_document(doc, theme="datasheet")
    assert lay.page_count >= 2
    paginated = rd(doc, theme="datasheet", paginate=True)
    assert "print-page" in paginated and paginated == rd(doc, theme="datasheet", paginate=True)
    root = Path(__file__).resolve().parent.parent
    out = root / "artifact_demo.html"
    out.write_text(a, encoding="utf-8")
    pag_out = root / "artifact_demo_paginated.html"
    pag_out.write_text(paginated, encoding="utf-8")
    web = root / "web" / "artifact_demo.html"
    if web.parent.exists():
        web.write_text(a, encoding="utf-8")
        (web.parent / "artifact_demo_paginated.html").write_text(paginated, encoding="utf-8")
    print(f"artifact_engine selftest OK → {out.name} + paginated "
          f"({lay.page_count} pages, {len(a)}/{len(paginated)} bytes)")
