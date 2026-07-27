---
name: project-setup
description: |
  Inventory project files, classify document types (drawings, specs, contracts,
  bids), and build initial context for the Document AST. Use at the start of
  any new project.
use_when: |
  new project folder or set of documents is provided,
  need to classify files and prepare context before composition
---

# Project Setup

## Instructions
1. Scan provided folder or file list.  
2. Classify each file:
   - Drawings → DrawingReference / image blocks  
   - Specifications / manuals → text for ingestion  
   - Contracts → contract-review skill  
   - Bids / quotes → tables  
3. Produce initial context summary (project name, key documents, missing items).  

## Output
```json
{
  "project_name": "...",
  "key_documents": [...],
  "missing": ["intended_use", "dimensions"],
  "classified_files": [...]
}
```

Feeds Structure / Composition. Does not invent facts or create layout.
