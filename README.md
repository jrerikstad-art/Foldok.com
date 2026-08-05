# Foldok Engine

Folder-compiler: sources in → manuals, forms, diagrams, and evidence packages out.

**Brand:** Foldok · mark `[…]`  
**Version:** see `VERSION` · **Deploy:** `DEPLOY.md` · **History:** `CHANGELOG.md`  
**Vision:** `PRODUCT_VISION.md` · **Editor:** `ENGINEERING_EDITOR.md` · **Direction:** `PRODUCT_DIRECTION.md`  
**Claim boundary:** `COMPLIANCE_POLICY.md` — structural profiles only; no legal compliance stamps.

**Latest release:** see GitHub Releases (`v` + `VERSION`) · build zip: `.\scripts\make_release.ps1`  
**0.114 notes:** `docs/RELEASE_0.114.md`  
**Surface PRDs:** `docs/prd/README.md`  
**Marketing deploy:** [Vercel import](https://vercel.com/new/import?s=https://github.com/jrerikstad-art/Foldok.com) · see `DEPLOY.md`

### Quick start (local workbench)

```powershell
.\scripts\workbench.ps1
# → http://127.0.0.1:8766/
```

### Marketing site (English)

Static landing in `public/` — deploy to **Vercel** from GitHub (see `DEPLOY.md`).

---

## Where we are

| Layer | Status |
|---|---|
| Local workbench (`local_app/`) | **Shipped** — English hub landing + project engine |
| Document Type Registry + structural profiles | **Shipped** — Phase 1 evidence / package breadth |
| Calculation Engine (library formulas + confirm) | **Shipped** — 8+ profiles; see `CALCULATION_SPEC.md` |
| Materials knowledge (steel + GFRP template) | **Shipped** — see `MATERIALS_SPEC.md` |
| Diagram symbols (piping / mechanical) | **Shipped** — 20 symbols + shared graph schema |
| Artifact / Form / Document engines | **Shipped** |
| Corpus engines (role → select → volume → budget → corpus) | **Shipped** — see table below |
| Production SaaS (Next.js + Stripe) | **Not started** |

### Corpus / author / compose packages (0.106–0.113)

| Package | Role |
|---|---|
| `foldok_role` | Project vs reference vs ignore; photo offers |
| `foldok_select` | Curate admissible figures; exclude sales shots |
| `foldok_volume` | Uncovered themes widen fixed outlines |
| `foldok_budget` | Per-section citation scope + pipeline health |
| `foldok_corpus` | Non-factual claim types + «Fra mappen» on every doc |
| `foldok_identity` | Project Identity + NarrativeBlueprint before the market |
| `foldok_evidence` | Project evidence assets (depicts / relevance / stage) |
| `foldok_director` | Content Director → composition plan + coverage |

### Folder → draft stack (0.114)

| Package | Role |
|---|---|
| `foldok_editorial` | Review-only publish gate (transitions, language, unused assets) — see `EDITORIAL_QA.md` |
| `foldok_reflow` | PDF visual rows → sentences; embedded figures; stops fragment claims |
| `foldok_tier` | Strong claims / descriptive candidates / rejected furniture |
| `foldok_sense` | Topics from folder recurrence («forstå mappen» / `sense_folder`) |

Chat **«make sense of this folder»** → short summary in chat; full draft in the editor (`doc.sense_md`).  
CLI audit: `python -m foldok_sense.audit FOLDER`.

Workbench **Compose** tab (`GET /api/compose`): Knowledge | Narrative | Live draft.
Generate remains the last ~10% (render draft into slots).

---

## Shared Artifact Engine (the visual spine)

Print-first publishing: Document, Form, and Diagram engines share one
`DesignSystem` and one paint path. HTML does not decide layout — it only
paints a finished `LayoutTree`.

```text
Document AST
  → CompositionEngine → MeasurementEngine → PrintLayoutEngine
  → LayoutTree → HTML / PDF paint
```

```text
                    ┌─────────────────────┐
                    │   ArtifactEngine    │
                    │  DesignSystem       │
                    │  LayoutTree · HTML  │
                    │  PDF                │
                    └─────────┬───────────┘
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    DocumentEngine      FormEngine         DiagramEngine
    (page templates)    (form → AST)       (graph → SVG)
```

| Consumer | What it contributes | What ArtifactEngine owns |
|---|---|---|
| DocumentEngine | Page templates → Document AST | Layout, theme, HTML, PDF |
| FormEngine | Fields → FormSection blocks | Layout, theme, HTML, PDF |
| DiagramEngine | Graph + pins + provenance | Theme colors/fonts; HTML/PDF wrap |

PDF backends (optional): WeasyPrint first, Playwright fallback.
Install one of: `pip install weasyprint` or
`pip install playwright && playwright install chromium`.

---

## Workbench — full experience, real engine

```powershell
cd foldok-engine
$env:ANTHROPIC_API_KEY = "sk-ant-..."
.\scripts\workbench.ps1
```

Opens **http://127.0.0.1:8766** — create a project from any folder,
index files (cost estimate; cached = free), confirm the artifact model,
pick a template, generate, edit with gaps, chat with the agent
(forms, diagrams, checklists, malimport).

Without a key, offline routers still answer many goldens; vision/Sonnet
paths need `ANTHROPIC_API_KEY`.

---

## Preview in browser (mocks + fixtures)

```powershell
cd foldok-engine
.\scripts\serve.ps1
```

Then open **http://localhost:8765/web/**

| Page | What it shows |
|---|---|
| `/web/editor.html` | Editor experience reference |
| `/web/results.html` | Archived compile output |
| `/web/prototype.html` | UI mock (checkpoints A/B/C) |
| `/sample_multipoint.html` | Form Engine structure fixture (`fixtures/sample_multipoint/`) |

---

## Engines

### Form Engine (`form_engine/`)

Faithful fill of the user’s paper — not a Foldok redesign — plus an
optional **artifact** compose path for professional Document AST output.

```
upload → ingest → layout_extract → fill(facts) → overlay HTML
              └─ PDF: native PyMuPDF spans/widgets (0 tokens)
              └─ else vision / offline
                                      └─ structure (letter sheet) if no backgrounds
                                      └─ artifact → Document AST → ArtifactEngine
```

```python
from form_engine import FormEngine, extract_form_layout

# Faithful overlay / structure
engine = FormEngine()
engine.load_template(your_template_dict)   # or load_upload / load_fixture
engine.set_artifact_model(artifact)
engine.set_project_facts(facts)
html = engine.render("html")               # hybrid → overlay|structure

# Professional compose (shared layout + theme + PDF)
engine.set_mode("artifact")
html = engine.render_html()                # or engine.render("html", mode="artifact")
doc = engine.to_document()                 # Document AST
# engine.render_pdf("filled.pdf")          # needs WeasyPrint or Playwright
```

Rules: ratings never AI-filled; empty slots stay blank in print HTML
(no `[MANGLER]`); overlay keeps original page images + positioned chips.

Self-test: `python -m form_engine` · Architecture: `form_engine/ARCHITECTURE.md`

### Diagram Engine (`diagram_engine/`)

Model/code proposes the **graph**; this package **draws** only.
Positions use a deterministic **Sugiyama-style layered layout**
(`artifact_engine.layout.graph.LayeredGraphLayout`) for block diagrams.

**Electrical v1 + multi-domain:** IEC / piping / mechanical symbol packs +
render profiles (`single_line`, `wiring`, `piping`, `pid`, `mechanical`, `hybrid`).
Same rule — graph in, deterministic SVG out.

```python
from diagram_engine import DiagramEngine

eng = DiagramEngine(theme="engineering", orientation="LR")  # or "TB"
eng.load_fixture("renseanlegg")        # excavator | renseanlegg
eng.set_intent("process")              # wiring|power|signal|process|star|overview
svg = eng.render("svg")                # data-graph="layered"
html = eng.render_html()
# eng.render_pdf("diagram.pdf")

# Domain profiles (one engine)
DiagramEngine().load_fixture("electrical_sld").render("svg")
DiagramEngine().load_fixture("piping").render_piping()
DiagramEngine().load_fixture("mechanical").render_mechanical()
DiagramEngine().load_fixture("hybrid").render_hybrid()

# Manual graph
eng = DiagramEngine(orientation="TB")
eng.add_node("tank", "Feed Tank")
eng.add_node("doser", "Feed Doser")
eng.add_connection("tank", "doser", "feed")
svg = eng.render_svg()
```

Provenance edge colors (fixed contract): extracted (blue) / user (green) /
reference (amber dashed). Propose/confirm lives in `connection_diagram.py`.

Self-test: `python -m diagram_engine` · Architecture: `diagram_engine/ARCHITECTURE.md`

### Document Engine (`document_engine/`)

Multi-page print HTML for datasheets / manuals / product sheets.
Prefers Artifact Engine when building from page templates.

```python
from document_engine import DocumentEngine

eng = DocumentEngine()
eng.load_fixture()
eng.set_project_facts({"product_name": "Demo CCS Feed System", ...})
eng.set_brand({"name": "DemoTek"})
html = eng.render("html")
# python -m document_engine
```

Unresolved `{{placeholders}}` stay blank in print HTML (truthful).

### Artifact Composition Engine (`artifact_engine/`)

LLM (or code) produces a **Document AST**; **CompositionEngine** decides
region order; **MeasurementEngine** + **LayoutEngine** place pages;
themes + renderer own visuals.

```python
from artifact_engine import (
    Document, Section, CompositionEngine, embed_diagram_engine,
    render_document, get_engine, DiagramBlock,
)
from diagram_engine import DiagramEngine

doc = Document(title="Demo CCS", theme="datasheet", sections=[…])
doc = CompositionEngine().compose(doc)          # overview → diagrams → specs
deng = DiagramEngine().load_fixture("renseanlegg").set_intent("process")
doc = embed_diagram_engine(doc, deng)           # DiagramBlock with SVG
html = render_document(doc, compose=True, paginate=True)
# python -m artifact_engine
```

Self-test: `python -m artifact_engine` · Architecture: `artifact_engine/ARCHITECTURE.md`

---

## Repository layout

| Path | Purpose |
|---|---|
| `ENGINE_CONTRACT.md` | Binding pipeline rules |
| `WORKQUEUE.md` | Implementation order (tiers + gates) |
| `CURSOR_BUILD_PLAN.md` | Production Phases 0–5 |
| `artifact_engine/` | Shared Document AST → layout → HTML/PDF + graph layout |
| `form_engine/` | Overlay + structure + Artifact compose |
| `diagram_engine/` | Intent + layered SVG + theme/HTML/PDF |
| `document_engine/` | Datasheet / manual HTML |
| `connection_diagram.py` | Graph propose/confirm for diagrams |
| `bom_engine.py` | BOM helpers |
| `templates/*.json` | System templates (incl. form_fill) |
| `capabilities.json` | Cold-start / pricing manifest (`scripts/build_caps.py`) |
| `foldok_compile.py` | Headless CLI |
| `local_app/` | Workbench: `server.py` + `app.html` |
| `web/` | Preview pages |
| `scripts/` | `workbench.ps1`, `make_release.ps1`, `agent_regression.py`, … |
| `releases/` | Versioned zip archives |
| `migration_001` … `006` | Supabase schema (for Phase 0) |
| `eval/` | Quality harness |

---

## Run the compiler

```bash
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...
python foldok_compile.py ./folder-a ./folder-b \
    --template templates/contract_review.json --lang no --yes
```

Multiple folders per project are supported; indexing runs in parallel
with a live ETA. Each folder keeps its own `.foldok_cache/`.

Validate templates: `python scripts/validate_templates.py`

---

## Release zip

```powershell
.\scripts\make_release.ps1
```

Builds `releases/foldok-engine-vX.Y.Z.zip` after regenerating
capabilities, running the **66**-test agent regression suite, and a
privacy grep (no real paths/names). Excludes `projects.json`, caches,
`.git`, prior zips.

---

## Plan status (vs `CURSOR_BUILD_PLAN.md` + `WORKQUEUE.md`)

### Local engine / agent (WORKQUEUE Tiers 1–4) — largely done

- [x] Truthfulness, receipts, money-from-manifest, isolation
- [x] One-agent / cold-start / flow polish
- [x] Diagrams (0.24–0.26) + Diagram Engine v2 + layered layout (0.35–0.42)
- [x] Forms / malimport (0.29–0.34) + Form → ArtifactEngine (0.40)
- [x] Artifact Engine AST / layout / PDF / shared core (0.37–0.41)
- [x] Incremental index tools (0.50) + Document Type Registry (0.51)
- [x] Hybrid Knowledge + location/OSM maps (0.52–0.53)
- [x] Industrial report blocks + composition profile (0.54)
- [ ] **LEARNING_AND_BOUNDARIES** — next local capability
- [ ] **Export & payment** — founder call (Tier 5); engines can emit PDF
      when backends are installed; paid branded export is not shipped

### Production Phases 0–5 — not started

| Phase | Intent | Status |
|---|---|---|
| 0 | Supabase + Next.js + auth + seed templates | ✗ |
| 1 | Projects & upload | ✗ |
| 2 | Port engine to TypeScript API | ✗ |
| 3 | Live UI on DB | ✗ |
| 4 | Export, Stripe, branding | ✗ |
| 5 | Template import hardening + deploy | ✗ (malimport exists **locally** only) |

**Diagrams and forms are shipped in the local engine**; production still
needs a Phase-2 port when that starts.

### Suggested next moves

1. Finish **LEARNING_AND_BOUNDARIES** (local learning + attachment routing).
2. Founder call: hosted vs local metering for **export/payment**.
3. Optional: eval loop (`eval/`) before Phase 0.
4. Then Phase 0 (Supabase + Next.js) when ready to leave workbench-only.

**Definition of shipped (unchanged):** one stranger pays real money for one export.
