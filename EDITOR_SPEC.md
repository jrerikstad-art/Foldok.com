# EDITOR_SPEC.md — the Bygg canvas as a design tool

Extends CURSOR_BUILD_PLAN.md Phase 3. Rules of record: ENGINE_CONTRACT.md.
Model: **structured canvas with Figma feel** — blocks flow in document order
(sections are real: pagination, gap detection, template requirements depend
on them), but every interaction is direct-manipulation, instant, reversible.

Cost law of the editor:
  DIRECT MANIPULATION = ZERO TOKENS   (move, resize, group, retype, delete)
  AI = EXPLICITLY SUMMONED            (toolbar action or chat), previewed,
                                       metered, versioned.

────────────────────────────────────────────────────────────────
1. SELECTION MODEL (the Figma transfer)
────────────────────────────────────────────────────────────────
- Click block → selected: 2px signal-yellow ring, floating toolbar above,
  chat context chip switches to "Block: <section> · <type>".
- Click section header → section selected (chat scope = section).
- Esc / click canvas → deselect (chat scope = document).
- Shift-click → multi-select (move/delete only; AI actions single-block).
- Keyboard: ↑↓ move selection, Cmd+↑↓ move BLOCK, Cmd+Z revert (see §5),
  Cmd+D duplicate, Del delete (soft — revertable), "/" insert menu.

────────────────────────────────────────────────────────────────
2. DIRECT MANIPULATION (all zero-token, all optimistic-UI)
────────────────────────────────────────────────────────────────
2.1 MOVE   Drag handle (visible on hover/selection). Drop targets:
    between any two blocks, any section. Cross-section drop → PATCH
    block {section_key, position} → gap engine re-runs in code →
    gap chips update live ("Technical Data now missing nameplate photo").
    Library: dnd-kit (sortable, multi-container).
2.2 RESIZE Images/diagrams: corner drag snaps to width presets
    full | half | third → layout.width. No free pixel sizing —
    presets are what the PDF renderer can honor deterministically.
2.3 GROUP  Drag block onto the right edge of another → two-column
    group (layout.group_id + slot). Drag out → ungroup. Max 2 columns
    (A4 compliance docs; more is a Phase-2 debate, default no).
2.4 EDIT   Text blocks: TipTap inline editor (bold, italic, lists,
    table cells). Debounced save 800ms → new document_versions row
    (scope=block, author_type=user, change_summary="Manual edit").
    Fact chips inside text render as atomic TipTap nodes: NOT
    editable as text — click chip → popover: source excerpt, file,
    confidence, [Edit value manually] → creates verified_by_user fact,
    re-cites. This keeps traceability through human edits.
2.5 INSERT "/" menu or drag from source panel: text, image (from
    sources or upload), table, warning_box, checklist, page_break,
    diagram placeholder. Inserted user blocks: ai_generated=false,
    exempt from bare-number validation (user-authored = user-owned;
    the responsibility screen covers them — same stance as v15).
2.6 DELETE Soft: block hidden, toast with Undo 10s, recoverable from
    version history after. Never hard-deletes content.

────────────────────────────────────────────────────────────────
3. BLOCK TOOLBAR (AI, single-block, metered)
────────────────────────────────────────────────────────────────
Actions by type (from template writing_rules + universal set):
  text:     Regenerate · Shorten · Expand · Translate · Add warnings
  table:    Regenerate · Fill from facts
  image:    Auto-caption · Suggest better source (from index, zero tokens)
  warning:  Stricter · Suggest from standard
Flow: action → POST /api/blocks/[id]/regenerate {action} →
  diff preview inline (old greyed, new highlighted, word-level diff) →
  Accept (new version, regen_count++) / Reject (nothing happened).
Never applies without preview. Ever.

────────────────────────────────────────────────────────────────
4. CHAT PANEL (docked right, 320px, collapsible)
────────────────────────────────────────────────────────────────
4.1 CONTEXT = SELECTION. Chip at top shows scope; user can pin scope.
4.2 SERVER CONTEXT BUDGET (contract: chat never re-reads originals):
      block scope:    that block + its section mapping + facts     (~2k tok)
      section scope:  section blocks + mapping + gaps              (~4k)
      document scope: artifact model + section list + gap summary  (~3k)
      + last 6 chat turns. Model: Sonnet. Purpose='chat_edit'.
4.3 REPLY CONTRACT: assistant returns prose AND optionally a proposal
    JSON (see migration_004 chat_messages.proposal). Proposals render
    as a diff card in-chat AND ghost-preview in the canvas at the
    target position. Accept → same pipeline as toolbar: postprocessor
    (citation rule enforced — chat CANNOT introduce uncited specs;
    unsourced values arrive as [MANGLER]), version row, chat_turn_count++.
4.4 ZERO-TOKEN ANSWERS first: "what's missing?" → answered from
    gap_flags in code, no API call. "where is X used?" → fact index
    lookup. Route these before calling the model (intent check is
    a cheap Haiku call only when local answering fails — or simple
    keyword routing in v1).
4.5 METER: "14 / 20 chat turns · 6 / 30 regenerations" quietly under
    the input. At limit: top-up card (€2–3), never a hard wall mid-thought.
4.6 WHAT CHAT REFUSES (scope guard, in system prompt + code):
    general questions unrelated to the document, generating content
    about facts not in the index without marking [MANGLER], editing
    boilerplate/legal blocks (locked — chip explains why).

────────────────────────────────────────────────────────────────
5. VERSIONS & UNDO (trust layer, unchanged from v15 rules)
────────────────────────────────────────────────────────────────
- Cmd+Z = revert last version (block-scope preferred, else document).
- History drawer: timeline of document_versions, human-readable
  change_summary, author badge (user/AI/chat), one-tap revert per entry.
- Layout changes also version (scope=block, "Moved to Safety, resized
  to half") — moving things must be as reversible as rewriting them.

────────────────────────────────────────────────────────────────
6. PDF PARITY RULE
────────────────────────────────────────────────────────────────
The canvas may not offer any layout the PDF renderer cannot honor.
render-pdf.tsx reads the same layout jsonb: width presets → fractional
widths, group_id → two-column row, page_break block → page break.
Weekly check: export the demo doc, hold it next to the canvas.
If they diverge, the canvas lies — fix the renderer or remove the option.

────────────────────────────────────────────────────────────────
7. BUILD ORDER (slots into CURSOR_BUILD_PLAN Phase 3/5)
────────────────────────────────────────────────────────────────
  E1 Selection model + block toolbar shell (no AI)        day 13
  E2 dnd-kit move within/between sections + gap re-run    day 14–15
  E3 TipTap inline edit + fact-chip atomic nodes          day 15–16
  E4 Resize presets + two-column groups + "/" insert      day 16–17
  E5 Toolbar AI actions with diff preview                 day 17–18
  E6 Chat panel: scope, proposals, ghost preview, meter   day 19–21
  E7 Version drawer + Cmd+Z + layout versioning           day 21–22
Cut from v1 if time presses: E4 groups, chat intent routing (keyword
routing suffices). Never cut: diff preview, versioning, citation rule.

────────────────────────────────────────────────────────────────
8. GAP PANEL — compact by default (v0.11.1, from field feedback)
────────────────────────────────────────────────────────────────
The MANGLER OG HULL list must not occupy standing space. It is a
STATUS PILL that expands on demand:
  - Collapsed (default): one pill in the status bar —
      "● 2 blokkerende · 3 advarsler ▾"   (red-amber dot if blocking,
      green "✓ Ingen mangler" when clear). Pill is ALWAYS visible;
      blocking count never hides.
  - Expanded (click): dropdown panel (max-height ~40vh, scroll), gaps
    grouped by severity, blocking first. Each row: severity dot ·
    section · label · [Gå til] → scrolls to and flash-highlights the
    block (2× pulse of the signal-yellow ring). MANGLER rows with
    inline-resolve open the input directly from the panel.
  - Auto-behavior: panel auto-expands ONCE when the first blocking gap
    appears after generation; never auto-expands again in that session.
  - Blocks with blocking gaps additionally carry a 3px left border in
    var(--gap) in the canvas, so criticality is visible without the
    panel open. Warnings get no canvas decoration (amber chip only in
    panel) — visual noise budget is spent on blocking only.
