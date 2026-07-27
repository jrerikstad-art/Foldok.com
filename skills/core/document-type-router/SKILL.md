---
name: document-type-router
description: |
  Identify the correct document type from user intent or project context
  and retrieve its full definition from the Document Type Registry.
use_when: |
  user asks for a new document,
  project context suggests a document type,
  or the agent needs required structure and compliance rules
---

# Document Type Router Skill

## Goal
Act as the entry point to the Document Type Registry (the brain).  
Select the right document type and return its complete definition so the rest of the system can materialise a template and compose correctly.

## Workflow
1. Analyse user request and project context.  
2. Match against known types and aliases in the registry (`list_document_types` / alias match).  
3. If several types are possible, ask a short clarifying question or rank them.  
4. Call `get_document_type` for the chosen type.  
5. Optionally call `materialise_template` to create a concrete instance for this project.  
6. Load **primary** skills from the type definition, then call listed tools (`compose_document`, `run_qa`, …).

## Registry location
`registry/document-types/*.yaml` — single source of truth for structure, preferred blocks, compliance notes, skills, and tools.

Do **not** invent a parallel section list in chat. Look it up.

## Output
- Selected document type id  
- Full type definition (from `get_document_type`)  
- Recommended skills and tools to load next  
- Optional materialised template (sections + writing rules) ready for CompositionEngine  

## Hard rules
- Never invent compliance rules that are not in the registry entry.  
- Never skip required sections from the type definition.  
- Prefer `update_document_from_sources` when a document of this type already exists and new files arrive.
