# Example: identification section with location + map proposal

Registry (after `set_location` + `propose_location_map`):

| Field | Example |
|-------|---------|
| address | Example Road 12 |
| municipality | Example Town |
| latitude / longitude | from Nominatim (stored in Excel) |
| map_image_path | `assets/maps/location_map_20260723_140501.png` |

## Document AST fragment (after user confirms)

```json
{
  "section_id": "identification",
  "blocks": [
    {
      "type": "EngineeringTable",
      "rows": [
        {"label": "Adresse", "value": "Example Road 12", "citation": "Nominatim OSM / project_findings.xlsx"},
        {"label": "Kommune", "value": "Example Town", "citation": "project_findings.xlsx"}
      ]
    },
    {
      "type": "ImageBlock",
      "path": "assets/maps/location_map_20260723_140501.png",
      "caption": "Example Road 12 · Example Town",
      "role": "site_map"
    }
  ]
}
```

## Agent turn (sketch)

1. User: «Adressen er Example Road 12, Example Town — lag et situasjonskart»  
2. Agent → `set_location(address=..., municipality="Example Town")`  
3. Agent → `propose_location_map(style="technical")`  
4. Chat: shows proposal + «Bekreft for å sette inn»  
5. On confirm → `confirm_diagram` / insert ImageBlock into section (existing confirm path)

Until confirm, the Document AST is unchanged; the PNG already exists under `assets/maps/` for preview.
