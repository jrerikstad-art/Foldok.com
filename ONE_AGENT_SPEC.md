# ONE_AGENT_SPEC.md
Status: active · v1.0

## Identity
There is **one** project agent.

It is the only conversational identity the user talks to.  
It never spawns parallel agents or separate chat threads.

## Core loop

```
User message
      │
      ▼
One Project Agent
      │
      ├── Role skills
      │     ├── project-director
      │     ├── lead-engineer
      │     ├── technical-writer
      │     └── compliance-manager
      │
      ├── Domain skills
      │     document-type-router, user-manual, force-blocks,
      │     cad-inspector, form-filler, graphic-design,
      │     qa-professional-manual, …
      │
      └── Engine tools
            list/get/materialise document types,
            knowledge_* (findings Excel + optional index),
            get/set_location, generate/propose_location_map,
            ingest_*, force_block, regenerate_section,
            propose_diagram, freecad_*, render_*, run_qa,
            reindex, diff_index, update_document_from_sources, …
```

Document structure is looked up in `registry/document-types/` — never invented in chat.  
Project facts live in `<project>/project_findings.xlsx` (Hybrid Knowledge).  
Site maps go only under `assets/maps/` and require user confirm before AST insert.

## Role skills (hats)

| Role skill          | Responsibility                              | When to load                          |
|---------------------|---------------------------------------------|---------------------------------------|
| `project-director`  | Scope, priorities, missing deliverables, overall package health | Start of project, “what’s missing?”, structure decisions |
| `lead-engineer`     | Technical accuracy, procedures, specs, safety, standards | Writing/reviewing technical sections |
| `technical-writer`  | Clarity, terminology, readability — preserve meaning | Unclear / repetitive prose, tighten wording |
| `compliance-manager`| Mandatory sections, standards/legal completeness, audit readiness | “Is this compliant?”, handover, formal review |

The agent may wear one hat, several, or none.  
Hats are loaded skills, not separate agents.

## Domain skills
Loaded by intent. Examples:

- `document-type-router` (registry entry)
- `hybrid-knowledge`, `location-map`
- `user-manual` + template
- `force-blocks`
- `cad-inspector`
- `form-filler`
- `research-assistant`
- `graphic-design`
- `qa-professional-manual`
- `file-organizer`
- `spec-splitter`, `project-setup`, etc.

Skills only propose AST fragments or tool calls.  
They never hold state and never paint layout.

Full library: `skills/README.md`. Tool surface: `ENGINE_TOOLS.md`.  
Compose path detail: `AGENT_TEAM_SPEC.md`.

## Engine tools
The agent is the only thing allowed to call tools.  
All tools are deterministic and owned by the engines (see `ENGINE_TOOLS.md`).

Key categories:
- Document types (`list` / `get` / `materialise`)
- Hybrid knowledge / findings Excel
- Location + OSM site maps (confirm before AST)
- Ingest / FreeCAD
- Structure & gaps / incremental index
- Composition (`force_block`, `regenerate_section`, …)
- Diagram / visual
- Form
- Render
- QA & versioning

## Decision rules (routing)

1. If the user talks about scope, priorities, or “are we finished?” → load `project-director`.
2. If the user talks about technical content, procedures, specs, or safety depth → load `lead-engineer`.
3. If the user asks to clarify / tighten / improve wording → load `technical-writer`.
4. If the user asks about compliance, standards completeness, or handover readiness → load `compliance-manager` (often with `qa-professional-manual` / `run_qa`).
5. Match the rest of the message to the best domain skill(s).
6. Call the minimum set of tools needed.
7. Surface any missing facts or confirmation requests before irreversible actions.
8. Never invent values. Never bypass DesignSystem / LayoutTree.

## Hard constraints
- One conversational identity only.
- Skills are playbooks, not agents.
- Tools execute; skills propose.
- Engines own state, layout, citations, and measurements.
- After index exists → index-only (unless user explicitly re-indexes).
- User confirmation required for: diagram insertion, file moves, re-index, destructive edits.

## Mental model

```
One Project Agent
      │
      ├── Role skills
      │     ├── project-director
      │     ├── lead-engineer
      │     ├── technical-writer
      │     └── compliance-manager
      │
      ├── Domain skills
      │     user-manual, force-blocks, cad-inspector,
      │     form-filler, graphic-design, qa-professional-manual, …
      │
      └── Engine tools
```

This is the complete, closed model.  
Everything else (templates, skills, tools, DesignSystem) plugs into this single agent.

---

## Workbench continuity (binding UI / chat rules)

Field origin: a second, dumber editor chat answered with feature menus.
That path is dead. Extends FLOW_ONE_OPERATION + COLD_START_SPEC — same
conversation stream from cold start through editing.

### Continuous identity and memory
- ONE conversation thread per project, persisted in state (`conversation: [...]`),
  spanning cold start → checkpoint A → build → editing → export.
- Opening the editor does NOT reset the thread.
- SCOPE ≠ IDENTITY: the scope chip (Prosjekt / Dokument / Seksjon / Utvalg)
  changes attached context only — never persona, history, or capabilities.
- Every in-project chat call attaches engine-built context via
  `build_project_chat_context()` (name, folder, file count, full artifact,
  documents + gaps, fact-key inventory counts only, history).

### Action surface
Editor router: `local_app/editor_chat.py` + `POST /api/doc/chat`.  
Canonical tool names live in `ENGINE_TOOLS.md`. Workbench aliases
(`list_gaps`, `resolve_mangler`, `toggle_source`, `reindex`, `diff_index`,
`update_document_from_sources`, …) map onto that surface.

When the user says they added new technical files, prefer:
`reindex` → `diff_index` → `update_document_from_sources` (merge into the
living Document AST). Do not spin up a new document unless asked.

Rules: money-costing actions surface € and need UI confirm; free writes
may execute then report; completion verbs need a tool receipt in the same
turn; sources and `templates/*.json` are immutable to the agent; reply
budget ≤120 words default / 200 hard; no `##` headings in chat.

### Intent standard
"den mangler registrerings nummer" → map to gap → ask for value or source →
`clear_mangel` / `resolve_mangler` — never a feature menu.

### Sticky layout
Editor grid: `[Kilder 240px] [Dokument flex] [Assistent 320px]`.  
Kilder + Assistent sticky; only the document column scrolls the page;
chat input stays in view.

### Open-ended asks
Ground from index first; search before asking; at most two questions the
index cannot answer; offer a concrete next step with €. No emoji;
no “eller er det noe helt nytt”.

### Acceptance (still required)
1. Same thread from cold-start into editor; recall earlier turns.
2. Gap utterance → resolve without canvas edits.
3. Regenerations show DIFF until Godta.
4. Sticky panels + chat input remain visible on long docs.
5. No invented specs; no `[MANGLER: ukjent kilde]` in prose.
6. Open-ended project asks ground first and do not pretend the folder is empty.
