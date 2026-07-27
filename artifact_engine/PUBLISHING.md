# PUBLISHING.md — LayoutTree as the universal contract

**Print publication first.** Every export format is a paint of the same geometry.

**v0.60 priority:** publishing foundation before Requirement Engine —
see root `V0_60_PLAN.md`.

```text
Document Model / Artifact AST
        ↓
Composition Engine          (structure, regions, preferred blocks)  ← highest visual leverage
        ↓
Measurement Engine          (intrinsic size of every component)
        ↓
Constraint Solver           (page breaks, keep-with, widows/orphans)
        ↓
LayoutTree                  ← THE ONLY THING RENDERERS SEE
        ↓
┌───────┴───────┬──────────┬──────────┐
│               │          │          │
HTML Renderer  PDF Renderer  SVG*     DOCX / Print*
```

\* SVG for diagrams uses `LayeredGraphLayout` (graph), not page LayoutTree.  
\* DOCX from LayoutTree is not shipped yet — same contract when it lands.

### What does *not* own visual quality

| Layer | Owns | Visual? |
|-------|------|---------|
| Knowledge / index | Project facts | No |
| Requirement / gaps | Must-have content + MANGLER | No |
| Template compiler | Skeleton | Low |
| Composition + solver + DesignSystem | Look & feel | **Yes** |

Requirement Engine must emit a rich Artifact AST only — never page geometry.

---

## Hard rule

**No renderer may inspect Document, Section, or Block models for layout.**

Renderers receive a `LayoutTree` with:

- final coordinates and sizes in **points**
- fully resolved styles (no DesignSystem token lookups left on components)
- content already prepared for paint

Convenience APIs that accept `Document` must run compose → measure → solve →
tree **before** calling `render_layout`.

---

## Contract types (`artifact_engine/layout/tree.py`)

| Type | Role |
|------|------|
| `LayoutTree` | Document-level package (`pages`, `design`, metadata, `contract_version`) |
| `PageLayout` (`LayoutPage`) | One printed page |
| `RegionLayout` | Hero / main / sidebar / footer region on a page |
| `ContainerLayout` | Flow box inside a region |
| `ComponentLayout` | Leaf paint unit (type, box, content, `ComponentStyle`) |
| `LayoutNode` | Flattened absolute node — **compat** for older painters / TOC |

`PageLayout.nodes` flattens regions→containers→components for legacy paint.

---

## Pipeline responsibilities

| Stage | May do | Must not do |
|-------|--------|-------------|
| Composition | Structure, preferred blocks, region *roles* | Exact x/y |
| Measurement | Intrinsic height/width | Place |
| ConstraintSolver | Page breaks, spacing, keep-with | Invent content |
| LayoutTree builder | Emit geometry + resolved styles | Know HTML/PDF |
| Renderer | Paint `LayoutTree` | Layout decisions |

Entry points:

- `PrintLayoutEngine.layout(doc)` → `LayoutTree`
- `HTMLRenderer.render_layout(tree)` / `render_tree(tree)`
- `PDFRenderer.render_layout(tree)` → PDF bytes
- Protocol: `artifact_engine.render.base.Renderer`

---

## Publishing questions (every layout pass)

Treat the output as a print publication:

1. Can a heading become isolated at the bottom of a page?
2. Is the figure kept with its caption?
3. Is whitespace balanced?
4. May tables break — and how (header repeat)?
5. Is hierarchy clear at a glance?
6. Does every page feel intentionally designed?

Policy knobs: `LayoutConstraints` + `ConstraintSolver.publishing_checks()`.

---

## Region thinking

Composition already yields semantic `PageRegion` roles. The LayoutTree now
carries **geometric** `RegionLayout` nodes (today: one `main` region per page
wrapping the flow). Next increments:

1. Map composition hero → `role="hero"` region
2. Optional sidebar / footer regions from profile
3. Solver packs measured components into those regions

---

## Legacy paths (do not grow)

| Path | Status |
|------|--------|
| `HTMLRenderer(flow=True)` | Legacy CSS flow — not publishing contract |
| `form_engine` overlay/structure HTML | Form print fixture — separate |
| `document_engine` page-dict HTML | Fallback only |

New export features must go through LayoutTree.

---

## Implementation checklist (order of work)

- [x] Freeze LayoutTree interface (regions / containers / components)
- [x] Renderer protocol (`render_layout`)
- [x] Explicit ConstraintSolver stage
- [x] HTML / PDF paint from LayoutTree
- [ ] Stronger region packing from Composition `PageRegion`
- [ ] DOCX renderer from LayoutTree
- [ ] Richer measurement rules per semantic component
