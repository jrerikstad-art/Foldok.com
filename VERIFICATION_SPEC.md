# VERIFICATION_SPEC.md — "prepared judgment" (post-v1, wedge-2 premium)

The insight: much queued "engineering judgment" is verification work —
lookup, comparison, routine standard checks. The product NEVER replaces
the engineer's signature; it eliminates the WAITING by delivering
review-ready packages. Boundary rules inherit from ENGINE_CONTRACT.

LEVEL 0 — DOCUMENTATION CALCULATIONS (shipped groundwork)
  Small curated formula library (`CALCULATION_SPEC.md`): bind cited facts →
  evaluate expression in code → user confirms → CalculationBlock in report.
  Not a design certificate. Feeds Level 3 later.

## The three levels
LEVEL 1 — CRITERION CHECKS (mostly built; productize)
  criterion facts × measurement/spec facts, compared in pure code.
  Output: check rows "value (cited) | criterion (cited) | PASS/FAIL".
  Already exists as ur_vs_criterion_per_row / loads_match_basis —
  generalize into a project-wide "Checks" view + a check_note block type.

LEVEL 2 — APPLICABILITY PROPOSALS (LLM proposes, human disposes)
  From artifact model + provided standards: "clause 7.3 (cited) appears
  to apply to [bracket] because [stated scope]" — confidence-scored,
  checkpoint-confirmed like everything else. Purpose='gap_check' pricing.
  The engineer confirms/rejects rows instead of reading 200 pages.

LEVEL 3 — DETERMINISTIC CHECK LIBRARY (the premium product)
  Curated formula modules in CODE (like the symbol library: curated,
  versioned, NEVER AI-generated at runtime). Launch set (each ~1-2 days):
    en1993_tension_member · en1993_bolt_group · weld_throat_static ·
    lifting_lug_dnv · beam_udl_deflection · pressure_test_hold
  Contract per module: declared inputs (each MUST bind to a cited fact
  or an explicitly user-entered value, flagged as such) → computation →
  result + criterion comparison → CHECK NOTE: formula id + revision,
  input table with sources, result, PASS/FAIL, reviewer signature line.
  HARD: the LLM never performs or post-edits arithmetic. LLM may only
  SUGGEST which module fits (level-2 style); binding and running is
  code + human confirmation.

## Schema (migration_007 when built)
  check_library: id, module_key, name, standard_ref, revision,
                 input_schema jsonb, active
  check_runs: id, document_id, module_key, module_revision,
              inputs jsonb (each {value, unit, fact_id|user_entered}),
              result jsonb, verdict pass|fail|review,
              confirmed_by uuid, created_at
  document_blocks: block_type += 'check_note'

## Liability posture (declaration text, fixed)
  "Checks computed by curated module <id> rev <n>; all inputs traceable
  per the input table. Module selection and results confirmed by the
  undersigned engineer, with whom engineering responsibility rests."
  Same structure the industry already accepts for calc software — plus
  the input traceability that software lacks.

## Pricing
  Levels 1-2 inside complex-tier documents. Level 3 check notes are the
  first honest per-seat/subscription justification (engineering teams,
  €79+/mo) — recurring verification volume, not document-shaped.

## Sequence discipline
  After first revenue, wedge-2 pull only. Level 1 generalization is
  cheap and may ride along earlier; Level 3 library is an asset built
  module-by-module against real customer check lists, never speculatively.
