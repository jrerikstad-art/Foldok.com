# WO 0.73 — Document editor: dynamic boxes on a real grid

**Target build:** 0.73
**Engine source:** `foldok_boxes/` (attached — 50 tests green; 167 with the other engines, inside your tree)
**Reference implementation:** `python -m foldok_boxes.demo` → http://127.0.0.1:8899

---

## 1. Full check of 0.72.0

**Healthy.** 233 tests pass — 117 in the engine packages, 116 in `scripts/`. The only 5 failures are `scripts/test_chat_isolation.py` dying on `import anthropic`; that's the environment, not the code. 178 Python files, 54k lines. `foldok_diagram`, `foldok_gaps` and `foldok_index` are integrated and green in place.

**The editor is the gap, and it isn't where it looks.**

`EDITOR_SPEC.md` describes exactly what you're asking for — E1 selection model, E2 drag, E4 resize presets. **None of E1–E4 exists.** `ui-editor-v3.jsx` is a static mockup: no pointer handlers, no selection state, no drag. The live editor in `local_app/app.html` has section selection and a `set_block_layout` tool that the *agent* calls from chat. So today a user reshapes layout by asking for it in words. That is why it doesn't feel like a workspace.

`migration_004_editor.sql` stores `layout: {width: "full"|"half"|"third"}`. Three discrete widths — a corner drag had nowhere to land even if the pointer layer existed.

But `artifact_engine/layout/grid.py` already has `columns`, `gutter`, `baseline`, `column_x(col)`, `span_width(start, span)`, `snap_y()`. **The renderer was always more capable than the editor allowed.** This work order does not add a renderer. It exposes the one you have.

---

## 2. The model

A box is a rectangle on the page grid, not in pixels:

```
col    which column it starts in     0 .. columns-1
span   how many columns wide         1 .. columns
rows   height in baseline units      None = as tall as its content
```

Twelve columns is continuous enough that dragging a corner feels like dragging a corner, and discrete enough that the PDF honours it exactly — which is your own §6 Parity Rule, kept.

Free pixel geometry was the alternative and it is a trap: pagination cannot reflow a box pinned to a coordinate, and "which section is this block in" stops having an answer — which is what `foldok_gaps` and template requirements are built on. You'd get Figma and lose the compliance engine.

**Control comes from the pin layer**, the same mechanism as the diagram engine, deliberately — one concept for the whole product:

```
user  >  template  >  engine (computed)
```

Reflow never destroys a hand edit. Width can be pinned while height stays automatic. `release()` is a real reset, not an approximation. Pins are scoped to the page geometry, so a layout tuned for A4 doesn't corrupt Letter. Locked blocks refuse and say why.

---

## 3. Templates that learn — the part that makes it feel like control

"Dynamic templates" is two requirements and the second one is the interesting half:

1. A template supplies defaults, not a cage. Anything it sets, a pin overrides.
2. **A repeated override should stop being an override.**

`promote_to_template()` looks at the user's pins, finds properties where every block of a role agrees, and writes those into the role default. Drag both photographs to a third-width and the template learns `image.span = 4` — one rule, not two exceptions, and the next document places photographs that way. Verified in the reference implementation:

```
promote: Saved as template v2: 1 rule(s), 0 block default(s)
```

Everything else lands as a block-level default. Promotion versions the template rather than mutating it, so it is reviewable and revertable like any other change.

---

## 4. What already runs

`python -m foldok_boxes.demo`, exercised end to end:

```
img1 span (template):            6/12
drag east edge inward:           4/12, 9 rows      (aspect stayed locked)
corner drag:                     7/12
double-click to release:         6/12              (back under the template)
resize a locked block:           refused — "boilerplate and legal text keep their layout"
set both images to 4, promote:   1 rule learned, 0 exceptions
```

Two images sit side by side in one band because the packer put them there, not because someone made a "group". Drop a block on the left or right third of another and it lands beside it — that is how a two-column band gets made, with no separate grouping gesture.

---

## 5. Tasks

### T1 — Schema: `layout` becomes grid coordinates
`{col, span, rows?, align, break_before, keep_with_next}` plus a `grid` stamp `{columns, page_size}`. Keep it jsonb; validate in code as you already do.

Run `integration.migrate_layout()` on every existing document. `full|half|third` maps onto 12 columns exactly, groups become adjacent columns, and — importantly — the migrated values arrive at the **template** layer, not the user layer. So a saved job opens looking identical, and a later "reset layout" returns to the template rather than to a width somebody picked once in 2025. Tested.

**Done when:** every document in the database opens unchanged and `reset_layout()` does the right thing.

### T2 — Pointer layer in `app.html`
Drop in `editor/foldok-box-editor.js`. It has selection, eight handles, hit-testing, live ghost, drop indicator, keyboard span nudge, zero dependencies.

**The one rule: the browser does no layout.** It mirrors the snap maths so the drag is instant, then sends an intent and redraws from whatever the engine returns. Optimistic locally, authoritative on the server. The moment the JS starts deciding where things go, the canvas and the PDF drift and only the parity test will tell you.

Wire the intents to `LayoutSession`: `select · resize · move · release · span · reset · promote`. `demo.py` is the whole loop in 80 lines; port it, don't reinvent it.

### T3 — Delete the chat path for layout
`set_block_layout` via the agent goes away as the primary route. Direct manipulation is zero-token and instant; spending a model call to move a box is the wrong economics and the wrong feel. Keep a chat path only for things a pointer is bad at ("put every photo at half width") — which now maps onto a template rule anyway.

### T4 — Selection UI
Selected box: signal ring, eight handles, a badge showing `span/12 · auto|edited`. That badge is the whole trust story in six characters — a user must always know whether they're looking at the engine's opinion or their own.

Locked blocks show a padlock and the refusal reason on click.

### T5 — Save as my layout
One button → `promote_to_template()`. Show the report before committing: *"Learned: images at 4/12 (from 2 blocks). Saved 1 block exception."* A template that changes silently is worse than one that doesn't change at all.

`doc_structure.py` already has `save_template_offered` — this is what it was waiting for.

### T6 — Parity in CI
```python
compare(session.geometry(), boxes_from_layout_tree(rendered_tree)).ok
```
`fingerprint(geometry)` as a golden value per fixture document. §6 currently says "weekly check: export the demo doc and hold it next to the canvas" — that finds divergence a week late, by eye, on one document. This finds it on every commit, on every fixture.

### T7 — Version drawer
`session.history` already carries a human-readable summary per change ("Resized to 4/12 columns, 9 rows"). The drawer is a read of that list. Layout edits must be as revertable as text edits — spec §5, still right.

---

## 6. Do not build

- Free absolute positioning. It breaks reflow, pagination and section membership, and there is no way back.
- Layout maths in JavaScript.
- A separate "group" object. Adjacency in a band already is the group.
- Splitting a band across a page. A table half on page 3 with its signature line stranded on page 4 is worse than a short page.
- Silent template mutation.

---

## 7. Build order

1. **T1 migration** first, with the existing documents as the test set. If saved jobs reshape, nothing else matters.
2. **T2 pointer layer** against the demo, before touching `app.html`.
3. **T6 parity test** — before T4/T5, so every later change is guarded.
4. T4, T5, T7.
5. T3 last: remove the chat layout path only once the pointer path is better.

---

## 8. Open questions

- **Columns: 12 or 6?** Twelve gives thirds, quarters and halves cleanly; six is easier to hit with a mouse and harder to make ugly. I defaulted to 12; it's one number in the theme.
- **The measurer.** `SimpleMeasurer` is a deterministic stand-in so the solver is testable without a font stack. Wire `artifact_engine/layout/measurement.py` in and the geometry gets exact — that's a half-day and it's the difference between the canvas being nearly right and being right.
- **Two-column body text.** The band model supports it, but flowing *one* text block across two columns is a different feature (text continuation) and I'd leave it out until someone asks.
