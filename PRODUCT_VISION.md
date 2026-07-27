# PRODUCT_VISION.md

**Foldok** · Product Vision  
Status: active · v1.3 · 2026-07-27

---

## One-liner

**Foldok is an Engineering Documentation Operating System** — where engineering documentation is created, completed, reviewed, delivered, and kept alive.

It is not an AI chat app.  
It is not a general writing tool.  
It is not a project-management suite.

**Documentation is the primary workspace.**  
**Projects provide structure, context, sources, and lifecycle.**

> Projects organize documentation. Documentation delivers projects.

---

## Problem

Engineering work produces drawings, photos, PDFs, spreadsheets, exports, and notes. Documentation is still assembled late, by hand, across Word and folders. Gaps appear at handover. Traceability is weak. When sources change, packages are rewritten from scratch.

Generic AI tools help people read and draft from files. They do not:

- keep **documentation** as a structured, maintainable workspace  
- bind **evidence** and **requirements** to sections and packages  
- treat **diagrams** as engineering data inside the package  
- support **versioned delivery** and **re-analysis** when inputs change  

Foldok makes engineering documentation a managed process—not a one-off writing task.

---

## Vision

Analogy: **Visual Studio for engineering documentation** — people spend their time in the documentation workspace (as developers spend time in code), while sources, knowledge, requirements, diagrams, responsibilities, and delivery stay integrated around that work.

AI is infrastructure.  
The product is **status, decisions, and deliverables** — not a chatbot.

### Philosophy

Engineering documentation should behave like engineered software:

- structure is explicit  
- requirements can be listed  
- evidence is traceable  
- packages are reproducible  
- updates are incremental  
- work is not rewritten from a blank page every time  

Foldok brings **history, traceability, reproducibility, and confidence under change** to documentation packages—similar in *discipline* to version control for source code, not as a clone of Git.

---

## Canonical workflow

The documentation lifecycle is stable. People move through it in the order their organization needs.

```text
Open / continue
    → Understand sources
    → Build knowledge
    → Resolve gaps
    → Edit documentation          ★ primary work
    → Review (when required)
    → Deliver
    → Maintain
```

| Stage | Outcome |
|-------|---------|
| Understand | Sources visible and grouped |
| Knowledge | Entities, facts, relations, citations inspectable |
| Resolve | Missing evidence handled with guided actions |
| Edit | Documents and diagrams improved in the main workspace |
| Review | Human acceptance when the organization requires a gate |
| Deliver | Versioned package exported or distributed |
| Maintain | Source changes map to affected documents |

No stage is named “AI.”  
No stage is locked to a job title.

---

## Role-agnostic by design

Foldok does **not** hard-code personas (documentation engineer, QA, PM, …) as product configuration.

Organizations differ: one person may do everything; another project may involve a dozen people and a customer approver. **The workflow stays the same. Only responsibilities change.**

### Responsibility layer (optional)

Projects may enable a **Responsibility layer** — a RACI (or optional RASCI) matrix over documentation **workflow steps** and, when useful, **deliverables**.

| UI term | Meaning |
|---------|---------|
| **Responsibilities** | Project roles and assignments (not “RACI” as the tab name) |
| **Workflow step** | e.g. Resolve gaps, Edit documents, Approve delivery |
| **Responsible** | Does the work (R) |
| **Accountable** | Signs off (A) — prefer one per step |
| **Support** | Hands-on help (S) — only if RASCI enabled |
| **Consulted** | Gives input (C) |
| **Informed** | Kept updated (I) |

- **Solo default:** Responsibilities off; full access implied.  
- **Teams:** Optional matrix; letters shown as words in UI, abbreviations on hover.  
- **Enforcement:** off → soft warnings → hard permissions (later).  
- **Not a PM tool:** no sprints, timesheets, or ticket boards—only ownership on the documentation lifecycle.

Custom workflow steps (e.g. customer FAT, factory sign-off) can extend the same model later without a second product.

### “My work”

When Responsibilities are enabled, the home context can show:

```text
My responsibilities
  Resolve 3 gaps
  Review 2 documents
  Approve package
```

Derived from role × matrix × project state—not a separate task system.

---

## Product surfaces

| Product | Outcome |
|---------|---------|
| **Documents** | Primary workspace — edit structured engineering documentation |
| **Workspace** | Project context, health, navigation |
| **Compiler** | Generate / refresh packages from knowledge + templates |
| **Compliance** | Requirements, evidence links, gaps |
| **Diagrams** | Engineering diagrams bound to project data |
| **Deliver** | Version, package, export, distribute |
| **Assets** | Templates, symbols, tables, themes, industry packs |

### Navigation (work-first)

```text
Documents ★
Assets
Figures
Tables
Diagrams
Requirements
Sources
Dashboard
Deliver
History
Responsibilities    (optional; when enabled)
```

Open project → prefer **last active document / document set** when it exists;  
show **Dashboard** when the project is new or blocked by gaps that prevent useful editing.

---

## Document lifecycle

```text
Draft → In review → Approved → Published → Superseded → Archived
```

Transitions may optionally require Accountable approval when Responsibilities and enforcement are on.  
Without Responsibilities: authors move states as project policy allows.

Deliverables (e.g. Installation Manual, Technical Package) can carry status, Responsible, Accountable, and approval history without becoming tickets.

---

## Engineering assets

Durable building blocks are **assets**: versioned, installable, inspectable, reusable.

| Kind | Role |
|------|------|
| Templates | Section structure + required blocks |
| Components | Cover, warning, revision history, cards, … |
| Symbols | Ports, medium, tags |
| Table types | BOM, cable schedule, I/O list, … |
| Layouts / composition profiles | Page regions |
| Themes | Design tokens (neutral defaults + customer brand packs) |
| Requirement profiles | Expected evidence types — not full legal standard text |
| Industry packs | Bundle of the above + terminology hints |

**Intelligent assets** bind to knowledge (symbol → ports; table → facts; block → evidence).

### Industry packs

```text
Pack → templates, symbols, tables, diagrams, requirement profiles,
       themes, AI terminology hints, optional examples
```

Rules:

- Do not ship full copyrighted standard texts (IEC, ISO, DNV, …)  
- Customer-owned standard PDFs allowed as project sources  
- No third-party vendor brand themes as official defaults  
- Grow one vertical pack before any marketplace  

---

## Core principles

1. **Documentation is the primary workspace.** Projects provide structure, context, sources, and lifecycle.  
2. **Knowledge before empty prose** — extract and structure; then edit.  
3. **Requirements and evidence** — items point to sources or an explicit gap.  
4. **User confirmation** — formal claims, numbers, and approval stay human.  
5. **No false compliance** — structural profiles and gaps, not “certified to ….”  
6. **Customer-owned sources** — files and licensed standards remain with the customer.  
7. **Deterministic publishing** — layout and diagrams from engines; models assist content and structure.  
8. **Lifecycle** — Maintain re-enters knowledge → gaps → edit → review → deliver.  
9. **Actions over chat** — Fix / Link / Create / Ignore / Explain; chat is optional assist, not the product.  
10. **Engines are implementation** — UI speaks documentation and workflow.  
11. **Everything is inspectable** — why it appeared, which source, which asset.  
12. **Role-agnostic** — optional Responsibility layer; no mandatory persona scripts.  

---

## What Foldok is not

- A NotebookLM-style research notebook  
- A chat-first product  
- A Jira/Monday-style project manager  
- A freeform illustration tool  
- A full FEA or statutory certification engine  
- A library of copyrighted standard text  
- An automatic CE / samsvar / ISO approval service  

---

## Information architecture

```text
Projects
  └── Project
        ├── Documents ★
        ├── Diagrams
        ├── Requirements
        ├── Sources
        ├── Knowledge
        │     ├── Entities
        │     ├── Relationships
        │     └── Evidence
        ├── Resolve gaps
        ├── Review
        ├── Dashboard
        ├── Deliver
        ├── History
        ├── Assets
        └── Responsibilities     (optional)
```

### Provenance chain

```text
Project
  → Knowledge graph
  → Requirement graph
  → Artifact graph
  → Documents / diagrams / packages
```

Responsibilities overlay workflow steps and deliverables; they do not replace the graphs.

---

## Platform layering

```text
User
  → Documentation workspace + project context
    → Surfaces (Compiler, Compliance, Diagrams, Deliver, Assets)
      → Responsibility layer (optional)
        → Engines (Knowledge, Requirement, Artifact, Diagram, Publishing, …)
          → Customer sources
          → Installable asset packs
```

---

## Flagship experience

1. Open or create a project.  
2. Connect folders of real project files.  
3. Analyze — knowledge + coverage.  
4. See health and gaps.  
5. **Work in Documents** — structure, edit, link evidence, place figures.  
6. Use Diagrams when drawings belong in the package.  
7. Review when the organization requires a gate (optionally via Responsibilities).  
8. Deliver a versioned package.  
9. Later: add sources → see affected documents → update and deliver again.

Daily time is in **documentation**.  
Project context makes that documentation trustworthy.  
Responsibilities (when used) make ownership explicit without turning Foldok into PM software.

---

## Collaboration model

| Mode | Behaviour |
|------|-----------|
| Solo | Responsibilities off; full access |
| Small team | Optional Responsibilities; soft guidance |
| Larger org | Matrix + optional approval gates on review/deliver |
| External reviewer | Future: limited role (e.g. Informed + comment / approve only) |

No forced sequence: edit first or clear gaps first; the system tracks state either way.

---

## Success metrics

| Metric | Intent |
|--------|--------|
| Time to first useful document view | Documentation workspace works |
| Time to first dashboard after connect | Analyze works |
| Blocking gaps visible and actionable | Resolve works |
| Section-level edits vs full rewrite | Compiler + editor quality |
| Requirement coverage % | Compliance surface |
| Time to first versioned package | Deliver works |
| Affected docs after source change | Maintain works |
| Responsibilities enabled only when teams need them | Flexibility works |
| Described as documentation system—not “AI chat” or “PM tool” | Positioning |

---

## Roadmap framing

### Foldok 1.0 — Documentation OS

- Documents as primary workspace  
- Project context: sources, knowledge summary, gaps  
- Compiler for core document types  
- Review supported; Responsibilities **optional display** (RACI)  
- Deliver (PDF / ZIP) + history  
- Asset foundation + one vertical pack  
- Solo-first  

**Non-goals:** heavy PM features, public marketplace, hard permission matrix, thousands of symbols.

### Foldok 1.5 — Diagrams & assets

- Diagram Studio (select / move / connect / place)  
- Richer packs  
- Stronger evidence binding in the editor  
- Soft responsibility warnings; “My work”  

### Foldok 2.0 — Org & lifecycle

- Approvals with checklists; soft/hard enforcement  
- RASCI option; custom workflow steps  
- Customer standards as owned packs  
- Integrations (SharePoint / PLM, etc.)  
- Stronger maintain impact analysis  

### Foldok 3.0 — Patterns (careful)

- Opt-in cross-project **patterns** only  
- Never silent sharing of raw customer documents  

---

## Positioning

**For people who must produce engineering documentation**  
Foldok is where you build and maintain the package—with sources, evidence, requirements, and diagrams attached.

**Against generic AI doc tools**  
They help you draft. Foldok helps you **complete, bind evidence, deliver, and update** documentation as a system.

**Against PM tools**  
They track tasks. Foldok produces **documentation outcomes**. Optional Responsibilities clarify ownership—they do not replace Jira.

**Against CAD / PLM alone**  
They own geometry and enterprise records. Foldok owns the **documentation workspace and package lifecycle** between sources and handover.

---

## One sentence for the team

> Build an operating system for engineering documentation: the editor is where work happens; the project supplies knowledge, requirements, evidence, and delivery; responsibilities stay optional and flexible; AI stays infrastructure.

---

## Related docs

| Doc | Role |
|-----|------|
| `PRODUCT_DIRECTION.md` | Settled GTM, wedge, pricing, never-list |
| `NAVIGATION_SPEC.md` | Explorer UX (converge with vision nav over time) |
| `docs/prd/` | Surface PRDs — shipped vs target at current version |
| `COMPLIANCE_POLICY.md` | Claim boundary |

---

*End of PRODUCT_VISION.md · v1.3*
