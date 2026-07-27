# NAVIGATION_SPEC.md — left explorer rail (project navigation)

Extends EDITOR_SPEC.md. Mental model: VS Code explorer. The explorer is
per-PROJECT navigation; the top workflow rail stays per-DOCUMENT.

## Layout
- Explorer panel: 264px, left of everything, full height, bg var(--paper),
  1px border-right var(--line). Collapsible to 48px icon rail (chevron
  button bottom; state persisted per user).
- AUTO-COLLAPSE on entering Bygg (step 3) to protect split-screen width;
  hover or click on the rail peeks it as an overlay; pin re-expands.

## Zone 1 — Project switcher (top, 56px)
- Current project name + chevron → dropdown: 5 recent projects (name,
  file count, last-opened), search field, divider, "+ Nytt prosjekt".
- Single active project at a time. Switching = route change; all data is
  indexed so switch is instant. NO multi-project simultaneous view in v1.
- Free tier: at 1-project cap, "+ Nytt prosjekt" opens the upgrade card.

## Zone 2 — KILDER (folders tree)
- Header row: "KILDER" + "+ Koble til" (opens: last opp filer / koble
  mappe [Drive/OneDrive when connectors ship — greyed with 'kommer' in MVP]).
- One row per attached folder (project_files grouped by source ref/folder):
    icon (upload/gdrive/onedrive) · folder name · count
    status line: "✓ 34 indeksert" | "⏳ 12 venter · ~€0,15 [Indekser]"
                 | "⚠ 2 feilet [Prøv igjen]"
  Pending never indexes silently — the cost estimate + explicit button
  is the budget-guard philosophy in navigation.
- Expand folder → flat file list (name + status dot). Click file →
  opens its summary popover (caption, tags, facts, "vis i Bygg").
- Row ⋯ menu: Indekser nye filer · Åpne i skytjeneste · Koble fra
  (detach keeps index rows, marks source detached — re-attach is free
  via sha256).

## Zone 3 — DOKUMENTER
- Header: "DOKUMENTER" + "+ Nytt" → template picker (recommendation
  from artifact model per TEMPLATE_LIFECYCLE coverage ladder).
- One row per document: template icon · name · status chip:
    "● Utkast · 1 mangel" (amber dot if blocking gaps)
    "○ Struktur venter" (outline/mapping not confirmed)
    "✓ Eksportert · rev A"
- Click → opens document AT ITS CURRENT WORKFLOW STEP (documents.status
  + confirmations decide: no artifact confirm → Forstå; no mapping →
  Struktur; else Bygg).
- Row ⋯: Dupliser · Eksporter på nytt (free if paid, per FORMATS.md) ·
  Slett (soft).

## Component map (Cursor)
  src/components/explorer/
    ExplorerRail.tsx      (collapse logic, zones, overlay peek)
    ProjectSwitcher.tsx   (dropdown, recent query, create)
    SourceTree.tsx        (folder groups from project_files, realtime
                           status via Supabase subscription)
    DocumentList.tsx      (documents + gap counts join)
  State: active project id in route (/p/[projectId]/...); explorer
  collapse in localStorage... (NOTE: localStorage fine in the real app;
  not in claude.ai artifacts).

## What NOT to build (v1)
Drag-files-between-projects · multi-select folder ops · nested project
grouping/workspaces · pinned projects. All post-revenue.

## Flow automation & loading states (from real use, v0.11)
THE COST RULE decides automation, not button-fondness:
  - AUTO-RUN with progress (no button): indexing of newly attached files
    after the batch-cost confirm, and checkpoint-B mapping the moment the
    artifact model is confirmed (~€0.01 — nothing to consent to).
  - EXPLICIT button with € estimate: generation (checkpoint C), full-doc
    regeneration, template import extraction. Money = consent.
LOADING is always concrete, never a bare spinner:
  - Indexing: "34 / 120 filer · ~40 s igjen" with per-file ticks
    (Supabase realtime on project_files.status; parallel workers server-
    side, mirror CLI's pool of 5).
  - Mapping: per-section ticks ("Kartlegger 8/12 seksjoner").
  - Generation: per-section progress with running token cost.
  - Anything >3 s without feedback is a bug.
