# CALCULATION_SPEC.md — library formulas + user confirm

Same claim boundary as `COMPLIANCE_POLICY.md`:

> Engine prepares data and formulas.  
> Auto-fills only when the answer is obvious and sourced.  
> Everything else is proposed for **user verification**.

This is a **Calculation Engine**, not a silent certified-result engine.
It is **Level-0 groundwork** toward `VERIFICATION_SPEC.md` Level 3 check library.

---

## Flow

```text
Project / document facts
        ↓
Suggest relevant calculations (profile or intent)
        ↓
Pull inputs from indexed data (with citations)
        ↓
Propose formula + filled values
        ↓
If all inputs present & unambiguous → draft result (ready_for_review)
If anything missing / ambiguous → needs_input
        ↓
User confirms → locked calculation block in report
```

## Principles

| Principle | Meaning |
|-----------|---------|
| Data from the project | Prefer extracted facts with source |
| Formula is visible | Always show expression / LaTeX |
| Obvious vs verify | Auto only when complete & unambiguous |
| User owns the number | Confirm before formal report |
| Traceable | Inputs cite source; result has revision |

**HARD:** LLM never invents numeric engineering results. AI may suggest which
profile fits and map text → input keys. Arithmetic is curated `formula_code`.

## Auto-draft allowed only if

1. Every required input is present in the project index (or explicit user entry)
2. Units are consistent or convertible by known rules
3. Formula is from the approved library (`registry/calculations/`)
4. Result is **not** formal until `status=confirmed`

Always ask / verify if missing, conflicting, unit-unclear, jurisdiction-dependent,
or `safety_critical: true` (still computes, but UI must emphasize confirm).

## State machine

| Status | Meaning |
|--------|---------|
| `draft` | Created, not yet evaluated |
| `needs_input` | Missing / ambiguous / formula error |
| `ready_for_review` | All inputs bound; result computed |
| `confirmed` | User locked for report insert |

Changing an input after confirm bumps `revision` and clears confirm.

## Ship set (v1 profiles)

| id | Formula |
|----|---------|
| `rect_area` | \(A = L \times W\) |
| `circle_area` | \(A = \pi r^{2}\) |
| `volume_rect` | \(Vol = L \times W \times H\) |
| `cable_length_simple` | \(L_{tot} = L_{route}(1 + s/100)\) |
| `ohms_law` | \(V = I R\) |
| `power_dc` | \(P = V I\) |
| `wind_dynamic_pressure` | \(q = 0.613 V^{2}\) (assumption note) |
| `utilization` | \(U = F_{ed}/F_{rd}\) |
| `steel_axial_tension_simple` | \(N_{rd}=A f_y\) (unfactored); binds material+section |
| `steel_bending_simple` | \(M_{rd}=W_y f_y\) (unfactored) |
| `gfrp_axial_tension_simple` | \(N_{rd}=A X_t\) — datasheet \(X_t\) required |

Materials / sections: see `MATERIALS_SPEC.md` (Quantity schema).

## AI vs engine

| Role | Does |
|------|------|
| AI | Suggest profile; map facts → keys; explain formula in plain language |
| Engine | Store formulas; unit checks; evaluate; render block; confirm state |
| User | Supply missing inputs; accept assumptions; confirm for report |

## APIs

- `POST /api/calculations/profiles`
- `POST /api/calculations/suggest`
- `POST /api/calculations/propose`
- `POST /api/calculations/set-input`
- `POST /api/calculations/confirm`

Implementation: `local_app/calculation_engine.py` · profiles in `registry/calculations/`.
Report block: `CalculationBlock` (`type: calculation`).

## Not ScaffCalc

Cross-trade documentation helper with a small explicit library.
Import external tool results later as **cited external calculations** —
do not reimplement full structural systems here.
