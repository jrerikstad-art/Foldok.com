# Document Type Registry

The **brain** for what a document type is: required structure, preferred
blocks, compliance metadata, skills, and tools.

```
registry/
├── document-types/
├── frameworks/
├── knowledge/          # vendor-neutral profiles (corrosion, …)
├── calculations/       # schema_core + steel/ + gfrp/ + general formulas
├── materials/          # _material_schema + steel/*.yaml + gfrp/_template.yaml
└── sections/           # _section_schema + steel/*.yaml
```

## Structural profiles (Phase 1) — not legal compliance

See **`COMPLIANCE_POLICY.md`**. Foldok never claims NEK/ISO/NEC/CE compliance.

Every type may declare:

- `regions` — `eu` · `eea` · `uk` · `no` · `us` · `ca` · `au` · `international`
- `domains` — `electrical` · `machinery` · `pressure` · `construction` · `process` · `marine` · `general`
- `obligation_types` — design / installation / inspection / operation / maintenance / handover
- `evidence_types` — drawing, test_record, photo, declaration, …

Framework profiles under `registry/frameworks/` define **evidence requirements**
only. Foldok does not store full legal text and does not decide legal pass/fail.
API responses include `disclaimer` and `legal_compliance_claimed: false`.
Prefer package language: coverage %, “ready for review”, missing evidence kinds.

Project state carries:

```yaml
compliance:
  regions: [eu, no]
  domains: [machinery, electrical]
  frameworks: [eu_machinery]          # user-confirmable
  suggested_frameworks: [...]
  confirmed: false
```

APIs: `/api/compliance/frameworks`, `/api/compliance/suggest`, `/api/compliance/gaps`.

## Calculation library (Phase 1)

Curated formulas under `registry/calculations/`. See **`CALCULATION_SPEC.md`**.
Engine binds project facts → inputs, evaluates `formula_code`, user confirms
before report insert. Never LLM arithmetic.

APIs: `/api/calculations/profiles|suggest|propose|set-input|confirm`.

## Materials & sections

See **`MATERIALS_SPEC.md`**. Steel grades + sections feed calculation `binds`.
GFRP is datasheet-driven. Never claims Eurocode/composite approval.

APIs: `/api/materials/list|get|suggest`, `/api/sections/list|get`.

## Knowledge packs

See **`registry/knowledge/README.md`**. Vendor-neutral vocabulary and checklists
(corrosion forms, C-classes, galvanic rules, `CorrosionProtectionNote` block).
Not manufacturer content; not automatic code pass/fail.

APIs: `/api/knowledge-packs/list|get|gaps|render-note`.

Engine: `local_app/knowledge_registry.py`.

## How the agent uses it

1. Skill `document-type-router` matches intent → type id  
2. Tool `get_document_type` loads the YAML  
3. Tool `materialise_template` builds a concrete section list for CompositionEngine  
4. `compliance-manager` loads structural profiles + evidence gaps (never invents rules; never stamps legal conformity)  

Workbench compile/gap templates (`templates/*.json`) remain the **facts /
MANGLER** layer. Registry types may point at them via `workbench_template`.

**How to author new templates:** see `TEMPLATE_STANDARD.md`.

## Tools

See `ENGINE_TOOLS.md` → Document Type Registry:

- `list_document_types` (optional `industry` / `region` / `domain`)
- `get_document_type`
- `materialise_template`

Implementation: `local_app/document_type_registry.py`, `local_app/compliance_engine.py`
