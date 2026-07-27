---
name: cad-inspector
description: |
  Inspect CAD models and drawings (STEP, IGES, FCStd, DXF, STL, etc.) using FreeCAD tools.
  Extract parts, dimensions, BOM, and views. Propose DiagramBlocks and EngineeringTables.
  Never invent geometry or measurements.
use_when: |
  user provides a CAD file or drawing,
  needs part list, dimensions, exploded views, technical drawings, or BOM from a model,
  or asks to inspect / measure / extract from a 3D model or 2D drawing
---

# CAD Inspector Skill

## Goal
Turn CAD models and technical drawings into structured, citable facts and visual proposals that the Composition and Diagram engines can use.  
All measurements come from FreeCAD. Nothing is invented.

## When to use
- A STEP, IGES, FCStd, DXF, DWG, or STL file is part of the project sources
- User asks for dimensions, part list, exploded view, orthographic views, or bill of materials
- Document needs accurate technical illustrations derived from the real model

## Workflow
1. Call the FreeCAD tools to open and inspect the model.
2. Extract what can be measured reliably:
   - Part hierarchy and names
   - Key dimensions and bounding boxes
   - Bill of Materials (when possible)
   - Suggested views (isometric, orthographic, exploded)
3. Map results into:
   - EngineeringTable rows (specs / BOM)
   - DiagramBlock or ImageBlock proposals (with placeholder until confirmed)
   - Missing-facts entries for anything that cannot be measured
4. Never insert generated images into the Document AST until the user confirms.

## Allowed FreeCAD tools
- `freecad_open`
- `freecad_list_parts`
- `freecad_extract_dimensions`
- `freecad_extract_bom`
- `freecad_generate_views`
- `freecad_section`
- `freecad_close`

## Output contract
Return structured data only:

```json
{
  "source": "filename or source_id",
  "parts": [
    {"name": "...", "id": "...", "type": "part|assembly"}
  ],
  "dimensions": [
    {"label": "...", "value": "...", "unit": "mm", "source": "freecad measurement"}
  ],
  "bom": [
    {"part": "...", "qty": 1, "material": "..."}
  ],
  "view_proposals": [
    {
      "type": "isometric|orthographic|exploded|section",
      "description": "...",
      "suggested_caption": "...",
      "status": "pending_confirmation"
    }
  ],
  "missing": [
    {"key": "...", "reason": "could not be measured from model"}
  ]
}
```

FreeCAD tools are read-only. CompositionEngine + DiagramEngine own AST insertion and render after user confirmation. Never invent geometry or measurements.
