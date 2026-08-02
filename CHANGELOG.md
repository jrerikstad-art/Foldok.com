# CHANGELOG — foldok-engine

Versioning rules (semver, honestly applied):
  MAJOR — 1.0.0 is reserved for the day one stranger pays for one export.
  MINOR — new capability: template pack, migration, spec, pipeline feature.
  PATCH — fixes, prompt tuning, doc corrections.
  Templates carry their own `version` field (already in schema).
  The zip filename always carries the version: foldok-engine-vX.Y.Z.zip.

## 0.113.7 — Regenerate typos → open Temabrief, not Installasjonsmanual
- `egaanerate` / `regaanerate` / bare `regenerate` now hit deterministic
  `run_generate` on the open document (clears stale €19 install pending)
- Stops Haiku inventing “Installasjonsmanual venter på bekreftelse”

## 0.113.6 — Restore regenSection (and section edit helpers)
- Toolbar «↻ Regenerer» called a missing `regenSection` — ReferenceError
- Restored regenerate → diff → Godta/Forkast, plus edit/revert and minimal MANGLER resolve

## 0.113.5 — Three guards: bridge / slug / cite-spam
- Bridge builder permanently empty (no «Etter dette —» stacking)
- Topic slugs (`Electromagnetic_compatibility`) never written as body text
- Volume author merges cites into real quotes; empty → honest MANGLER gap
- Scrub + compose_brief wipe old Compatibility/Protection spam on assemble

## 0.113.4 — Scrub bridge spam + TOC-title “facts”
- ``bridge_opening`` disabled (source of endless «Etter dette —»)
- ``scrub_authored_prose`` removes bridge paragraphs and lines like
  ``Corrosion_protection. [17]`` on assemble and author
- Empty scrubbed sections become an honest content GAP
- Topic-brief cache key bumped so old composed bodies are not reused

## 0.113.3 — Kill nested «Etter dette — Etter dette»
- Root cause: ``bridge_opening`` wrapped the previous section summary; when that
  summary was itself a bridge, it nested forever
- Bridges no longer quote prior prose — only fixed beat-to-beat lines (or none)
- ``strip_nested_bridges`` cleans old drafts on assemble and new author output

## 0.113.2 — Document language follows UI (EN/NO)
- UI language was chrome-only; ``/api/generate`` defaulted to Norwegian
- ``api()`` now injects ``lang`` from the EN/NO toggle on every engine call
- Server generate/compose defaults flipped to English; ``state.lang`` persisted on generate
- Regenerate with EN selected to get an English document

## 0.113.1 — Installation sections must instruct, not meta-narrate
- Reject hollow TOC/filename “claims” (`Installation_guide`) as section body
- Install/procedure sections no longer get research “argumentet” bridges
- Nested bridge bug fixed (“Etter dette — Etter dette — Reglene forankres…”)
- Honest GAP when folder only has chapter titles, not mounting steps

## 0.113.0 — Engineering Editor: Compose
- **`foldok_evidence`**: project Asset model (depicts, relevance, stage) — distinct from registry `foldok_assets`
- **`foldok_director`**: Content Director → CompositionPlan with checklist, section clips, coverage bars
- **`GET /api/compose`**: deterministic plan for the workbench (no LLM)
- Workbench **Compose** tab: Knowledge | Narrative timeline | Live draft; draft is last ~10%
- Default editor rail opens on Compose (gaps still take priority when blocking)
- Docs: `ENGINEERING_EDITOR.md` status table updated

## 0.112.0 — Project Identity (before the section market)
- **`foldok_identity`**: `ProjectIdentity` + `NarrativeBlueprint` — purpose,
  audience, primary/secondary/excluded topics, purpose-shaped arcs
- Corpus → Identity → Blueprint → Topics → Sections (see `PROJECT_IDENTITY.md`)
- `build_offer(..., identity=)` scores Relevant / Somewhat / Background / Ignore;
  Ignore is not kept by default so OEM density cannot become the document
- Wired through `sketch_patch` + `foldok_corpus.integrate`
- **Hard rule:** no vendor catalogues / real project needles in engine logic —
  removed `VENDORS` list; replaced with generic manufacturer/publisher signals;
  stripped Dogger/Toyota/rav4 hardcoding from compile + chat intent
- Tests use synthetic fixture names only

## 0.111.0 — Engine package stack + cleanup release
- Ships foldok_role / select / volume / budget / corpus as first-class packages
- Corpus «Fra mappen» on every generate (including form_fill)
- Citation scope (foldok_budget) required — removed dead one-cite-per-file fallback
- Removed superseded install-only corpus compiler (shared ``integrate`` owns it)
- Release script: strip all ``_import_*`` scratch; privacy-grep new packages
- Docs: README package table; VERSION sync

## 0.110.2 — Corpus appendix on every document type
- ``foldok_corpus`` no longer topic-brief-only: ``run_generate`` *and*
  ``run_form_fill`` inject «Fra mappen» after assemble for all templates
- Shared ``foldok_corpus.integrate`` (PDF + caption extract, offer, inject)
- Removed duplicate install/topic-brief-only corpus section writers
- Harden empty/corrupt index cache JSON (no more KeyError on ``caption``)

## 0.110.1 — Corpus reaches installation manuals
- ``foldok_corpus`` was only wired into topic briefs; install regenerates
  saw no change. Focus OEM PDFs are now wide-extracted (full page text) and
  append «Fra mappen» sections (begrunnelse, konsekvenser, …)
- Clears ``_install_corpus_md`` cache on overview rebuild

## 0.110.0 — foldok_corpus (folder proposes, user disposes)
- Ten non-factual claim types (decision, problem, condition, open_question, …)
  so sections are not all built from "what is true?"
- ``build_offer`` / section market: folder supports N sections before any
  document type is named; user deletes what they do not want
- Narrative order held by band (frame → basis → body → evidence → exception → close)
- Wired into ``plan_narrative`` (+ purpose→type map in ``claims_bridge``)

## 0.109.0 — foldok_budget (citation scope + pipeline health)
- Document-wide one-cite-per-file discarded ~95% of claims; ``CiteScope``
  allows up to 3 cites/file per section with a 45% document-share ceiling
- ``rank_key`` puts project role before keywords (vendor asides stay fallback)
- ``section_budget`` scales claims per section with retrieval yield
- ``check_pipeline`` diagnoses thin/broken stages; surfaces in topic-brief gaps
- Wired into ``foldok_ask.author_doc`` / ``compose_brief``

## 0.108.3 — Install volume actually expands (single-PDF focus)
- Page-guidance claim ids truncated on long OEM stems — only 1 of 16 pages
  survived; ids now use short stem + page + content digest
- Volume read claims from flat plan keys that never existed; uses ``plan.claims``
- Single-PDF focus: page-grain sources + lowered min_sources/min_evidence
- Outline coverage terms are bilingual so ``safety`` is not re-proposed
- ``foldok_volume`` justified()/theme vocabulary honour caller thresholds;
  modal/filler themes (should, always, …) filtered

## 0.108.2 — Volume expands installation manuals too
- Active install manuals never hit ``plan_narrative``; volume now appends
  «Ytterligere emner fra kildene» on the sequence section from uncovered claims
- Topic-brief compose cache keys include VERSION so regenerates pick up fixes
- Sequence step cap scales with claim budget

## 0.108.1 — Volume actually expands the document
- Framing ``retrieve_query`` dumped every theme, so coverage thought everything
  was already covered and ``widen()`` added nothing — fixed via narrow outline
  terms for analysis
- Proposed sections are authored from carried evidence (not omitted as optional)
- Volume note surfaces in Åpne punkter; claim pick scales with corpus size

## 0.108.0 — foldok_volume (corpus decides document length)
- Fixed outlines no longer cap the document at ~40 claims
- Uncovered themes become marked optional sections (delete = one click)
- Claim budget per section scales with corpus size
- Wired into ``plan_narrative`` + ``extract_claims``

## 0.107.0 — foldok_select (curation then selection)
- ``build_context``: admissible corpus; sales material excluded (role=ignore)
- Section illustration menus are bounded choices — model never asked if an
  image exists
- ``ensure_min_figures`` filters/ranks via select context

## 0.106.1 — foldok_role ignore tier
- Sales brochures / price lists get role ``ignore`` (weight 0) — not weak
  reference; they do not vote on the subject

## 0.106.0 — foldok_role (project vs reference + photo offers)
- Classify index entries as project / reference / unknown; theme votes are
  role-weighted so vendor brochures inform but do not decide the subject
- Document title from artifact → project → folder (never file sort order)
- Photo gaps offer existing folder photos for confirmation before capture
- Wired: `foldok_ask.plan.corpus_sketch`, `PhotoCaptureResolver`,
  `CompletionSession.photo_offers` / capture publish

## 0.105.1 — Free PDF download on Export (dev)
- Export PDF is a real PDF (PyMuPDF Story), not a renamed `.md`
- Clicking **Eksporter** always returns `download_base64` → browser download
- Local/dev remains free when `FOLDOK_EXPORT_PRICE` is unset (no paywall)
- Sidecar `.md` still written under `Rapporter/` for archive/re-open

## 0.105.0 — Install claim partitioning (single assignment)
- Extract claim set once from locked/focus sources (+ page spans)
- Assign each claim_id to exactly one bucket: identity | overview |
  prerequisites | safety | checks | sequence | supplier_only
- Sequence → ordered numbered steps (mount/connect/route/verify…);
  if fewer than 3 actionable steps → one clear gap
- Never re-emit the same claim in two body sections
- Diagrams once (overview); «Tillegg fra sider» at most once (sequence appendix)
- Prerequisites = short prose + compact table; safety = hazards/limits;
  verification = checklist

## 0.104.4 — Compact install illustration marks
- Shrink cable-tray, bonding-connector, and protection-class symbols to sit
  with breaker/earth scale (reference strips no longer dominate the page)

## 0.104.3 — Cable-tray shielding cross-section symbols
- Marks: ``cable_tray_deep``, ``cable_tray_shallow``, ``cable_tray_deep_ok``,
  ``cable_tray_shallow_bad``, ``cable_multicore``
- Install reference strip when cable-tray / tray-shielding facts are cited
  (deep U preferred; cables below top edge)

## 0.104.2 — Equipotential bonding connector symbols
- Marks: ``bond_strap`` (solid), ``bond_braid_lug`` (square lugs),
  ``bond_braid_ring`` (ring terminals) — large-area bonding connectors
- Install reference strip when ground-strap / equipotential facts are cited

## 0.104.1 — IEC protection-class marks (I / II / III)
- Symbols: ``protection_class_i`` (earth in circle), ``protection_class_ii``
  (double square), ``protection_class_iii`` (SELV diamond)
- SELV install recipe tags class III; optional I/II/III reference strip when
  protection-class facts are cited

## 0.104.0 — Expanded foldok_diagram symbol pack
- New electrical marks: mains_filter, transformer, power_supply, sensor,
  cable_shielded, rcd, fuse, contactor, switch, lamp, terminal_strip,
  ferrite, capacitor
- New piping marks: valve_gate, valve_mixing, valve_prv, strainer,
  water_meter, expansion_vessel, air_vent, radiator, boiler, cross_equal
- New mechanical: bearing, shaft
- Install recipes use pack symbols (sensor / filter / PSU / shielded cable)
  instead of anonymous module boxes

## 0.103.0 — Install manuals use foldok.diagram.v1 wiring quality
- Install recipes render via ``foldok_diagram_tool`` (same engine as water-heater
  interconnection SVGs: IEC symbols, wire colours, designations, jumps)
- Drop card-style ``render_block_diagram`` for install illustrations
- Specs use ports + L1/N/PE or ELV designations; modules for filter/sensor/PSU

## 0.102.1 — Preserve SVG openers through contact-noise postprocess
- ``xmlns="http://…"`` no longer strips ``<svg>`` lines outside contact sections

## 0.102.0 — Install manuals: Foldok-generated block diagrams
- From cited install facts, auto-build connection_spec recipes (shield/earth,
  mains filter at cabinet entry, SELV/PELV) — no vendor hardcoding
- Render original SVG via ``connection_diagram`` / ``diagram_engine`` into
  overview, safety, and sequence
- Still never rasterize OEM PDF pages; diagrams are Foldok drawings

## 0.101.0 — Install manuals must not copy OEM PDF pages
- Hard rule: no rasterized supplier PDF pages in installasjonsmanual body
  (copyright / “just a copy of the original”)
- Overview is authored from cited facts; ``append_install_figures`` strips page copies
- ``ensure_min_figures`` / ``ensure_figures_in_doc`` skip install manuals
- Declaration states Foldok-generated cited extracts ≠ supplier original

## 0.100.0 — Install: use focus PDF depth (pages + figures + unfacted text)
- System overview from focus source caption/detail + up to 8 page figures
- Procedure sections attach page illustrations from the focused technical PDF
- Focus mode pulls all engineering facts (not a 14-tip cap)
- Harvest install sentences from PDF pages that were never fact-indexed
- Pass project folders into generate so page text can be read from disk

## 0.99.1 — Fix stale-server miss + duplicate-index cite scramble
- Dedupe index by file path before install compile/postprocess (same PDF under
  project + Documents/ was reusing fact ids with different values)
- Install identity compiled from allowlisted sources + locked system
- Tip table header uses ``Nr`` (``#`` broke Markdown as H1)

## 0.99.0 — Install gaps: catch folder facts under real extractor keys
- Soft-match + aliases: ``hazard`` ← ``safety_device_fault_response`` / warnings;
  ``system_type`` ← ``applicable_products`` / locked system; ``requirement`` /
  ``criterion`` ← ``*_requirement`` / ``*_limit`` / coverage keys
- Install ``template_gaps`` runs on the allowlist (not the whole loud corpus)
- Generate uses map_sections gaps (with file_map) — photos no longer always MANGLER
- Overview media: mapped technical PDFs count toward min_photos
- Weak allowlist scores need procedure signal or engineering role

## 0.98.0 — Install tips from technical-info PDFs (not filename-only)
- Lexicon/score: ``technical information``, background knowledge, shielding,
  cable routing, laser/scanner/camera — so tips docs score without ``install``
  in the filename
- Strict ``system_under_install`` lock: foreign-system catalogues stay out even
  when they score high on generic install words
- Procedure sections compile cited tip tables from allowlisted facts (no empty
  shells when tips exist)
- Gap/thin messages list real candidate filenames from *this* index
- Still no project/vendor hardcoding

## 0.97.0 — Install manual: locked system, stay thin, named focus
- Hard allowlist: facts no longer Tier-A from the whole project corpus
- ``install_system_locked`` + system-shaped file filter
- Strategy/standards corpora stay thin (identity + one procedure gap)
- «bruk …» / «utvid med fil.pdf» → ``install_focus_sources`` (any user-named
  needle from *that* index — no vendor hardcoding)
- Focus allowlist is exclusive (no strategy/BoD fallback when a name is locked)

## 0.96.0 — Installation manual: system gate + install lexicon
- Require ``system_under_install`` (tray/sensor/machine/enclosure/other) before plan
- Deterministic install file map; downrank BoD/market/persona sources
- Identity table allowlist: engineering fields only
- No procedure chunks → one explicit MANGLER on sequence (no hollow shells)
- Kilderegister = cited files only; unused high-value PDFs offered to expand
- ``sequence`` intent = ``instruct_procedure`` (was mis-resolved to describe)

## 0.95.0 — Wire foldok_index watermarks (WO 0.65 T3)
- **Bug:** `context_for_update` / `new_since` / `set_watermark` existed in
  `foldok_index` but nothing outside that package called them — “update with
  new files” stayed a silent semantic miss
- Bridge `foldok_index_bridge`: sync `.foldok_index/index.db` on reindex
- `diff_index` + `update_document_from_sources` call `context_for_update`
- Generate + update set document watermarks (`doc:{template_stem}`)
- Honest “nothing new” (and unreadable files) from the manifest, not a search

## 0.94.0 — foldok_scan 0.91 (explain silent index drops)
- Vendored **foldok_scan 0.91**: `scan()`, depth/reason report, `biggest_win`,
  `widened_doc_ext()` (advisory — not auto-applied)
- Prescan attaches coverage: `coverage`, `by_reason`, `by_depth`, `coverage_text`
- Decision card + Hurtigscan UI show why `.doc`/`.xls`/`.msg` etc. were dropped
- Chat: “hvorfor er ikke filene indeksert?” → zero-token coverage reply
- Does **not** widen `DOC_EXT`; product must opt in to legacy formats

## 0.93.0 — NarrativeBlueprint (Document Brain)
- **NarrativeBlueprint** persisted on the document: thesis, main_argument,
  reader_should_leave_with, arc steps with purposes
- Author receives `previous_summary` + bridge openings between sections
- Critic: section-serves-main_argument + citation repetition (≥4×)
- Expand-chip helper `propose_arc_expansion` (user-confirmed arc step)
- Lead remains arc step `frame` via Lead Generator
- Regression: blueprint on compose; continuity bridges in body

## 0.92.0 — Lead Generator (Innledning)
- Dedicated **Lead Generator** (`foldok_ask/lead.py`): sketch → overview retrieve →
  rerank → ground → write → verify for the document opening
- ~½ page framing: corpus character, working thesis, roadmap, honest limits
- File count is a footnote only; ban abstract-paste and SKU noise in the lead
- Controls: `lead_depth` short/standard/rich, `max_claims`, `prefer_paraphrase`
- Critic warns on thin leads (<100 words) and abstract paste
- Regression: lead ≥120 words with kildebibliotek / thesis / limits signals

## 0.91.0 — foldok_claims 0.88 (claims in retrieve)
- Vendored **foldok_claims 0.88** with `integrate.py`: claims_from_index, as_chunks,
  standards_register, coherence_section, ranking patch
- Retrieve injects ``kind=claim`` chunks; claims outrank captions
- Standards register from *rule* claims (not character windows around names)
- Cable-class sections can name Klasse 1A/1B — not Marco abstracts
- Regression: claim chunks present; kabelklasser names a class

## 0.90.0 — Engineering story (Narrative → Author → Evidence)
- **Narrative layer** (`narrative.py`): DocumentIntent + thesis + arc + section purposes
- Author writes **to purpose**; consumes **short claims**, paraphrases (NO) — not PDF abstracts
- One body cite per file; purpose fidelity gate (classes/zones → gap if only brochure blurbs)
- Standards: clean id — role table; drop ISO-quality / truncated garbage roles
- Honest **Åpne punkter** when thesis promised zones/classes but retrieve did not deliver
- Lead = thesis-led framing; file count footnote; lightweight Document Critic
- Fix: `showToast` defined in workbench (export no longer throws)
- Regression: no abstract salad; no findings-table body; standards roles clean

## 0.86.0 — Document-first topic brief (planner + author)
- **Document Planner** outlines from intent + corpus sketch (what to teach), not fact-key inventory
- **Technical Author** writes framing lead + section prose with `[n]` cites; **no findings-table body**
- **Standards** as `id — role` + cite; sources as appendix; gaps short and honest
- File count is a footnote — opening paragraph orients the human
- Regression: opening ≠ only “N indekserte filer”; standards ≠ bare `.pdf` names; no `Påstand | Verdi | Kilde`

## 0.85.0 — Ask understanding (prose, not claim tables)
- Retrieve → **answer-relevance rerank** → drop weak / install-clearance hijacks
- Synthesize short **cited prose** from top chunks; tables only if a structured list is in sources
- Omfang from file count + tags — **never MANGLER** when index is non-empty
- Regression: “kabelklasser” does not lead with tray-to-ceiling 300 mm; omfang = 2 sentences for 54 files

## 0.84.0 — Ask the project (question-driven briefs)
- New `foldok_ask`: Question → retrieve chunks → ground → AuthoringEngine → verify → Answer
- `topic_brief` is now a **thin shell** over ask results (omfang, temasvar, gaps, kilderegister) — **no EMC facet section engine**
- Suggested questions are retrieval probes from tags/filenames, not schema keys
- APIs: `POST /api/ask`, `POST /api/ask/suggest`; chat extras use grounded ask for topic questions
- Regression: “kabelklasser” hits cable-class chunks, not Faraday brochure by default; empty retrieve → gap, not essay

## 0.83.0 — Topic brief (cited packs) + corpus router
- **North star:** default output for EMC/spec libraries is a **cited topic brief**, not a hollow research report
- New template `topic_brief` — zones, cable classes, earthing, standards register, gaps, sources
- Facet retrieval (`topic_brief_compile.py`) + AuthoringEngine per section; MANGLER only when facet silent
- Corpus router: `classify_corpus` → `spec_library | lab_campaign | research_lab | install_job | general`
- Generate guard: `research_project_report` on spec libraries without lab keys → auto-switch to `topic_brief`
- Suggestions / Checkpoint A chips: Temabrief + Spec coherence primary; research secondary
- Research Metode hard-stop unchanged (body &lt; 500 chars, no fact walls)
- Regression: EMC-like index → zones/class structure or gap; never phones; classify EMC as spec_library

## 0.82.0 — Shredder + console + local learning
- Vendored `foldok_learn` — Tier 1 local lessons; standards → citations only (never clause text)
- Vendored `foldok_console` — operator snapshot + ranked decision queue; failure-tolerant probes
- New `foldok_shred` — document intake: read → measure → propose → **drop text** → return
- `Shred` has no body-text field; `source_id` is content hash (filename never stored)
- Grades: `sample`/`ours` measure only; `exemplary` offers skeleton/design/obligation proposals
- Console `probe_shred` maps bay proposals into the decision queue (never auto-applied)
- Regression: fixture body phrases must not appear in `to_dict()` / proposal JSON
- Package tests: learn + console + shred green

## 0.81.0 — Get Capture widget (foldok_getapp)
- Vendored `foldok_getapp` — header control for installing the Capture app (QR on desktop, direct install on Android, honest iOS line)
- Inline SVG QR at build time (`segno`); no third-party requests on page load
- QR points at `https://foldok.com/capture` — durable landing page; distribution can change without invalidating printed codes
- `public/capture.html` — platform-aware install landing (Android APK sideload, iOS coming, desktop hint)
- 23 package tests green

## 0.78.0 — Capture bridge (foldok_capture)
- Vendored `foldok_capture` for Capture app folder-bridge integration (`.foldok/capture_tasks.json`, `binding.json`, `*.foldok.json` sidecars)
- Includes desktop publish/ingest flow: no guessing, checksum verification, idempotent gap closure
- Privacy defaults preserved (`may_leave: false`, location optional); ingest reports unlinked/missing/tampered evidence
- 24 package tests green

## 0.77.0 — Signals package (content-free telemetry)
- Vendored `foldok_signals` — strict event vocabulary (counters + fixed codes only), no free-text fields
- Local-first consent flow: always record locally; consent gates sending; revoke purges log + install id
- Funnel and refusal analytics for actionable drop-off diagnosis without content leakage
- Feedback preview + export safety boundaries aligned with `foldok_private`
- 32 package tests green

## 0.76.0 — Private calls hardened (policy + at-rest)
- Updated `foldok_private` — Policy returns renderable `Decision` (allowed / needs_approval / blocked)
- Findings language flagged for human judgement (masking ≠ findings protection)
- Token repair for mangled model tokens; Fernet encryption at rest; export denylist for vaults
- STRICT / OPEN / OFFLINE presets; 48 package tests green

## 0.75.0 — Private calls (foldok_private)
- Vendored `foldok_private` — model works on masked text; EntityVault holds ground truth locally
- Leak guard refuses any payload that still contains known real values
- Audit log is content-free (purpose, model, bytes, entity count, hash, outcome)
- Images blocked by default; enterprise = transport swap only
- 32 package tests green

## 0.74.0 — Asset library + vision landing (local install)
- Vendored `foldok_assets` — one index over registries (127 assets / 11 kinds); seal() blocks unshippable packs
- Landing §1 rewritten to PRODUCT_VISION: documentation OS; **this site is marketing** — install local workbench
- Static HTML shell + CTAs point to GitHub Releases
- Flow: Install locally → connect folder → documentation & deliver

## 0.73.0 — Document box editor (foldok_boxes)
- Vendored `foldok_boxes` — 12-col grid layout, pins (user > template > engine)
- Demo: `/boxes-demo.html` · APIs `/api/layout/session`, `/api/layout/session/intent`
- Workbench Tools → Layout opens box editor reference
- Account panel: fix first-open on marketing/Vercel (forceOpen); marketing stubs for guest/demo
- `public/index.html` synced from workbench UI

## 0.72.0 — Diagram Studio + foldok_diagram integration
- **Diagram Studio** (`web/diagram.html`) — edit wiring/piping fixtures; save to project; insert into document sections
- `foldok_diagram` — pins-not-geometry engine, validation, jurisdiction gate on export
- APIs: `/api/diagram/*`, bind-project, insert-into-doc, persist graph + pins JSONL
- Workbench Tools → Diagrammer opens studio with active project context
- `diagram_document.py` — bridge diagrams into workbench markdown + SVG blocks
- Golden SVG tests: `scripts/test_foldok_golden_svg.py`
- Editor helpers: `move_component`, `connect_ports`, `refresh`, port-snap preview
- `PRODUCT_VISION.md` v1.3 — documentation OS north star
- `docs/prd/` — surface PRDs at 0.72.0

## 0.71.0 — Material + Section + Calculation YAML schema
- Nested packs: `materials/steel|gfrp`, `sections/steel`, `calculations/steel|gfrp`
- Schema docs: `schema_core`, `_material_schema`, `_section_schema`, `_calculation_schema`
- Quantity fields: value/unit/source/status; multi-statement `formula_code`
- Steel MVP unfactored checks; GFRP `Xt` datasheet template
- Alias ids: `steel_axial_tension` → `steel_axial_tension_simple`, etc.
- Spec: `MATERIALS_SPEC.md` rewritten to match shipped YAML

## 0.70.0 — Materials knowledge (steel + GFRP) for design reports
- `registry/materials/` — S235–S460 grades; GFRP datasheet template
- `registry/sections/steel_open.yaml` — IPE/HEA/RHS subset
- `materials_engine.py` — bind properties → calculation inputs
- Checks: `steel_axial_tension`, `steel_bending_simple`, `gfrp_tension_simple`
- `MaterialBlock` + calc `binding`; APIs `/api/materials/*`, `/api/sections/*`
- Spec: `MATERIALS_SPEC.md` — groundwork only, no code-compliance claim
- Tests: `scripts/test_materials_engine.py`

## 0.69.0 — Calculation Engine (library formulas + confirm)
- `registry/calculations/` — 8 curated profiles (area, cable, Ohm, power, wind q, …)
- `local_app/calculation_engine.py` — safe eval, fact bind, unit convert, confirm
- State: `draft | needs_input | ready_for_review | confirmed`
- `CalculationBlock` + HTML render; APIs `/api/calculations/*`
- Spec: `CALCULATION_SPEC.md` (not certified design; user owns the number)
- Tests: `scripts/test_calculation_engine.py`

## 0.68.0 — Claim boundary: structural profiles, not legal compliance
- `COMPLIANCE_POLICY.md` — canonical “what we don’t claim”
- `compliance_engine`: `DISCLAIMER`, `package_status`, `legal_claim: false` on gaps
- APIs `/api/compliance/*` return disclaimer + `legal_compliance_claimed: false`
- Marketing/UI: evidence packages / ready-for-review language (no “NEK compliant”)
- Tests: coverage math + forbidden claim labels

## 0.67.0 — Diagram canvas (graph editor + engine preview)
- `DiagramCanvasEditor` / `DiagramDocument` — place/move/rotate/connect/delete
- Manual layout: user positions; engine orthogonal-routes edges only
- Hit-test overlay (ports > components > connections) for SVG-in-canvas
- `figure_payload()` for DiagramBlock / document sync
- Hard rule: no freehand ink; AI does not own geometry
- Tests: `scripts/test_canvas_editor.py`

## 0.66.0 — DiagramStyle (DesignSystem tokens for 2D SVG)
- `artifact_engine/diagram_style.yaml` + `DiagramStyle` dataclass
- `diagram_engine/paint.py` — layout paints from tokens only
- Profiles share strokes/colors/labels; `data-diagram-style` on SVG
- `DesignSystem.diagram_style_id` + `DiagramBlock.style_id`
- Golden hash test: `scripts/test_diagram_style.py`

## 0.65.0 — Figure pipeline (2D, not Visoid)
- Position: deterministic engineering SVG only — no photoreal path for core docs
- `DiagramBlock`: figure_number, source_citation, diagram_type, revision, graph_id
- `propose_diagram` / `confirm_diagram` + templates (panel_sld, pump_skid, …)
- `visual_qa_svg` print checklist (stroke, legend, labels, collisions)
- HTML: “Figure N — caption” + citation meta
- Spec: `DIAGRAM_SPEC.md` Visoid vs Foldok + 90-day status

## 0.64.0 — One DiagramEngine, three domains
- Shared `graph.py` normalize (Component / Port / Connection) for all domains
- Piping schematic + P&ID-style profile (`piping.py`); media/DN legend (`schema/media.yaml`)
- Mechanical arrangement + hybrid skid lanes (`mechanical.py`)
- Symbol adds: `drain`, `vent`, `belt_drive`
- Fixtures: `piping` | `pid` | `mechanical` | `hybrid` (+ electrical)
- Tests: `scripts/test_domain_diagrams.py`

## 0.63.0 — Electrical SLD + wiring diagrams
- `diagram_engine/symbols/electrical/` — 21 IEC-style SVG symbols with terminal metadata
- Graph schema: terminals alias, wire `color` / designation / cable_ref
- `electrical.py`: orthogonal **single_line** + **wiring** SVG + auto wire-color legend
- Fixtures: `electrical_sld` / `electrical_wiring`; `DiagramEngine.render_electrical()`
- Tests: `scripts/test_electrical_diagrams.py`

## 0.62.0 — Foldok brand, English landing, compliance Phase 1
- Brand: **Foldok** throughout; English hub landing + `public/` marketing page
- Compliance Phase 1: framework profiles + evidence gaps + expanded document types
- Diagram: shared graph schema + 20 piping/mechanical symbols
- Deploy: `DEPLOY.md`, `vercel.json`, release zip `foldok-engine-v0.62.0.zip`

## 0.61.0 — Create from chat, output formats, zero-token sketch
- Path B money round follow-up: folder-less projects + memory state until mappe is chosen.
- «+ Nytt» format row (PDF/HTML/PPTX/DOCX); errors never silent; opens Tools on success.
- Hub «lag en installasjonsmanual» creates document immediately (no invented folder).
- Sketch geometry via `/api/doc/sketch/upsert|move|delete` — zero tokens asserted.
- PPTX/DOCX/HTML exporters from the same content; table split notices on slides.
- Regression test 69. Suite = 69.

## 0.60.0 — Account, credits, payment status (Path B)
- Architecture: local-first + Foldok metering proxy (files never leave the machine).
- Hamburger account: magic-link stub, guest trial, Konto/Saldo/Forbruk/Dokumenter/Firma.
- €2 free credit; top-up stub; auto-refill opt-in; AI = cost×margin; zero-token = €0.
- Export €9/€19/€49 against balance; paid re-export free; UTKAST watermark when unpaid.
- Document status chips: Utkast / N mangler / Klar for eksport / Betalt / Rev B–utkast.
- Proxy log: tokens + job types only. Regression test 68. Suite = 68.

## 0.59.0 — «+ Nytt» creates a document + sketch canvas
- Documents rail picker: recommendations, Tomt dokument (skisse), catalog, import.
- `POST /api/doc/create` always opens a shell; Tools pane; no toast / no chat gate.
- Sketch mode: A4 canvas, block tools, geometry recognition, zero-token fill.
- `origin: sketched` under Dine maler; export blocked on unlabelled placeholders.
- Annot insert unified with sketch. Regression test 67. Suite = 67.

## 0.55.0 — Pre-scan, chunked index, cancel / heartbeat / budget
- `index_prescan.scan_folders`: filesystem-only ScanReport (cost/time ranges,
  by_ext, by_folder, oversize, no_extractor) — zero tokens.
- Decision card when indexable > 200: all / subfolders / documents / newest 500.
- Chunked index (100 files): cancel between files/chunks; keep work so far.
- `POST /api/index/cancel`, `/heartbeat`, `/resume`, `/prescan`.
- Heartbeat: no client ping for 60 s → pause (closed-window must not keep spending).
- Default `index_budget_eur` €10 → pause at ceiling with Fortsett +€10.
- UI: Stopp indeksering on progress; Fortsett after cancel/pause.
- D1/D2: skip >25 MB; PDF >200 pages → first 60 (partial). JOBS/LOCK fixed.
- Tests: `scripts/test_index_prescan.py`. See `WORKORDER_0.55.md`.

## 0.54.1 — Figure relevance pool + curated template intent
- `ensure_min_figures`: widen candidate pool to full index; caption/tag
  relevance scoring (fixes mapper-starved wrong photo, e.g. boat vs install).
- `/api/template/intent`: call `match_curated_template` before Haiku
  (installasjonsmanual → `installation_manual`, not technical_doc_package).
- Broader install-manual regex + project-chat `wantsTemplateFromChat` trigger.
- See `PATCH_0.54.md`. Regression `test_64` (relevance) + `test_66`.

## 0.54.0 — Industrial report blocks + design tokens
- New AST blocks: `EvaluationMatrix`, `StakeholderCard`, `ComparisonTable`,
  `Rating`; enhanced `CalloutBox` (`insight`/`quote`, attribution, icon).
- `FeatureGrid` accepts `StakeholderCard` / rated summary cards.
- DesignSystem: print spacing scale (`space_2xl`, `space_section`), card and
  rating tokens; theme `industrial_report`.
- Composition profile `INDUSTRIAL_REPORT_PROFILE` + registry type
  `industrial_report.yaml` (decision / compliance / evaluation packs).
- Regression `test_65`; registry now lists seven document types.

## 0.53.1 — Figures default-on + privacy gate widened
- `ensure_min_figures`: default-on when a section has mapped visual files
  (unless `no_figures`, boilerplate, or register/declaration/signature).
- Legacy `generate_section` code-compiled branches now call
  `place_section_figures` (same as the structured path; server still uses legacy).
- Scrubbed real address from `skills/core/form-filler/SKILL.md` and
  `FLOW_ONE_OPERATION.md`; anonymised historical CHANGELOG / workorder names.
- Release privacy grep now covers `skills/`, `registry/`, engines, tools, and
  all root `*.md` (0.19 §4 was code-path-only and missed shipped docs).

## 0.53.0 — Location + OSM site maps
- Extended `project_findings.xlsx` with location columns (address, municipality,
  coordinates, map_image_path, map_style, …).
- `HybridKnowledgeEngine`: `get_location`, `set_location`, `generate_location_map`,
  `propose_location_map` → ImageBlock proposal (confirm required).
- `tools/osm_vector_tiles/`: tile stitch backend + geocode; optional
  `custom_vector_renderer.py` drop-in for full vector-tile generator.
- Skill `location-map`; tools in ENGINE_TOOLS v0.6; HTTP `/api/knowledge/*-map`.
- Example: `examples/location_map_section_example.md`.

## 0.52.0 — Hybrid Knowledge Engine
- `hybrid_knowledge_engine.py`: project-local `project_findings.xlsx` (editable
  source of truth) + optional `.foldok_index/` LanceDB cache.
- Tools: `knowledge_index_project`, `knowledge_get_findings`,
  `knowledge_update_finding`, `knowledge_semantic_search`,
  `knowledge_rebuild_index`, `knowledge_import_index_facts`.
- Skill `hybrid-knowledge`; HTTP `/api/knowledge/*`; chat intents.
- Excel path requires `pandas` + `openpyxl`; LanceDB / sentence-transformers optional
  (semantic search falls back to text match).
- Findings never leave the project folder. Suite tests: `test_hybrid_knowledge.py`.

## 0.51.0 — Document Type Registry
- `registry/document-types/` brain: user_manual, datasheet, installation_guide,
  maintenance_manual, samsvarserklaring, inspection_report (YAML).
- Tools: `list_document_types`, `get_document_type`, `materialise_template`
  (`local_app/document_type_registry.py`). HTTP `/api/registry/*`.
- Skill `document-type-router`; compose path looks up registry then materialises.
- Skills + `ENGINE_TOOLS` v0.4, `ONE_AGENT_SPEC`, `AGENT_TEAM_SPEC`,
  `skills/README` rebuilt to prefer registry over hard-coded structure.
- Dependency: `pyyaml>=6.0`. Tests: `scripts/test_document_type_registry.py`.

## 0.50.0 — Incremental index tools + editor sticky chat
- **ENGINE_TOOLS:** `reindex`, `diff_index`, `update_document_from_sources`
  with exact contracts; agent prefers this path when new technical files appear
  (merge into living Document AST — do not spin a new document by default).
- Index manifest (`.foldok_index_manifest.json`) + `index_version`; confirm
  gate when delta > 15 files. HTTP: `/api/reindex`, `/api/diff-index`,
  `/api/doc/update-from-sources`. Chat intents NO/EN.
- `local_app/index_tools.py` + `scripts/test_index_tools.py`.
- Editor: Kilder + Assistent sticky while document scrolls; side Assistent is
  the live one-agent surface when a document is open (same conversation).
- KILDER: always-available “Scan for nye filer”; UI scan sends `confirm=true`.
- Specs: `ENGINE_TOOLS.md` v0.3, `ONE_AGENT_SPEC` action surface, ingest skill.

## 0.49.0 — Call contracts + editorial layer
- Every model call: shape + validator + deterministic fallback (`call_contracts.py`).
- Section pipeline: select → partition → prose → table (code) → figures → layout.
- `editorial_layer.py`: B1 column vocab, numbered figures + illustration index,
  title page/TOC/revision/glossary, cross-refs; assemble_draft uses furniture.
- LayoutTree running header/footer; TOC page numbers; caption 7.5pt (AKVA).
- ENGINE_CONTRACT §4 amended. Regression test 63. Suite = 63.

## 0.48.0 — Document quality: facts, tables, figures, one-click
- Two-tier section facts (PRIMARY + AVAILABLE ≤120); missing only if absent from both.
- Enforce writing_rules.structure (table/list/checklist) with retry + generic table builder.
- `{{fig:filename}}` → figure blocks; code fallback when `min_photos > 0`.
- One-click chips (verb + €) and agreement card → generate; scroll to doc + gaps.
- `postprocess` keeps markdown newlines (tables no longer flattened).
- Regression test 62. Suite = 62.

## 0.47.0 — User-manual profile: no MANGLER in prose + forced blocks
- `USER_MANUAL_PROFILE` enforces industrial manual section order
  (incl. troubleshooting; `technical_specs` slot).
- Strip `[MANGLER: …]` from prose; collect into final
  “Information Still Required” EngineeringTable.
- Force block types: specs/glossary → tables; assembly/operation/…
  → Procedure; symbols → CalloutBox; revision → RevisionHistory.
- `document_type` accepts `brukermanual`. Suite = 61.

## 0.46.0 — User-manual Document AST
- `TableOfContentsBlock` auto-filled from section titles on compose.
- `CalloutBox(variant="requirement")` for safety-symbol legends.
- `document_type=user_manual` composition order: legal → symbols →
  summary → glossary → TOC → product → specs → assembly → …
- Theme `manual` (+ `akva` alias → same neutral tokens; no customer brand).
- Fixture `demo_rotor_spreader_manual()` (DemoTek).
- Regression test 60. Suite = 60.

## 0.45.0 — Print-first publishing (DesignSystem + LayoutTree)
- `DesignSystem` is the shared visual source of truth (pt, A4, grid).
- New blocks: `ParameterGrid`, `EngineeringTable`, `RevisionHistory`,
  `DrawingReference`; `FeatureCard.metric`.
- `LayoutTree` / `LayoutNode` / `LayoutPage` — absolute print placement.
- `PrintLayoutEngine` → LayoutTree; HTMLRenderer paints positions only
  (default path is paginated absolute; `flow=True` keeps legacy CSS flow).
- ArtifactEngine / FormEngine / DocumentEngine share this pipeline.
- Regression test 59. Suite = 59.

## 0.44.0 — Full compose → measure → layout → paint pipeline
- MeasurementEngine refined (professional heights); LayoutEngine always
  delegates measure/space_after.
- CompositionEngine priority buckets (overview → diagram → features →
  specs → procedure → bom → form → other); form path unchanged.
- `ArtifactEngine` is the central pipeline; `render_document` /
  `layout_document` / `render_pdf` default `compose=True` via `get_engine`.
- DocumentEngine HTML uses `get_engine(...).render_document_html` (compose on).
- Regression test 58. Suite = 58.

## 0.43.0 — Composition + Measurement + diagram embed
- `CompositionEngine` — composition-first region order (hero → overview →
  diagrams → specs → body); form-aware (legend → fields → sign-off).
- `MeasurementEngine` — shared height estimates; LayoutEngine delegates.
- `DiagramBlock` + `embed_diagram_engine()` — DiagramEngine SVG into docs.
- FormEngine artifact path runs CompositionEngine; ArtifactEngine
  `compose_document` / optional compose on render.
- Regression test 57. Suite = 57.

## 0.42.0 — Layered (Sugiyama) graph layout for diagrams
- `artifact_engine.layout.graph.LayeredGraphLayout` — longest-path ranks +
  barycenter ordering; TB/LR; deterministic.
- DiagramEngine SVG positions via layered layout (`data-graph="layered"`);
  provenance colors, pins, Kanter legend unchanged.
- `orientation=` / `set_orientation("TB"|"LR")`; process defaults TB, else LR.
- Docs: README engines section + `artifact_engine/` / `diagram_engine/` /
  `form_engine/` ARCHITECTURE.md refreshed for 0.42.
- Regression test 56. Suite = 56.
- Release zip: `releases/foldok-engine-v0.42.0.zip`.

## 0.41.0 — Layout accuracy + DiagramEngine ↔ ArtifactEngine
- Layout: content-aware `_measure`, smarter `_should_break`, multi-column
  height for FeatureGrid/FormSection (single placed container for HTML).
- DiagramEngine: `theme=` / `get_engine()`, sheet tokens from Theme;
  provenance colors unchanged; `render_html()` / `render_pdf()` via shared PDF.
- `PDFRenderer.render_html_string()` for non-Document HTML.
- Regression test 55. Suite = 55.

## 0.40.0 — FormEngine consumes ArtifactEngine
- Form blocks: FormSection, FormField, SignatureBlock, RatingLegend.
- FormEngine builds Document AST → shared layout/typography/PDF via
  `get_engine()`; modes: overlay | structure | hybrid | **artifact**.
- `render_html()` / `render_pdf()` / `to_document()`; ratings still never
  auto-filled; print HTML never stamps `[MANGLER]`.
- Regression test 54. Suite = 54.

## 0.39.0 — Artifact PDF + pro blocks + shared core
- **PDF:** `PDFRenderer` — WeasyPrint first, Playwright fallback;
  `render_pdf()` / `pdf_backends_available()`.
- **Blocks:** Procedure, Timeline, BOM, ProcessFlow, Warning, Note,
  TechnicalData (+ dict deserialize + layout measures).
- **Core:** `ArtifactEngine` / `get_engine()` shared facade for future
  FormEngine / DiagramEngine reuse of theme + layout + PDF.
- Regression test 53. Suite = 53.

## 0.38.0 — Artifact layout + pagination
- **`artifact_engine/layout`:** `Grid` (pt, baseline snap), `Spacing`,
  `LayoutConstraints`, `LayoutEngine` / `LayoutResult` / `PlacedBlock`.
- `flatten_document` + forced `PageBreak` from section flags.
- HTML renderer: `paginate=True` → absolute placed pages (theme-driven).
- `layout_document()` public helper. Regression test 52. Suite = 52.

## 0.37.0 — Artifact Composition Engine
- **`artifact_engine/`:** Document AST (hero, sections, blocks) → deterministic
  HTML. Themes `engineering` / `datasheet` own all visual decisions.
- Rule: LLM proposes structure only; code draws (same contract as diagrams).
- Bridge: `document_from_pages` + DocumentEngine HTML prefers AST render.
- Demo fixture synthetic (Demo CCS / DemoTek). Self-test:
  `python -m artifact_engine`. Regression test 51. Suite = 51.

## 0.36.0 — Document Engine (datasheets / manuals HTML)
- **`document_engine/` package:** page templates (cover / overview / specs)
  → print HTML; `{{placeholders}}` from artifact + facts.
- Unresolved slots stay **blank** in HTML (no invented prose); optional
  missing marker for markdown only. Demo fixture is synthetic (DemoTek),
  not a real customer brand.
- Bridge: `load_from_foldok_sections` for section-based templates.
- Self-test: `python -m document_engine`. Regression test 50. Suite = 50.

## 0.35.3 — Form fill example + layout_extract re-export
- Root `layout_extract.py` re-export for `from layout_extract import …`.
- `examples/fill_form_from_pdf.py` runnable demo; README usage snippet.
- Suite still 49 tests.

## 0.35.2 — FormEngine v3 API (facade)
- `FormEngine`: `set_mode` (overlay|structure|hybrid), `set_backgrounds`,
  `set_layout_from_extract`, `fallback_keys`, `format_string`, conditions.
- `Field` dataclass exported; print HTML still uses real overlay/structure
  renderers (not stub CSS). `[MANGLER]` only in markdown gaps, never print.
- Regression test 49. Suite = 49 tests.

## 0.35.1 — Native PDF layout extract
- `form_engine/pdf_layout.py`: PyMuPDF text spans + AcroForm widgets →
  normalized 0–1000 field bboxes (your sketch, wired into FormPackage).
- Ingest attaches `pdf_native`; `extract_layout` prefers it (0 tokens)
  before vision / offline grid.
- `extract_form_layout` / `fields_from_pdf_layout` exported.
- Regression test 48. Suite = 48 tests.

## 0.35.0 — Diagram Engine v2 (intent + layout)
- **`diagram_engine/` package:** `intent` → `layout` → deterministic SVG;
  provenance colors unchanged (0.24/0.26 contract).
- Layout kinds: `wiring` | `power` | `signal` | `process` | `star` | `overview`.
- **`DiagramEngine` OO facade** over the real renderer (connections + pins;
  not a node-only stub).
- Self-test: `python -m diagram_engine`. Regression test 47. Suite = 47.

## 0.34.1 — FormEngine class facade
- `FormEngine` OO API (`load_template` / `load_upload` / `set_artifact_model` /
  `set_project_facts` / `render`) over the v2 overlay+structure pipeline.
- Does **not** invent addresses or stamp `[MANGLER]` into HTML — empty
  slots stay blank; gap ledger unchanged.
- Regression test 46. Suite = 46 tests.

## 0.34.0 — Form Engine v2 (faithful overlay)
- **Architecture:** `form_engine/` package — ingest → layout extract →
  fill → overlay render (original page + positioned fields). Structure
  mode keeps the v1 letter sheet when no backgrounds exist.
- **Fidelity rule:** fill content from facts; never redesign the user's
  paper unless asked. Ratings still never AI-suggested.
- **Import:** `/api/chat/attach/import-template` uses package ingest +
  layout extract; templates store `form_package` (backgrounds + bboxes).
- **Export:** `export_form_html` chooses overlay vs structure from
  `layout_mode` / `form_package`.
- Smart defaults hook stub (`smart_defaults.py`); Diagram Engine v2
  design-only in `form_engine/ARCHITECTURE.md`.
- Regression test 45. Suite = 45 tests. Self-test: `python -m form_engine`.

## 0.33.0 — Ja-dispatch, currency gate, recreate-form
- **0.25 §B:** any `chat_pending` + affirmative (`ja`) → server-side
  `dispatch_pending` in the same turn; model never re-asks.
- **0.22/0.25 receipts:** progress claims still need `job_id` (unchanged).
- **0.23 §A2:** editor chat runs money validator; €0.18/€0.24 style
  drift rejected unless a tool receipt allows the amount.
- **0.29 recreate-form:** «recreate this form» / multipoint →
  `toyota_multipoint` template + document + HTML — never a `.txt`.
  Model «Skal jeg…?» about forms sets pending `recreate_form`.
- Templates: `templates/toyota_multipoint.json` (+ root copy).
- Regression tests 42–44. Suite = 44 tests.

## 0.32.1 — Form HTML screen layout (letter sheet)
- Fixed **8.5in** centered page on grey backdrop (no fluid sprawl).
- Measure cells **inline after label** (not right-flung).
- Page grid uses `column-count` + `column-fill:balance` +
  `break-inside:avoid`; side labels **16px**.
- Extra field types for denser paper originals: `vin_boxes`,
  `header_grid`, `wedge_chart`, `vehicle_diagram`, etc.
- Preview: `/toyota_multipoint.html` via workbench web/.

## 0.32.0 — Print-faithful form HTML (WORKORDER_0.29 §D)
- **`form_engine.py`:** form_fill JSON → deterministic print HTML (rating
  boxes, measure lines, cited chips, company logo). Toyota multipoint
  fixture self-test.
- **Export:** form_fill writes `Rapporter/<name>.html` beside `.md` on
  generate and `/api/export` (`export_html` in response).
- Bridge: `build_form_doc` / `export_form_html` from template + doc state.
- Regression test 41. Suite = 41 tests.

## 0.31.0 — Progress receipts visible; skjema.jpg → mal
- **Receipt validator (0.25 C / 0.22 B):** any reply with starter / kjører /
  skriver nå / klar om needs a job-start `job_id` in the same turn, or the
  reply is rejected. Tool-name-only receipts no longer count for progress.
  Capability prose («Indeksering kjører med…») excluded.
- **Progress UI (NAVIGATION_SPEC):** `pollJob` shows job id · step counter ·
  ETA for generate/index and chat-started jobs; import shows elapsed after 3s.
- **Malimport images:** `*skjema*.jpg` classifies as form_template; chat
  «create … as a template» → one offer → review → owned template. Vision OCR
  on image import.
- Regression: test_23 extended; test_40. Suite = 40 tests.

## 0.30.0 — Form-fill documents + malimport (WORKORDER_0.29 / 0.30)
- **0.29 Form-fill:** `document_species: form_fill`, `form_section` fields
  (rating3/check/measure/text/date/signature). Prefill from index; ratings
  never auto-fill. Zero Sonnet. System template `inspection_checklist`.
  Filled measures become project facts. Interactive form UI + MD export.
- **0.30 Malimport:** form-shaped drop → one offer with field summary →
  `extract_form_structure` (cached) → review screen → owned template
  (`origin: imported`). Same form_fill schema as 0.29.
- migration_009 adds `form_section` block type.
- Regression tests 37–39. Suite = 39 tests.

## 0.28.0 — Conversation isolation, PDF depth, brukermanual intent
- **Conversation (BUGFIX_0.19 §A extended):** turns stamped with
  `project_id`; chat context and API payloads filter foreign turns.
  Regression: alternating A/B conversation markers must not cross.
- **PDF extraction depth:** per-page `chars_per_page` / `facts_per_page`
  instrumentation; vision fallback for pages under 80 chars (scanned
  technical manuals). Stats stored on index cache entries.
- **Template intent:** new `user_manual` (Brukermanual) template;
  «brukermanual» / «bruksanvisning» map to it — never silently to
  `technical_doc_package`.
- Regression tests 34–36. Suite = 36 tests.

## 0.27.0 — Rung-3 templates, prescriptive prose, layout via chat (WORKORDER_0.27)
- **A** `draft_template` flow live: structure card + [Bruk denne] → save
  owned template + document shell + € generate offer; `origin: ai_drafted`.
- **B** Prescriptive compile: sequence banner, author placeholders,
  `supplier_manual_gaps` table from [MANGLER]; curated `installation_manual`.
- **C** Layout tools (`move_section`, `add_section`, `toggle_section`,
  `set_block_layout`) — versioned, zero-token, no regeneration; save-as-template
  offer after 3 structural edits.
- **D** Shipped `templates/installation_manual.json`; hub alias matching.
- Regression E1–E5 (tests 29–33). Suite = 33 tests.

## 0.26.0 — Chat references artifacts; diagram_engine sole renderer (WORKORDER_0.26)
- **A** Chat may not contain `<svg`/`<html`/markdown tables/fenced code
  (unless code asked) or >5-item intake lists; validator + one retry.
- **B/C** Tools create the artifact; reply is ≤3 lines naming what/where.
  `create_diagram`, `write_checklist` land SVG / SJEKKLISTE.txt on disk.
- **D** `diagram_engine.py` is the only SVG renderer (multiline labels);
  fixtures: ExcavatorBrain wiring + renseanlegg process flow. Confirm
  rows are plain text (not markdown tables).
- Regression E23–E26 (tests 25–28). Suite = 28 tests.

## 0.25.0 — System events, «ja» dispatch, no fictional jobs (WORKORDER_0.25)
- **A** Hub/project system events join conversation history (file added,
  indexed caption, project created, job started). Cold-start drops ack
  from extraction; gap-match only when a project has open gaps.
- **B** Confirm questions store `pending_action`; affirmative (ja/yes/…)
  dispatches the tool in the same turn — no re-ask. One confirm max.
- **C** Progress verbs («starter», «klar om») need a real job-id receipt.
- **D/E** Indexed answers quote extraction; CTAs bind to the offer
  (`Opprett prosjekt →`, never mismatched tom-mappe default).
- Regression F19–F22 (suite tests 21–24) gate release.

## 0.24.0 — Connection spec + code-rendered block diagram (WORKORDER_0.24)
- **A** `connection_spec` block: components + edges with provenance
  (extracted / verified_by_user / reference). Propose → confirm table →
  save. Free-text «schematic / how connected» triggers the flow (EN/NO).
- **B** `render_block_diagram(spec)` — deterministic layered SVG (amber
  dashed = reference). Circuit-schematic asks get an honest boundary.
- **C** Regression C16–C18. migration_008 adds `connection_spec` enum.

## 0.23.0 — Pricing truth, legal phrasing, synthetic demos (WORKORDER_0.23)
- **A** `pricing` block in capabilities.json; € claims must match manifest
  (index €0.001–0.01/file; export €9/€19/€49). Validator + retry on hub.
- **B** Forbidden legal phrases (evidence handling, chain of custody, …);
  approved `legal_framing`; cannot-list: juridisk vurdering / beviskjede /
  utforme juridisk tekst. One-direction openers (no «I can… However my role»).
- **C** `create_demo_project` — marked DEMO_ files + banner; paid export
  blocked (watermark only). Cold-start offers [Lag demosak] for samples.
- Regression E13–E15 gate release.

## 0.22.0 — Agent truthfulness (WORKORDER_0.22)
- **A** Perception: image claims quote «Indeksert som: …» from index
  extraction only; part IDs require extraction facts or user confirm;
  conf <0.80 → «usikker». No free-form vision.
- **B** Completion verbs require tool receipts (post-reply validator +
  one retry); otherwise honest fallback. Narrating fictional writes
  is rejected in code.
- **C** User source files read-only (additive upload only);
  `templates/*.json` unreachable to agent tools; photo → one BOM row
  in document state (`bom_components` + bom_engine merge).
- **D** Bulk «legg bildene i BOM» → count + € + [Skann]; no triage /
  format questions.
- Regression E10–E12 gate release with privacy/golden suite.

## 0.21.0 — Act, don't describe (WORKORDER_0.21)
- «Start med Design Basis» executes `create_project_with_skeleton` +
  SJEKKLISTE from the real template; ~60-word completion reply, ≤1 `?`.
- Never tell the user to create folders / drag files when a tool exists.
- Reply length budget (≤120 default, 200 hard); no `##` in chat;
  banned closers («Klar til å starte?»). `list_gaps` capped at 5 + «…og N til».
- Regression goldens C7–C9 gate release.

## 0.20.1 — C2-BIS: cold-start always hits the model
- Removed the keyword precheck as a gate: `/api/hub/chat` calls the
  model with the full §C5 capabilities payload (catalog + scale +
  history). Manifest constrains *claims*, not *whether* to answer.
- Logs `model_called=` per hub message. Zero-token only for privacy
  sentences and unambiguous cannot-list boundaries.
- ROV / multi-folder aliases; offline reasoner kept for no-key/tests.
- Regression: model-path + ROV golden; force_offline on prior cold tests.

## 0.20.0 — Agent knows where it is, executes, answers (WORKORDER_0.20)
- **A** Context payload: indexed count + active document; code-first
  open-ended grounding (never «helt nytt»); A2–A4 in CHAT_AGENT_POLICY.
- **B** Imperatives execute: «bruk dette bildet på forsiden» → set_cover
  + «Indeksert som: …»; no permission-seeking.
- **C** Cold start reasons: structure rendered inline; canned
  kapabilitetslisten shrug deleted; scale block C6; hub history.
- **D** `scripts/agent_regression.py` gates release (make_release.ps1).

## 0.19.10 — Cold-start: match before shrug (COLD_START §3)
- Capability *claims* stay grounded; capability *matching* is inference
  from user words → listed templates. Due diligence / scale questions
  map to contract_review, spec_coherence_review, tender_compliance_matrix
  with real numbers from a new `scale` block (never «Ikke sikker»).
- Language mirroring (EN↔NO). `privacy_en` + bilingual hub replies.
- Acceptance: English DD + «thousands of files» → grounded EN answer.

## 0.19.9 — Open-ended ask policy (ONE_AGENT_SPEC §7)
- Ground first, search index before asking, ≤2 questions, € document
  offer; warm professional voice (no emoji / «Kult!»). Corpus brief +
  zero-token known-from-index on every chat turn. Acceptance paired
  with §3 (registreringsnummer).

## 0.19.8 — Project chat context on every call
- Every in-project chat model call attaches engine-built context:
  name + folder + file count, full artifact (incl. confidence),
  documents + gap counts, fact-key inventory (keys+counts only),
  conversation history. `build_project_chat_context()`.

## 0.19.7 — Chat attachments + learning boundaries
- `LEARNING_AND_BOUNDARIES.md`: attachments in chat, ENGINE vs AI line,
  L1/L2/L3 learning policy (no central content collection; NN rejected).
- Drop zone + 📎 on hub / Checkpoint A / editor → classify → form import
  review, project index+gap match, or one ambiguous question.
- L2: `local_app/local_learning.json` (aliases); column corrections teach
  it; `GET/POST /api/learning`. Company templates + caps regen on confirm.
- ENGINE_CONTRACT §0.1 names the engine/AI line.

## 0.19.6 — One agent through editing (ONE_AGENT_SPEC)
- Single persisted `conversation` from cold start → Checkpoint A → editor;
  hub folder create seeds the thread. Canned «Jeg kan hjelpe med» menu
  removed; one-time editor hint only.
- `POST /api/doc/chat` with code-first tools (`list_gaps`, `resolve_mangler`,
  `suggest_reference`, `regenerate_section` → diff confirm).
- Sticky editor layout (240 / flex / 320); tabs + gap pill sticky; mobile
  assistant bottom sheet.
- B1 title dedupe; B2 drawing-role structure suggestions (max 2 cards);
  B3 forbid `[MANGLER: ukjent kilde]`.

## 0.19.5 — Cold start hub (COLD_START_SPEC)
- Zero-state chat on the projects hub answers «kan du lage X?» from
  `capabilities.json` (built by `scripts/build_caps.py`, regenerated
  in `make_release.ps1`). Privacy uses approved sentences only.
- `POST /api/hub/chat`, `POST /api/project/create-with-skeleton` (folder
  skeleton + SJEKKLISTE.txt), base dir asked once via settings.

## 0.19.4 — Empty projects, identity, reference values (WORKORDER_0.19B)
- **Project name is a source:** synthetic `(prosjektnavn)` index entry with
  Haiku-extracted identifier facts (cached by name hash); empty-folder
  Checkpoint A notice.
- **Rung-3 identity rule:** `draft_template` requires ≥3 identity
  `required_facts` on first section (re-ask once, else inject); API
  `/api/template/draft`.
- **Reference provenance:** MANGLER popover offer (`reference_suggest`);
  amber `~` chips; ubekreftet gap count; export declaration. Compliance
  keys never get a reference offer.

## 0.19.3 — Chat open on empty folder
- Stream chat is always available in «PROSJEKT — forstå og bygg», even with
  zero files. Seed artifact from project name; assist treats user text as
  source of truth when the index is empty. Sonnet «bygg fra kilder» is
  demoted to an optional link once sources exist.

## 0.19.2 — One stream: talk → agree → document
- **FLOW_ONE_OPERATION:** FORSTÅ/BYGG merge into one card «PROSJEKT — forstå
  og bygg». Intent posts an agreement card in chat (why, €, Annen mal);
  one click confirms + generates. Progress and «Ferdig» live in the stream.
- Manual «Velg mal manuelt ▾» and FORSLAG «+ Opprett» call the same
  `lagDokumentet` path. Document tabs above the editor; [+ Nytt] scrolls
  to chat. Standalone BYGG checkpoint UI removed.

## 0.19.1 — Prosjektplan template
- New system template `project_plan` / **Prosjektplan**: overview, AI-proposed phases
  with `[AUTHOR:…]` sequencing placeholders, cited milestones only, risks from index,
  document deliverables (incl. foreslått rows), source register, planning declaration.
- `project_name` aliases to artifact title; suggestion rules surface Prosjektplan for
  structure/byggesak signals; generate_section honors `ai_proposed_banner` /
  `author_placeholder_for_sequencing`.

## 0.19.0 — Cross-project chat isolation (BUGFIX_0.19)
- **Root cause (UI):** Checkpoint-A `A_CHAT_HTML` survived project switches while
  the artifact model reloaded correctly — chat from tilbygg leaked into
  renseanlegg. Cleared on `LAST_PID` change with editor chat / intent state.
- **Server ISOLATION RULE:** `resolve_project` / `load_project_index` /
  `build_artifact_assist_sources` — no module-level current-project cache;
  chat context prepends `PROSJEKT: … · MAPPE: …`; folder mismatch → 500.
- **Instrumentation:** `[isolation:…]` logs id, folder, state path, index_n, first file.
- **Regression:** `scripts/test_chat_isolation.py` — alternate A/B context builds.

## 0.18.3 — Intent box (matrix removed) + citation restore + supersede hints + packaging
- **Checkpoint A:** RETNINGSMATRISE removed; extracted questions demoted to collapsible
  «Funn fra kildene (N)» in Bakgrunn (read-only + «→ still spørsmålet» prefills assistent).
- **Intent box (BYGG):** one Haiku call (`template_intent`) chooses template from catalog with
  why_no quoting user words; chips from `detect_suggestions()`; no_fit → rung-3 offer;
  dropdown + Generer utkast remains below.
- **Rider 1 (complete):** `sections[key].stale_citations` — md stored intact; display/postprocess
  shows `[MANGLER: kilde ekskludert]`; toggle-on restores values; banner adds «Angre ekskludering»;
  gaps recompute against filtered index.
- **Rider 3 (complete):** KILDER row hints with Ekskluder/Behold; per-document dismiss;
  ⚠ on superseded rows in doc_control tables; mtime tie-break on rev compare.
- **Privacy:** `scripts/make_release.ps1` (blocking grep: BYGG-\\d, C:\\Users\\, projects.json);
  ships `local_app/projects.example.json`.

## 0.18.2 — Stale citation traceability + revision supersede + packaging privacy
- **Rider 1:** toggling a source OFF intersects `cited` / `cited_fact_ids` with that
  file's facts → affected sections show banner «Kilde ekskludert — N siteringer berørt
  [Regenerer · ~€0.05]»; baked-in values become `[MANGLER: kilde ekskludert]` (no auto-gen).
  Recompile/postprocess respects excluded fact ids.
- **Rider 3:** `detect_revision_supersede()` — same `drawing_no`, lower rev → dismissible
  suggestion card with «Ekskluder fil» (zero tokens).
- **Privacy (WORKORDER 0.14 §A):** neutral UI placeholders; `projects.json.example` ships
  instead of `projects.json`; `scripts/package-release.ps1` enforces step-7 privacy grep
  (fails on real paths/names before zip).

## 0.18.1 — Illustrations stay inside document panel
- Wide tegninger no longer push content past the assistent sidebar: `max-width:100%` containment,
  `.fig-wrap`, grid `min-width:0`, and unwrap figures from marked `<p>` wrappers.
- Page-level horizontal scroll removed (`overflow-x:hidden` on editor shell).

## 0.18.0 — SOURCE_INTERACTION_SPEC S1–S5: sources are switches, tables are editable views
- **S1 Source toggle:** switch on every indexed KILDER row — off = out of THIS document
  (tables/figures recompiled without it, zero tokens), index untouched. `excluded_sources[]` in state.
- **S2 Structured tables:** `compile_doc_control_data` / `compile_spec_overview_data` emit rows+cells;
  markdown is now a render of the structure. Old projects migrate on open.
- **S3 Hover trace:** hover a table row → its source file lights up in KILDER (and reverse).
- **S4 Cell edit:** click any editable cell (Utgiver, Revisjon, Dokumentnr …) → popover with
  index candidates [Bruk] or write yourself (verified fact). `cell_overrides[]` are sovereign —
  survive recompiles; «Tilbakestill til kildeverdi» reverts. MANGLER cells with foreign keys
  (design_basis_ref) route to the guided flow.
- **S5 Picture toggle:** 🖼 button per visual source row hides the illustration while the
  table row stays; unified `/api/doc/toggle-figure` (on/off).
- New APIs: `toggle-source`, `toggle-figure`, `edit-cell` (incl. clear), `cell-candidates`.
- Gap engine and «Fyll inn det vi vet» respect toggled-off sources.

## 0.17.3 — Guided gap completion (MANGLER → next step)
- `gap_guide()` + `/api/doc/gap-guide`: one clear primary action per missing field (apply from source, create Designgrunnlag, refresh table).
- `/api/doc/fill-known-gaps`: bulk or single apply of values already in index/artifact (e.g. 25 m² from artefaktformål).
- MANGLER popover rewritten: human label + green primary CTA; numbered menu moved under «Andre måter».
- Gap pill: **Fyll inn det vi vet (N)** when auto-fillable gaps exist.
- `spec_ref` / `design_basis_ref` inferred from indexed Designgrunnlag; spec_overview lists it first.
- Auto-refresh spec_overview when any stale `[MANGLER: issuer]` remains.

## 0.17.2 — Spec overview: issuer from drawings, table stays in document
- `compile_spec_overview`: code-built 5-column table; `issuer` from `architect_name` on tegninger.
- Removed stray `MANGLER: invoked_document` row — standards listed from index when found.
- Tables scroll inside document panel (no overflow into assistent sidebar).

## 0.17.1 — Dokumentkontroll links to real files
- `compile_doc_control`: code-built table from indexed drawings (like tegningsliste).
- `doc_no` aliases `drawing_number`; filename fallback when title block unreadable.
- Auto-fixes stale AI doc_control tables with false doc_no MANGLER on project open.
- MANGLER chips show green «fil funnet» when matching drawings exist in kilder.

## 0.17.0 — BOM engine + completeness suggestions
- `bom_engine.py`: element extraction from drawings, code-summed materialliste, zero-token suggestions.
- Indexing prompt extended with `element` facts (qty, length_mm, material in props).
- BOM section in structural_design_report, design_basis, technical_doc_package.
- Workbench: suggestion cards under DOKUMENTER, BOM MANGLER → «Pek på kilden», «Oppdater BOM» button.
- `migration_007_bom.sql` for hosted schema (props column, bom_table block, project_suggestions).

## 0.16.13 — Selective illustrations + remove button
- Only the primary section (Sammendrag/Omfang) gets the 4 anchor drawings — not every chapter.
- Click **×** on any illustration to remove it; restore from the list below the editor.
- Opening a project strips duplicate figure blocks from other sections.

## 0.16.12 — Fast project open; fewer illustrations
- `/api/project` no longer re-injects figures or calls Haiku section-mapping on every page view (~15s → under 1s).
- Illustrations capped at 4 anchors per section, 1 page each; bloated docs auto-trimmed on open.
- Workbench shows figure refs as captions only (no duplicate image gallery per section).

## 0.16.11 — Remove fictional Løfteverktøy product-repo project
- Dropped the registered «Foldok» project (product folder + capture/ mock).
- Deleted contaminated `.foldok_state.json` / `.foldok_cache` in the product root.
- `load_projects()` auto-filters any folder that looks like the Foldok product repo.

## 0.16.10 — Artifact name/author fill title MANGLER
- `thesis_title` / `project_title` / `product_name` seed from confirmed
  Checkpoint A name; `author_name` from purpose («… for Jan Rune Erikstad»).
- Stops the absurd case where Prosjekt text already has the title/author but
  the table cells still say MANGLER.
- Drawing anchors prefer higher REV (REV2/REV3) and `approved_drawings` in
  project state (e.g. Example kommune–godkjent fasade).

## 0.16.9 — In-UI folder browser (no frozen native dialog)
- **Velg mappe** opens a browser overlay via `/api/browse` instead of a Windows
  FolderBrowserDialog that blocked the HTTP thread and made the workbench lag.
- TheFuzzyFront-main can be created by paste or the new picker.

## 0.16.8 — Checkpoint A focus mode (stop the mental crash)
- Decision canvas only: sources/assistant hidden until «Kilder / assistent».
- Shows 4 questions at a time; «Behold 4 viktigste» trims the hazard list.
- File list in KILDER capped at 8; source rail lists cited files only (not all 100+).

## 0.16.7 — Checkpoint A: drag questions into the matrix
- Decision-first layout: hazards become a **Spørsmål** pool; drag into the
  matrix to create a beslutning. Components/lifecycle tucked under «Mer detalj».
- First dropped question is auto-selected; click another card for the yellow ring.

## 0.16.6 — New project: Velg mappe copies the folder name
- Home «NYTT PROSJEKT» has a native **Velg mappe** picker; project name is
  filled from the folder basename (also on paste into the path field).
- Creating a project with only a path set uses the folder name as fallback.

## 0.16.5 — Anchor drawings only (no stray PDFs in summary)
- Summary/scope prefer the four named PNG cutouts (plantegning, fasade, snitt,
  situasjon) when available — skips PERSPEKTIV.pdf / misc. PDFs that dilute the
  shared visual referent next to the dimension prose.

## 0.16.4 — Summary shares the same drawing as the prose
- Sammendrag/konklusjon and scope always get anchor illustrations: one each of
  plantegning, fasade, situasjon, snitt (prefers Til Søknad / REV PNGs).
- structural_design_report summary now requires drawing media in the template.
- Keeps the visual referent next to dimensions so reader and author see the same thing.

## 0.16.3 — Illustrations are generated into the document
- Engine injects `{{figure:file:page|caption}}` cutouts from mapped PDF pages,
  photos, and PPTX embedded images into each section (### Illustrasjoner).
- Workbench renders those markers as images; export writes JPEGs to
  `Rapporter/media/` and rewrites markdown to `![](media/...)`.
- Button **Forny illustrasjoner** re-runs cutout injection without full regenerate.
- Presentation PDFs (e.g. Erikstad) contribute up to 6 pages per section.

## 0.16.2 — Checkpoint A as decision workspace
- FORSTÅ: editable components/hazards (add/delete/inline edit), lifecycle toggles,
  direction matrix (impact × feasibility) with drag-drop + chosen decision.
- Source rail linked to seen_in/source files — click opens PDF/photo preview.
- Illustration strip under the matrix; Assistent chat with patch proposals
  (/api/artifact/assist, /api/artifact/save).

## 0.16.1 — Illustrations in the draft (PDF pages + photos)
- WORKBENCH: sections show a figure gallery for mapped photos and drawing/
  presentation PDFs (first pages rendered via PyMuPDF). Click to enlarge.
- Media enrichment attaches site_plan/drawing/presentation files to relevant
  sections without a full regenerate (e.g. Erikstad presentation PDF).
- API: GET /api/media, /api/media/meta. Skips product-repo folders still apply.

## 0.16.0 — Phase A editor shell: canvas + Assistent
- WORKBENCH: draft view becomes a three-column editor (kilder i dokumentet ·
  canvas · Assistent), matching the design-dummy feel on the real engine.
- Primary edit path: click MANGLER chips / section select + chat. Markdown
  textarea moved under Avansert per section.
- Assistent: keyword routing — «hva mangler?» (0 tokens from gap state),
  «finn <key>» → gap-assist, «skriv om…» → regenerate-section with diff
  Accept/Reject. Chat history survives project re-renders.
- Sections with blocking gaps get a left border; selected section scopes chat.

## 0.15.0 — Four ways out of every MANGLER (+ domain-smart templates)
- TEMPLATE: technical_doc_package cover — model_no/serial_no/manufacturer only when
  artifact_type is lifting_tool|machine|tool|equipment|prototype; product_name
  relabeled "Produkt-/prosjektnavn" for byggesaker.
- ENGINE: robust artifact_type condition parser; extract_targeted (Haiku, one fact),
  search_fact_candidates (0 tokens), gap_assist, match_new_facts_to_gaps.
- DISMISS: "Ikke relevant" with audit trail (dismissed[]), blocking requires reason,
  undismiss from gap pill, export lists blocking dismissals.
- MANGLER MENU (5 paths): ① write ② pek på kilden ③ legg til fil ④ spør assistenten
  ⑤ ikke relevant. Cited values render blue; user values green ✓.
- API: /api/doc/dismiss, undismiss, extract-targeted, apply-cited, gap-search,
  gap-assist, /api/files/upload, apply-matches.
- UI: popover menu on every MANGLER chip; locked ⟦tokens⟧ in section editor.

## 0.14.0 — Editing round: resolve MANGLER, complete document in workbench
- PRIVACY: removed `examples/sandnes-renseanlegg/` (real case data). Added
  `examples/demo-lifting-tool/` with synthetic files (Verkstedveien 1, 4000 Demo).
  `.gitignore` excludes `.env`, `projects.json`, cache/state from commits.
- STATE v2: per-section drafts in `.foldok_state.json`, `user_facts[]`,
  append-only `versions[]`. Migration splits legacy `draft.md` by `##` headings.
- ENGINE: `inject_user_facts()`, user-cited values render as **value ✓**,
  `regenerate_one_section()` wrapper (no writes until accept).
- WORKBENCH API: `/api/doc/resolve-mangler`, `regenerate-section`, `accept-regen`,
  `edit-section`, `revert`, `versions`.
- UI: MANGLER chips → inline resolve (0 tokens), gap pill dropdown,
  per-section toolbar (regenerate/diff/edit/revert), history drawer,
  green completion banner when all gaps drained.

## 0.13.0 — Multi-folder projects + parallel indexing (v0.11.0/v0.11.1 upstream merge)
- NOTE on numbering: upstream zips 0.11.x collide with our local 0.11.0
  (workbench). Local repo continues at 0.13.0; upstream content is
  identified by zip name in releases/.
- MULTI-FOLDER PROJECTS: CLI accepts several folders (nargs+, per-folder
  .foldok_cache so a shared folder indexes once, free everywhere; rel
  names prefixed with folder name when several). The workbench gets the
  same: projects.json now stores folders[] (old records auto-migrate),
  "+ Legg til mappe" in the project view, state + draft live in the
  first folder.
- PARALLEL INDEXING (5 workers) in both CLI and workbench — ~4-5×
  faster on big folders, with live counter + ETA ("34/120 · ~40s igjen").
- Docs from upstream 0.11.1: CURSOR_BUILD_PLAN Addendum A (template-
  switch semantics: un-generated = re-map in place; generated = confirm
  + snapshot + wipe; exported = new document), EDITOR_SPEC §8 (gap panel
  as status pill, blocking-only canvas markers), NAVIGATION_SPEC flow-
  automation rules (cost rule: auto-run near-free steps, explicit €
  button for generation; ">3s without feedback is a bug").
- Engine hardening kept (upstream zip still lacks it): ask_json retry,
  cardinality gaps, fail-open conditions, redaction, UTF-8 cache I/O,
  2500-token budgets, drawings_register code path, markitdown[pdf].

## 0.12.0 — Subfolders + drawings register (v0.10.1/v0.10.2 upstream merge)
- Merged foldok-engine-v0.10.2.zip into the local hardened engine (all
  0.11 hardening kept: JSON retry via ask_json, cardinality gaps,
  fail-open conditions, redaction, UTF-8 cache I/O, 2500-token budgets).
- RECURSIVE FOLDER WALK (upstream 0.10.2 bug fix): iterdir() read only
  the top level — Bilder/, Tegninger/, Rapporter/ were silently skipped.
  Now rglob at every level, hidden dirs excluded. File identity is the
  RELATIVE PATH (fixes same-filename collisions across subfolders) and
  the path is fed to the index prompt as a role hint. Applied to both
  the CLI and the workbench (file list, index job, generation).
- DRAWINGS (upstream 0.10.1 fix, third real run): INDEX_SYSTEM gains
  roles drawing/site_plan/schematic/sketch + title-block fact extraction
  (drawing_no, revision, scale, drawing_title). design_basis and
  structural_design_report templates gain an auto-compiled
  drawings_register section — implemented in the CLI as pure code
  (compile_drawings_register, zero tokens): one row per drawing-role
  file, [MANGLER] cells where the title block is illegible.
- Templates design_basis + structural_design_report updated from the
  zip (drawings_register section, scope now wants a site plan/GA).
  All 11 templates validate. requirements.txt kept at markitdown[pdf]
  (upstream dropped the extra; we need it for PDFs on Windows).
- Note: existing caches predate relative-path identity; re-indexed
  subfolder files cache under the same sha, so nothing re-bills.

## 0.11.0 — Local workbench: the full "start a project" experience
- local_app/server.py + local_app/app.html: a browser app on the REAL
  engine (no mock data) covering the missing front of the journey —
  create a project by pointing at a folder, see every file with index
  status, index with a cost estimate (sha256 cache = free re-runs),
  build + confirm/edit the artifact model (checkpoint A), pick any of
  the 11 templates, generate (checkpoints B+C) with live per-section
  progress and per-job cost, then read the rendered draft with MANGLER
  highlighting and the gap list. State lives beside the folder
  (.foldok_state.json); projects register in local_app/projects.json.
- Start: scripts/workbench.ps1 → http://127.0.0.1:8766 (hub card added).
- Engine fixes surfaced by the workbench: cache files are now written
  AND read as UTF-8 (read_json_file falls back to cp1252 for caches
  written by older builds on Windows); template load forced to UTF-8;
  server refuses to double-bind port 8766 (Windows SO_REUSEADDR lets a
  second instance silently steal requests — that cost an hour).
- Verified end-to-end on the demo folder: 2 new PDFs indexed
  (€0.019), checkpoint A rebuilt (€0.022), contract_review regenerated
  over all 7 sources (€0.025), 5 gaps reported, draft rendered.

## 0.10.0 — Editor experience prototype
- Both milestone tests green (contract PDFs + photo folder — "really
  promising"). Gate cleared; UI build phase begins.
- ui-editor-v3.jsx: working reference for EDITOR_SPEC + NAVIGATION_SPEC —
  explorer rail (folder statuses, index-with-cost button, document chips),
  selection model + block toolbar, regenerate with DIFF PREVIEW
  (accept/reject, nothing changes unpreviewed), MANGLER inline resolve →
  verified fact (gap counter + export button react live), chat panel
  (scope = selection, zero-token gap answers, proposal diff cards, meter),
  version drawer with author badges. Norwegian only; i18n via v2 pattern.
- Workspace integration: ui-editor-v3.compiled.js + web/editor.html
  (featured on the hub), scripts/regenerate_prototype.ps1 now builds both
  bundles. Engine kept at local hardened build (superset of the 0.10 zip
  engine: JSON-retry indexing, cardinality gaps, Windows UTF-8 stdout,
  contract doc_role_hints) — no regression. releases/ archives the zip.

## 0.9.0 — Milestone test passed
- First real-folder run: Example Treatment Plant, 5 PDFs,
  contract_review, €0.11, partial pass → pipeline proven end-to-end.
- PATCH-level fixes from the run, folded in: INDEX_SYSTEM contract
  vocabulary (all 20 fact types, canonical key preference), type-fallback
  fact matching (vocabulary drift → info candidates, not false blocking
  gaps), --out defaults to source folder.
- 0.9 signals: engine proven, production port (CURSOR_BUILD_PLAN) begun,
  photo-mapping criterion still untested (battery tool folder pending).

## 0.8.0 — Landing + verification + staleness
- foldok-landing.html (live traceable-ink demo), VERIFICATION_SPEC.md
  ("prepared judgment", 3 levels, LLM-never-does-arithmetic rule),
  source staleness detection policy (FORMATS.md).

## 0.7.0 — Contracts & coherence pack
- migration_006 (obligation/deliverable/deadline/penalty/right/requirement),
  templates: contract_review, tender_compliance_matrix, spec_coherence_review.

## 0.6.0 — Direction, navigation, coverage
- PRODUCT_DIRECTION.md incl. section 0 (folder = database, documents =
  views), NAVIGATION_SPEC.md (explorer rail), TEMPLATE_LIFECYCLE.md with
  coverage ladder (rung 3: AI-drafted templates), free_document template,
  FORMATS.md (ingestion/export/storage ledger).

## 0.5.0 — Grammar v2 + diagram spec
- migration_005 (hierarchy, repeat_for, ref registry, doc_symbols,
  doc_memory), phd_materials_draft template, DIAGRAM_SPEC.md (two lanes,
  sketch→graph→render), GRAMMAR_V2_NOTES.md.

## 0.4.0 — Design pack + editor
- migration_003 (decision/assumption/load/criterion), migration_004
  (layout, chat, bundle counters), templates: design_basis,
  structural_design_report, research_project_report, EDITOR_SPEC.md.

## 0.3.0 — Headless pipeline + eval kit
- foldok_compile.py (full CLI: index→A→B→C→draft+ledger),
  eval/eval_harness.py + expected.example.json + debugging guide,
  CURSOR_BUILD_PLAN.md (6 phases).

## 0.2.0 — Custom templates + branding
- migration_002 (company_profiles, template ownership/import pipeline),
  ui-prototype.jsx v2 (i18n NO/EN/PL, import flow).

## 0.1.0 — Engine foundation
- migration_001 (index, facts, artifact model, template system, blocks,
  versions, token ledger, RLS), ENGINE_CONTRACT.md, templates:
  technical_doc_package, samsvarserklaering_el, sja.
