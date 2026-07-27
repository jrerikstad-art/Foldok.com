# foldok_boxes

Word's flow, InDesign's grid, Figma's directness — in one geometry model.
Pure Python, no dependencies. `python -m foldok_boxes.demo` for a working editor.

    blocks + template + pins
        -> solve()      deterministic geometry, document order preserved
        -> Geometry     consumed by BOTH the canvas and the PDF renderer

## Why a box is not a pixel rectangle

    col   which column it starts in    0 .. columns-1
    span  how many columns wide        1 .. columns
    rows  height in baseline units     None = as tall as its content

Continuous enough that dragging a corner feels like dragging a corner. Discrete
enough that the PDF honours it exactly. Free pixel geometry feels better for
about a day and then starts lying: pagination cannot reflow a box pinned to a
coordinate, and "which section is this in" stops having an answer — which is
what gap detection and template requirements are built on.

## Why the user stays in control

Same mechanism as the diagram engine, deliberately — one concept for the product:

    user  >  template  >  engine (computed)

Reflow never destroys a hand edit. Pin the width, leave the height automatic.
`release()` is a real reset. Pins are scoped to the page geometry, so a layout
tuned for A4 does not corrupt Letter. Locked blocks refuse edits and say why.

## Files

| File | Contains |
|---|---|
| `model.py` | `PageGrid`, `Box`, `PlacedBox`, `Geometry`. The shared vocabulary. |
| `pins.py` | The override layer. |
| `flow.py` | Band packing + pagination. Bands are atomic; document order survives. |
| `snap.py` | Pointer deltas to grid boxes. The authority the JS mirrors. |
| `template.py` | Templates that learn: repeated edits become rules. |
| `session.py` | `LayoutSession` — what a gesture turns into. |
| `parity.py` | Canvas/PDF agreement as a test, not a weekly eyeball check. |
| `integration.py` | Adapters + migration of the existing `full\|half\|third` data. |
| `editor/foldok-box-editor.js` | Pointer tool, selection, 8 handles, ghost, drop indicator. |
| `demo.py` | Runnable reference implementation of the whole loop. |

## The loop

```
pointer gesture -> intent -> LayoutSession -> solve() -> geometry -> redraw
```

The browser never decides where a box goes. It draws the ghost locally with the
mirrored snap maths so the drag is instant, then sends the intent and redraws
from whatever the engine says. Optimistic locally, authoritative on the server,
identical formulas on both sides.

## Quick start

```python
from foldok_boxes import BlockInput, LayoutSession, compliance_a4

blocks = [BlockInput("h1", "heading", text="Scope"),
          BlockInput("img1", "image", aspect=1.5),
          BlockInput("img2", "image", aspect=1.5)]

s = LayoutSession(blocks, template=compliance_a4())
s.resize("img1", "e", dx=-90, dy=0)   # drag the right edge in -> 4/12 columns
s.set_span("img2", 4)
s.promote_to_template()               # both images at 4 -> learns image.span = 4
s.release("img1")                     # back under the template
print(s.state())                      # the payload the canvas draws
```

## Rules the tests enforce

- Document order survives every layout operation.
- Boxes never overlap, never escape the margins, always sit on the baseline.
- A hand resize survives content being added above it.
- The ghost under the cursor equals the box you get on release.
- A band is never split across a page; one too tall is reported, not clipped.
- Locked blocks refuse layout edits with a reason.
- A repeated edit becomes one rule, not twelve exceptions.
- Existing `full|half|third` documents migrate without reshaping.
- Canvas geometry and renderer geometry are byte-identical, or the test fails.

```
python -m pytest foldok_boxes/tests -q
```
