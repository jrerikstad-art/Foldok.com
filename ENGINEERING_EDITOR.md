# ENGINEERING_EDITOR.md — Foldok is an Engineering Editor

Status: active product philosophy · 2026-08-02  
Companion to `PRODUCT_VISION.md`, `PROJECT_IDENTITY.md`, `LEARNING_AND_BOUNDARIES.md`

---

## The mistake we were making

We kept improving the **Document Engine**.

That is infrastructure. It is not the product.

| Tool | Native material |
|------|-----------------|
| CAD | Geometry |
| MATLAB | Calculations |
| Excel | Data |
| Word | Writing |
| PowerPoint | Presentation |
| **Foldok** | **Engineering evidence → deliverable** |

Foldok is not Word, not InDesign, not NotebookLM.

It is an **engineering-native authoring environment** — an engineering documentation operating system whose core surface is an **editor where engineers compose knowledge into packages**.

---

## Three philosophies (only one is ours)

**Word — document-first**

```text
Blank page → write → add images → move pictures → style headings
```

**NotebookLM — knowledge-first**

```text
Files → AI understands → chat → summary → study guide
```

**Foldok — evidence-first**

```text
Evidence → Understanding → Narrative → Document → Publishing
```

Readability matters. So do engineering correctness, traceability, reuse, deterministic publishing, and lifecycle maintenance. NotebookLM optimizes for the story. We optimize for the package an engineer can stand behind.

---

## Compose, do not Generate

The primary verb of the product is wrong if it is **Generate**.

It must be **Compose**.

Opening an Installation Manual is not a one-shot export. It is a composition checklist:

```text
Installation Manual
  ✓ Purpose
  ✓ Audience
  ✓ Story
  ✓ Outline
  ✓ Assets
  ✓ Requirements
  ✓ Evidence
  ✓ Draft
```

Generation is the last ~10% (rendering prose into slots). The first ~90% is understanding, selecting, and arranging.

---

## The editor metaphor: movie timeline, not blank page

Feel like **Premiere**, not Word.

| Pane | Role |
|------|------|
| **Left — Knowledge** | Project, sources, requirements, images, drawings, standards, symbols, tables, facts, decisions, procedures, warnings |
| **Middle — Narrative** | The arc (purpose → … → close). Sections as clips on a timeline |
| **Right — Live page** | Exactly how it will publish |

You are rarely typing paragraphs. You are composing knowledge. Paragraphs are a render of a section object.

### Section as object

```yaml
Installation:
  purpose: Explain how the system is installed
  audience: Field engineer
  evidence: { facts: 18, procedures: 4, photos: 7, drawings: 2, standards: 1 }
  narrative: step-by-step procedure
  status: complete
  coverage:
    evidence: 0.92
    figures: 0.70
    standards: 1.00
    warnings: 0.80
    open_questions: 2
```

Edits look like: replace image · move drawing · add warning · add procedure — not freeform essay surgery.

AI inside a section is Copilot-shaped: small suggestions (“add grounding step”, “insert Fig. 12”, “cite IEC …”), never “write the whole document.”

---

## Architecture (product stack)

```text
Evidence (index, facts, assets)
    ↓
Project Intelligence          # deterministic — foldok_identity + role/select
    ↓
Content Director              # what belongs in *this* story
    ↓
Narrative Blueprint           # arc + required slots
    ↓
Section objects + coverage
    ↓
Author (slot fill, last 10%)
    ↓
Renderer / publish
```

### Project Intelligence (not another LLM)

Deterministic understanding of the work. Already started as `foldok_identity`:

```yaml
ProjectIdentity:
  type: installation_manual
  subject: Cable Management System
  audience: Installation Engineers
  purpose: Safe installation and commissioning
  primary_topics: [Cable routing, Supports, EMC, Grounding]
  secondary_topics: [Sensors, PLC, Diagnostics]   # inform, do not dominate
  ignored_topics: [Marketing, Company history]
```

**Hard rule:** no real client/vendor catalogues in engine code. Topics come from the artifact and folder the user named. See `PROJECT_IDENTITY.md`.

### Content Director (next major class)

Consumes Project Intelligence. Decides:

- which facts / images / tables / standards belong  
- which PDFs are background only  
- which topics deserve a chapter  

The LLM stops guessing the subject. It fills slots the director opened.

### Project assets (first-class — not decoration)

Distinct from `foldok_assets` (registry: symbols, templates, packs).

A **project evidence asset** is fact-shaped:

```yaml
Asset:
  id: …
  type: photo | drawing | table | symbol | procedure | …
  caption: …
  depicts: Cable cleat on vertical ladder — correct spacing
  confidence: …
  relevance: relevant | somewhat | background | ignore
  engineering_domain: …
  installation_stage: …
  components: […]
```

The composer binds assets to sections the way it binds facts — never “search the folder and hope.”

### Coverage before polish

Every section exposes weakness before publish: evidence %, required figures, standards, warnings, open questions. That is the engineering editor’s status bar — not a word count.

---

## Mapping to what we already built

| Layer | Status |
|-------|--------|
| Role / subject / weighted themes | Shipped (`foldok_role`) |
| Figure curation | Shipped (`foldok_select`) |
| Project Identity + NarrativeBlueprint | Shipped (`foldok_identity`) |
| Section market + wide claims | Shipped (`foldok_corpus`) |
| Citation scope / budget | Shipped (`foldok_budget`) |
| Project evidence Asset model | Shipped (`foldok_evidence`) |
| Content Director + coverage | Shipped (`foldok_director`) |
| Compose UI (3-pane) | Shipped — workbench **Compose** tab · `GET /api/compose` |
| Section-local AI suggestions | Partial — director suggestions + assist chat |

The engine stack is approaching the point where this editor is buildable. The leap is not another extraction package. It is making the **editor** the place engineers compose.

---

## Product sentence

> Foldok is the engineering editor: evidence in, composed deliverables out — with identity, coverage, and traceability held by the system, and AI as a section assistant, never the author of the project.

Philosophy line that still holds:

> The folder proposes, the user disposes, the engine holds the order.

Updated with identity:

> The project identifies, the folder proposes, the user disposes, the engine holds the order.
