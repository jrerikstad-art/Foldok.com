# Release 0.114 — Folder sense + editorial gate

**Tag:** `v0.114.12` · **Shipped:** 2026-08-05

## Verdict

0.114 turns “fill the template” into **read the folder first**, then publish only
what evidence supports. Chat stays short; the document holds the draft.

## What shipped (0.114.0 → 0.114.12)

| Area | What |
|------|------|
| **Editorial QA** | `foldok_editorial` — review only; no silent rewrite (`EDITORIAL_QA.md`) |
| **PDF reflow** | `foldok_reflow` — join visual rows into sentences; harvest embedded figures |
| **Claim tiers** | `foldok_tier` — strong / candidate / rejected; candidates fill thin sections |
| **Folder sense** | `foldok_sense` — topics from cross-source recurrence; absent themes named |
| **Chat honesty** | Job status, language lock, no fictional progress; sense reply is summary-only |
| **Install path** | Section→file map refill; procedural compile from mapped manuals |

## How to use sense

1. Open a project with indexed (or on-disk) sources.
2. Chat: **«forstå mappen»** / **«make sense of this folder»**.
3. Chat shows counts + topic titles; editor reloads the full markdown draft.
4. Optional: `GET /api/sense?id=…` · `python -m foldok_sense.audit FOLDER`.

## Code check (pre-release)

- `pytest` on sense / tier / reflow / editorial + ask / local_app contracts: **pass**
- Broader `foldok_claims`, `foldok_index`, `foldok_ask`, `foldok_director`, `local_app/tests`: **pass**
- `scripts/test_section_map_and_procedure.py`: **ok**
- Syntax check `local_app/server.py`, `foldok_compile.py`: **ok**
- Release zip: `.\scripts\make_release.ps1` (privacy grep + agent regression)

## Docs

| Doc | Role |
|-----|------|
| `CHANGELOG.md` | Patch-by-patch history |
| `EDITORIAL_QA.md` | Editorial gate contract |
| `PRODUCT_VISION.md` | Next-cycle list updated for 0.114 |
| Package `README.md` under `foldok_{editorial,reflow,tier,sense}/` | Package intent |

## Not in this release

- Transition Engine (deferred until editorial metrics are trusted)
- Production SaaS / Stripe
- Silent source or template rewrite tools
