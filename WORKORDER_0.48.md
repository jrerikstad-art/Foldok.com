# WORKORDER_0.48 — Dokumentkvalitet: alle fakta inn, tabeller og bilder UT

Diagnosis from reading `foldok_compile.py` @0.47 (`generate_section`):
the rendering stack (0.39–0.47) is good; the **content pipeline** was starving it.

## Shipped fixes

### Bug 1 — two-tier fact context
- `PRIMARY` = mapper `fact_ids`; `AVAILABLE` = required-key matches + mapped-file facts + artifact synth, cap 120, confidence-sorted.
- Prompt shows both blocks; `{{missing:key}}` only when absent from **both** tiers.

### Bug 2 — structure enforced
- `structure_ok` + one corrective retry; table failure → `build_generic_fact_table` (`Parameter | Verdi | Enhet | Kilde`).
- OUTPUT FORMAT placed first in the generate prompt.
- `postprocess` preserves newlines (tables / figure lines must not flatten).

### Bug 3 — figures
- Model emits `{{fig:filename}}`; `resolve_fig_markers` → `{{figure:…}}`; unknown dropped.
- `ensure_min_figures` + `ensure_figures_in_doc` when `required_media.min_photos > 0`.
- Drawings preferred for overview/scope-ish sections.

### Bug 4 — one-click document
- Agreement card: title + file count + est. € + time; `[Lag dokumentet →]` + Annen mal.
- Chips are verbs with objects; document chips show € and call `lagDokumentFromChip` → generate immediately.
- After generation: scroll to document + gap pill (`PENDING_STREAM_DONE`).

## Acceptance (manual / rich PDF)
Measure on a rich source (e.g. equipment manual): one-click tech package; Tekniske data as markdown table ≥6 rows; ≥3 figures with captions; ≥60 % relevant facts reach the doc; false `[MANGLER]` near zero vs index; one chat from chip to open document.

## Regression
`test_62_wo048_fact_context_structure_and_figs` — suite = **62**.
