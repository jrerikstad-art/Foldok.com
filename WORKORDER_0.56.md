# WORKORDER_0.56.md — Tegnelag: visuell instruksjon over dokumentet
New tool in the left Tools rail: a transparent annotation layer over the
rendered document. Pencil, box, arrow, text note, and text selection.

CORE RULE (this is what makes it work rather than frustrate):
    THE DRAWING IS A POINTING DEVICE, NOT A PROMPT.
Every mark is resolved IN CODE to the block(s) it overlaps, producing a
structured command. The agent never receives a picture to interpret. It
receives targets + the user's typed words, and only when words require
interpretation is a model call made.

════════════════════════════════════════════════════════════
A. HIT-TESTING — marks resolve to blocks, not pixels
════════════════════════════════════════════════════════════
A1. Every rendered block carries `data-block-id` (section_key/block_idx)
    and its bounding box is known to the client (already true — the
    LayoutTree/HTML renderer emits positions).
A2. On mark completion, code computes:
      · overlapped blocks (≥30 % area, or the block under the stroke's
        centroid for pencil/arrow)
      · for arrows: source block (tail) and destination anchor
        (nearest block edge to the head → `before:` / `after:`)
      · for boxes drawn in empty space: the insertion point between the
        two nearest blocks
      · for text selection: block id + character range
A3. Result is an ANNOTATION object, never an image:
    { id, kind: "pencil|box|arrow|note|selection",
      targets: ["sec-4/blk-2"], anchor: "after:sec-2/blk-5"|null,
      selection: {block, start, end, text}|null,
      note: "gjør denne tabellen bredere",      // user's typed text
      geometry: {…}                              // kept for redraw only
    }

════════════════════════════════════════════════════════════
B. WHAT EACH TOOL MEANS (deterministic verbs)
════════════════════════════════════════════════════════════
  PENCIL over a block ....... "mark this" → attaches a note to the block
  BOX around blocks ......... "group/act on these"
  BOX in empty space ........ "put something here" (insertion anchor)
  ARROW block → position .... MOVE (code executes; zero tokens)
  ARROW block → block ....... "relate these" (needs the note to explain)
  ✕ over a block ............ DELETE (code executes; confirm on export-
                              blocking content)
  NOTE (text box) ........... free instruction bound to whatever it
                              overlaps
  SELECTION in text ......... edit target: replace / rewrite / cite / add

B1. ZERO-TOKEN ACTIONS (execute immediately in code, versioned, undoable):
      move block, delete block, reorder, resize figure (S/M/L/full),
      insert figure placeholder, split/merge column layout,
      mark section for regeneration
B2. MODEL ACTIONS (require the user's words; one call, diff preview):
      rewrite selection, "make this shorter/stricter", "explain this
      value", "turn this paragraph into a table", "add a caption here"
B3. A note with NO recognizable verb → the agent asks ONE clarifying
    question with the targets named («Gjelder dette tabellen i §4?»).

════════════════════════════════════════════════════════════
C. THE ROUND-TRIP (how the agent sees it)
════════════════════════════════════════════════════════════
C1. Annotations are sent as a compact JSON list plus BLOCK CONTEXT —
    each target block's type, heading, and first ~200 chars. The agent
    never gets the canvas image.
C2. Agent reply must reference targets by their human label
    («§4 Tekniske data, tabellen») not by id, and must be ≤120 words
    (0.21 length budget applies).
C3. Batch semantics: multiple marks = ONE operation. The user draws
    three arrows and a box, hits [Utfør (4)], and gets one version entry
    with four changes and one undo. This is the main advantage over
    chat — do not lose it by executing marks one at a time.
C4. Cost line on the button: zero-token actions show «gratis»; model
    actions show «€0,0X». Mixed batch shows the model portion only.
C5. Annotations are conversation context. Pending marks are attached to
    every chat call in the project as structured targets with their
    resolved actions and human labels. When ≥1 mark is pending, the chat
    input shows a badge («1 merke venter» / «N merker venter») and the
    user's next message is treated as that mark's note — pressing Enter
    executes the mark rather than starting a separate conversation.
    Deictic references («denne boksen», «her», «dette») resolve to
    pending marks, never to a new document. If a mark is pending, the
    agent may NOT create a document unless the user's text explicitly
    names one (template key, document-type id, or a clear «opprett …»).

════════════════════════════════════════════════════════════
D. UI (left Tools rail, reusing the wireframe tool's canvas)
════════════════════════════════════════════════════════════
D1. Tools rail: [✏ Penn] [▢ Boks] [→ Pil] [✕ Slett] [T Notat]
    [⌖ Velg tekst] [↺ Angre] · toggle «Vis tegnelag».
D2. Canvas is an absolutely-positioned SVG overlay, same coordinate
    space as the document; scrolls and zooms with it. Marks snap to
    block bounds when within 12 px (feels intentional, avoids ambiguity).
D3. Each mark renders a small chip at its top-left showing the resolved
    action («Flytt → etter §2») so the user sees the interpretation
    BEFORE executing. Chip is editable (dropdown of alternative verbs).
D4. [Utfør (n)] commits the batch. When marks are pending, chat Enter
    is an equivalent commit path (C5) — the typed text becomes the
    note(s), then the same execute path runs. Nothing else changes
    until one of those commits.
D5. Annotations persist per document in state (`annotations: []`) so a
    half-marked-up document survives a reload; cleared on execute.

════════════════════════════════════════════════════════════
E. TEXT SELECTION EDITING (the most-used path — make it excellent)
════════════════════════════════════════════════════════════
E1. Select text in the rendered document → floating toolbar:
    [✎ Rediger] [↻ Skriv om] [＋ Legg til under] [🔗 Sitér kilde]
    [⌫ Fjern]
E2. «Rediger» = inline contenteditable, saves as user edit (warn-never-
    block per EDITOR_SPEC 2.5). Fact chips inside the selection are
    ATOMIC — cannot be split or typed over (protects citations).
E3. «Skriv om» = model call scoped to the selection only, returns a diff
    card (accept/reject), never applies silently.
E4. «Sitér kilde» opens the 0.15 «Pek på kilden» flow for the selected
    value — turning an unsourced sentence into a cited one.

════════════════════════════════════════════════════════════
F. ACCEPTANCE
════════════════════════════════════════════════════════════
1. Draw an arrow from the table in §4 to above §2 → chip reads
   «Flytt tabell → før §2» → [Utfør] → block moves, one version entry,
   zero tokens, undo works.
2. Box an empty area + note «bilde av pumpen her» → figure placeholder
   inserted at that anchor with a picker of relevant indexed photos
   (0.54 relevance ranker).
3. Select a paragraph + «Skriv om» + «strengere» → diff card → accept →
   only that paragraph changes.
4. Draw ✕ over a section containing a blocking gap → confirm dialog
   naming the consequence, not a silent delete.
5. Four marks executed as one batch → one undo restores all four.
6. Nothing in any agent reply contains coordinates, SVG, or image data.
