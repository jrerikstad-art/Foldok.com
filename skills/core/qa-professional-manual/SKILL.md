---
name: qa-professional-manual
description: |
  Quality-check a generated Document AST or rendered draft against the Document
  Type Registry and professional manual standards. Flag missing sections, weak
  tables, placeholder images, residual [MANGLER] prose, and inconsistent structure.
use_when: |
  after composition or render, user asks to review / check quality /
  “is this good enough”, or before final export
---

# QA Professional Manual Skill

## Checklist
1. Section order matches **`get_document_type` required (+ recommended if materialised)** for the active type  
2. Specs live in EngineeringTable / ParameterGrid per `preferred_blocks`, not paragraphs  
3. Procedures are numbered Procedure blocks where the type requires them  
4. No [MANGLER] / “oppgi” left in running text  
5. Missing facts collected in one structured section  
6. Figures / diagrams have captions; missing ones are explicit placeholders  
7. RevisionHistory present when the type lists it as required  
8. Callouts use correct variants  
9. `compliance_notes` from the registry entry are addressed or explicitly residual  

## Output
Structured report only:
- Pass / Fail per item  
- Concrete fixes (e.g. regenerate_section X, force EngineeringTable on Y)  
- Suggested tool calls for the orchestrator (`run_qa`, `force_block`, `update_document_from_sources`, …)  

Does not rewrite the document. Proposes ops only.

## Registry
Always load the type definition first. Do not hard-code a user-manual-only checklist when the document is a datasheet, samsvarserklæring, etc.
