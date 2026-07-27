# Artifact Composition Engine — Architecture

**Guiding rule:** the LLM is an architect, not a designer.
It may propose a **Document AST**. Code alone decides layout, typography,
colors, page breaks, and PDF.

**Publishing contract:** `LayoutTree` is the **only** input renderers may see.
See **`PUBLISHING.md`** (regions → containers → components).

**Version context:** LayoutTree contract v1; DesignSystem; compose → measure →
ConstraintSolver → LayoutTree → paint. See root `CHANGELOG.md`.

---

## Pipeline (print-first)

```text
Document AST (semantic only)
        │
        ▼
  CompositionEngine     ← structure + region roles
        │
        ▼
  MeasurementEngine     ← intrinsic sizes (pt)
        │
        ▼
  ConstraintSolver      ← page breaks, keep-with, widows/orphans
        │
        ▼
  LayoutTree            ← Page → Region → Container → Component
        │
        ▼
  HTML / PDF Renderer   ← Renderer.render_layout only (no CSS flow)
```

### User-manual path (skill + template)

```text
User / Wireframe tool
        │
        ▼ (optional sketch of structure)
Template instance (schemas/user-manual-template-v1.json)
        │
        ▼
Agent loads skill "user-manual" + template
        │
        ▼
CompositionEngine.compose(...)
        │
        ├── enforces required sections
        ├── forces preferred block types
        └── produces Document AST
        │
        ▼
Tools (regenerate_section, force_block, propose_diagram, set_image, run_qa …)
        │
        ▼
LayoutTree → Render (HTML / PDF)
```

See `AGENT_TEAM_SPEC.md` and `skills/core/user-manual/SKILL.md`.
Compile/gap facts: `templates/user_manual.json`. Composition profiles:
`schemas/user-manual-template-v1.json`.

`DesignSystem` is the shared visual language (colors, type, A4 grid).
`ArtifactEngine` / `get_engine(theme)` runs this end-to-end. FormEngine
(artifact mode) and DocumentEngine HTML both consume it.
Legacy CSS-flow HTML remains available via `flow=True`.

---

## Package layout

```text
artifact_engine/
  __init__.py          # public API: render_document, build_layout, get_engine, …
  __main__.py          # python -m artifact_engine → demo HTML
  core.py              # ArtifactEngine, get_engine
  composition.py       # CompositionEngine
  design_system.py     # DesignSystem, ENGINEERING_DS, DATASHEET_DS
  bridge.py            # document_from_pages (DocumentEngine bridge)
  fixtures.py          # demo CCS Document (synthetic brand)
  model/
    document.py        # Document
    section.py         # Section
    blocks.py          # All block types + block_from_dict
    theme.py           # Theme dataclass (legacy bridge)
  themes/
    engineering.py
    datasheet.py
  layout/
    engine.py          # PrintLayoutEngine → LayoutTree
    tree.py            # LayoutTree contract (Page/Region/Container/Component)
    measurement.py     # MeasurementEngine
    solver.py          # ConstraintSolver
    grid.py            # A4 grid, column_x, snap_y
    spacing.py         # baseline rhythm
    constraints.py     # LayoutConstraints flags
    pagination.py      # placement LayoutEngine, PlacedBlock, flatten_document
    graph.py           # LayeredGraphLayout (Sugiyama) for diagrams
  render/
    base.py            # Renderer protocol
    html.py            # HTMLRenderer.render_layout
    pdf.py             # PDFRenderer.render_layout
  PUBLISHING.md        # LayoutTree universal contract
  ARCHITECTURE.md      # this file
```

---

## Block types (Document AST)

| Type | Purpose |
|---|---|
| `paragraph`, `heading`, `bullet_list` | Text |
| `image` (`hero` / `figure` / `exploded` / `component`) | Photos / drawings |
| `drawing_reference` | Drawing / P&ID / GA + revision |
| `feature_grid`, `parameter_grid`, `specification_table`, `engineering_table`, `technical_data` | Specs / cards / params |
| `hero`, `callout` | Cover / callouts |
| `table_of_contents` | Auto-filled TOC (user manuals) |
| `warning`, `note` | Callout variants |
| `form_section`, `signature`, `rating_legend` | Form compose path |
| `diagram` | Embedded DiagramEngine SVG |

### User-manual profile (`USER_MANUAL_PROFILE`)

When `document_type` is `user_manual` / `brukermanual` / `manual`:

```text
cover → legal → symbols → summary → glossary → toc
  → product_description → technical_specs → interface
  → assembly → installation → operation → maintenance
  → troubleshooting → transport → identification → revision_history
```

Composition also:
- strips `[MANGLER: …]` from prose into **Information Still Required**
- forces Procedure / EngineeringTable / CalloutBox / RevisionHistory
  on the matching slots

Exported as `USER_MANUAL_PROFILE` / `MANUAL_PROFILE` / `MANUAL_PROFILE_ORDER`.

---

## Graph layout (diagrams)

`layout/graph.py` — deterministic layered (Sugiyama-style) layout:

1. Longest-path rank assignment
2. Barycenter ordering (crossing reduction)
3. Coordinate assignment (`TB` or `LR`)

Consumed by `diagram_engine` for SVG node positions. Provenance edge
colors stay in `diagram_engine/style.py` (product contract).

---

## Rules

- Same AST + theme → same HTML (byte-stable CSS)
- HTML/PDF default path is absolute paint of `LayoutTree` (not CSS flow)
- Renderers implement `Renderer.render_layout(LayoutTree)` — no Document inspection for layout
- Ratings / invented brands never appear in fixtures (DemoTek / Demo CCS)
- Print HTML never stamps `[MANGLER]` for unresolved form slots
- PDF is optional; missing backends raise a clear install error
