# WORKORDER_0.24.md — Tilkoblingsspesifikasjon + kode-rendret blokkskjema

Demand: «i need a schematic drawing of how these components should be
connected». DIAGRAM_SPEC lane 2, minimally: propose CONNECTION GRAPH →
user confirms → CODE renders SVG.

Implementation: `connection_diagram.py`, editor tool
`propose_connection_spec` / `confirm_connection_spec`, block type
`connection_spec` (migration_008).
