# OSM vector tiles / map renderer (Foldok)

## Role
Generate **project-local** location maps under `assets/maps/`.  
No map files or coordinates are stored outside the project folder.

## Backends
1. **Default:** `tile_stitch.py` — XYZ tile stitch (Pillow) + marker.  
2. **Optional drop-in:** place your full vector-tile generator as
   `custom_vector_renderer.py` in this folder with:

```python
def render_map(lat, lon, out_path, *, width, height, zoom, style,
               color_overrides, output_format) -> str:
    ...
    return out_path
```

If present, it is used automatically.

## Styles
`default` · `minimal` · `technical` · `satellite`

## Attribution
Maps based on OpenStreetMap / Carto / Esri imagery — cite in document footnotes
when publishing externally. Local project documentation is fine for engineering use.
