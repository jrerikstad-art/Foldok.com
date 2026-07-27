# Foldok Skills Library

Playbooks (`SKILL.md`) loaded by the **single project agent** by intent.  
Skills propose AST fragments, section order, block conversions, or tool ops.  
They never paint layout, invent facts, or hold project state.

Deterministic counterparts: `ENGINE_TOOLS.md`.  
Document-type structure: **`registry/document-types/`** (look up; do not hard-code).

## Role vs domain

**Role skills (hats)** — steering lenses, not separate agents:

- `project-director` · `lead-engineer` · `technical-writer` · `compliance-manager`

**Domain skills** — playbooks by document/task type (see tree below).

## Structure

```
skills/
├── core/
│   ├── document-type-router/   ← entry to registry
│   ├── hybrid-knowledge/       ← project_findings.xlsx brain
│   ├── location-map/           ← address + OSM site maps
│   ├── user-manual/
│   ├── force-blocks/
│   ├── qa-professional-manual/
│   ├── ingest-pdf-to-ast/
│   ├── file-organizer/
│   ├── research-assistant/
│   ├── form-filler/
│   ├── cad-inspector/
│   ├── graphic-design/
│   ├── project-director/
│   ├── lead-engineer/
│   ├── technical-writer/
│   └── compliance-manager/
├── construction/
│   ├── spec-splitter/
│   └── project-setup/
├── document-generation/
│   ├── pdf/
│   └── docx/
├── contract-review/
│   └── contract-review/
└── diagram-proposal/
    └── diagram-proposal/

registry/document-types/        ← brain (YAML)
├── user_manual.yaml
├── datasheet.yaml
├── installation_guide.yaml
├── maintenance_manual.yaml
├── samsvarserklaring.yaml
├── inspection_report.yaml
└── industrial_report.yaml
```

## Stage → Skill mapping

| Stage          | Primary skills                                      | Engine owner            |
|----------------|-----------------------------------------------------|-------------------------|
| Route type     | document-type-router                                | Document Type Registry  |
| Knowledge      | hybrid-knowledge                                    | HybridKnowledgeEngine   |
| Location       | location-map                                        | OSM tiles → assets/maps |
| Ingest         | ingest-pdf-to-ast, spec-splitter, pdf, file-organizer, cad-inspector | Ingest + FreeCAD |
| Structure      | project-setup, force-blocks, form-filler, project-director | Structure / checkpoints |
| Compose        | user-manual, force-blocks, graphic-design, lead-engineer, technical-writer | CompositionEngine |
| Visual propose | diagram-proposal, cad-inspector, graphic-design     | DiagramEngine + FreeCAD |
| Research       | research-assistant, lead-engineer                   | Orchestrator + index    |
| Render / Export| pdf, docx, graphic-design                           | Render engine           |
| QA             | qa-professional-manual, graphic-design, project-director, lead-engineer, technical-writer, compliance-manager | Orchestrator + tools |

After the index exists the HARD rule remains: **index-only**. Skills do not re-read source files unless the user explicitly re-indexes. CAD extractionsions are cached by sha256 like PDF index entries.

## New document path

```
User asks for a document
        │
        ▼
document-type-router
        │
        ├── list_document_types / match aliases
        ├── get_document_type
        └── materialise_template
                │
                ▼
Load primary skills from type YAML → compose_document → run_qa
```

## Core set

**Roles:** project-director · lead-engineer · technical-writer · compliance-manager  

**Domain:** document-type-router · hybrid-knowledge · location-map · user-manual · force-blocks · qa-professional-manual · ingest-pdf-to-ast · file-organizer · research-assistant · form-filler · cad-inspector · graphic-design  

Plus: construction (`spec-splitter`, `project-setup`), document-generation (`pdf`, `docx`), contract-review, diagram-proposal.

## Later

bom-takeoff (may lean on `freecad_extract_bom`) · site-diary / meeting-notes · changelog / revision-skill · standards-checker

## Rules of record

- `ONE_AGENT_SPEC.md` — **v1.0 closed model**: one identity, role hats, domain skills, tools  
- `AGENT_TEAM_SPEC.md` — compose / CAD paths + skills catalogue  
- `ENGINE_TOOLS.md` — deterministic tool surface (registry + FreeCAD + index)  
- `registry/README.md` — Document Type Registry  
- `TEMPLATE_STANDARD.md` — how to author templates (shape vs content)  
- `V0_60_PLAN.md` — publishing pipeline first (Composition → LayoutTree)  
- `LEARNING_AND_BOUNDARIES.md` — AI never holds state; engine never guesses  
- `ENGINE_CONTRACT.md` — index-only after ingest; citation rule  
- `artifact_engine/ARCHITECTURE.md` — LLM is architect, not designer  
- `schemas/user-manual-template-v1.json` — composition profile (user-manual); registry is authority for type structure  
