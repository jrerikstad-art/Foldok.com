# ENGINE_TOOLS.md
Status: draft · v0.6 · aligns with ONE_AGENT_SPEC, ENGINE_CONTRACT, SOURCE_INTERACTION_SPEC

## Purpose
The single project agent calls these deterministic tools.  
Skills propose structure and intent.  
Tools execute and own state, layout, citations, and side-effects.

Rules that never change:
- Tools never invent facts.
- Tools never paint layout (DesignSystem + LayoutTree own that).
- After the project index exists → index-only unless the user explicitly re-indexes.
- Destructive or irreversible actions require explicit user confirmation.
- When the user adds new technical files, prefer **reindex → diff_index → update_document_from_sources** over creating a brand-new document.
- Document structure knowledge lives in **`registry/document-types/`** — look it up; do not hard-code.

---

## Tool Surface

### Document Type Registry

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `list_document_types` | `industry?: string` | List of `{id, name, aliases, industries}` | Filterable by industry |
| `get_document_type` | `type_id: string` | Full YAML definition as structured object | Aliases accepted |
| `materialise_template` | `type_id: string`, `project_id?: string`, `overrides?: object` | Concrete template instance (sections + rules) ready for CompositionEngine | Applies project context and allowed overrides |

**Preferred new-document path:** skill `document-type-router` → `get_document_type` → `materialise_template` → load primary skills → `compose_document` / `run_qa`.

Workbench HTTP: `POST /api/registry/list`, `/api/registry/get`, `/api/registry/materialise`.  
Implementation: `local_app/document_type_registry.py`.

### Hybrid Knowledge (project-local findings)

Excel `project_findings.xlsx` is the editable source of truth inside the project folder.  
Optional `.foldok_index/` LanceDB cache for semantic search (rebuildable).  
Skill: `hybrid-knowledge`. Implementation: `hybrid_knowledge_engine.py`.

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `knowledge_index_project` | `project_id`, `force_rebuild?: bool` | `{ registry_path, rows, vectors_rebuilt }` | Ensures Excel exists; optionally rebuilds vectors |
| `knowledge_get_findings` | `project_id`, `component?`, `property_name?`, `source_file?` | `Finding[]` | Filters Excel registry |
| `knowledge_update_finding` | `project_id`, `finding: object` | `{ finding_id }` | Upsert one row; requires citation |
| `knowledge_semantic_search` | `project_id`, `query`, `limit?: number` | `Finding[]` | LanceDB if available; else Excel text fallback |
| `knowledge_rebuild_index` | `project_id` | `{ rows_indexed }` | Rebuild vectors from Excel only |
| `knowledge_import_index_facts` | `project_id` | `{ imported: number, ids: string[] }` | Map Foldok cache facts → Excel |

**Privacy:** findings never leave the project folder. Deleting `.foldok_index/` is safe.

Workbench HTTP: `POST /api/knowledge/*`.

### Location & maps (project-local OSM)

Stored in the same `project_findings.xlsx` (location columns).  
Maps written only to `assets/maps/`. Skill: `location-map`.  
Backend: `tools/osm_vector_tiles/` (tile stitch by default; drop-in `custom_vector_renderer.py` for full vector tiles).

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `get_location` | `project_id` | location row or null | Primary `LOC-PRIMARY` |
| `set_location` | `project_id`, `address`, `municipality?`, `postal_code?`, `latitude?`, `longitude?`, `location_type?` | location row | Geocodes via Nominatim when coords missing |
| `generate_location_map` | `project_id`, `style?`, `width?`, `height?`, `zoom?`, `color_overrides?`, `output_format?` | relative path under `assets/maps/` | Updates `map_image_path` |
| `propose_location_map` | same as generate + `caption?` | `{ needs_confirm, ImageBlock proposal, location }` | Never auto-inserts |

Styles: `default` · `minimal` · `technical` · `satellite`.

### Index & Incremental Update

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `reindex` | `project_id`, `confirm?: bool` (default false for small changes) | `{ added, changed, removed, total_files, index_version }` (+ `job_id` when started) | Rescans the project folder and updates the index. Returns a clear diff. Requires `confirm=true` if \|added\|+\|changed\|+\|removed\| > 15. Does **not** modify any Document AST. |
| `diff_index` | `project_id`, `since_version?: string` | `{ added: Source[], changed: Source[], removed: Source[] }` | Shows what has changed since the last index (or since a given version). Read-only. |
| `update_document_from_sources` | `document_id`, `source_ids?: string[]`, `mode?: "merge" \| "replace_sections"` | `{ updated_sections, added_blocks, remaining_gaps, change_summary }` | Merges extracted facts into the **existing** Document AST. Default `"merge"`. Never creates a new document. Preserves user edits and citations. |

#### Preferred agent path (new technical files)

1. `reindex` → see what is new  
2. `diff_index` → understand the delta  
3. `update_document_from_sources` → update the living document  

Workbench HTTP: `POST /api/reindex` (alias `/api/index`), `POST /api/diff-index`, `POST /api/doc/update-from-sources`.  
Chat intents (NO/EN): «reindekser», «hva er nytt», «oppdater dokumentet fra kilder».

#### Detailed contracts

**`reindex`**
```json
{
  "name": "reindex",
  "description": "Rescan the project folder and update the search index. Returns a diff of what changed.",
  "parameters": {
    "project_id": "string (required)",
    "confirm": "boolean (optional, default false)"
  },
  "returns": {
    "added": ["source_id or filename"],
    "changed": ["source_id or filename"],
    "removed": ["source_id or filename"],
    "total_files": "number",
    "index_version": "string"
  },
  "side_effects": "Updates the project index and `.foldok_index_manifest.json`. Does not modify any Document AST."
}
```

**`diff_index`**
```json
{
  "name": "diff_index",
  "description": "Show what files have been added, changed or removed since the last index (or a given version).",
  "parameters": {
    "project_id": "string (required)",
    "since_version": "string (optional)"
  },
  "returns": {
    "added": [{"id": "...", "path": "...", "type": "..."}],
    "changed": [{"id": "...", "path": "...", "type": "..."}],
    "removed": [{"id": "...", "path": "...", "type": "..."}]
  },
  "side_effects": "None (read-only)"
}
```

**`update_document_from_sources`**
```json
{
  "name": "update_document_from_sources",
  "description": "Merge new or changed source facts into the existing Document AST. Prefer this over creating a new document.",
  "parameters": {
    "document_id": "string (required)",
    "source_ids": "string[] (optional – if omitted, use all new/changed sources from latest reindex)",
    "mode": "\"merge\" | \"replace_sections\" (optional, default \"merge\")"
  },
  "returns": {
    "updated_sections": ["section_id", "..."],
    "added_blocks": "number",
    "remaining_gaps": [{"key": "...", "reason": "..."}],
    "change_summary": "Human-readable summary of what was updated"
  },
  "side_effects": "Updates the Document AST in place. Creates a new version entry. Does not overwrite user-verified facts unless mode is replace_sections (engine-owned compiled tables only)."
}
```

**Mode notes for `update_document_from_sources`:**
- `merge` — fill open `[MANGLER]` from index facts; refresh engine-owned tables (`doc_control`, `spec_overview`, `drawings_register`, `bom`) while keeping `cell_overrides` and `user_facts`.
- `replace_sections` — same MANGLER fill + force-refresh of those compiled sections. Free-prose narrative sections are **not** silently rewritten (use `regenerate_section` + confirm).

### Ingest Engine

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `ingest_pdf` | file_path(s), project_id | index update + extraction report | One-shot or incremental |
| `extract_tables` | source_id or file_path | list of structured tables | Used by form + document engines |
| `extract_facts` | source_id | facts dict + missing list | Feeds artifact model |
| `list_sources` | project_id | source list with status | |

### Structure / Gaps

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `get_gaps` | project_id / document_id | list of MANGLER / missing facts | |
| `add_missing_fact` | key, label, reason | updated missing table | |
| `clear_mangel` | key or fact_id | removed from missing list | Only after verified value exists |
| `set_project_fact` | key, value, source | fact written to artifact model | Must cite source |

### Composition Engine

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `compose_document` | document_type **or** materialised template, skill_name (optional) | Document AST | Prefer registry type id; loads skill if provided |
| `load_template` | type_id or template_file | template instance | Prefer `materialise_template` from registry |
| `regenerate_section` | section_id, skill_name or instructions | updated section AST | Section-scoped only |
| `force_block` | block_id or content, target_type | converted block | EngineeringTable / Procedure / etc. |
| `convert_to_table` | content or block_id | EngineeringTable | |
| `convert_to_procedure` | content or block_id | Procedure | |
| `insert_block` | section_id, block, position | updated AST | |
| `move_block` | block_id, new_section / position | updated AST | |
| `delete_block` | block_id, confirm=true | updated AST | |

### Source Interaction (Document view)

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `toggle_source` | source_id, document_id, enabled | document view updated | Index unchanged |
| `exclude_figure` | figure_id / source_id | figure removed from view | |
| `edit_cell` | table_id, row, col, value, source | cell updated + citation | Creates verified_by_user fact |
| `apply_cited` | fact_id or cell | citation written | |
| `refresh_spec_overview` | document_id | table rebuilt from index | |
| `refresh_doc_control` | document_id | doc-control table rebuilt | |

### Visual / Diagram Engine

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `propose_diagram` | template \| profile \| graph, title, section_id? | Proposal: graph + SVG preview + visual_qa | User must confirm; templates: `panel_sld`, `cable_wiring`, `pipe_run`, `drive_train`, `pump_skid` |
| `confirm_diagram` | proposal, confirm=true, graph_overrides? | Final SVG + DiagramBlock payload | Engine draws; insert via `embed_diagram_engine` |
| `list_diagram_templates` | — | Template ids/labels | Low skill barrier |
| `visual_qa` (diagram) | svg \| DiagramEngine | ok / issues (stroke, legend, labels) | Print clarity checklist |
| `set_cover` | image_source or file | cover updated | |
| `set_image` | block_id, image_source, caption | ImageBlock updated | |
| `remove_image` | block_id | image removed | |

### FreeCAD / CAD Engine (external capability — read-only)

Headless FreeCAD (`FreeCADCmd` / Python API). Runs in workbench or controlled
local/Docker process. Skill wrapper: `skills/core/cad-inspector/`.

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `freecad_open` | file_path, project_id | session_id / handle | STEP, IGES, BREP, FCStd, STL, OBJ, DXF; limited DWG |
| `freecad_list_parts` | session_id | assembly tree + part names | Hierarchy only |
| `freecad_extract_dimensions` | session_id, part_id? | bounding boxes, key lengths, diameters | Cite model + measurement; missing → gaps |
| `freecad_extract_bom` | session_id | structured BOM rows | Feeds EngineeringTable |
| `freecad_generate_views` | session_id, view_types[] | image file paths | Ortho / iso / exploded — proposals until confirmed |
| `freecad_section` | session_id, plane / params | section image + measures | Ambiguous → missing-facts |
| `freecad_close` | session_id | cleaned up | Always call when done |

**CAD rules:** never modify source files; never invent dimensions; cache by sha256
in project index; on open failure return explicit error → fall back to image/PDF
ingest; diagram/view insert still requires user confirmation.

### Form Engine

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `fill_form` | template_id or layout, facts | filled form AST / overlay data | |
| `render_form_overlay` | filled_data, background_images | HTML/PDF with positioned fields | |
| `render_form_structure` | filled_data | clean letter-sheet fallback | |

### Render Engine

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `layout_document` | Document AST | LayoutTree | Measurement + pagination |
| `render_html` | LayoutTree + theme | HTML | |
| `render_pdf` | LayoutTree + theme | PDF bytes / path | Print-first |
| `render_docx` | Document AST + theme | .docx | |
| `export` | format, document_id | final file | Paid export path if applicable |

### QA / Orchestrator helpers

| Tool | Inputs | Output | Notes |
|------|--------|--------|-------|
| `run_qa` | document_id, skill=qa-professional-manual | structured QA report | |
| `list_versions` | document_id | version history | |
| `revert_to_version` | document_id, version_id, confirm=true | previous AST restored | |
| `get_document_ast` | document_id | current AST | Read-only |
| `get_layout_tree` | document_id | current LayoutTree | Read-only |

---

## Calling convention (for the single project agent)

1. Load relevant `SKILL.md` by intent.
2. Decide which tools are needed.
3. Call tools with explicit parameters.
4. Surface any `needs_confirm` or `missing` results to the user before irreversible steps.
5. Never let a skill directly mutate the index or paint layout.
6. New files in the project folder → `reindex` (confirm if large) → `diff_index` → `update_document_from_sources` — **not** `compose_document` unless the user asks for a new document.
7. New document ask → `document-type-router` → `list_document_types` / `get_document_type` → `materialise_template` → compose. Do not invent section lists in chat.

## Out of scope for tools
- Inventing missing values
- Free-form prose generation without going through CompositionEngine
- Multi-agent hand-offs
- Background watching / auto-reindex without user action
- Storing or claiming ownership of customer documents outside their own storage
- Modifying customer CAD/source files (FreeCAD tools are read-only)

---

One-line contract:  
**Skills propose. Tools execute. Engines own truth and layout. One agent routes.**
