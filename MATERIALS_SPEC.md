# MATERIALS_SPEC.md — Material + Section + Calculation schema

Canonical claim boundary (same as compliance / calculations):

> Foldok holds **material property data and typical design checks**.  
> It does **not** replace a structural engineer or claim code certification.

Concrete YAML lives under `registry/` — this doc is the product contract.

---

## Layout

```text
registry/
  calculations/
    schema_core.yaml              # Quantity + units
    _calculation_schema.yaml
    steel/axial_tension_simple.yaml
    steel/bending_simple.yaml
    gfrp/axial_tension_simple.yaml
    *.yaml                        # general library (area, ohm, …)
  materials/
    _material_schema.yaml
    steel/s235.yaml … s460.yaml
    gfrp/_template.yaml
  sections/
    _section_schema.yaml
    steel/ipe200.yaml …
```

## Quantity

Every formal numeric field:

```yaml
{ value, unit, source, status, note }
# status: bound | missing | user_provided | assumed
# source: fact_id | datasheet_ref | user_entry | profile_default | catalog | formula
```

## Steel MVP

| Asset | Examples |
|-------|----------|
| Materials | `steel_s235` … `steel_s460` — EN 10025 *family label*, typical \(f_y\), \(E\) in GPa |
| Sections | `IPE200`, `HEA200`, `RHS100x50x5` — geometry + \(A,I,W\) |
| Checks | `steel_axial_tension_simple`, `steel_bending_simple` — **unfactored** |

```text
N_rd = A * fy / 1000   # mm²·MPa → kN
U    = N_ed / N_rd
```

No silent \(\gamma_{M0}\). Assumptions list “no partial factors.”

## GFRP template

`gfrp_template` — directional \(E_1,E_2,G_{12}\), \(X_t,X_c,Y_t,Y_c,S_{12}\) start **missing**.  
Bind from datasheet → `status: from_datasheet`.  
Check: `gfrp_axial_tension_simple` uses \(X_t\) only; always flag manufacturer method.

## Binding rules

1. Load material + section profiles  
2. Map project facts → loads where possible  
3. Any required `missing` → `needs_input`  
4. Complete → evaluate `formula_code` (multi-statement OK) → `ready_for_review`  
5. User confirms → `confirmed` → Calculation / Material block in report AST  
6. Never label “Eurocode/ISO compliant” — only “simple check, assumptions listed”

## APIs

`/api/materials/*` · `/api/sections/*` · `/api/calculations/propose`  
(`material_id`, `section_id`, `material_overrides`)

Engines: `local_app/materials_engine.py`, `local_app/calculation_engine.py`
