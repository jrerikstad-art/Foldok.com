---
name: file-organizer
description: |
  Scan a project folder, classify files (drawings, specs, photos, contracts, invoices, notes),
  propose a clean structure, rename consistently where useful, and flag orphans or incomplete items.
  Use at the start of a project or when the Capture Folder Engine needs hygiene.
use_when: |
  user asks to organize project files, clean up a messy folder, classify drawings/specs/photos,
  or prepare sources before ingestion
---

# File Organizer Skill

## Goal
Turn a messy project folder into a predictable structure that the Ingest engine and Capture Folder Engine can index reliably. Never invent content. Never move files without explicit user confirmation.

## Instructions
1. Scan the provided folder (or list of files).
2. Classify each file by type and role:
   - Drawings / tegninger
   - Specifications / manuals
   - Photos / site images
   - Contracts / tenders
   - Invoices / receipts
   - Notes / site diary
   - Other / unknown
3. Propose a clean folder structure (example):
   ```
   Project/
   ├── 01_Drawings/
   ├── 02_Specs/
   ├── 03_Photos/
   ├── 04_Contracts/
   ├── 05_Invoices/
   ├── 06_Notes/
   └── _Needs_Review/
   ```
4. Suggest standardized filenames where helpful (date + type + short description).
5. Flag orphans, duplicates, and files that cannot be classified.
6. Produce a summary table of all files with proposed new path and status.

## Output contract
Return a structured proposal only:

```json
{
  "proposed_structure": [...],
  "file_map": [
    {
      "original": "...",
      "proposed_path": "...",
      "type": "drawing|spec|photo|...",
      "status": "ok|needs_review|duplicate"
    }
  ],
  "needs_review": [...],
  "summary": "X files classified, Y need review"
}
```

Do **not** move or rename files until the user confirms.  
After confirmation the orchestrator can call engine tools to apply the changes.  
Never invent metadata that is not extractable from the file itself.
