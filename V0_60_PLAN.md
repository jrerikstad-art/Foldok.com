# V0.60 — Publishing pipeline first

**One-sentence goal**

> Turn the system into a real publishing pipeline where the Composition Engine
> decides *how* the document should feel, the Layout Solver decides *exactly
> where everything goes*, and every renderer only consumes a finished LayoutTree.

**Core insight (settled)**

Rendering sophistication, Design System maturity, and publishing-quality output
live almost entirely **after** the Artifact AST.

- **Requirement Engine** → content correctness (what must be in the doc + gaps)
- **Composition + Layout Solver + Design System** → how the document looks and feels

Do not mix compliance logic with layout logic.

---

## Separation of concerns

| Layer | Responsibility | Affects visual quality? |
|-------|----------------|-------------------------|
| Knowledge Graph | What we know about the project | No |
| Requirement Engine | What *must* be in the document + gaps | No |
| Template / Section Compiler | Structural skeleton | Low |
| **Composition Engine** | Regions & professional component arrangements | **Yes – highest impact** |
| Layout Solver | Exact placement, pagination, constraints | **Yes** |
| Design System | All visual tokens | **Yes** |
| Publishing Engine | Typography rhythm, whitespace, figures, tables | **Yes** |
| LayoutTree → Renderers | Final output | Execution only |

Contract detail: `artifact_engine/PUBLISHING.md`.

---

## Why this order

1. Visible document-quality gains land faster.
2. Compliance stays out of layout.
3. Requirement Engine only produces a rich, traceable Artifact AST — it never
   knows how pages look.
4. Composition is where professional publishing decisions are made.

---

## Phased work

### Phase 1 — Publishing foundation (highest leverage)

| # | Work | Status |
|---|------|--------|
| 1 | **LayoutTree** as universal contract (no renderer looks at Document for layout) | **Done** (contract v1 — regions/containers/components; see `layout/tree.py`) |
| 2 | **Composition Engine** thinks in regions + pro components (Hero, Feature Grid, Sidebar, Spec blocks, …) | Next — map `PageRegion` → geometric `RegionLayout`; richer arrangements |
| 3 | Centralize / mature **Design System** (type scale, spacing, grid, table/callout/figure styles) | Partial — `DesignSystem` exists; deepen tokens + component styles |
| 4 | Upgrade **Measurement + Constraint Solver** (measure-before-place) | Partial — `MeasurementEngine` + `ConstraintSolver` exist; strengthen keep-with, table-split, widows |

### Phase 2 — Content correctness

| # | Work | Status |
|---|------|--------|
| 5 | **Requirement Engine** as semantic compiler → fully traceable Artifact AST | Not started as named engine (gaps/facts today via compile + form_model) |

### Phase 3 — Publishing quality

| # | Work | Status |
|---|------|--------|
| 6 | Dedicated **Table Engine** | Not started |
| 7 | Dedicated **Figure Engine** | Partial (compile figure pool / placement) — not a dedicated engine |
| 8 | Advanced pagination, cross-refs, TOC, auto-numbering, print-first composition | Partial (TOC page hints; more to do) |

---

## Immediate next increments (after LayoutTree freeze)

1. Composition → emit region roles that the solver packs into `RegionLayout`
   (hero / main / sidebar / footer), not only a linear `main` flow.
2. DesignSystem: explicit table, callout, and figure style packs used when
   resolving `ComponentStyle`.
3. ConstraintSolver: figure+caption keep-with; heading orphan guard; table
   header-repeat on break.
4. Keep Requirement Engine **out** of this track until Phase 1 feels visibly better in exports.

---

## Non-goals for v0.60 Phase 1

- Mixing gap/compliance rules into layout
- Growing legacy `flow=True` HTML or form overlay as the “real” document path
- DOCX before LayoutTree paint is solid for HTML/PDF

---

## Related docs

- `artifact_engine/PUBLISHING.md` — LayoutTree contract
- `artifact_engine/ARCHITECTURE.md` — package map
- `TEMPLATE_STANDARD.md` — shape vs content for templates
- `ENGINE_CONTRACT.md` — citation / index rules (content truth)
- `CURSOR_BUILD_PLAN.md` — production port (orthogonal; local publishing leads)
