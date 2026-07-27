---
name: user-manual
description: |
  Structure content as a professional user manual. Enforce section order and convert
  loose content into EngineeringTable, Procedure, RevisionHistory, and CalloutBox.
  Output is Document AST only — never free markdown or layout.
use_when: |
  user asks for a user manual / installation guide / operation manual,
  or document_type is user_manual / manual / brukermanual
  (after document-type-router has selected user_manual from the registry)
---

# User Manual Skill

## Pipeline
```
User / Wireframe tool
        │
        ▼
document-type-router → get_document_type(user_manual)
        │
        ▼
materialise_template(user_manual)   # registry/document-types/user_manual.yaml
        │
        ▼
Agent loads skill "user-manual" + materialised template
        │
        ▼
CompositionEngine.compose(...)
        │
        ├── enforces required sections (from registry)
        ├── forces preferred block types (from registry)
        └── produces Document AST
        │
        ▼
Tools (regenerate_section, force_block, propose_diagram, set_image, run_qa …)
        │
        ▼
LayoutTree → Render (HTML / PDF)
```

## Section order & preferred blocks
**Source of truth:** `registry/document-types/user_manual.yaml`  
(Do not invent a parallel list in chat.)

Load via `get_document_type("user_manual")` or use the materialised template sections.

Typical required core (see YAML for full list): cover → legal → symbols → summary →
product_description → technical_specifications → identification → revision_history.

## Conversion rules
- Specs / parameters / glossary / data lists → EngineeringTable or ParameterGrid  
- Assembly, installation, operation, maintenance, troubleshooting steps → Procedure (numbered steps + optional warnings)  
- Revision history / changelog → RevisionHistory  
- Risks, warnings, notes, requirements → CalloutBox (correct variant)  
- Never leave [MANGLER] or “oppgi” in running prose — collect into final “Information Still Required” EngineeringTable  

## Output contract
Return a Document AST (or equivalent JSON) with the section order and forced block types from the registry.  
CompositionEngine + DesignSystem + LayoutTree own all visual decisions.  
Do not invent facts. Do not paint layout.

## Profile layers
| Layer | File | Role |
|-------|------|------|
| Type brain | `registry/document-types/user_manual.yaml` | Structure, blocks, compliance, skills |
| Composition profile | `schemas/user-manual-template-v1.json` | Profiles (`single_product` \| `system`) |
| Compile / gaps | `templates/user_manual.json` | Facts + MANGLER for workbench |
