# WO 0.64 — Completion engine: gaps, resolvers, modes

**Target build:** 0.64
**Engine source:** `foldok_gaps/` (attached — 36 tests green; 74 with the diagram engine)
**Depends on:** WO 0.63 diagram engine, and the 0.62.x figure pipeline before either

---

## 1. What this is

Thirty *mangler* stop being a wall of red text and become thirty things you can click and finish. A gap is an object with an id, a state, an authority, and a set of offers. Resolving one produces an artifact, an empty form, or a signed "not applicable" — and the same engine serves an electrician, a machine builder, a fish farm, and someone documenting a prototype in a garage.

```
document + requirement pack
    -> evaluate()        gaps, stable ids, pure function
    -> options(gap)      what Foldok can offer for this one
    -> resolve(gap)      artifact | empty form | signed N/A
    -> gate()            can this be exported, and as what
```

---

## 2. Three rules Cursor must not soften

**A gap is an object, never a rendered word.** Identity is `sha1(pack | requirement | subject)`. Never a list index — resolving number 7 must not renumber 8–30.

**Evaluation is pure.** No mode, no user, no clock enters `evaluate()`. Only *gating* varies. This is what makes compliance a view rather than a decision taken on day one.

**A model may draft what someone intends. A model may never author what someone observed.** `generates_content` on the resolver, `evidence` on the requirement, refusal in the registry. See §5 — this is the one that has legal consequences if it slips.

---

## 3. Your question: are the 21 sections broad enough?

I can't audit the actual list without seeing it, but the question has a structural answer that matters more than the list:

> **Sections are labels. Requirements are the schema.**

A section model is a table of contents — an ordering and some headings. If breadth lives in the *sections*, every new segment needs new sections, and eventually new code, and you have forked the product per segment. If breadth lives in **requirement packs**, a new segment is a data file written by a domain person.

The four packs in `packs.py` prove it: electrical installation (NEK 400/FEL), EU machinery technical file (2006/42/EC), aquaculture site (NS 9415), prototype build log. Same engine, zero code differences. The prototype pack even defines its own five sections and nothing notices.

**The test to apply to your 21 sections.** For each one, ask: *is this a heading, or is it a rule?* Headings are fine and cheap. Anything that encodes a rule — "this section must contain a test report", "this repeats per circuit" — has to move into a pack, or that section is only ever going to work for electrical.

The second test is harder and more important:

> Could someone who has never seen the Foldok source write a pack for their own trade?

If it needs a code change, the requirement model is too narrow and you'll find out at customer three, not customer one.

**What actually carries breadth**, and none of it is section count:

| Mechanism | What it buys |
|---|---|
| `per: circuit / machine / cage / weld / room` | One requirement becomes 30 gaps. This is where "30 mangler" comes from |
| `applies_when` against project facts | The cheapest resolution is a gap never raised |
| `evidence: expository / evidential` | Same split in every trade — a measured value is evidence everywhere |
| `severity` + `allow_not_applicable` | Same content, different insistence per market |
| `authority` | A gap that can't cite why it's a gap is an opinion |

Where I'd expect the current 21 to strain: **subjects**. If the sections assume one installation per document, then per-machine, per-cage and per-weld requirements have nowhere to attach, and the gap list will look complete when it isn't. That failure is silent, which is why `evaluate()` emits a `no_subjects_declared` notice rather than quietly producing fewer gaps.

---

## 4. Your question: what about people who don't care about compliance?

They're the larger group, and probably your first users. Someone building a prototype who opens Foldok to thirty red MANGLER and a blocked export closes it and doesn't come back.

The answer is **not** a stripped-down "lite" product — that forks the data model and their work doesn't carry forward. The answer is that mode changes *gating only*:

| | Build | Review | Compliance |
|---|---|---|---|
| What must close | nothing | required + blocking | down to recommended |
| Export | always, watermarked | gated | gated |
| Drafts need confirming | no | yes | yes |
| N/A needs a name | no | yes | yes |
| Language | "35 things Foldok can help with" | "35 open" | "35 open" |

Same gap objects either way. Consequences worth stating out loud:

- **Nobody chooses on day one.** Build now, attach a compliance pack in eighteen months, and the full list appears retroactively over work already done. There's a test for exactly this.
- **A prototype pack is a pack like any other.** It just asks for less: seven requirements, nothing above `recommended`, so `gate()` passes empty. The person recording a rig build gets a tool that helps them finish.
- **The framing is a product decision, not a cosmetic one.** In build mode the UI must say what Foldok *offers*, not what the user is *missing*. `progress()["framing"]` returns `"offer"` or `"gap"`; use it, don't hardcode red.
- **Build-mode exports are watermarked** "Working document — not a compliance package". This protects the person and it protects you.

One line to hold everywhere: **complete never renders as compliant.** Completeness is a fact about the document that Foldok can check. Compliance is a judgement made by someone with a licence. `Gate.statement` says so; don't rewrite it in the UI.

---

## 5. The evidential guard — read this one twice

| Gap kind | What Foldok may do |
|---|---|
| Method statement, scope, procedure, principle schematic | **Draft it.** Marked AI, unconfirmed, doesn't resolve until a person confirms |
| Measured values, test results, as-built photo, serial numbers, deviations, signatures | **Build the empty form and the instruction. Nothing else.** |

If a gap says "insulation resistance missing" and Foldok writes a plausible protocol with plausible numbers, you have shipped fabricated evidence with an electrician's name on it. That's not a bug report, that's a liability.

Enforcement is `ResolverRegistry.check()`, called on every resolve, and generative resolvers are never even *offered* for an evidential gap. Tests `test_evidential_guard_*` and `test_generative_resolvers_are_never_even_offered_for_evidence` are the contract. Do not relax them to make a demo smoother.

The one subtlety: **a diagram can be either.** A typical/principle schematic is expository — draft it. An as-built is evidence, so `DiagramScaffoldResolver` seeds a canvas from parts that already have a source reference, draws **no connections**, and leaves the artifact in progress until the user connects and confirms. `test_diagram_scaffold_places_only_sourced_parts` checks that an unsourced BOM row is not placed.

And say it in the product. *Foldok will not invent your test results* is a sentence an inspector wants to hear.

---

## 6. Tasks

### T1 — Gap list UI
- Group by batch, not by section, for the action view: "5 × Insulation resistance" beats five identical rows. `session.batches()`.
- Every gap shows its `authority` when it has one.
- One "Prepare everything" button → `prepare_everything()`. Creates every form, capture task and scaffold that needs no authoring — 30 tasks, 0 words. This is the ninety-second demo.
- **Done when:** a 35-gap job collapses to six actions on screen.

### T2 — Resolve sheet
- `session.options(gap_id)` drives the buttons. Show `Offer.caution` verbatim — it's where the honesty lives.
- Generative offers get visibly different treatment from form-building ones. A user must never be unsure whether Foldok wrote something or asked them to.
- `ResolverRefused` and `EvidentialGuard` messages are written to be read by users; surface them as-is.

### T3 — Forms, capture, confirm
- Measurement forms render from `Requirement.fields`, filled via `session.fill(artifact_id, values, by=...)`. The `by` is the record.
- Capture tasks hand off to the existing Capture app; the returned path fills `pending_fields`.
- Confirm actions call `session.confirm(artifact_id, by=...)`. Unconfirmed AI content blocks compliance export.

### T4 — Modes
- Mode is a document property, switchable at any time, defaulting to **build**.
- Build mode must not show red. Use `progress()["label"]`.
- Watermark build exports.
- **Done when:** a prototype user never sees a blocked export, and flipping to compliance produces the full list without touching stored data.

### T5 — Pack authoring
- Packs load from JSON/YAML via `RequirementPack.from_dict`. Ship the four, let customers write their own.
- Run `pack.validate()` in CI. It catches evidential-but-free-text requirements and blocking-but-waivable ones.
- **Done when:** a new segment ships without a build.

### T6 — Persistence
```
documents/{doc_id}.json                  entries, artifacts, provenance
packs/{pack_id}.json                     shipped and customer packs
diagrams/{graph_id}.json + .pins.jsonl   from WO 0.63
```
Local-first, text, diffable. Same discipline as the diagram engine.

### T7 — CI
```
python -m pytest foldok_gaps/tests foldok_diagram/tests -q     # 74 tests
```

---

## 7. Do not build

- A "lite" mode with its own data model.
- Any path where a model writes into an evidential artifact, including "just to show the format".
- Gap numbering by position.
- A completeness percentage that reads as a compliance score.
- Auto-resolving anything generative in bulk. `resolve_batch` refuses without `include_generative=True`, and that flag should be behind a deliberate user action, not a default.

---

## 8. Build order

1. Gap list + batches + `prepare_everything` — this is the demo, and it needs no AI at all.
2. Measurement forms and capture tasks end to end — the two hardest evidential paths.
3. Modes and watermarking.
4. Text drafting last. It's the flashiest and the least load-bearing, and building it last keeps the guard honest.

---

## 9. Open questions for you

- **The 21 sections.** Send me the list and I'll mark each one heading vs rule, and say which need to become pack data.
- **Subject kinds in the live spec.** If a document today assumes one installation, per-circuit and per-machine requirements have nowhere to attach — that's a schema change, not a UI change, and it's cheaper now.
- **Who signs.** N/A and confirmation both record a name. Free-text name, device identity, or a real signatory record? It affects how much the audit trail is worth, and it's hard to retrofit.
