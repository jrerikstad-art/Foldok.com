# PRD — Workspace

**Surface:** Workspace (hub / workbench / projects)  
**Product version:** 0.72.0  
**Status:** Shipped core; UX targets in `NAVIGATION_SPEC` / `EDITOR_SPEC` partially ahead of UI  
**Primary entry:** `http://127.0.0.1:8766/` (`local_app/app.html` via `scripts/workbench.ps1`)

---

## 1. Problem

Technical professionals drown in folders of PDFs, photos, and notes. They need a **project memory** they can open, understand, and turn into the right deliverable — without rebuilding structure from a blank page every time.

## 2. Outcome

A user can:

1. Start from a project folder (or create a document first and bind a folder later).
2. Choose a system template, imported template, or free document.
3. See what the engine understands (artifact) and what is missing (gaps).
4. Edit with citation integrity preserved.
5. Hand off to Delivery for export.

**Success metric (product):** one stranger can complete this path for a real job folder without support.

## 3. Users & jobs-to-be-done

| User | JTBD |
|------|------|
| Sole trader / contractor | “Turn this site folder into the document I must deliver.” |
| Engineer / EPC | “Keep many sources linked; produce manuals, reports, and packages from one memory.” |
| Ops / competent person | “Review structure and missing evidence before I sign.” |

## 4. Scope

### In scope (shipped)

- Hub landing (NO/EN) and project registry (`projects.json`, local only — never shipped in release zips).
- Create / open project; multi-folder sources; browse / pick folder.
- Folder-less document create from hub chat; bind folder later (WO 0.61).
- Hub chat + editor chat; chat attachments classified into project files or template import.
- Checkpoint A: artifact model confirm before generation.
- Document list, template picker / intent, generate, section editor, gap rail.
- Account hamburger + Path B metering UI hooks (see Delivery PRD).
- Local learning file for durable preferences.

### In scope (target)

- Navigation / explorer UX per `NAVIGATION_SPEC` (without abandoning local-first).
- Editor interaction targets per `EDITOR_SPEC` where they improve gap resolution and citation UX.
- First-class entry points to Compliance and Diagrams **inside** the project UI (not only separate dummy pages).

### Out of scope

- Multi-project simultaneous editing as a first-class mode.
- Cloud folder sync as MVP (Drive/OneDrive remain “kommer”).
- Team collaboration / presence / comments threads.
- Marketing site identity (`public/`) as the workbench.

## 5. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| W-1 | User can create a project from a local folder or from chat without a folder | P0 |
| W-2 | User can add/remove source folders; indexing is scoped to those folders | P0 |
| W-3 | At document creation, user chooses system template / imported template / free document | P0 |
| W-4 | Artifact confirmation (Checkpoint A) is required before generation when confidence rules say so | P0 |
| W-5 | Gaps are visible and actionable in the editor | P0 |
| W-6 | Chat can dispatch create-document and related tools with explicit “ja” confirmation where required | P0 |
| W-7 | Demo / synthetic projects cannot produce unpaid clean exports | P0 |
| W-8 | Diagram canvas and compliance package status are reachable from the project without leaving Feltdok | P1 |
| W-9 | Settings expose projects base dir and account state without leaking paths into shipped builds | P1 |

## 6. Non-functional requirements

- Local-first: project files remain on disk under user-chosen folders.
- Release packaging must never include `projects.json` or real customer paths.
- Bilingual chrome (NO/EN) for hub and primary flows.
- Cold-start honesty: refuse out-of-scope asks (3D, legal advice, native CAD) per `COLD_START_SPEC`.

## 7. Dependencies

| Depends on | Why |
|------------|-----|
| Compiler | Index, artifact, generate |
| Compliance | Profile gaps and package readiness language |
| Diagrams | Insert figures into sections |
| Delivery | Export and metering |

## 8. Key APIs / artifacts

- `/api/bootstrap`, `/api/projects`, `/api/project/*`, `/api/hub/chat`, `/api/doc/chat`
- `/api/doc/create`, `/api/generate`, `/api/artifact*`, `/api/confirm`
- State: `.foldok_state.json` or folder-less `project_states/`
- UI: `local_app/app.html`, `local_app/server.py`

## 9. Acceptance criteria

- [ ] New user creates “Diagram demo”-class project from a sample folder and reaches an editable document shell.
- [ ] Hub chat can create a folder-less document and later bind a folder without losing the shell.
- [ ] Blocking gaps prevent “clean” export until resolved or explicitly overridden (logged).
- [ ] Privacy grep on release zip passes (no `C:\Users\…` customer paths).

## 10. Open decisions

- How deeply to embed Diagrams inside `app.html` vs keep a dedicated canvas route.
- When to surface Compliance package status as a first-class rail (vs only MANGLER pills).

## 11. References

`PRODUCT_DIRECTION.md`, `ONE_AGENT_SPEC.md`, `COLD_START_SPEC.md`, `NAVIGATION_SPEC.md`, `EDITOR_SPEC.md`, `FLOW_ONE_OPERATION.md`
