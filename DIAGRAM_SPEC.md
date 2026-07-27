# DIAGRAM_SPEC.md — technical 2D graphics (not photoreal)

**Positioning:** Tools like Visoid optimize *look and atmosphere* (SketchUp/Revit
→ AI render). Foldok needs the opposite: **clear, consistent, printable 2D
diagrams** tied to project data. Copy Visoid’s *iteration UX* (fast regenerate,
templates, side-by-side preview). Do **not** copy photorealism, 3D upload, or
atmospheric prompting for core engineering figures.

**Pipeline (source of truth):**

```text
Components + ports + connections
        ↓
DiagramStyle (DesignSystem tokens — strokes, colors, labels)
        ↓
Layout profile (SLD | wiring | piping | mechanical | hybrid | flow)
        ↓
SVG (orthogonal, print-safe, data-diagram-style=…) + visual_qa
        ↓
DiagramBlock (caption, figure #, citation, style_id)
        ↓
LayoutTree → HTML / PDF
```

Rule: content from the graph · looks from DiagramStyle · placement from LayoutTree.
Style: `artifact_engine/diagram_style.yaml` · paint: `diagram_engine/paint.py`.

**Canvas edit contract (wiring / manual layout)**

| User may change | Engine owns |
|-----------------|-------------|
| `position` (grid snap) | Orthogonal wire paths + stubs |
| `rotation` (90°) | Stroke colors / widths from style + medium |
| reconnect / delete | Label anchors (preferred → sides → leader) |
| tag / notes | Port hotspots + snap radius |

| Not stored as truth | Handled by engine |
|---------------------|-------------------|
| Freehand wire paths | Orthogonal router from ports |
| Ad-hoc stroke colors | Style + medium (L1/L2/PE) |
| Manual label x,y ink | Label rules from style |

**Busy middle fix:** drag component → `position` snaps to grid → engine re-routes
wires → labels reflow. Connection IDs / endpoints unchanged unless reconnect.

**Port snap (connect mode)**

```text
onPointerMove → ports within style.ports.snap_radius (legal media only)
onRelease     → commit to nearest legal port, else cancel
```

API: `editor.preview_connect_at` / `finish_connect_at` · `editor.move_component` · `auto_spread`.

**Acceptance**

- Move component → GRAPH connection list unchanged (only `position` / `rotation`)
- PE stays green, L1/L2 palette from DiagramStyle
- Delete component → incident wires removed (no orphan endpoints)
- Labels prefer `above`, then sides, then leader — never change connectivity
- Figure export = same `graph_id` / SVG from session

Port snap: `DiagramStyle.ports.snap_radius`. Busy drawings: drag or **Auto-spread**.
Demo: `/diagram.html` · API: `/api/diagram/session/*`.

AI may **propose** the graph; the engine **owns** geometry/symbols/SVG.
User confirms before insert. Never free-draw diagrams.

---

## Status vs 90-day 2D plan (2026-07-25)

| Window | Deliverable | Status |
|--------|-------------|--------|
| W1–2 | Freeze schema + first 20 piping/mech + electrical pack | **Done** |
| W3–5 | Orthogonal SLD / piping / legends | **Done** |
| W6–8 | Generate tools + DiagramBlock insert | **Done** (`propose_diagram` / `confirm_diagram`, figure fields) |
| W9–12 | Hybrid skid + figure #/citation + visual QA | **Done (v1)** — refine collision/A4 sizing next |

Lane A (illustration / photo cleanup) remains separate and optional.

---

## Local history

**2026-07-24:** Lane B block diagrams + electrical SLD/wiring.
**2026-07-25:** Unified multi-domain engine; propose/confirm; visual_qa;
`DiagramBlock.figure_number` / `source_citation` / `diagram_type`.

Full elkjs canvas editor remains post-v1.

Prior art: FigureLabs (sketch→image) validates UX, disqualified for technical
diagrams (no graph, no standards, no traceability). Visoid: same lesson for
architecture viz vs engineering 2D.

────────────────────────────────────────────────────────────────
LANE A — ILLUSTRATION BLOCK (optional, not core evidence package)
────────────────────────────────────────────────────────────────
Use: manual overview graphics, research concept figures, "clean up my
cluttered rig photo". Input: sketch photo / site photo + optional style
prompt. One image-model call (Gemini image API or equivalent; abstract
behind src/engine/illustrate.ts so provider is swappable).
Rules:
  - block_type='illustration' (add to enum): {image_url, source_file_id,
    prompt, provider}. Caption auto-suggested, user-editable.
  - HARD: illustration blocks may not carry spec values; generation prompt
    forbids text/numbers in image; postprocessor strips numeric claims
    from captions unless cited. PDF renders small "Illustrasjon" tag.
  - Metered like a regeneration (counts in the bundle).
Why: 80% of the FigureLabs delight at 2% of the build cost, without
polluting the evidence / documentation layer.

────────────────────────────────────────────────────────────────
LANE B — TECHNICAL DIAGRAM (the moat: sketch → GRAPH → render)
────────────────────────────────────────────────────────────────
Never sketch→image. Pipeline:

 1. INTERPRET  Sketch photo (or voice walkthrough) → Sonnet vision →
    diagram graph JSON. Purpose='diagram_interpret'.
      graph = { domain: 'electrical'|'pid'|'plumbing',
        nodes: [{id, symbol_key, label, props{rating,size,...},
                 source:'sketch'|'voice'|fact_id, confidence}],
        edges: [{from,to, kind:'wire'|'pipe'|'signal',
                 label, props{cable_type,dn,...}, confidence}] }
 2. CHECKPOINT (the trust gate, same pattern as artifact/outline):
    plain-language readback — "12 circuits; breaker 5 → kitchen 16A;
    RCD covers 3–7" — plus ghost-render. User confirms per-node/edge;
    confidence <0.8 rendered amber, must be tapped. Nothing renders
    final until confirmed. Node props matching indexed facts auto-cite.
 3. RENDER  Deterministic SVG from symbol library. Layout profiles in
    `diagram_engine/` (orthogonal). Zero tokens. Output = DiagramBlock
    {graph, svg, diagram_type, figure_number, source_citation}.
 4. EDIT  Graph is the source of truth: patch graph → re-render;
    every change versioned. Voice edit allowed:
    "circuit 9 is 2.5mm² not 1.5" → graph patch → preview → accept.

SYMBOL LIBRARY: `diagram_engine/symbols/{electrical,piping,mechanical}/`
— see `symbols/CATALOG.md`. Curated SVG, NEVER AI-generated symbols.

TEMPLATES: `panel_sld`, `cable_wiring`, `pipe_run`, `drive_train`, `pump_skid`
via `propose_diagram(template=…)`.

COST: interpret ~1 vision call + checkpoint local + render free.

FAILURE HONESTY: messy sketches will misread. The checkpoint is the
product answer.
