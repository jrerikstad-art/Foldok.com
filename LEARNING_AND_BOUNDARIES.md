# LEARNING_AND_BOUNDARIES.md — Chat attachments · the engine/AI line · how the engine learns

Three settled answers. §3 is direction-memo-grade policy.

────────────────────────────────────────────────────────────────
1. ATTACHMENTS IN CHAT (feature — routes into existing machinery)
────────────────────────────────────────────────────────────────
Drop zone + 📎 on the chat input, everywhere the agent lives.
The agent CLASSIFIES the drop and routes; it never builds a third path:

  a) Looks like a FORM/TEMPLATE (form fields, company header, blank
     value slots) → "Dette ser ut som et skjema — skal jeg gjøre det
     til en mal dere kan bruke på alle jobber?" → template import
     pipeline (review screen, pills). [migration_002 path]

  b) PROJECT MATERIAL (photo, PDF, spreadsheet) → "Legger den i
     prosjektet — indekserer (~€0,01)." → saved into the project
     folder (Bilder/ or by type), indexed, then GAP-AWARE match runs:
     "Dekker 2 mangler: serial_no, manufacturer [Bruk]". [0.15 §B③ —
     the chat becomes another door to Legg-til-fil]

  c) Ambiguous → ONE question: "Skjema til gjenbruk, eller
     prosjektfil?" Two buttons, no menu.

Photos pasted mid-conversation about a specific gap inherit that gap
as context ("her er merkeskiltet" while reg_no is open → targeted
extraction offer first).

**Implementation (local workbench):**
- UI: compose rows on hub / Checkpoint A / editor (`chatAttach*` in `app.html`)
- Classify: `local_app/chat_attach.py` (deterministic heuristics — engine)
- Route: `POST /api/chat/attach` → existing `/api/files/upload` machinery
  or template draft/import confirm; never a parallel indexer

────────────────────────────────────────────────────────────────
2. THE LINE: ENGINE vs AI (write on the wall; already true, now named)
────────────────────────────────────────────────────────────────
ENGINE (deterministic code, owns all state):
  the index & facts store · templates-as-data · gap detection ·
  aggregation/arithmetic (BOM, totals) · citation validation &
  redaction · code-compiled tables/registers · versioning · rendering
  & export · the ledger · suggestion rules · capabilities manifest ·
  corpus packages (role, select, volume, budget, corpus market) —
  including «Fra mappen» appendix injection on every generate.

AI (stateless calls at the edges, no memory between calls):
  extraction (file → facts) · artifact modeling · mapping proposals ·
  constrained prose under the citation rule · intent/template choice ·
  conversation · reference-value suggestions.

THE RULE: **the AI never holds state; the engine never guesses.**
Every AI output lands in engine-validated structures or it doesn't
land. Every engine behavior is explainable by pointing at data.
(Corollary: "smarter" almost always means better engine data —
vocabulary, rules, templates — not bigger models or new ML.)

# Project chat context (non-negotiable on every in-project chat call):
#   · project name + folder + file count
#   · artifact model (full, incl. confidence) — not a summary
#   · document list + gap counts
#   · fact-key inventory: ~40 most common keys with counts (NOT values)
#   · open conversation history
# Built by local_app/server.py → build_project_chat_context().


────────────────────────────────────────────────────────────────
3. HOW THE ENGINE LEARNS — without collecting user data
────────────────────────────────────────────────────────────────
Goal (agreed): the engine gets better with use. Constraint (agreed):
no central collection of user documents, facts, or content. Three
mechanisms, in order of power:

### L1 — TEMPLATES ARE THE LEARNING (explicit, licensed, permanent)
Every imported company form = the engine explicitly taught a
document type, as inspectable data, with permission. Enterprise
angle: large companies CONTRIBUTE their professional templates under
license/partnership — the library is the trained model, readable by
anyone. Rung-3 draft signals (which types users describe that we
lack) tell us what to author next. This loop already exists; name
it as the learning strategy and invest here first.

### L2 — LOCAL ADAPTATION (personalization as user-owned state)
The engine learns each user's world INSIDE their own state, never
leaving the machine: alias corrections ("utgiver" → architect_name
once corrected, remembered), preferred phrasings from accepted
regenerations, dismissed suggestions and n/a-dismissals feeding
local severity tuning, custom vocabulary from their templates.

Implementation: `local_app/local_learning.json` — portable,
inspectable, deletable. This is "it knows how WE work" with zero
central collection. (Team sync later = sharing that file inside
their org, still never through us.)

APIs: `GET /api/learning`, `POST /api/learning/alias`,
`DELETE /api/learning` (clear file).

### L3 — CONTENT-FREE TELEMETRY (opt-in, aggregate, structural only)
What we MAY collect with explicit opt-in, and the whitelist is the
spec: event counts and keys only — never values, excerpts, captions,
filenames, or prose. Examples:

| Event shape | Use |
|-------------|-----|
| `{template_key, gap_key, action: dismissed_as_irrelevant}` | tune default severities |
| `{rung3_request, suggested_name}` | template roadmap |
| `{file_kind, extraction_conf_bucket}` | prompt tuning targets |
| `{intent→template, accepted?}` | intent quality |

Schema versioned in repo (`telemetry_schema.json`); anything not
whitelisted is not sent. This is how default behavior improves for
everyone while content stays local — and it's a sentence we can say
to a DPO with a straight face.

Local stub: events may be appended to
`local_app/telemetry_opt_in.jsonl` only when
`workbench_settings.json` has `"telemetry_opt_in": true`. Default off.

### EXPLICITLY REJECTED: a trainable neural network inside the engine
Reasons of record: (a) training requires the data we've promised not
to collect; (b) our learnable surface is symbolic (keys, rules,
structures) — config beats weights; (c) unexplainable behavior is
incompatible with the trust architecture ("why did it do that" must
always have an answer that points at data); (d) solo-founder ops:
a model to maintain is a second product. RECONSIDER only for one
narrow case post-revenue: a tiny static classifier (e.g. doc-role
pre-filter to cut vision cost), trained on corpora WE own/license,
shipped as a frozen asset, never learning in the field.

────────────────────────────────────────────────────────────────
ACCEPTANCE (for §1; §2–3 are policy)
────────────────────────────────────────────────────────────────
1. Drop a photo of a nameplate into chat while serial_no is an open
   gap → targeted-extraction offer → accept → cited fact, gap closed.
2. Drop the company's SJA form → import flow proposed → review screen
   → owned template appears in catalog and in "hva kan du bygge?"
   (manifest regen).
3. Ambiguous PDF → exactly one question, two buttons.
4. Correct a column mapping once (utgiver) → local_learning.json gains
   the alias → next project maps it without asking; delete the file →
   behavior reverts (proof of locality).
