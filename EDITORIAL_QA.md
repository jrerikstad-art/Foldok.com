# EDITORIAL_QA.md — Review what the Author produced (do not rewrite)

Status: active · shipped 0.114.0  
Rule: **no new LLM author.** Deterministic review only.

---

## Why

The remaining failures are pipeline problems, not “model not smart enough”:

| Symptom | Cause |
|---------|--------|
| «Etter dette…» / «Videre…» everywhere | Section-isolated generation invents continuity |
| Facts in PDFs unused | Retrieve-top-k ≠ claim/layout extraction |
| EN UI / NO body (or mix) | Language not a hard contract through every stage |
| “No images” while folder is full | Assets exist; selection never ran or never bound |

Foldok already has fragments: `scrub_authored_prose`, `foldok_ask.critic`, `foldok_budget.check_pipeline`, `foldok_select.DocumentContext`.  
**Editorial QA** is the missing **publish gate that only reviews**.

---

## Product shape

```text
Knowledge → Outline → Section Drafts → [scrub] → Editorial QA → Publish
                                              ↑
                                    report only — no rewrite
```

Optional later: **Transition Engine** (opens/closes only) and deeper extraction.  
Not this milestone.

---

## DocumentContext (language contract)

Every generate / compose / QA call receives:

```yaml
language: en | nb-NO          # one document language
style: engineering
audience: installers | engineers | …
tone: professional
units: metric
keep: [standards ids, product names, quotes]
```

Stages must not invent language. UI `lang` → `state.lang` → this contract. Default **`en`**.

---

## What Editorial QA checks (v1)

### Narrative continuity
- Repeated openers: `Etter dette`, `Videre`, `Neste`, `Til slutt`, `Having established`, …
- Same bridge string in ≥2 sections → **fail**

### Body hygiene
- `snake_case` / topic slug lines as prose
- `Key: value` fact-printer lines
- Empty / MANGLER-only sections that still claim success

### Language
- Document language = contract
- Count of majority-wrong-language sentences → **mixed_language**
- Allowed exceptions: IEC/ISO tokens, product names, quoted source text

### Assets (when registry present)
- Section with 0 figures while folder has relevant images/drawings → **unused_assets**
- Never “photos missing” if registry non-empty (`foldok_select` rule)

### Coverage metrics (KPI — not “document created”)

```text
fact_coverage        claims cited / claims available (approx)
procedure_coverage   install-like sections with ≥1 real step quote
language_consistency 1 − mixed_language_rate
repeated_phrases     count of banned openers
mixed_language       count
unused_relevant_assets  count
```

---

## Output

Not a rewritten PDF. An **editorial report**:

```json
{
  "ok": false,
  "language": "en",
  "metrics": { "repeated_phrases": 3, "mixed_language": 0, ... },
  "findings": [
    {
      "code": "repeated_transition",
      "severity": "fail",
      "section": "Compatibility",
      "message": "Opener «Etter dette» also used in Installation",
      "action": "Strip openers or run Transition Engine (future)"
    }
  ]
}
```

UI: show on Compose / before export. Export chip must not say ready when `ok` is false **and** severity includes `fail` (pairs with false-green work).

---

## What we deliberately defer

| Idea | When |
|------|------|
| Transition Engine (rewrite opens/closes) | After QA metrics are trusted |
| Full layout→tables→KG extraction | Parallel track; don’t block QA |
| Multi-agent editorial committee | Never — one deterministic reviewer |

---

## Implementation home

Package: `foldok_editorial/`  
Calls: after assemble / compose_topic_brief  
Depends on: scrub helpers, optional select context, budget pipeline numbers  

**Freeze new packages beyond this one** until EMC golden path + editorial report are weekly green.
