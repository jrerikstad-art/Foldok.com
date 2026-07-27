# PRD — Compiler

**Surface:** Compiler (index → artifact → map → generate)  
**Product version:** 0.72.0  
**Status:** Shipped on `foldok_compile`; next architecture in `foldok_index` (library)  
**Primary entry:** Workbench generate/index APIs; CLI `foldok_compile.py`

---

## 1. Problem

Professionals re-read the same PDFs and photos for every document. Without a compiler, each export reinvents facts, invents numbers, or silently drops new files.

## 2. Outcome

Feltdok **indexes a project once**, builds a confirmable artifact model, maps sources to document structure, and generates drafts that:

- cite sources for factual claims, or
- mark `[MANGLER: …]` when evidence is absent — **never invent values**.

**Identity line:** Index once, document many times. The index is the asset; exports are the harvest.

## 3. Users & jobs-to-be-done

| User | JTBD |
|------|------|
| Author | “Fill this template from my folder without me pasting every number.” |
| Reviewer | “See what came from sources vs what is still missing.” |
| Agent operator | “Tools that never skip Checkpoint A/B/C.” |

## 4. Scope

### In scope (shipped)

- SHA-cached indexing (`.foldok_cache/`); re-index of unchanged files is free.
- Prescan estimate + cancel / resume (WO 0.55).
- Artifact model + user confirm (ENGINE_CONTRACT Checkpoint A).
- Template-driven section map + gaps (Checkpoint B).
- Generation with post-process citation rule (Checkpoint C).
- Form-fill path; malimport; section regenerate with accept.
- Incremental tools: reindex, diff-index, update-from-sources.
- Hybrid findings Excel + optional vector cache (`hybrid_knowledge_engine`).
- Capabilities manifest built from templates.

### In scope (library / target)

- **`foldok_index`** (WO 0.65): SQLite FTS + vectors, `reconcile()`, `diagnose()`, watermarks, `context_for_update()` so “what’s new” is a manifest lookup — not a semantic guess.
- Wire diagnose / reconcile into Workspace UI (“Check index”).
- Retrieval hits always carry `path#chunk=n` provenance into documents as unconfirmed AI content until user confirms.

### Out of scope

- Re-reading originals for every generation (HARD rule: right of index uses the index).
- Native CAD (DWG/STEP) parsing — drawing PDFs only.
- Video as first-class evidence in MVP.
- Verifying engineering calculations (see `CALCULATION_SPEC` claim boundary).

## 5. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| C-1 | Index is idempotent by content hash; unchanged files cost no embedding/vision | P0 |
| C-2 | Zero extracted text must never be reported as successfully indexed content | P0 |
| C-3 | Artifact confirm is a hard gate before generation when required | P0 |
| C-4 | Generators must not invent numeric or measured facts; emit `[MANGLER]` instead | P0 |
| C-5 | Prescan shows estimated cost and allows cancel/resume | P0 |
| C-6 | `reconcile(folder)` reports not_indexed / stale / orphaned / failed / empty / unsupported | P1 |
| C-7 | Document update uses `context_for_update(watermark)` for new knowledge, not similarity alone | P1 |
| C-8 | Changing embedder identity forces reindex rather than blending vector spaces | P1 |
| C-9 | Agent tools for index/generate match `ENGINE_TOOLS.md` receipts for completion claims | P0 |

## 6. Non-functional requirements

- Parallel workers with cancel between chunks.
- Offline routers for many golden paths without API key; vision/Sonnet require key.
- Diagnose canary: a document written moments ago is retrievable without reopening the store.

## 7. Dependencies

| Depends on | Why |
|------------|-----|
| Workspace | Jobs, folder scope, confirm UX |
| Compliance | Evidence keys / pack requirements consume indexed facts |
| Diagrams | Cited node properties; propose from facts |
| Delivery | AI metering on index/generate calls |

## 8. Key APIs / artifacts

- `/api/index`, `/api/index/prescan|cancel|heartbeat|resume`, `/api/reindex`, `/api/diff-index`
- `/api/artifact*`, `/api/confirm`, `/api/generate`, `/api/doc/update-from-sources`
- `/api/knowledge/*` (findings)
- Packages: `foldok_compile.py`, `foldok_index/`, `index_tools.py`, `index_prescan.py`

## 9. Acceptance criteria

- [ ] Indexing a folder twice does not re-bill unchanged files.
- [ ] Empty/failed extraction is visible to the user with a fix hint (e.g. scanned PDF → OCR).
- [ ] Generated section with no source for a required fact contains `[MANGLER]` not a fabricated value.
- [ ] `pytest foldok_index/tests` remains green; diagnose passes on a healthy project sample.
- [ ] After wiring WO 0.65: “update document with new files” lists new files or problems — never silent miss.

## 10. Open decisions

- Cutover plan: replace vs wrap `foldok_compile` cache with `foldok_index` SQLite.
- Whether findings Excel remains SoT beside the new manifest, or becomes a view.

## 11. References

`ENGINE_CONTRACT.md`, `ENGINE_TOOLS.md`, `LEARNING_AND_BOUNDARIES.md`, `FORMATS.md`, `WO-0.65-index-diagnosis.md`, `foldok_index/README.md`
