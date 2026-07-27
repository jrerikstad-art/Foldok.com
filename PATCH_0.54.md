# PATCH_0.54.md — Figurer og malruting (Claude-side patch + wiring TODO)

Attached: `foldok_compile.py` — patched against 0.53.0 (3047 → 3110 lines,
compiles clean). Three fixes are IN THE FILE. One fix is NOT — it lives in
`server.py` and needs Cursor. Symptoms this addresses:

  · «no images in most documents»
  · «asked for an installation manual, got a technical document»
  · «one image of a boat when it had hundreds of product photos»

════════════════════════════════════════════════════════════
IN THE ATTACHED FILE — merge as-is
════════════════════════════════════════════════════════════

### FIX 1 — legacy path was figure-blind  (generate_section)
`generate_section` returned code-compiled sections (`supplier_manual_gaps`,
`drawings_register`, `doc_control`, `spec_overview`, `bom`, boilerplate)
WITHOUT calling `place_section_figures`, while `generate_section_with_structure`
wrapped all of them. Two divergent copies of the same dispatch — and
`server.py:969` calls the legacy one.
→ All six branches now call `place_section_figures(...)`.

### FIX 2 — figures were opt-in, and nothing opted in  (ensure_min_figures)
`ensure_min_figures` returned immediately when `min_photos <= 0`.
Measured: **18 of 138 template sections (13 %) declare min_photos.**
`contract_review`, `free_document`, `inspection_checklist`: zero.
That alone explains image-less documents.
→ DEFAULT-ON policy: any section with mapped visual files gets ≥1 figure.
   Opt-outs, all respected:
     · `required_media: {"no_figures": true}` in the template
     · `writing_rules.structure == "boilerplate"`
     · section_key in new constant `NO_FIGURE_SECTIONS` (declaration,
       source_register, drawings_register, doc_control, revision_history,
       abbreviations, toc, signature, erklaering, kilderegister,
       supplier_manual_gaps, ambiguities, risk_flags)
   Verified: section with silent template → 1 figure; opt-out → 0;
   registers → 0.

### FIX 3 — figure candidate pool was starved  (ensure_min_figures)
Root cause of the boat photo. Selection ranked ONLY `mapping["files"]` —
the handful checkpoint B assigned to that section. With hundreds of photos
the mapper had given that section a boat, so a boat is what appeared. The
scoring function was fine; the pool was one item.
→ Pool = mapped files + every other visual file in the index.
→ New `relevance()` scorer: section title + notes + section_key vs the
   file's caption + content_tags, 6-char prefix match (montasje~montert),
   capped at 24.
→ Rebalanced `total()`: relevance outweighs role bonuses; captioned-but-
   irrelevant files take −8; mapper's pick keeps a +4 tiebreak (never an
   override); files scoring ≤6 and unmapped are dropped entirely.
   Verified on a 150-photo fixture: section «Installasjonssekvens» now
   picks «Fôringssystem rørføring og buffersilo montert» instead of
   «Båt ved kai».
   Cost: zero tokens — pure code.

════════════════════════════════════════════════════════════
NOT IN THE FILE — Cursor must wire this  (server.py)
════════════════════════════════════════════════════════════

### FIX 4 — curated template routing is missing from PROJECT chat
`template_lifecycle.is_installation_manual_ask()` and
`match_curated_template()` work correctly, but are only called from:
    local_app/editor_chat.py:679      (in-document assistant)
    local_app/hub_chat.py:51          (cold start)
The **project-level chat** — where the user actually asks — never calls
them, so «lag en installasjonsmanual» falls through to generic intent
matching and lands on `technical_doc_package`.

TODO:
  1. In the project chat's document-creation path, call
     `tl.match_curated_template(text, caps)` BEFORE the generic intent
     route, exactly as editor_chat does.
  2. Vocabulary collision to resolve: registry has
     `registry/document-types/installation_guide.yaml` while the template
     is `templates/installation_manual.json`. Two names for one thing is
     probably how the router got bypassed. Pick one key, alias the other.
  3. Regression test: in a project, «jeg trenger en installasjonsmanual»
     → created document's template_key == "installation_manual".

════════════════════════════════════════════════════════════
ALSO FOUND — privacy gate leak (fix before any external share)
════════════════════════════════════════════════════════════
Real address still shipped in docs (the 0.19 §4 grep only covers code):
    skills/core/form-filler/SKILL.md:38   "<real street address>"
    FLOW_ONE_OPERATION.md:21             "Tilbygg og fasadeendring — <real street>"
→ Scrub both, and widen the release grep to *.md, *.yaml and skills/.
(Done in 0.53.1 — fictional Example Road used instead.)

════════════════════════════════════════════════════════════
HOW TO VERIFY AFTER MERGE
════════════════════════════════════════════════════════════
1. Regenerate a document on a photo-rich folder → figures appear in
   narrative sections, none in registers/declarations.
2. Figures chosen match the section topic (check an installation section
   contains installation photos, not a cover shot).
3. «lag en installasjonsmanual» in a project → installation_manual
   template (after FIX 4).
4. Full test suite still green: scripts/test_*.py (test_chat_isolation
   needs a live API key).
