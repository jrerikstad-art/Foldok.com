# Foldok Product Requirements Documents

**Product version:** 0.72.0  
**Frame:** The project folder is the database; every document is a view over it.  
**Vision:** `PRODUCT_VISION.md` · **Claim boundary:** `COMPLIANCE_POLICY.md`

| Surface | PRD | One-line job |
|---------|-----|----------------|
| Workspace | [PRD_Workspace.md](./PRD_Workspace.md) | Open a job folder, pick a document, finish what's missing |
| Compiler | [PRD_Compiler.md](./PRD_Compiler.md) | Index once; generate cited drafts without inventing facts |
| Compliance | [PRD_Compliance.md](./PRD_Compliance.md) | Track evidence against structural profiles; human decides conformity |
| Diagrams | [PRD_Diagrams.md](./PRD_Diagrams.md) | Editable 2D system figures that insert into packages |
| Delivery | [PRD_Delivery.md](./PRD_Delivery.md) | Export a clean deliverable; meter AI and paid exports |

## Cross-cutting architecture

```text
Project folder (source of truth)
  → Compiler: index once → artifact confirm → map → generate
  → Compliance: structural profile + gaps (build / review / compliance modes)
  → Diagrams: foldok_diagram graph + pins → SVG → document section
  → Delivery: export (MD / HTML / DOCX / PPTX / PDF) + account metering
```

## Shared non-goals (all surfaces)

- Not Notion / wiki / team chat / task board
- Not blank-canvas-first identity (free document = escape hatch only)
- Not legal advice, CE/NEK/ISO pass-fail, or calculation certification
- Not photoreal / 3D / native CAD authoring
- Files stay on the user's machine; AI sees excerpts per call only

## Status legend

| Tag | Meaning |
|-----|---------|
| **Shipped** | In workbench / API at 0.72.0 |
| **Library** | Package exists (tests green); not fully wired to UI |
| **Target** | Required for the surface to meet its PRD outcome |
