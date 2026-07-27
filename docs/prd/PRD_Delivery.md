# PRD — Delivery

**Surface:** Delivery (export, packaging, account / metering)  
**Product version:** 0.72.0  
**Status:** Multi-format export + Path B metering stub shipped; production Stripe / SaaS not started  
**Primary entry:** Workbench export; release via `scripts/make_release.ps1`

---

## 1. Problem

Authors need a **clean deliverable** they can hand to a customer or authority. The product must charge fairly for harvest (exports and AI calls) without uploading project files to a Feltdok cloud or claiming legal sign-off.

## 2. Outcome

Users can:

1. Choose an output format (PDF / HTML / DOCX / PPTX / Markdown as supported).
2. Export only when structural / sketch / demo rules allow.
3. See metering for AI calls and export tiers.
4. Re-export paid content without re-paying when entitlement matches.
5. Operators ship a privacy-clean engine release zip.

**Commercial identity:** Pay per exported document (and metered AI), not seats.  
**1.0 milestone:** one stranger pays for one export.

## 3. Users & jobs-to-be-done

| User | JTBD |
|------|------|
| Author | “Take this package home as a clean file.” |
| Buyer / guest | “Try with free credit; understand what I pay for.” |
| Maintainer | “Ship vX.Y.Z without leaking customer projects.” |

## 4. Scope

### In scope (shipped)

- `/api/export` — write under project `Rapporter/` (and format variants via `export_formats.py`).
- Format choice pdf | html | pptx | docx (WO 0.61); table-split notices for pptx where needed.
- Guards: demo/synthetic watermark; unpaid draft limits; sketch unlabeled placeholders can block export.
- Account Path B stub: magic-link / guest / top-up stubs; AI cost ×2; export tiers €9 / €19 / €49; usage + receipt endpoints.
- Release packaging: `make_release.ps1` — exclude `projects.json`, privacy grep, regen `capabilities.json`, optional agent regression.
- Marketing site separate (`public/` → Vercel); engine remains local workbench.

### In scope (target)

- Production payment (Stripe) + real magic-link email.
- Branded paid PDF polish (layout engine path).
- Compliance-mode export gate + build-mode watermark driven by `foldok_gaps` policy (when Compliance UI is wired).
- Hard free-tier caps as product hardens (projects / files) matching `PRICING_AND_STORY`.

### Out of scope (until after 1.0 test)

- Multi-seat SaaS collaboration as the delivery model.
- Feltdok storing customer signed PDFs as product property.
- Subscription required to start.
- Proxy that receives file content (tokens / job_type only).

## 5. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| E-1 | Export produces a file on the user’s machine under the project | P0 |
| E-2 | Demo / unpaid / blocking-gap rules prevent “clean” paid-looking exports | P0 |
| E-3 | User can select output format before export | P0 |
| E-4 | AI calls and exports are metered; balance visible in account UI | P0 |
| E-5 | Re-export of identical paid content is free when hash entitlement matches | P1 |
| E-6 | Release zip never contains `projects.json` or customer absolute paths | P0 |
| E-7 | Build-mode compliance exports carry working-document watermark | P1 |
| E-8 | Compliance-mode export can block on open blocking gaps | P1 |
| E-9 | Receipt download available for paid exports (when ledger populated) | P2 |

## 6. Non-functional requirements

- Privacy: originals stay local; AI excerpts per call only; metering proxy never stores content.
- Pricing copy must not imply legal certification.
- Release gate severity: privacy grep = ship-stopper; agent regression = ship-stopper unless explicitly skipped for hotfixes.

## 7. Dependencies

| Depends on | Why |
|------------|-----|
| Workspace | Document ready state, demo flags |
| Compiler | Content to export; AI jobs to meter |
| Compliance | Mode, watermark, gate |
| Diagrams | SVG/figures in export HTML/PDF |

## 8. Key APIs / artifacts

- `/api/export`
- `/api/account`, `/api/account/usage|receipt|topup|magic-link|verify|guest|sign-out|delete`
- `export_formats.py`, `account_metering.py`, `proxy/`
- `scripts/make_release.ps1` → `releases/foldok-engine-v*.zip`

## 9. Acceptance criteria

- [ ] Export from a real project writes under `Rapporter/` (or format-specific output) without uploading the folder.
- [ ] Demo project export is watermarked / non-paid.
- [ ] Account chip shows balance; insufficient balance blocks paid export with a clear code.
- [ ] `make_release.ps1` fails if privacy patterns hit staged files.
- [ ] When Compliance is wired: build export watermark present; compliance export blocked on blocking gaps.

## 10. Open decisions

- Stripe vs other PSP; how free €2 credit is granted in production.
- Whether PDF always goes through `artifact_engine` LayoutTree or remains MD→HTML→PDF for v1.

## 11. References

`PRICING_AND_STORY.md`, `FORMATS.md`, `DEPLOY.md`, `WORKQUEUE.md`, `V0_60_PLAN.md`, `proxy/README.md`
