"""python -m form_engine — structure self-test + write fixtures/sample_multipoint HTML."""
from pathlib import Path

from . import FIXTURE, render_form

if __name__ == "__main__":
    a = render_form(FIXTURE, company={"name": "VERKSTED AS"})
    b = render_form(FIXTURE, company={"name": "VERKSTED AS"})
    assert a == b, "determinism broken"
    n_fields = sum(len(s["fields"]) for s in FIXTURE["sections"])
    n_req = sum(1 for s in FIXTURE["sections"] for f in s["fields"]
                if f.get("required") and f.get("value") is None)
    assert 'class="chip cited"' in a and "AB 12345" in a
    assert "width:8.5in" in a
    assert "column-fill:balance" in a
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "fixtures" / "sample_multipoint"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "sample_multipoint.html"
    out.write_text(a, encoding="utf-8")
    print(f"form_engine selftest OK — {len(FIXTURE['sections'])} sections, "
          f"{n_fields} fields, {n_req} required-empty (= gaps), "
          f"2 prefilled from index -> {out.relative_to(root)}")
