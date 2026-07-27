# Diagram Engine — Architecture

**Principle:** the model proposes the **GRAPH** (user confirms);
**this code draws**. Same graph → byte-identical SVG.

**Version context:** v2 package 0.35; Artifact theme/PDF 0.41;
Sugiyama layered positions 0.42; shared print-first DesignSystem **0.45**.

---

## Pipeline

```text
connection_spec { components[], connections[] }
        │
        ▼
  intent.classify / set_intent     → wiring|power|signal|process|star|overview
        │
        ▼
  LayeredGraphLayout (artifact_engine.layout.graph)
        │  longest-path ranks + barycenter order
        │  orientation: TB (process default) | LR (else)
        ▼
  render_svg                       → boxes, pins, orthogonal paths
        │  provenance colors FIXED (extracted/user/reference)
        ▼
  optional render_html / render_pdf  (ArtifactEngine theme + PDF backends)
```

Propose/confirm UI path still lives in root `connection_diagram.py`.

---

## Package layout

```text
diagram_engine/
  schema/graph.yaml          # Component / Port / Connection (canonical)
  schema/wire_colors.yaml
  schema/media.yaml
  symbols/
    CATALOG.md               # first-20 piping+mechanical port table
    electrical/ | piping/ | mechanical/
  graph.py                   # normalize + validate + SVG helpers
  electrical.py | piping.py | mechanical.py
  render/                    # documented aliases
    piping_layout.py
    mechanical_layout.py
    orthogonal_router.py
  engine.py                  # DiagramEngine facade
```

---

## Canvas interaction (graph editor)

```text
User place / move / connect
        ↓
DiagramCanvasEditor (graph mutations only)
        ↓
validate → manual layout (positions) + orthogonal edges
        ↓
SVG preview  ↔  figure_payload() → DiagramBlock
```

- Wire paths are **not** freehand — engine routes from ports  
- Hit-test: `build_hit_index` / `editor.hit_test` (ports → bodies → edges)  
- Affordances: `AFFORDANCES` in `hit_test.py` (radii in pt)  
- Modes: select | place | connect | pan | drag  

```python
from diagram_engine import DiagramCanvasEditor, DiagramDocument

ed = DiagramCanvasEditor(DiagramDocument(profile="piping"))
ed.place_component("tank_vertical", {"x": 100, "y": 120}, tag="T-101")
ed.place_component("centrifugal_pump", {"x": 220, "y": 120}, tag="P-101")
ed.connect("T-101.outlet", "P-101.suction", medium="pipe")
svg = ed.doc.svg
fig = ed.figure_payload()  # insert into document
```

---

## Electrical / piping / mechanical / hybrid

```text
shared graph { components[], connections[] }
        │  normalize_graph (ports, medium, attributes)
        ▼
  profile: single_line | wiring | piping | pid | mechanical | hybrid | block
        │  orthogonal paths + domain symbol pack + auto legend
        ▼
  SVG  data-foldok="domain_diagram" | electrical_diagram | connection_spec
```

```python
from diagram_engine import DiagramEngine

DiagramEngine().load_fixture("electrical_sld").render("svg")
DiagramEngine().load_fixture("piping").render_piping()
DiagramEngine().load_fixture("mechanical").render_mechanical()
DiagramEngine().load_fixture("hybrid").render_hybrid()
# Same components can feed electrical wiring AND mechanical arrangement.
```

Wire colors: `schema/wire_colors.yaml`. Pipe media / DN weights: `schema/media.yaml`.
Not AutoCAD / QElectroTech — graph in, deterministic SVG out.

---

## Provenance colors (do not restyle)

| Provenance | Color | Style |
|---|---|---|
| `extracted` | `#1450B4` | solid |
| `user` / `verified_by_user` | `#1E7A46` | solid |
| `reference` | `#C74E19` | dashed |

Sheet ink/paper/accent may follow ArtifactEngine Theme; provenance stays fixed.

---

## Public API

```python
from diagram_engine import DiagramEngine

eng = DiagramEngine(theme="engineering", orientation="LR")
eng.load_spec(spec)                 # or load_fixture / load_from_artifact
eng.set_intent("process")
eng.set_orientation("TB")
eng.add_node("a", "A", pins=["ut"])
eng.add_connection("a.ut", "b.inn", label="link", provenance="user")
svg = eng.render("svg")             # also: html, json, markdown
html = eng.render_html()
# eng.render_pdf("out.pdf")
```

SVG markers: `data-foldok="connection_spec"`, `data-layout="<kind>"`,
`data-graph="layered"`, `data-component`, `data-provenance`.
