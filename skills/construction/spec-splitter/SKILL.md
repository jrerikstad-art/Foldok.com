---
name: spec-splitter
description: |
  Split a single bound PDF (project manual, specification, user manual) into
  individual section PDFs + extracted text. Use when one large combined PDF
  needs to be broken down for further processing.
use_when: |
  user uploads a single large PDF that needs section splitting,
  or preparing documents for per-section analysis / ingestion
---

# Spec Splitter

## Instructions
1. Analyze PDF structure (TOC, major headings, logical breaks).  
2. Split into logical sections (e.g. “1 PRODUCT DESCRIPTION”, “2.1 TECHNICAL SPECIFICATIONS”).  
3. For each section produce:
   - Separate PDF named after the section  
   - Clean extracted text  

## Output format
```json
[
  {
    "section_title": "1 PRODUCT DESCRIPTION",
    "pdf_path": "section-01-product-description.pdf",
    "text": "..."
  }
]
```

This output feeds the Ingest agent / ingest-pdf-to-ast skill.  
Do not invent content. Do not re-index after the project index exists unless the user re-indexes.
