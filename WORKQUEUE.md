# WORKQUEUE.md — implementeringsrekkefølge (oppdater ved hver release)
Single source of order. Work the tiers top-down; within a tier, order
is free. A tier is done when its regression tests are green.

Last updated: **0.60.0** (2026-07-23). Money round Path B (local + metering) shipped
as stub. Next: real Stripe/magic-link SMTP, then **v0.60 publishing foundation**
(`V0_60_PLAN.md`) / 1.0.0 when one stranger pays for one export on production.

## TIER 1 — TRUTHFULNESS & DISPATCH (before anything else; these are
## trust-breaking in front of any prospect)
[x] WORKORDER_0.25  events→conversation, pending_action dispatch
                    *0.33.0: generic editor dispatch on «ja»*
[x] WORKORDER_0.22  perception receipts, completion-verb validator
                    *0.31.0: progress verbs require job_id; UI shows job*
[x] WORKORDER_0.23  money/legal from manifest
                    *0.33.0: editor path currency gate*
[x] BUGFIX_0.19     project isolation — green; conversation scope
                    extended in 0.28.0
[x] WORKORDER_0.26  chat references artifacts only; diagram_engine sole
                    renderer; write_checklist / create_diagram —
                    *shipped 0.26.0; E23–E26 = tests 25–28*
[x] WORKORDER_0.27  rung-3 draft_template, prescriptive compile,
                    layout tools, installation_manual —
                    *shipped 0.27.0; E1–E5 = tests 29–33*
[x] 0.28            conversation isolation §A; PDF thin-page vision;
                    brukermanual → user_manual — *shipped 0.28.0*
[x] WORKORDER_0.29  form_fill + inspection_checklist — *shipped in 0.30.0;
                    0.32.x form_engine HTML; 0.33.0 recreate_form;
                    0.34.0 Form Engine v2 overlay package*
[x] WORKORDER_0.30  malimport (form → owned template) — *shipped 0.30.0;
                    0.31.0: skjema.jpg + chat «as a template»;
                    0.34.0: ingest + layout_extract on import*

## TIER 2 — THE AGENT ACTS AND SPEAKS RIGHT
[x] WORKORDER_0.20
[x] WORKORDER_0.21
[x] WORKORDER_0.23

## TIER 3 — FLOW & COLD START POLISH
[x] FLOW_ONE_OPERATION
[x] ONE_AGENT_SPEC
[x] COLD_START_SPEC
[x] WORKORDER_0.19
[x] WORKORDER_0.19B

## TIER 4 — NEW CAPABILITY
[x] WORKORDER_0.24  connection_spec + diagram_engine (closed by 0.26 §D)
[x] WORKORDER_0.27  templates/layout/prescriptive (shipped 0.27.0)
[x] Document Engine  datasheet/manual print HTML — *shipped 0.36.0*
[x] Artifact Engine   Document AST → layout → HTML/PDF — *0.37–0.39*
                    FormEngine consume — *0.40*; measure/multi-col — *0.41*;
                    Diagram layered graph — *0.42*; compose/measure — *0.43–0.44*;
                    print-first DesignSystem + LayoutTree — *0.45*;
                    user-manual TOC + composition — *0.46*;
                    no MANGLER in prose + forced blocks — *0.47*;
                    content pipeline (facts/tables/figs/one-click) — *0.48*;
                    call contracts + editorial layer — *0.49*
[ ] LEARNING_AND_BOUNDARIES  §1 chat attachments routing (partial),
                    local_learning.json, telemetry whitelist — **NEXT**

## TIER 5 — THE MONEY ROUND
[x] Path B chosen: local-first + Foldok metering proxy (WORKORDER_0.60).
[x] Account hamburger, € ledger, export chips, stub Checkout (0.60.0).
[ ] Production Stripe + real magic-link e-mail; watermarked draft PDF polish.
    (Engines can emit PDF when WeasyPrint/Playwright installed;
     paid branded export is not shipped.)

## GATES (block every release, cumulative)
- Privacy grep (0.19 §4) — *live in make_release.ps1*
- Golden agent suite: **67 tests** green (`scripts/agent_regression.py`)
- Isolation suite: `scripts/test_chat_isolation.py` green (incl. conversation)
- `python -m diagram_engine` selftest green
- `python -m form_engine` selftest green
- `python -m document_engine` selftest green
- `python -m artifact_engine` selftest green
- bom_engine selftest + agent_regression.py green
- Capabilities regenerated for VERSION (`scripts/build_caps.py`)
