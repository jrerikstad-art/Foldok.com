---
name: force-blocks
description: |
  Convert loose or unstructured content into the correct semantic blocks
  required by the Artifact Engine (EngineeringTable, Procedure, RevisionHistory,
  CalloutBox, etc.). Use when content needs to be forced into professional
  document structure instead of plain prose.
use_when: |
  content contains specifications, parameters, steps, risks, or revision info,
  or post-processing loose LLM output for the Document AST,
  or the active document type lists preferred_blocks in the registry
---

# Force Blocks Skill

## Rules
Prefer **`preferred_blocks` from the active document type**
(`get_document_type` / materialised template). Fallback defaults:

- Specifications / parameters / glossary / data lists → EngineeringTable or ParameterGrid  
- Assembly, installation, operation, maintenance, troubleshooting steps → Procedure with numbered steps  
- Revision history / changelog → RevisionHistory with entries  
- Risks, warnings, notes, requirements → CalloutBox (variant: warning / important / note)  
- Missing information → collect into one structured “Information Still Required” EngineeringTable (never leave [MANGLER] in prose)

## Output
Return content already wrapped in the appropriate block types so it can be dropped directly into `Document.sections[].blocks`.  
Do not invent values. Do not emit layout or styling.

## Registry
When composing, load the type via `document-type-router` first so section → block
mapping comes from `registry/document-types/*.yaml`, not from memory.
