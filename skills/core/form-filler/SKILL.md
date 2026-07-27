---
name: form-filler
description: |
  Take a blank form template (PDF, image, or structured template) plus known project facts
  and produce a filled form representation ready for overlay or structure fallback.
  Use for permits, checklists, inspection forms, samsvarserklæring-style documents, etc.
use_when: |
  user uploads a blank form or checklist and wants it filled from project facts,
  or asks to complete a compliance form / inspection record
---

# Form Filler Skill

## Goal
Fill forms faithfully from existing project facts. Prefer exact matches. Never invent values. Surface every unfilled required field as a clear missing item.

## Instructions
1. Ingest the blank form (layout extraction or structured template).
2. Map form fields to existing project facts / artifact model.
3. Fill every field that has a verified source.
4. Leave unfilled required fields empty and collect them into a missing-facts list.
5. Produce two outputs:
   - Filled form representation (for FormEngine overlay or structure fallback)
   - Explicit list of still-missing fields

## Rules
- Prefer exact key matches, then fallback chains (e.g. email → e_post → epost).
- Dates, numbers, and checkboxes must respect field type.
- Never invent a value just to make the form look complete.
- If the form has repeating groups (contacts, items), expand only from real data.

## Output contract
```json
{
  "filled_fields": [
    {
      "key": "project_address",
      "value": "Example Road 12, 0001 Demo City",
      "source": "artifact.project.address",
      "confidence": "high"
    }
  ],
  "missing_required": [
    {
      "key": "model_no",
      "label": "Modellnummer",
      "reason": "not found in index"
    }
  ],
  "form_ast": { ... }   // ready for FormEngine
}
```

The FormEngine then performs the actual overlay or structure render.  
This skill only proposes the filled data and the missing list.
