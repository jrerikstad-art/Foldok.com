# WORKORDER_0.19B.md — Empty projects, identity blocks, reference values

Field test: empty folder "Toyota RAV4 2013" → service procedure.
Three failures, three fixes. All engine-level, all small.

────────────────────────────────────────────────────────────────
1. PROJECT NAME IS A SOURCE (fixes "missed 2013")
────────────────────────────────────────────────────────────────
Synthesize one index entry per project from the project/folder name(s):
  { "file": "(prosjektnavn)", "sha": "projname:<hash>", "kind": "project_name",
    "caption": "<the name verbatim>", "doc_role_hints": [], "facts": [...] }
Facts extracted by ONE cheap Haiku call (cached against the name hash):
  "Extract identifier facts explicitly present in this project name:
   make/model/year/address/gnr-bnr/drawing-no patterns. Only what is
   literally in the string. key examples: make, model, model_year,
   address, case_ref."
Citation renders as source "prosjektnavn" — honest and traceable.
Applies always (not only empty projects); for "Example Treatment Plant"
it yields kommune + artifact hints for free.
Empty-project UX: when file count == 0, checkpoint A states it plainly:
  "Mappen er tom — forståelsen bygger kun på prosjektnavnet. Legg til
   filer, eller fortsett med et dokument der du fyller inn verdiene."

────────────────────────────────────────────────────────────────
2. RUNG-3 IDENTITY RULE (fixes missing reg/owner/mileage MANGLER)
────────────────────────────────────────────────────────────────
Add to the template-draft prompt (TEMPLATE_LIFECYCLE rung 3) as a hard
requirement:
  "The drafted template MUST begin with an identification/data section
   listing the standard identity fields for this artifact type as
   required_facts (severity: warning). Examples — vehicle: reg_no, vin,
   model_year, mileage, owner; building: address, gnr_bnr, kommune;
   machine/product: manufacturer, model_no, serial_no; contract:
   party, contract_ref. Choose fields a professional in the domain
   would expect on page one."
Validation in code after draft: first section contains ≥3 required_facts
→ else re-ask once, else inject a generic identification section.
(System templates already comply; this closes the gap for drafted ones.)

────────────────────────────────────────────────────────────────
3. REFERENCE VALUES — third provenance class (fixes "no effort on
   oil type" WITHOUT breaking the citation rule)
────────────────────────────────────────────────────────────────
Provenance classes: extracted (blue, cited) · verified_by_user (green ✓)
· NEW: reference (amber ~, "AI-foreslått referanseverdi").

Where it appears — ONLY as a pre-fill offer in the MANGLER menu:
  Popover: "Foreslått: 0W-20 — typisk for Toyota RAV4 2013.
            [Bruk — merkes som ubekreftet]  [Verifiser selv]"
  Fetched lazily: one Haiku call per gap on popover open, purpose=
  'reference_suggest', prompt: "Suggest the commonly known value for
  <key> for <artifact summary>. Reply value+unit+one-line basis, or
  NOT_CONFIDENT." NOT_CONFIDENT → no offer shown. Cache per (key,
  artifact hash).

HARD RULES (these make it safe — implement all four):
  a) NEVER auto-inserted. User action required, always.
  b) NEVER satisfies a blocking gap on compliance/safety-critical keys;
     accepting downgrades the gap to state "ubekreftet" (amber pill
     count, separate from resolved), not "closed".
  c) Renders distinctly: amber ~chip; popover text "AI-foreslått —
     ikke verifisert mot kilde. Verifiser mot håndbok/typeskilt."
  d) Export responsibility screen lists EVERY accepted reference value;
     the declaration names them: "Verdier merket ~ er AI-foreslåtte
     referanseverdier som ikke er verifisert mot prosjektets kilder;
     ansvaret for verifisering ligger hos undertegnede."
State: user_facts entry gains "provenance": "reference" (default
"user" for typed, "extracted_targeted" for pek-på-kilden — unify the
field while touching this).

────────────────────────────────────────────────────────────────
ACCEPTANCE
────────────────────────────────────────────────────────────────
1. Empty folder "Toyota RAV4 2013" → artifact knows make/model/YEAR,
   cited to prosjektnavn; checkpoint A shows the empty-folder notice.
2. Rung-3 service template → first section demands reg_no, vin,
   model_year, mileage, owner as warning MANGLER.
3. Oil-type MANGLER popover → amber suggestion with [Bruk — merkes som
   ubekreftet]; accepting shows ~chip, gap moves to "ubekreftet" count,
   export screen lists it; declaration paragraph present in export.
4. A blocking compliance key (e.g. test_standard on lifting tool)
   NEVER shows a reference offer.
5. "Example Treatment Plant" project → kommune fact exists cited to
   prosjektnavn (regression: feature helps non-empty projects too).
