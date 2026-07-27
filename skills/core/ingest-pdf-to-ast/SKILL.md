---
name: ingest-pdf-to-ast
description: |
  Ingest one or more PDFs and produce structured facts, section map, tables,
  and image references ready for the Document AST. Use at the start of a
  document generation pipeline.
use_when: |
  user uploads PDFs, asks to ingest a manual/spec/drawings, or starts a new
  project from source documents
---

# Ingest PDF to AST Skill

## Instructions
1. Extract text, tables, and image locations from the PDF(s).  
2. Identify logical sections (headings, TOC, page breaks).  
3. Extract all tables as structured data.  
4. Collect explicit missing facts (fields that cannot be filled).  
5. Produce a clean intermediate representation:

```json
{
  "title": "...",
  "facts": { ... },
  "sections": [
    {
      "type": "summary|technical_specs|assembly|...",
      "title": "...",
      "text": "...",
      "tables": [...],
      "images": [{"role": "figure|hero|exploded", "caption": "...", "page": N}]
    }
  ],
  "missing": ["model_no", "intended_use", ...]
}
```

## Rules
- Do not invent values.  
- After the project index exists, subsequent runs must stay index-only unless the user explicitly re-indexes.  
- If a Document AST already exists and the user adds files, prefer engine tools
  `reindex` → `diff_index` → `update_document_from_sources` (see `ENGINE_TOOLS.md`)
  instead of composing a brand-new document.  
- Output feeds Structure / Composition engines. Never produce layout or free-form markdown.
