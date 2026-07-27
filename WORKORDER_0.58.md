# WORKORDER_0.58.md — Gap-navigasjon, faste paneler, forklarende assistent
Field requirements from live use of the three-pane editor. Four changes,
plus one contamination bug that must be fixed first.

════════════════════════════════════════════════════════════
0. BUG FIRST — foreign gaps in the ledger (fix before the rest)
════════════════════════════════════════════════════════════
Screenshot evidence: project «Sandnes renseanlegg», document
«Minirenseanlegg – Koblingsskjema», but the Resolve Gaps panel lists
Dato · Kunde · Reg.nr · Km-stand · VIN · Mønsterdybde with sources
`kunde_og_kjoretoy · form_field` and `dekk · form_field` — fields from
the Toyota Multipoint Inspection template that was created by mistake in
this project.

Cause: gaps are collected across the PROJECT's templates/documents rather
than scoped to the ACTIVE document.
Fix:
  · `gaps_for_document(doc_id)` — gaps derive ONLY from the active
    document's template sections + its own state. Never union across
    documents.
  · The panel header states the scope: «Hull i Minirenseanlegg –
    Koblingsskjema (0 blokkerende · 8 advarsler)».
  · Regression: two documents in one project → each shows only its own
    gaps; assert no field key from doc A appears in doc B's panel.
  · Also delete/quarantine the stray Multipoint template from that
    project (it came from the routing bug in PATCH_0.54 §FIX 4).

════════════════════════════════════════════════════════════
A. CLICK A GAP → JUMP TO IT
════════════════════════════════════════════════════════════
A1. Clicking a gap card (anywhere on the card, not just «Løs»):
    · scrolls the document pane so the gap's block is centred
      (`scrollIntoView({block:"center", behavior:"smooth"})`)
    · flash-highlights the target: 2× pulse of a 3 px signal-yellow ring
      on the row/cell, then a persistent 2 px ring until focus moves
    · sets the editor's active section (the Assistant's scope chip
      follows: «Seksjon: Identifikasjon og anleggsdata»)
    · does NOT scroll the page itself — only the document pane
A2. The gap card and the in-document MANGLER chip are the same object in
    two places: hovering either highlights both.
A3. Keyboard: ↓/↑ move between gaps, Enter jumps, Esc returns focus to
    the list. «Neste hull →» button at the bottom of the panel.

════════════════════════════════════════════════════════════
B. THE ASSISTANT EXPLAINS THE GAP (and offers engine buttons)
════════════════════════════════════════════════════════════
B1. On gap focus, the assistant posts ONE short message (≤60 words),
    zero tokens where possible — the explanation is assembled from
    template metadata, not generated.
B2. Button set under the message, ranked, all zero-token unless marked.
    Max 4 visible. «Fyll inn det vi vet (N)» replaces the first slot
    whenever the index can satisfy ≥1 focused gap.
B3. If the engine already knows a candidate, the first button becomes
    «Bruk «…» fra … · gratis» — one click, cited, gap closed.
B4. No model call is made merely by focusing a gap. Only «Foreslå verdi»
    and free-text answers cost anything.

════════════════════════════════════════════════════════════
C. LAYOUT — panels stay, document scrolls
════════════════════════════════════════════════════════════
C1. Editor is a fixed-height flex/grid row filling the viewport below the
    header. EACH pane owns its own `overflow-y: auto`. The PAGE never
    scrolls in the editor (`body.editor-locked { overflow: hidden }`).
C2. Left panel and Assistant are the same height; assistant input pinned.
C3. Tool buttons sticky; annotation SVG spans full document height;
    edge auto-scroll while drawing (8 px/frame).
C4. Tab switching preserves each tab's scroll and the document scroll.
C5. Min widths: left 240 · document 520 · assistant 300.
    Below 1100 px the assistant collapses to a toggle.

════════════════════════════════════════════════════════════
D. ACCEPTANCE
════════════════════════════════════════════════════════════
1. Two documents in one project → each shows only its own gaps; no
   Toyota field appears in a renseanlegg document.
2. Click a gap → document pane scrolls to it, ring pulses, assistant
   posts an explanation ≤60 words with ≤4 buttons; token_ledger unchanged.
3. Where the index holds a candidate, the first button applies it in one
   click and the gap closes as a cited value.
4. Scroll the document to the bottom → tool buttons still visible and
   usable; draw a mark there → it lands on the correct block.
5. Switch tabs and back → document scroll position unchanged.
6. Assistant input never scrolls out of view; panes are equal height.
