# PRD — Compliance

**Surface:** Compliance (structural profiles, evidence gaps, completion modes)  
**Product version:** 0.72.0  
**Status:** Phase-1 APIs shipped (0.68); `foldok_gaps` library shipped; **workbench UI largely unwired**  
**Primary entry (today):** `/api/compliance/*`, `/api/knowledge-packs/*`; editor MANGLER rail  
**Target entry:** Package status + gap list inside Workspace

---

## 1. Problem

“30 mangler” feels like a wall. Users either invent evidence, skip structure, or ask the product to declare legal conformity it cannot decide.

## 2. Outcome

Feltdok helps users **build and check a documentation package against a structural profile**:

- Gaps are objects with stable IDs, authority, and offers — not renumbered list rows.
- Modes change **gating and language**, not evaluation.
- **Complete ≠ compliant.** Humans (or licensed counsel / competent persons) decide legal conformity.

**Canonical claim boundary:** `COMPLIANCE_POLICY.md` — product language must not say NEK/ISO/NEC/CE compliant.

## 3. Users & jobs-to-be-done

| User | Mode | JTBD |
|------|------|------|
| Prototype / builder | Build | “Show me what Feltdok can help finish — don’t block me with red walls.” |
| Reviewer | Review | “What is still open before export?” |
| Competent person | Compliance | “What evidence kinds are missing for this profile before I sign?” |

## 4. Scope

### In scope (shipped)

- Structural frameworks under `registry/frameworks/` (electrical installation, EU machinery, US electrical structural, general inspection, declaration pattern).
- `compliance_engine.py`: suggest frameworks, evidence gaps, package status (`ready_for_review`, coverage %).
- APIs always return `disclaimer` + `legal_compliance_claimed: false`.
- Document-type registry profiles (technical file, samsvar, inspection, handover, confidentiality, opportunity, product strategy, …).
- Template MANGLER gaps in the editor (dismiss / override / fill) — primary UX today.
- Knowledge packs (corrosion, cable management) as neutral vocabulary + checklists.
- **`foldok_gaps` library:** `evaluate` / `options` / `resolve` / `gate`; Build / Review / Compliance modes; evidential guard; four packs.

### In scope (target — WO 0.64)

- Gap list UI grouped by batch (`session.batches()`).
- Resolve sheet driven by `session.options(gap_id)` with generative vs form distinction.
- Measurement forms + capture handoff; confirm actions with named `by`.
- Mode as a document property (default **build**); build exports watermarked.
- Pack authoring via JSON/YAML + `pack.validate()` in CI.
- Persistence: documents / packs / diagrams as local text.

### Out of scope

- Storing or redistributing copyrighted standard clause text.
- Automatic legal pass/fail against a code.
- A “lite” product with a forked data model.
- AI inventing measurements, serial numbers, signatures, or as-built connections.
- Completeness percentage presented as a compliance score.

## 5. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| P-1 | UI and APIs use only allowed claim language from `COMPLIANCE_POLICY.md` | P0 |
| P-2 | Gap identity is content-addressed; resolving one gap never renumbers others | P0 |
| P-3 | `evaluate()` is pure — mode does not change the gap set, only gate/framing | P0 |
| P-4 | Generative resolvers are never offered for evidential requirements | P0 |
| P-5 | Build mode never blocks export; compliance mode may gate; build exports watermarked | P0 |
| P-6 | Package status exposes open gaps, blocking count, coverage %, ready_for_review | P0 |
| P-7 | Workspace shows package status + gap batches for the active document | P1 |
| P-8 | “Prepare everything” creates forms/scaffolds that need no authoring (`prepare_everything`) | P1 |
| P-9 | Diagram scaffolds for evidential as-builts place only sourced parts and draw no invented wires | P1 |
| P-10 | Knowledge packs link into selection checklists without vendor content | P2 |

## 6. Non-functional requirements

- Same engine serves multiple segments via **requirement packs**, not forked section code.
- Tests: `foldok_gaps/tests` + compliance phase-1 scripts remain green.
- Export gate (Delivery) must read compliance mode when wired — not invent a second policy.

## 7. Dependencies

| Depends on | Why |
|------------|-----|
| Compiler | Facts/index satisfy evidence requirements |
| Workspace | Mode switch, gap UI, confirmations |
| Diagrams | Diagram artifacts for schematic / scaffold gaps |
| Delivery | Watermark + gated export |

## 8. Key APIs / artifacts

- `/api/compliance/frameworks|suggest|gaps`
- `/api/knowledge-packs/list|get|gaps|render-note`
- `/api/registry/*` (document types)
- Packages: `compliance_engine.py`, `foldok_gaps/`, `registry/frameworks/`, `registry/knowledge/`

## 9. Acceptance criteria

- [ ] No UI string claims NEK/ISO/CE compliance without human determination framing.
- [ ] Switching Build → Compliance on an existing document reveals the full gap list without rewriting stored work.
- [ ] Evidential gap resolve path creates empty form / capture task — never filled measurements by AI.
- [ ] `pytest foldok_gaps/tests` green; phase-1 compliance tests green.
- [ ] After UI wiring: a 30+ gap job collapses to batch actions on screen.

## 10. Open decisions

- Unify MANGLER template gaps, framework evidence gaps, and `foldok_gaps` into one rail without three competing models.
- Who signs N/A and confirmations (free-text name vs device identity vs signatory record).

## 11. References

`COMPLIANCE_POLICY.md`, `WO-0.64-completion-engine.md`, `foldok_gaps/README.md`, `registry/README.md`, `PRICING_AND_STORY.md` (claim language)
