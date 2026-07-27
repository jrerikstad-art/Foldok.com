---
name: pdf
description: |
  Extract text, tables, and structure from PDFs. Create or manipulate PDFs.
  Use for ingestion or final rendering steps involving PDF files.
use_when: |
  user mentions PDF, extract from PDF, create PDF, merge PDFs, etc.
---

# PDF Skill

## Core capabilities
- Extract text and tables (including scanned PDFs)  
- Merge, split, rotate pages  
- Create new PDFs from structured content  
- Fill forms, add annotations, watermarks  

## Rules
- Used by Ingest and Render engines.  
- Never used to generate free-form prose.  
- Final PDF export is owned by the Render engine + DesignSystem + LayoutTree.  

## Output
Structured extraction results or a rendered PDF file path / bytes.  
No layout invention.
