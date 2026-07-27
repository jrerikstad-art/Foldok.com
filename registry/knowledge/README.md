# Knowledge packs

Vendor-neutral structural profiles: vocabulary, checklists, and report block
templates. Not legal compliance engines.

```
registry/knowledge/
├── _knowledge_schema.yaml
├── corrosion/
│   ├── pack.yaml
│   ├── basics.yaml
│   ├── forms.yaml
│   ├── environments.yaml
│   ├── materials_and_protection.yaml
│   ├── galvanic.yaml
│   ├── selection_checklist.yaml
│   └── report_block.yaml
└── cable_management/
    ├── pack.yaml
    ├── tray_ladder_systems.yaml
    ├── wiring_systems.yaml
    ├── evidence.yaml
    └── report_blocks.yaml
```

## Corrosion pack (`corrosion_materials`)

| Layer | Role |
|-------|------|
| Knowledge pack | Forms, C-classes, protection types, galvanic rules, checklist |
| Project sources | User specs, datasheets, preferred standards |
| Materials engine | Optional link: steel grade + coating as material attributes |
| Report | `CorrosionProtectionNote` after user confirm |
| Compliance posture | Evidence and selection structure — not "certified corrosion-free" |

## Cable management pack (`cable_management_wiring`)

| Layer | Role |
|-------|------|
| Knowledge pack | Tray/ladder classifications, wiring selection topics, evidence list |
| Project sources | User-owned datasheets and standard references |
| Diagram engine | Optional tray route/support sketches (2D) |
| Report | `CableSupportSystemNote` and `WiringSystemSelectionNote` |
| Compliance posture | Structural documentation only — no clause-text reproduction |

APIs: `/api/knowledge-packs/list` · `/api/knowledge-packs/get` · `/api/knowledge-packs/gaps`

Engine: `local_app/knowledge_registry.py`

**Note:** `/api/knowledge/*` is the hybrid project-findings brain (`hybrid_knowledge_engine.py`).
Knowledge **packs** use `/api/knowledge-packs/*` to avoid collision.
