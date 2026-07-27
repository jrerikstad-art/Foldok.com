# PRD — Diagrams

**Surface:** Diagrams (system figures for documents)  
**Product version:** 0.72.0  
**Status:** Dual stacks shipped; canvas→document insert wired; **not yet embedded in main workbench chrome**  
**Primary entry:** `http://127.0.0.1:8766/diagram.html` (Workbench Tools → Diagrammer)  
**Spec SoT:** `DIAGRAM_SPEC.md`

---

## 1. Problem

Technical packages need **printable 2D figures** (wiring, single-line, piping). Generic drawing tools don’t preserve provenance, jurisdiction checks, or document insertion. Photoreal/3D tools are the wrong product.

## 2. Outcome

Users can:

1. Create or open a project-scoped diagram session.
2. Edit layout via **pins** (engine owns geometry / routing / symbols).
3. Validate (including jurisdiction where applicable).
4. Save graph + pins + SVG under `project/diagrams/`.
5. Insert a `DiagramBlock`-style figure into a workbench document section.
6. Export the package via Delivery.

**Honesty:** Feltdok does not claim standard-sheet conformity from a figure alone.

## 3. Users & jobs-to-be-done

| User | JTBD |
|------|------|
| Electrician / installer | “Get a clear wiring / SLD figure into my installation or samsvar package.” |
| Mech / process author | “Document a supply / drainage sketch for the technical file.” |
| Reviewer | “See AI-proposed vs user-confirmed parts before export.” |

## 4. Scope

### In scope (shipped)

**Stack A — `foldok_diagram` (editable canvas)**  
- Sessions: create / move / release / jurisdiction / reset / confirm AI.  
- Persist: `diagram_store` → `*.json` + `*.pins.jsonl` (+ SVG on insert).  
- Bridge: `/api/diagram/bind-project`, `/api/diagram/save`, `/api/diagram/insert-into-doc`.  
- UI: `web/diagram.html` (project picker, document type, insert into workbench).

**Stack B — `diagram_engine` (publish / propose)**  
- Intent → deterministic SVG; propose/confirm; symbol packs; connection diagrams via chat.  
- Used in artifact / figure pipelines and agent tools.

### In scope (target)

- Single **source of truth** for canvas editing: `foldok_diagram`.
- Embed canvas in Workspace project UI (or deep-link with shared project context).
- Migrate remaining publish paths from `diagram_engine` propose/confirm onto foldok graphs (or thin adapter).
- Compliance integration: expository draft vs evidential scaffold (sourced parts only, no invented wires).

### Out of scope

- Visoid / photoreal / 3D CAD.
- Freehand ink as authoritative geometry.
- AI-invented symbols or as-built connections.
- Full KiCad / IEC-certified schematic suite.
- Claiming “complies with IEC 61537 / NEK 400” from a drawing.

## 5. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| D-1 | Graph JSON remains geometry-free; layout lives in pins | P0 |
| D-2 | Engine owns orthogonal routing and symbol placement | P0 |
| D-3 | Export blocked when validation has errors; warnings visible | P0 |
| D-4 | AI provenance is distinguishable; Confirm AI flips ai→user | P0 |
| D-5 | Save requires a project folder; files land under `diagrams/` | P0 |
| D-6 | Insert-into-doc creates/updates a workbench section with SVG + citation path | P0 |
| D-7 | Inserted content is marked unconfirmed until responsible review (banner) | P0 |
| D-8 | Document targets include installation guide, technical file, samsvar, inspection | P0 |
| D-9 | Canvas reachable from workbench with current project preselected | P1 |
| D-10 | Evidential as-built scaffolds never invent connections | P1 |

## 6. Non-functional requirements

- Deterministic SVG for the same graph + pins + style.
- Fixtures for demos (water heater / piping) without customer data.
- Tests: `foldok_diagram/tests` remain green.

## 7. Dependencies

| Depends on | Why |
|------------|-----|
| Workspace | Project bind, document shell |
| Compiler | Cited facts on components when available |
| Compliance | Gap kinds diagram / scaffold / draft |
| Delivery | SVG included in export formats |

## 8. Key APIs / artifacts

- `/api/diagram/session`, `/api/diagram/session/*`, `/api/diagram/save|open|propose`
- `/api/diagram/bind-project`, `/api/diagram/insert-into-doc`
- `diagram_sessions.py`, `diagram_store.py`, `diagram_document.py`
- Packages: `foldok_diagram/`, `diagram_engine/` (legacy publish)

## 9. Acceptance criteria

- [ ] User selects project → edits water-heater fixture → Insert into installation guide succeeds.
- [ ] `project/diagrams/` contains graph, pins, and SVG after insert.
- [ ] Document section `block_type` is `DiagramBlock` with `foldok_diagram` metadata.
- [ ] Export-blocked diagrams cannot insert without `force` (and force is logged / discouraged in UI).
- [ ] No product copy claims IEC/NEK compliance from the figure alone.

## 10. Open decisions

- Timeline to retire or wrap `diagram_engine` for new electrical work.
- Whether piping / mechanical profiles share the same canvas chrome as electrical.

## 11. References

`DIAGRAM_SPEC.md`, `web/diagram.html`, `foldok_diagram/README.md`
