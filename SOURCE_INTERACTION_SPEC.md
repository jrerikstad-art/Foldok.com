# SOURCE_INTERACTION_SPEC.md — one-pager
**Sources ↔ document: toggle, trace, edit inline**

Status: **implemented S1–S5 in workbench (engine v0.18.0)** · v0.2 · 2026-07-21 — S6 (Capture Folder sync) pending  
Rules of record: `ENGINE_CONTRACT.md`, `EDITOR_SPEC.md`, `NAVIGATION_SPEC.md`

---

## Problem

KILDER today is mostly a **list**. Files are indexed, but the user cannot easily:

- turn a **source file off** in the document (still indexed, not cited)
- turn a **picture off** without hunting for the × on the figure
- **edit a table cell** (e.g. Utgiver in spesifikasjonsoversikt) by hovering the column

The screenshot case — `MANGLER: issuer — fil funnet` — shows the gap: the file is there, the row is there, but interaction stops at a chip instead of a direct edit on the cell.

**Goal:** every source file is a **switchable participant** in the document; every value in a compiled table is **hover → inspect → edit** with traceability preserved.

---

## Mental model

```
KILDER (all indexed)          DOKUMENT (active view)
─────────────────────         ─────────────────────
[●] FASADETEGNING.pdf   ←──→  row in spec_overview
[○] gammel_rev.pdf      ←──→  (excluded — grey in rail)
[●] PERSPEKTIV.svg      ←──→  figure in section / table ref

Toggle OFF  = excluded from THIS document (index unchanged, €0)
Toggle ON   = eligible again → code sections refresh from index
Edit cell   = user fact OR mapping override → version row → gaps re-run
```

**Hard rule (unchanged):** prose and tables may only show values backed by `extracted_facts` or `verified_by_user` facts. Inline edit never silently invents — it creates or confirms a fact.

---

## 1. Source file toggle (on / off)

| State | KILDER rail | Document | Index |
|-------|-------------|----------|-------|
| **On** (default) | full opacity, green dot | file can appear in mappings, tables, figures | unchanged |
| **Off** | dimmed, ⏸ badge | removed from section `files[]`, table rows built without it, figures stripped | unchanged |

**Scope:** per **document**, not per project. Same PDF can be on in Konstruksjonsrapport and off in a tender matrix.

**Actions when toggled OFF:**

1. Add to `state.excluded_sources[]`: `{ file, at, by: "user" }`
2. Remove file from all section mappings for this document
3. Re-run **zero-token** compilers for affected sections: `doc_control`, `spec_overview`, `drawings_register`
4. Strip `{{fig:…}}` markers for that file
5. Recompute gaps; toast: *«Fjernet fra dokumentet — filen ligger fortsatt i kilder»*

**Actions when toggled ON:**

1. Remove from `excluded_sources`
2. Re-run mapping for that file only (Haiku, metered) OR user drags file chip onto section (zero tokens)
3. Refresh code-built tables

**UI — KILDER row:**

```
[IMG] PERSPEKTIV NY.svg          [ toggle ● ]
     perspektiv, fasade · 3 facts
     i dokumentet · klikk = forhåndsvis
```

- Toggle is a switch on the right (not delete — file stays indexed)
- Click name → preview popover (caption, facts, «Åpne fil», «Gå til bruk i dokument»)
- Hover a **fact chip in the document** → highlight this row (traceable ink, already in `ui-editor-v3.jsx`)

---

## 2. Picture toggle (on / off)

Extends existing `excluded_figures[]` (workbench v0.16) to a unified **media toggle**:

| Control | Where | Behaviour |
|---------|-------|-----------|
| × on figure card | in canvas | same as today → `exclude_figure` |
| toggle on source row | KILDER, if file is visual | excludes all pages of that file in this document |
| «Fjernede illustrasjoner» strip | under toolbar | restore one or all |

**Rule:** toggling picture OFF does **not** toggle source OFF. A drawing PDF can stay **on** for `doc_control` / `spec_overview` rows while its inline figure is **off** in the narrative section.

**Rule:** toggling source OFF always hides its pictures.

---

## 3. Table hover → edit (doc_control, spec_overview)

Compiled tables (`compile_doc_control`, `compile_spec_overview`) render as **interactive grids**, not dead markdown.

### Hover affordances

| Hover target | Visual | Action |
|--------------|--------|--------|
| **Cell with fact** | blue underline (traceable ink) + source chip | click → popover: excerpt, file, confidence, [Rediger verdi] |
| **Cell with MANGLER** | amber dashed box (today) + **fil funnet** if source exists | click → inline input OR pick from indexed candidates |
| **Whole row** | left accent if source file selected in KILDER | — |
| **Column header** (e.g. Utgiver) | subtle highlight | click → «Fyll kolonne fra…» only if same fact key missing in all rows |

### Edit flow (zero ambiguity)

1. User clicks **Utgiver** cell showing `MANGLER: issuer`
2. Popover shows: *«Funnet i FASADETEGNING.pdf: "Arkitekten AS" (confidence 0.72)»* + **[Bruk]** **[Skriv selv]**
3. **Bruk** → cites existing fact id → cell updates → gap cleared → `document_versions` row (*«Bekreftet utgiver fra FASADETEGNING»*)
4. **Skriv selv** → inline input → creates `verified_by_user=true` fact → same path

**Column hover edit:** hovering **Betegnelse** or **Revisjon** enables click-to-edit only for keys that belong to that column (`drawing_title`, `revision`, `issuer`, …). Wrong column edits are rejected in UI.

**After edit:** call `refresh_spec_overview` / `refresh_doc_control` only if row structure changes; single-cell fact swap updates DOM without full recompile.

---

## 4. Bidirectional linking

```
Document                          KILDER
────────                          ──────
hover fact chip ────────────────► highlight source row + scroll into view
hover table row ────────────────► highlight source file(s) for that row
toggle source OFF ◄────────────── dim rows/cells that cited it
click «fil funnet» on MANGLER ──► open source preview at likely page
```

**Traceable ink (keep):** hovering a value dims all sources except the cited file(s). Implemented in editor shell CSS (`.srcf.lit`, `.dim`) — extend to table cells.

---

## 5. Data model (additions to `doc_state` / Supabase)

```json
{
  "excluded_sources": [
    { "file": "Tegninger/gammel_fasade.pdf", "at": "…", "reason": "user_toggle" }
  ],
  "excluded_figures": [
    { "file": "Bilder/IMG_001.jpg", "page": 0, "section": "summary" }
  ],
  "cell_overrides": [
    {
      "section": "spec_overview",
      "row_key": "fasade|FASADETEGNING - NY.svg",
      "column": "issuer",
      "fact_id": "…",
      "verified_by_user": true
    }
  ]
}
```

`cell_overrides` survive recompile of code-built tables (applied after `compile_*`, before render). Recompile from index remains the default; overrides are sovereign.

---

## 6. API surface (workbench → production)

| Route | Purpose | Tokens |
|-------|---------|--------|
| `POST /api/doc/toggle-source` `{ file, on }` | include / exclude source | 0 (recompile) or ~mapping if on |
| `POST /api/doc/toggle-figure` `{ file, page, on }` | unify exclude / restore | 0 |
| `POST /api/doc/edit-cell` `{ section, row_key, column, value?, fact_id? }` | inline table edit | 0 |
| `GET /api/doc/cell-candidates` `{ section, row_key, column }` | facts for MANGLER popover | 0 |

Existing: `/api/doc/exclude-figure`, `/api/doc/refresh-spec-overview`, `/api/doc/refresh-doc-control`, `/api/doc/apply-cited`.

---

## 7. Build order

| Step | Deliverable | Notes |
|------|-------------|-------|
| **S1** | Source toggle in KILDER + `excluded_sources` | extends `renderDocSources()` |
| **S2** | Table renderer for `doc_control` / `spec_overview` | replace raw `<table>` markdown with cell components |
| **S3** | Hover trace source ↔ cell | shared `hoverSourceId` state |
| **S4** | Cell edit popover + `edit-cell` API | reuses MANGLER / `apply-cited` logic |
| **S5** | Picture toggle on source row | merges with `excluded_figures` |
| **S6** | Capture Folder Engine sync | desktop pushes index; web owns toggles + overrides |

**Do not ship S6 before S1–S5** — interaction model must work in local workbench first.

---

## 8. Out of scope (this spec)

- Deleting files from disk (engine admin only)
- Auto-guessing issuer without user confirm
- Editing boilerplate / locked legal blocks
- Multi-document batch toggle

---

## 9. Done when (acceptance)

1. User toggles **off** a tegning → row disappears from spesifikasjonsoversikt; file still in KILDER as indexed + dimmed.
2. User toggles **off** a picture → figure gone; same file still feeds table row if source on.
3. User hovers **Utgiver** cell → sees source; clicks → edits → MANGLER cleared; export shows verified value with citation.
4. Hover fact in narrative section → correct KILDER row lights up.
5. All edits appear in version history; re-export is free if document already paid.

---

*One line:* **Sources are switches; tables are editable views; the index stays truth — the document chooses what to show.*
