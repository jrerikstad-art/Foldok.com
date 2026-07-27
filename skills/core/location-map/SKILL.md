---
name: location-map
description: |
  Handles project location data and generates high-quality maps
  using the OpenStreetMap vector tile generator (or built-in tile stitcher).
use_when: |
  document needs location or site map,
  user provides an address,
  or compliance documents require municipality / property data
---

# Location Map Skill

## Goal
Keep address, municipality, coordinates, and site maps in the project-local
`project_findings.xlsx`. Generate maps into `assets/maps/` and **propose**
them as `ImageBlock` for user confirmation — never auto-insert.

## Workflow
1. Prefer `get_location` from the registry.  
2. If the user gives an address → `set_location` (geocodes when coords missing).  
3. When a visual map is needed → `propose_location_map` (generates + ImageBlock proposal).  
4. Wait for user confirm before inserting into Document AST.  
5. User may replace any file under `assets/maps/` with their own image; update
   `map_image_path` via `set_location` / registry edit.

## Tools
- `get_location`
- `set_location`
- `generate_location_map`
- `propose_location_map`

## Document use
For identification / samsvarserklæring / site sections:
- Pull `address` + `municipality` (+ postal_code) from the registry with citation.  
- Optionally attach the confirmed map ImageBlock.  
- Never invent coordinates.

## Hard rules
- Never store coordinates or maps outside the project folder.  
- `project_findings.xlsx` remains the editable source of truth.  
- Generated maps → `assets/maps/location_map_{timestamp}.{format}`.  
- Color/style fully controllable (`style`, `color_overrides`).  
- Confirm before insert.
