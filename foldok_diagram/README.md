# foldok_diagram

Deterministic 2D technical diagram engine for Foldok. Pure Python, no dependencies.

    graph + pins + style + profile
        -> layout()        deterministic geometry
        -> render_svg()    byte-stable SVG, also the canvas surface
        -> EngineeringFigure (ArtifactEngine)

## Files

| File | Contains |
|---|---|
| `model.py` | Schema v2. Components carry no geometry. Provenance on everything. |
| `overrides.py` | Pin store. The mechanism that makes the drawing hand-editable. |
| `layout.py` | Columns, rows, routing, label placement, crossing bridges, tight bbox. |
| `render.py` | SVG emit. Mono-safe strokes, stroke floor, `data-target` hit-testing. |
| `profile.py` | One graph, several views. Previously undefined; now specified. |
| `style.py` | Tokens only. Colour + dash + width per conductor class. |
| `symbols.py` | Symbol pack. Geometry only; ports come from the graph. |
| `validate.py` | Structural, media, fitting-branch and jurisdiction checks, each with a fix. |
| `jurisdiction.py` | NO IT / NO TN / IEC / NEC rulesets. Catches the confidently-wrong diagram. |
| `editing.py` | `DiagramSession` — the user-facing API. Gestures in, pins and graph edits out. |
| `migrate.py` | v1 -> v2. Old coordinates become pins, so existing figures open unchanged. |
| `examples.py` | Corrected Norwegian water heater; plumbing supply schematic. |

## Quick start

```python
from foldok_diagram import DiagramSession, figure, profile
from foldok_diagram.examples import water_heater_no, plumbing_supply

# publish
res = figure(water_heater_no(), profile.WIRING, target_width_pt=360)
open("figure.svg", "w").write(res.svg)

# edit by hand
s = DiagramSession(plumbing_supply(), profile.PIPING)
s.move("WH1", 320, 40)                      # pin position for this profile only
s.move("SK1", 480, None)                    # pin x, leave y automatic
s.add_waypoint("p03", 300, 120)             # pull the run through a point
s.insert_fitting("p03", "tee_equal", size="DN16")   # a branch is a part
s.nudge_label("component:WH1", 0, -4)
s.lock_figure()                             # freeze a signed-off drawing

print(s.validate())
open("pins.jsonl", "w").write(s.pins.to_jsonl())
```

## Rules the tests enforce

- Same graph + pins + style = same bytes. No clock, no dict ordering, no float noise.
- A relayout never destroys a user pin; `release()` returns control to the engine.
- Colour is never the only carrier of meaning.
- Two runs on one fluid port is an error, not a drawing.
- AWG on a Norwegian job is an error.
- Handles never appear in a published figure.
- No label overlaps another label; anything unplaceable is reported.

```
python -m pytest foldok_diagram/tests -q
```
