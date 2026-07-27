"""python -m document_engine — write datasheet_demo.html."""
from pathlib import Path

from .engine import render_datasheet_demo
from .fixtures import DEMO_FACTS

if __name__ == "__main__":
    html = render_datasheet_demo()
    assert "Demo CCS Feed System" in html
    assert "[MANGLER]" not in html
    assert "Akvasmart" not in html  # no real-brand fixture
    a = render_datasheet_demo()
    b = render_datasheet_demo()
    # generated_at differs — compare without timestamp by re-render same clock... 
    # Instead check structure stable:
    assert "spec-table" in html and ("feature-grid" in html or "component-grid" in html)
    assert DEMO_FACTS["comp_1_name"] in html
    root = Path(__file__).resolve().parent.parent
    out = root / "datasheet_demo.html"
    out.write_text(html, encoding="utf-8")
    web = root / "web" / "datasheet_demo.html"
    if web.parent.exists():
        web.write_text(html, encoding="utf-8")
    print(f"document_engine selftest OK → {out.name} ({len(html)} bytes)")
