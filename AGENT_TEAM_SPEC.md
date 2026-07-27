# AGENT_TEAM_SPEC.md
Status: active · aligns with ONE_AGENT_SPEC v1.0 + LEARNING_AND_BOUNDARIES + ENGINE_CONTRACT

**Authority:** `ONE_AGENT_SPEC.md` is the closed model (one agent + hats + skills + tools).  
This file holds compose/CAD paths and the skills catalogue pointer.

## User-manual compose path (canonical)

```
User / Wireframe tool
        │
        ▼
document-type-router → get_document_type / materialise_template
        │                    (registry/document-types/*.yaml)
        ▼
Agent loads primary skills from type YAML + materialised template
        │
        ▼
CompositionEngine.compose(...)
        │
        ├── enforces required sections
        ├── forces preferred block types
        └── produces Document AST
        │
        ▼
Tools (regenerate_section, force_block, propose_diagram, set_image, run_qa …)
        │
        ▼
LayoutTree → Render (HTML / PDF)
```

- Wireframe / sketch is optional input — never the source of layout tokens.  
- **Registry YAML** = type brain; materialised template = structure contract; skill = playbook; engine = enforcement.  
- Compile/gap facts still come from `templates/*.json` when `workbench_template` is set (index layer).  
- Tools only mutate AST or confirm visuals; DesignSystem + LayoutTree own paint.

### CAD / FreeCAD path
```
Source (STEP / FCStd / DXF)
        │
        ▼
FreeCAD tools (read-only, engine-owned)
        │
        ▼
Facts + DiagramBlock / ImageBlock proposals
        │
        ▼
CompositionEngine + DiagramEngine  (user confirms views)
```
Skill: `cad-inspector`. Tools: `freecad_*` in `ENGINE_TOOLS.md`. Never invent dimensions.

## Model
One project agent (orchestrator)  
→ loads SKILL.md by intent  
→ calls deterministic engines via tools (`ENGINE_TOOLS.md`)  

```
One project agent
        │
        ▼ loads skill by intent
┌──────────┬───────────┬──────────┬───────────┬─────────┐
│ Ingest   │ Structure │ Compose  │ Visual    │ Render  │
│ engine   │ engine    │ engine   │ proposer  │ engine  │
└──────────┴───────────┴──────────┴───────────┴─────────┘
        ▲ user confirms / edits AST / clicks section
```

## Rules (unchanged)
- One conversation identity. No parallel agent personas.
- Skills propose AST fragments or ops. Engines own DesignSystem, LayoutTree, citations, state.
- After index: index-only (HARD). Skills do not re-read originals unless user re-indexes.
- LLM never paints layout or invents facts.
- Skills do not swarm-call each other; the orchestrator sequences skill → tools.

## Stage → Engine → Typical tools / skills
| Stage     | Engine              | Tools / skills                          |
|-----------|---------------------|-----------------------------------------|
| Route     | Document Type Registry | document-type-router, list/get/materialise |
| Ingest    | Ingest + FreeCAD    | ingest-pdf-to-ast, spec-splitter, pdf, file-organizer, cad-inspector |
| Structure | Structure / gaps    | project-setup, force-blocks, form-filler, project-director |
| Compose   | CompositionEngine   | user-manual, force-blocks, graphic-design, lead-engineer, technical-writer |
| Visual    | DiagramEngine + CAD | diagram-proposal, cad-inspector, graphic-design → user confirm |
| Research  | Orchestrator        | research-assistant, lead-engineer       |
| Render    | Render (print-first)| pdf, docx, DesignSystem + LayoutTree, graphic-design |
| QA        | Orchestrator        | qa-professional-manual, graphic-design, project-director, lead-engineer, technical-writer, compliance-manager |

## UI implication
Stages are visible. Section click → “skriv / bytt bilde / endre rekkefølge” maps to existing tools (`regenerate_section`, `set_cover`, layout tools). Skills make the instructions consistent; they do not replace the tools.

## Skills library
See `skills/README.md`. Tool surface: `ENGINE_TOOLS.md`. Registry: `registry/README.md`.

| Skill | Path |
|-------|------|
| document-type-router | `skills/core/document-type-router/` |
| hybrid-knowledge | `skills/core/hybrid-knowledge/` |
| location-map | `skills/core/location-map/` |
| user-manual | `skills/core/user-manual/` |
| force-blocks | `skills/core/force-blocks/` |
| qa-professional-manual | `skills/core/qa-professional-manual/` |
| ingest-pdf-to-ast | `skills/core/ingest-pdf-to-ast/` |
| file-organizer | `skills/core/file-organizer/` |
| research-assistant | `skills/core/research-assistant/` |
| form-filler | `skills/core/form-filler/` |
| cad-inspector | `skills/core/cad-inspector/` |
| graphic-design | `skills/core/graphic-design/` |
| project-director | `skills/core/project-director/` |
| lead-engineer | `skills/core/lead-engineer/` |
| technical-writer | `skills/core/technical-writer/` |
| compliance-manager | `skills/core/compliance-manager/` |
| spec-splitter | `skills/construction/spec-splitter/` |
| project-setup | `skills/construction/project-setup/` |
| pdf | `skills/document-generation/pdf/` |
| docx | `skills/document-generation/docx/` |
| contract-review | `skills/contract-review/contract-review/` |
| diagram-proposal | `skills/diagram-proposal/diagram-proposal/` |

## Next
Wire the orchestrator to load `user-manual` + `qa-professional-manual` by intent and run one end-to-end pass on a real source set to measure quality delta.
