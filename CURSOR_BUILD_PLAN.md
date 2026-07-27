# CURSOR_BUILD_PLAN.md — Foldok production v1

Execute this AFTER the headless milestone test passes (ENGINE_CONTRACT.md §7).
Written for a solo founder + Cursor. Each phase ends with a runnable state.
Reference implementations already in this repo — port, don't reinvent:
  - Pipeline logic:   foldok_compile.py  (port to TypeScript per Phase 2)
  - Schema:           migration_001..006    (deploy in order)
  - UI:               ui-prototype.jsx    (componentize, wire to live data)
  - Rules of record:  ENGINE_CONTRACT.md  (any conflict → contract wins)

────────────────────────────────────────────────────────────────
STATUS — updated 2026-07-23 (engine **v0.59.0**; target **v0.60** publishing)
────────────────────────────────────────────────────────────────

WHERE WE ARE
  Engine repo (foldok-engine/) — **v0.59.0**, pre-production.
  **Local priority for v0.60:** publishing pipeline first
  (`V0_60_PLAN.md`) — Composition + LayoutSolver + DesignSystem +
  LayoutTree. Requirement Engine is Phase 2 (content correctness),
  not mixed into layout.

  DONE recently (high level — see CHANGELOG / WORKQUEUE):
    ✓ LayoutTree contract v1 (Page → Region → Container → Component);
      ConstraintSolver stage; Renderer.render_layout; PUBLISHING.md
    ✓ TEMPLATE_STANDARD — shape vs content; flexible inspection_checklist
    ✓ Pre-scan / cancel / budget (0.55); industrial report blocks (0.54)
    ✓ Print-first DesignSystem + compose→measure→layout→paint (0.43–0.49)

  WORKQUEUE next (local):
    → V0_60_PLAN Phase 1 items 2–4 (composition regions, DS depth, solver)
    → Then Phase 2 Requirement Engine
    → Export/payment founder call when publishing quality is visible

  NOT STARTED (production — Phases 0–5 below):
    ✗ Supabase project + migrations deployed
    ✗ Next.js app scaffold
    ✗ Auth, upload, engine API routes, live UI, Stripe export

WHAT TO DO NEXT (strict order)
  1. **v0.60 Phase 1** — Composition regions + DesignSystem + ConstraintSolver
     (`V0_60_PLAN.md`). LayoutTree contract already frozen.
  2. v0.60 Phase 2 — Requirement Engine (Artifact AST only).
  3. Founder call — export/payment A/B (hosted vs local+metering).
  4. Optional EVAL LOOP — expected.json + eval_harness before Phase 0.
  5. PHASE 0 — Supabase (EU), migrations 001→006, create-next-app,
     seed templates, RLS test.
  6. PHASES 1–2 — upload + port engine to TypeScript; use local_app/
     server.py + form_engine/ + diagram_engine/ as the API/shape refs.
  6. PHASE 3 — componentize editor against live data.
  7. PHASES 4–5 — export, Stripe, harden template import, first customer.

POST-V1 (documented, do not build yet):
  · Grammar v2 runtime (repeat_for, hierarchy, doc_memory) — GRAMMAR_V2_NOTES
  · Verification levels 1–3 — VERIFICATION_SPEC
  · Source staleness UX — FORMATS.md
  · OAuth connectors, BankID — cut list below

DEFINITION OF SHIPPED (unchanged): one stranger pays real money for one export.

────────────────────────────────────────────────────────────────
Architecture (MVP, deliberately boring):
  Next.js 14 (App Router, TS) on Vercel
  Supabase: Postgres + Auth + Storage + pgvector
  Ingestion: file UPLOAD ONLY for v1 (OAuth connectors = Phase 2)
  AI calls: Next.js API routes → Anthropic SDK (server-side only)
  PDF: @react-pdf/renderer server-side (blocks → branded PDF)
  Payments: Stripe Checkout, one-time per export

────────────────────────────────────────────────────────────────
PHASE 0 — Foundation (Day 1–2)
────────────────────────────────────────────────────────────────
0.1 Supabase project (EU/Frankfurt). Run migration_001 through 006.
    Enable pgvector. Verify RLS with two test users (user A must not
    see user B's project — write the test, keep it).
0.2 `npx create-next-app foldok --typescript --tailwind --app`
    Add: @supabase/supabase-js, @supabase/ssr, @anthropic-ai/sdk,
    zod, @react-pdf/renderer, stripe.
0.3 Auth: Supabase email magic-link (Vipps deferred to post-MVP).
    Route group (app)/ requires session; /login public.
0.4 Seed templates: script `scripts/seed-templates.ts` reads
    templates/*.json → inserts into doc_templates + template_sections.
    Idempotent (upsert on template_key + owner null). Seed all templates
    under `templates/` (16 as of v0.35.0 — not the historical “11”).
DONE WHEN: login works, templates visible via SQL, RLS test passes.

────────────────────────────────────────────────────────────────
PHASE 1 — Projects & Upload Ingestion (Day 3–5)
────────────────────────────────────────────────────────────────
1.1 /projects — list + create (name only).
1.2 /projects/[id] — drag-drop upload zone (react-dropzone).
    Upload → Supabase Storage bucket `sources/{project_id}/`,
    insert project_files row: sha256 (compute client-side via
    crypto.subtle), filename, mime, size, status='pending'.
    Dedupe: if sha256 exists in project → skip upload, toast "already indexed (free)".
1.3 File grid: name, kind icon, status chip (pending/indexed/failed).
DONE WHEN: 20 files upload, dedupe works, rows visible with RLS.

────────────────────────────────────────────────────────────────
PHASE 2 — The Engine, server-side (Day 6–12)  ← the core work
────────────────────────────────────────────────────────────────
Port foldok_compile.py to `src/engine/` as pure TS modules.
Keep function names aligned so the Python file stays the readable spec:

  src/engine/
    prompts.ts        INDEX_SYSTEM, GEN_SYSTEM, artifact/mapping prompts
                      — copy VERBATIM from the (post-eval-tuned) Python.
    ledger.ts         logCall(purpose, model, usage) → token_ledger insert
                      + increment projects.total_cost_eur. EVERY call.
    indexer.ts        indexFile(fileRow): photo → resize (sharp, max 1024px)
                      → Haiku vision; pdf/docx/xlsx → extract text → Haiku.
                      Text extraction TS options: pdf-parse, mammoth (docx),
                      xlsx (sheets). If extraction thin, fallback: send pdf
                      base64 to Haiku directly (still one call).
                      Writes file_summaries + extracted_facts. Sets status.
    artifact.ts       buildArtifactModel(projectId) — Sonnet, one call,
                      upsert artifact_models. Refuses if <1 indexed file.
    mapping.ts        mapSections(documentId) — condition eval (port
                      _condition_holds), one Haiku mapping call, fact match
                      + gap computation in code. Writes section_mappings.
    generate.ts       generateSection(documentId, sectionKey) — boilerplate
                      short-circuit, fact/caption context, Sonnet/Haiku
                      routing, POSTPROCESS: resolve {{fact:id}} → block
                      cited_fact_ids, {{missing:key}} → missing_placeholder
                      block, bare-number validation in SPEC_SECTIONS with
                      one regeneration retry. Writes document_blocks +
                      document_versions (scope=document, v1).
    guards.ts         budget guards from contract §6: free-tier file cap,
                      per-export regen bundle counter, runaway-session pause.

API routes (thin wrappers, zod-validated):
  POST /api/projects/[id]/index        → runs indexer over pending files
                                         (sequential; queue later if slow)
  POST /api/projects/[id]/artifact     → checkpoint A
  POST /api/projects/[id]/artifact/confirm  { corrections? }
  POST /api/documents                  { projectId, templateKey } → creates
                                         document + runs mapping (checkpoint B)
  POST /api/documents/[id]/generate    → all sections (or ?section=key)
  POST /api/blocks/[id]/regenerate     { instruction? } → single block,
                                         new document_versions row
HARD RULES (contract): no route ever re-reads Storage originals after
indexing; artifact must be user_confirmed before mapping/generation runs;
every Anthropic call goes through ledger.ts.

DONE WHEN: curl sequence index→artifact→confirm→document→generate produces
blocks in DB for the battery-tool test folder, ledger rows present,
one deliberately-missing fact appears as missing_placeholder block.

────────────────────────────────────────────────────────────────
PHASE 3 — UI on live data (Day 13–18)
────────────────────────────────────────────────────────────────
Componentize ui-prototype.jsx → src/components/. Keep the design tokens
(T object), Archivo + IBM Plex Mono, the traceable-ink hover, MANGLER
styling, i18n STRINGS pattern (move to src/i18n/{no,en,pl}.ts).
Add ExplorerRail per NAVIGATION_SPEC.md (project switcher, KILDER tree,
DOKUMENTER list) left of the workflow stepper; auto-collapse on Bygg.
  3.1 Stepper shell reads real project state (which checkpoint is next).
  3.2 Forstå: renders artifact_models row; edit = corrections JSON →
      confirm route. Gate UI until confirmed (button disabled + reason).
  3.3 Struktur: section_mappings + gap_flags; drag file chip between
      sections → PATCH mapping (user_adjusted=true, zero AI).
  3.4 Bygg: sources panel from file_summaries (thumbnails: Storage
      signed URLs, 52px); document canvas renders document_blocks by
      type; Fact chips carry cited_fact_ids → hover lights source file
      (join facts→file); MANGLER placeholder has inline input → creates
      user-entered fact (verified_by_user=true) → block re-render.
      Block toolbar → regenerate route; version history drawer from
      document_versions with per-block revert.
  3.5 Cost meter in header ← projects.total_cost_eur (realtime sub).
DONE WHEN: full flow in browser on a fresh folder, hover-tracing works
against real facts, a MANGLER can be resolved inline.

────────────────────────────────────────────────────────────────
PHASE 4 — Export, Payment, Branding (Day 19–24)
────────────────────────────────────────────────────────────────
  4.1 Company profile page → company_profiles (logo/stamp upload to
      private bucket, footer text, org.nr).
  4.2 PDF: src/engine/render-pdf.tsx with @react-pdf/renderer.
      Blocks in order; branding applied at render time (contract);
      watermark "UTKAST" diagonal unless document.status='exported';
      Source Register appendix auto-appended (files + captions +
      citing sections — pure data, matches templates' source_register).
  4.3 Export flow: blocking gaps → export disabled with reasons list
      (override allowed, logged). Responsibility confirmation screen
      (text + checkbox, logged to document_versions change_summary).
      Stripe Checkout one-time (price from export_price_tier:
      basic €9 / standard €19 / complex €49 launch pricing — tune later).
      Webhook → status='exported' → clean PDF generated in-memory,
      streamed; NOT persisted (legal stance: no stored signed PDFs).
  4.4 Signature block: typed-name + drawn (signature_pad lib) → SVG in
      private bucket → rendered into PDF. BankID = post-MVP.
DONE WHEN: paid test-mode export downloads a branded, watermark-free PDF
with source register; unpaid preview is watermarked.

────────────────────────────────────────────────────────────────
PHASE 5 — Template import + hardening (Day 25–30)
────────────────────────────────────────────────────────────────
  5.1 Template import per migration_002 contract: upload → extraction
      call (purpose='template_import') → review UI (port from prototype:
      field list, requirement-pill cycling, boilerplate verbatim notice)
      → insert owner-scoped doc_templates + template_sections.
  5.2 Guards live: free tier 1 project / 50 files; batch >100 files →
      cost-estimate confirm; regen bundle 30/doc then soft top-up.
  5.3 Error states: every engine failure → status='failed' + fail_reason
      + retry button. Never a dead spinner. Sentry on server routes.
  5.4 Deploy: Vercel prod + Supabase prod keys + Stripe live-mode
      switch DEFERRED until first real customer says yes.
DONE WHEN: you compile a real project end-to-end in production and
send the PDF to one of the two warm survey leads.

────────────────────────────────────────────────────────────────
CUT LIST (explicitly NOT in v1 — resist)
────────────────────────────────────────────────────────────────
OAuth folder connectors · Vipps/BankID · teams/roles · chat-edit ·
knowledge base · offline · mobile app changes · RAG library ·
public template marketplace. (Local diagrams + forms already exist —
port, don’t cut.) Every remaining item is post-revenue unless Tier 5
says otherwise.

DEFINITION OF SHIPPED: one stranger pays real money for one export.

────────────────────────────────────────────────────────────────
ADDENDUM A — Template switching semantics (v0.11.1, from field bug)
────────────────────────────────────────────────────────────────
A document is BORN with its template (documents.template_id). A template
"switch" is a re-compilation, never a style toggle. Required behavior:

  UN-GENERATED draft (no blocks yet):
    switch → UPDATE documents.template_id → wipe section_mappings →
    auto-re-run checkpoint B (cost rule: ~€0.01, auto with progress) →
    Struktur view refreshes. One document, re-mapped in place.

  GENERATED draft (blocks exist):
    switch → confirm dialog: "Bytte mal regenererer alle seksjoner
    (est. €X). Nåværende utkast beholdes i historikken." → on confirm:
    document_versions snapshot (scope=document, 'Byttet mal fra X til Y')
    → wipe blocks + mappings → re-run B → generation stays EXPLICIT
    button (money = consent).

  EXPORTED document: no switch. "Opprett nytt dokument fra samme
  prosjekt" instead (index reused — cheap).

  Workbench (local_app) equivalent: template dropdown re-runs mapping
  on generate; a draft is overwritten only after explicit "Generer".
