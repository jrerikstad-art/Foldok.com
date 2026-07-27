# Foldok — The Complete Story & Pricing Model

**Brand:** Foldok · mark `[…]`  
**One-liner:** Foldok turns project folders into complete technical documentation packages.  
**Pricing line:** Free to try — pay per exported document (€9 / €19 / €49).

---

## 1. The story

### What Foldok is

Foldok is a **local-first documentation engine**. You point it at a project folder — photos, drawings, PDFs, notes, voice captures — and it helps you produce structured manuals, declarations, inspection packages, technical files, and handover docs.

The chat is the product. The engine is deterministic. The AI is the architect; the engine is designer and publisher.

```text
Project folder
    ↓
Index once (facts, drawings, photos)
    ↓
Artifact model + gaps
    ↓
Composition (structure, tables, procedures)
    ↓
LayoutTree (print-first pages)
    ↓
Export (PDF / HTML / DOCX)
```

### The problem it solves

**Today**, documentation is still assembled **after** the work is finished:

- Notes on phones, hand sketches, late declarations, incomplete manuals  
- Hours of unpaid office time per job — after the field work is done  
- Incomplete packages = incomplete evidence and late review pain  

People rebuild the same documentation from scratch on every job. Foldok keeps documentation building **as the project runs** — sources in, knowledge grows, packages stay alive.

### What it does (only three things)

1. **Capture and organize** project sources  
2. **Compile** structured technical documents  
3. **Keep facts, gaps, and revisions under control**

Example outputs: installation manual · technical package · inspection report · declaration of conformity · risk file · handover / FDV-style package.

### How AI vs engine divide the work

| Generic AI (ChatGPT etc.) | Foldok |
|---------------------------|--------|
| Starts from a blank prompt | Starts from your project files |
| Can invent facts | Only uses extracted, cited facts |
| Free-form text | Forced structure + professional blocks |
| You copy-paste into Word | You review and export a finished package |

**AI role:** understand intent, propose structure, fill from indexed facts.  
**Engine role:** layout, tables, citations, gaps, export.  
**Your role:** confirm before anything is final. Foldok never stamps legal conformity for you.

### Who it’s for

- Sole traders and small contractors (electricians, plumbers, installers)  
- Engineers building prototypes and delivery packages  
- EPCs and yards needing structured handover docs  
- Teams who think in **evidence packages** and structural profiles, not one national codebook  

Frameworks in Foldok are **structural profiles** (EU machinery, electrical installation, US electrical–style evidence shapes, Nordics, …) — not full code text and not a compliance stamp. The engine proposes missing evidence kinds; the customer’s compliance manager decides legal sufficiency. See `COMPLIANCE_POLICY.md`.

### What we do not claim

Foldok does **not** hold full NEK / ISO / NEC / Machinery Regulation text and does **not** declare projects “compliant,” “CE OK,” or “ISO satisfied.”

| We say | We do not say |
|--------|----------------|
| Evidence coverage for selected profile | “NEK compliant” |
| Missing: test record, as-built photos | “Legally compliant” |
| Ready for review | “CE marking is valid” |
| Package structurally complete for this template | “Approved by the standard” |

**Safe product line:** Build documentation packages mapped to common regulatory *structures*. Link your own standards and evidence. You review and sign off.

### Trust & ownership

- You own the documents  
- Your files stay on your machine / your storage as the source of truth  
- Foldok does not keep project originals as a hosted library  
- When AI runs, **excerpts** for that call go to the model provider — cost shows in the € meter  
- Finished / signed PDFs are yours — not stored as Foldok’s property  
- No automatic stamping or transfer of legal liability  

### Why not just ChatGPT / Word / Figma

- **ChatGPT** — strong at text, weak at project memory, citations, and print packages  
- **Word** — full control, zero structure help  
- **Figma** — excellent for design, wrong tool for structured technical documentation packages  

Foldok sits in the gap between them.

---

## 2. Pricing philosophy

Three principles:

1. **Pay for outcomes, not seats** — no required monthly subscription to start.  
2. **Transparent meters** — AI work draws from balance at cost × margin; exports are fixed document prices.  
3. **Local work stays free** — viewing, editing, and engine work that does **not** call AI does not drain balance. Re-export of an already paid document is free.

**Definition of shipped (product):** one stranger pays real money for one export.

---

## 3. The pricing model (as implemented)

### 3.1 Account & starting credit

| Item | Amount | Notes |
|------|--------|--------|
| New account free credit | **€2** | Loaded once when you create / sign in (workbench Path B ledger) |
| Guest / try-without-account | **€2** local allowance | Same idea for demo guest mode |
| Low-balance warning | below **€1** | UI prompts top-up |
| Top-up | user chooses (€5 / €10 / €25 / …) | Stub / Path B today; Stripe later |

Optional auto-refill (UI): refill when balance falls under a threshold (e.g. €5), with a monthly ceiling (e.g. €100) — opt-in.

### 3.2 What you pay for

#### A. AI usage (metered)

Whenever Foldok calls a model (index a file, generate a section, chat that needs the model):

```text
charged_eur = raw_model_cost_eur × 2.0
```

- **Margin multiplier:** `2.0` (covers provider cost + product margin)  
- **Zero-token / cache hit:** **€0** — re-reading an already indexed file (SHA cache) is free  
- **Pure local editing** (no model call): **€0**  

Rough index guidance (capabilities manifest — ranges, not invoices):

| Work | Typical scale |
|------|----------------|
| Index per file | ~€0.001 – €0.01 |
| Typical text doc | ~€0.01 |
| Typical photo | ~€0.008 |
| Large corpus | Prefer several focused projects over one giant index |

Batch index shows an estimate and confirm when the job is large.

#### B. Export (fixed tiers — the “document price”)

You pay when you **export a finished package** (PDF / HTML / DOCX, etc.), not for opening the editor.

| Tier | Price | Typical use |
|------|-------|-------------|
| **basic** | **€9** | Simpler / shorter packs |
| **standard** | **€19** | Default for most templates |
| **complex** | **€49** | Heavy packs (e.g. contract review / dense evidence packages) |

Tier comes from the template’s `export_price_tier` (default **standard** → €19).

**Included with a paid export:** editing and AI help inside that document (within normal guards).  
**Re-export** of a document already paid for the current content revision: **free**.  
**New substantial revision** that creates a new paid entitlement: charged again at the tier price.

### 3.3 Free to try

Public line (capabilities / hub):

> **Free to try — pay per exported document (€9 / €19 / €49).**

Free-tier shape (product intent):

- Start with free credit (€2)  
- Rough free envelope: **1 project**, **~50 files** indexed, **watermarked preview** until export is paid  
- Engine contract also budgets soft guards (e.g. confirm large index batches; soft top-up if a session burns many regenerations)

Exact free-file caps are enforced as the product hardens; the **commercial story** is always: try freely, pay when you take a clean export home.

### 3.4 What is never charged as “export”

- Scrolling the draft, fixing typos locally, dismissing gaps, toggling documents  
- Re-exporting a paid document without a new paid revision  
- Showing watermarked preview when balance is too low for clean export  

If balance is too low for export, Foldok asks you to top up — then continues the same export.

---

## 4. How a euro flows through a job (example)

**Residential install → inspection + declaration package**

1. Sign in → **€2** free credit on the ledger.  
2. Connect folder → index 40 files → say **€0.20–€0.40** AI (cost × 2) if not cached; next open of those files **€0**.  
3. Chat + generate draft → another small AI spend from balance.  
4. Export **standard** package → **€19** deducted once.  
5. Fix a typo, export again → **€0** (paid re-export).  
6. Later: major rewrite / new paid revision → tier price again.

**Headline for the website:**  
*Typical residential job documentation → a few euros of AI plus one export price — not a monthly plan.*

---

## 5. Money claims the product is allowed to make

Foldok’s agent must only quote money from the **capabilities / pricing manifest** (validated in regression):

- Free to try  
- Pay per exported document **€9 / €19 / €49**  
- Index per file roughly **€0.001–€0.01**  
- Editing and AI help inside a paid document  
- Re-export free for paid documents  
- Contract-style work typically **€49** tier  

It must **not** invent “€0.01 per export” or designer day-rates. If unsure → fall back to the pricing line above.

---

## 6. Path B vs future Path A (architecture note)

| | **Path B (current workbench)** | **Path A (future cloud product)** |
|--|-------------------------------|-----------------------------------|
| Ledger | Local / proxy stub + device token | Hosted account + Stripe (or similar) |
| Files | Stay on machine | Customer storage / connectors; Foldok still not “your DMS of record” by default |
| AI meter | `raw_cost × 2` against balance | Same idea, production billing |
| Export | Tier charge + paid flag on document | Same commercial model |

The **story and price list stay the same**; only how money is settled changes.

---

## 7. One paragraph you can paste anywhere

> Foldok turns project folders into complete technical documentation packages. Your files stay with you. AI work is metered from a small prepaid balance (model cost × 2; cache hits are free). You try for free, then pay **per exported document** — **€9**, **€19**, or **€49** by complexity — not a monthly subscription. Re-exports of paid documents are free. The engine proposes structure and gaps; you confirm before anything is final.

---

## 8. Source of truth in the repo

| Concern | Where |
|---------|--------|
| Public pricing line & tiers | `capabilities.json` → `pricing`, `pricing_line_en` |
| Ledger constants | `proxy/ledger.py` → `EXPORT_TIERS_EUR`, `FREE_CREDIT_EUR`, `MARGIN_MULT` |
| Account UI / export charge | `local_app/account_metering.py`, workbench export flow |
| Budget guards (product contract) | `ENGINE_CONTRACT.md` §6 |
| Landing story | Hub `local_app/app.html` + `public/index.html` |

When prices change, update **ledger + capabilities + this file** together so the agent money validator and the website stay aligned.
