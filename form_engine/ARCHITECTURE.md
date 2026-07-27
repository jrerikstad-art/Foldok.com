# Form Engine — Architecture

**Principle:** fill content from facts; **never** redesign the user's paper
unless they explicitly ask. Visual identity is sacred.

**Version context:** v2 overlay 0.34; FormEngine class 0.35; Artifact
compose path 0.40; print-first LayoutTree paint **0.45**.

---

## Two output lanes

| Mode | When | Renderer |
|---|---|---|
| `overlay` | PDF/image import with page rasters | Original page bg + absolute field chips |
| `structure` | No backgrounds / legacy FIXTURE | Letter-width structural HTML |
| `hybrid` | Default | overlay if backgrounds else structure |
| `artifact` | Professional compose | Document AST → **ArtifactEngine** HTML/PDF |

```text
User template / imported form
        ↓
Form AST (sections + fields)
        ├── overlay / structure  → form_engine renderers
        └── artifact             → Document AST → ArtifactEngine
```

---

## Overlay / structure pipeline

```text
upload (PDF | image | DOCX | HTML)
        │
        ▼
   ingest.pages()          → page rasters + optional native HTML
        │
        ▼
   layout_extract()        → FormPackage { backgrounds[], fields[] }
        │                     PDF native (PyMuPDF) / vision / offline
        ▼
   fill.bind(state,facts)  → values; ratings NEVER AI-filled
        │
        ▼
   render.overlay() or render.structure()
```

---

## Artifact compose path (0.40+ / print-first 0.45)

```python
from form_engine import FormEngine

eng = FormEngine(theme="engineering")
eng.load_template(tpl).set_project_facts(facts)
doc = eng.to_document()          # FormSection / Signature / RatingLegend blocks
html = eng.render_html()         # ArtifactEngine LayoutTree → absolute HTML
# eng.render_pdf("out.pdf")      # shared PDF backends
```

Artifact mode uses the shared print-first pipeline
(`compose → measure → LayoutTree → paint`). Overlay / structure modes
are unchanged.

Print HTML never stamps `[MANGLER]` — empty slots render blank / missing
style. Ratings, checks, signatures are never auto-filled from facts.

---

## Package layout

```text
form_engine/
  __init__.py                # public API
  __main__.py                # python -m form_engine
  engine.py                  # FormEngine OO facade
  model.py                   # FormPackage, Field, validate
  ingest.py                  # PDF→PNG, image, DOCX
  layout_extract.py          # vision / offline / pdf_native
  pdf_layout.py              # PyMuPDF spans/widgets
  fill.py                    # facts → values
  render_overlay.py
  render_structure.py        # FIXTURE + letter sheet
  smart_defaults.py
  ARCHITECTURE.md
```

Root `form_engine.py` removed — the package is the module.
`layout_extract` also re-exported at repo root for older imports.

---

## Field region schema (normalized 0–1000 page coords)

```json
{
  "key": "reg_no",
  "type": "text|rating3|check|measure|date|signature|photo",
  "label": "Reg.nr",
  "page": 0,
  "bbox": {"x": 120, "y": 80, "w": 200, "h": 28},
  "required": true,
  "unit": null,
  "verbatim_style": true
}
```

---

## Rules (product law)

- Prefill from index/artifact; **ratings never AI-suggested**
- Required empty → gaps (gap ledger); print HTML stays blank
- Deterministic: same package + values → same HTML
- Smart defaults / web lookup are **optional plugins**, never silent redesign
- Diagram drawing lives in `diagram_engine/` — see `diagram_engine/ARCHITECTURE.md`
