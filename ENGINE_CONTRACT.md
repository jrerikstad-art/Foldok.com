# Foldok Engine Contract v1.0

The binding rules between the index, the templates, and every AI call.
This document is the spec Cursor builds against. Nothing in the pipeline
may violate a rule marked **HARD**.

---

## 0. The One-Line Model

```
source files ──index once──▶ PROJECT INDEX ──▶ A: artifact model
                                            ──▶ B: section mappings + gaps
                                            ──▶ C: block generation
                                            ──▶ export
```

Every arrow to the right of the index reads **only** the index.
Original files are never re-sent to any model after indexing. **HARD**

### 0.1 Engine vs AI (LEARNING_AND_BOUNDARIES §2)

**THE RULE: the AI never holds state; the engine never guesses.**

| Engine (deterministic, owns state) | AI (stateless edge calls) |
|---|---|
| index & facts · templates-as-data · gaps · BOM/totals · citation validation · code tables · versioning · export · ledger · suggestion rules · capabilities | extraction · artifact model · mapping proposals · constrained prose · intent/template choice · conversation · reference suggestions |

Every AI output lands in engine-validated structures or it does not land.
Smarter ≈ better engine data (vocabulary, rules, templates), not bigger models.
See `LEARNING_AND_BOUNDARIES.md`.

**In-project chat calls** always attach engine-built context (name, folder,
file count, full artifact incl. confidence, documents + gap counts, fact-key
inventory keys+counts only, conversation history). Never a thin summary.

---

## 1. Indexing (runs once per file, ever)

| Input | Model | Output | Budget |
|---|---|---|---|
| Photo | Haiku (vision) | caption ≤40w, content_tags, doc_role_hints, quality_flags, facts | ≤1 call, ~1.3k in / 250 out |
| PDF / DOCX / XLSX | MarkItDown → Haiku | caption, detail_summary ≤200w, facts | ≤1 call per 8k-token chunk |
| Text / CSV | Haiku | same as PDF | 1 call |
| Video / CAD | none (MVP) | status=skipped, filename searchable | 0 |

Rules:
- **HARD** — `sha256` match in project ⇒ skip entirely, cost €0.
- **HARD** — every call writes a `token_ledger` row (purpose=`index_photo`/`index_doc`).
- Facts are extracted in the same call as the caption (one prompt, two output blocks) — never a second pass.
- `confidence < 0.8` facts are stored but flagged; UI shows them amber.
- Embedding computed locally-cheap (voyage/openai small) on `caption + tags`.

### Fact extraction prompt contract (index-time)
The model receives file content + this instruction core:

> Extract only facts explicitly present. For each: fact_type, key (canonical
> snake_case from the vocabulary list), value, unit, confidence, verbatim
> source_excerpt, source_location. If a value is partially legible, lower
> confidence — never complete it. Do not infer. Do not compute.

Canonical key vocabulary lives in `fact_keys.json` (start: ~40 keys —
swl, weight, dimensions, serial_no, model_no, manufacturer, test_standard,
pullout_force, insulation_resistance, earth_continuity, rcd_test, torque_x,
inspection_interval, material, …). Unknown keys allowed but flagged
`nonstandard_key` for later canonicalisation.

---

## 2. Checkpoint A — Artifact Model

- Input: **all captions + all facts** for the project (text only; ~5–8k tokens for 120 files).
- Model: Sonnet. One call. Purpose=`artifact_model`.
- Output: `artifact_models` row — artifact_type, name, purpose, main_components
  (each with `seen_in` file ids), hazards (each with source file id or `"inferred"`),
  lifecycle_stages, confidence.
- **HARD** — `user_confirmed=false` blocks checkpoint B and C. The UI shows
  "Here's what I think this is" and the user edits/confirms. Corrections append
  to `corrections_log` and re-run is **incremental** (send diff, not full re-analysis).

## 3. Checkpoint B — Structure + Mapping + Gaps

Per document (template chosen by user; `applies_to` filters the picker):

1. **Section applicability** — evaluate each `template_sections.condition`
   against the artifact model. Pure code, no AI, 0 tokens.
2. **File mapping** — for each applicable section: embedding retrieval
   (section title + doc_role_hints as query) → top-K candidates → one Haiku
   call per section to accept/reject/rank (~800 in / 150 out). Purpose=`section_mapping`.
3. **Fact mapping** — `required_facts[].key` matched against `extracted_facts.key`.
   Pure code, 0 tokens.
4. **Gap computation** — pure code, 0 tokens:
   - required fact absent ⇒ gap `{type:'missing_fact', key, severity}`
   - `required_media.min_photos` unmet ⇒ gap `missing_media`
   - `cardinality:'one_per_hazard'` unmet ⇒ gap per uncovered hazard
   - severity from template; `blocking` gaps disable export until resolved
     or explicitly overridden (override logged to audit).

User rearranges mappings in the UI (drag/drop) ⇒ `user_adjusted=true`,
zero AI cost.

## 4. Checkpoint C — Generation

**Per section, never per document.** Pipeline (WORKORDER 0.49):

| Step | Owner | Purpose / notes |
|---|---|---|
| 1 SELECT FACTS | code | keys+aliases+mapped files → fact set |
| 2 PARTITION | model | purpose=`partition_facts` — JSON `{prose_facts, table_facts}`; skipped when `writing_rules.structure` already decides |
| 3 WRITE PROSE | model | purpose=`generate_section_prose` — sentences citing `{{fact:id}}`; **no** tables, figures, or headings |
| 4 BUILD TABLE | code | B1 column vocabulary (`editorial_layer.TABLE_COLUMN_VOCAB`) |
| 5 PLACE FIGURES | code | `required_media` + caption relevance; `{{fig:}}` → `{{figure:}}` |
| 6 COMPOSE/PAGINATE | code | LayoutTree + editorial furniture (title page, TOC, H/F, illustration index) |

**HARD — Call contract rule:** every model call declares (1) one output shape,
(2) a code validator, (3) a deterministic fallback after two failures.
A call missing any of the three must not ship. Prefer **computation over
validation**: if code can produce the artifact, do not ask the model.

**HARD — the citation rule:**
> Every factual claim (number, rating, standard, dimension, interval, name)
> must reference a provided fact id as `{{fact:UUID}}`. If a required value
> has no fact, output `{{missing:key}}` instead. Never state a specification
> without a fact id. Never estimate. Never use typical values.

Post-processor (code, 0 tokens):
- resolves `{{fact:id}}` → value+unit, records id in `document_blocks.cited_fact_ids`
- resolves `{{missing:key}}` → `missing_placeholder` block, rendered as an
  amber `[MANGLER: <label_no>]` box with an inline "provide value" input
- **HARD** — any bare number matching `\d` in spec-type sections
  (`technical_data`, `circuit_schedule`, `test_results`) without a citation
  fails validation ⇒ regenerate once ⇒ if still failing, insert placeholder
  and flag for user. Hallucination is a *validation failure*, not a hope.
- `boilerplate` sections: verbatim insert, **no AI call at all**.
- Warning boxes: symbol chosen from the built-in library by tag, never generated.
- Editorial layer (title page, TOC page numbers, running header/footer,
  numbered figures, illustration appendix, glossary, cross-refs) — **zero
  model calls**.

Model: Sonnet for `generate_section_prose`; Haiku for `partition_facts`.
Tables and figures are never model-assembled when code can build them.

See `call_contracts.py` and `editorial_layer.py`.

## 5. Iteration

- `regenerate_block`: that block's section mapping + user instruction only.
  ~2–3k in / ≤1k out. Purpose=`regenerate_block`.
- `chat_edit`: scoped to the active section; context = that section's blocks +
  mapping. Purpose=`chat_edit`.
- **HARD** — no iteration path ever re-reads original files or the full document.
- Every accepted change ⇒ `document_versions` row (v15 revision rules apply:
  auto-version, per-block revert, change_summary auto-written by the same call).

## 6. Budget Guards (code-enforced)

| Guard | Limit | On breach |
|---|---|---|
| Free tier index | 50 files / 1 project | "Upgrade to index more" |
| Index batch preview | >100 files or >€1 est. | Confirm dialog with € estimate |
| Per-export bundle | 30 regenerations + 20 chat turns | Soft top-up €2–3 |
| Runaway session | >€3 tokens in 1 hour, unpaid project | Pause + notify |
| Model routing | Haiku unless purpose ∈ {artifact_model, generate_section_prose} | — |

`token_ledger` is the single source of truth; the per-project cost meter
in the UI reads `projects.total_cost_eur` (updated by trigger on ledger insert).

## 7. Definition of Done (headless milestone)

A CLI run — `foldok compile ./polyanchor-folder --template technical_doc_package`
— that produces:
1. index rows for every file, with costs in the ledger
2. an artifact model that a human confirms is ≥80% correct unedited
3. section mappings where ≥80% of photos land in the right section
4. a generated markdown draft where **zero** specs lack a fact citation,
   and every genuine gap surfaces as `[MANGLER]`

Only after this passes does UI work begin. The UI is a skin over
checkpoints A/B/C — the engine must already be trustworthy headless.
