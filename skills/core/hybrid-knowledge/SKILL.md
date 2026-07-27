---
name: hybrid-knowledge
description: |
  Use the project-local HybridKnowledgeEngine: editable Excel findings registry
  plus optional LanceDB semantic cache. Source of truth stays in the user's
  project folder — never copy findings outside.
use_when: |
  user asks what we know about a component / dimension / property,
  after CAD or PDF extraction produces structured facts,
  when searching findings semantically,
  or when syncing index facts into the living findings workbook
---

# Hybrid Knowledge Skill

## Goal
Treat `project_findings.xlsx` inside the project folder as the **editable memory**
for engineering findings. LanceDB under `.foldok_index/` is only a fast cache.

## Location (always inside the project)
| Path | Role |
|------|------|
| `<project>/project_findings.xlsx` | Source of truth (user-editable) |
| `<project>/.foldok_index/` | Optional vector cache (safe to delete) |

## Workflow
1. Ensure engine is open on the project folder (`knowledge_index_project`).  
2. After ingest / FreeCAD / user input → `knowledge_update_finding` (with citation).  
3. Answer “what do we know?” → `knowledge_get_findings` first (structured), then
   `knowledge_semantic_search` if the ask is fuzzy.  
4. If the Excel was edited by hand → `knowledge_rebuild_index`.  
5. Feed cited findings into Document AST via existing compose / gap tools — do not invent values.

## Tools
- `knowledge_index_project`
- `knowledge_get_findings`
- `knowledge_update_finding`
- `knowledge_semantic_search`
- `knowledge_rebuild_index`
- `knowledge_import_index_facts` (map Foldok cache facts → Excel rows)

## Hard rules
- Never invent dimensions or properties — only write what was extracted or user-confirmed.  
- Every row must carry `citation` (file / view / excerpt).  
- Never move `project_findings.xlsx` or findings data outside the project folder.  
- Prefer Excel filters for exact component/property; use semantic search for open language.  
- After new technical files: still prefer `reindex` → then import facts into the registry.  
