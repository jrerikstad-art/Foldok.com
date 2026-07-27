# foldok_gaps

Completion engine for Foldok. Turns "30 mangler" into thirty things you can click and finish.
Pure Python, no dependencies. Uses `foldok_diagram` when present, works without it.

    document + requirement pack
        -> evaluate()        gaps, stable ids, pure function
        -> options(gap)      what Foldok can offer
        -> resolve(gap)      artifact | empty form | signed N/A
        -> gate()            can this be exported, and as what

## Files

| File | Contains |
|---|---|
| `requirements.py` | Requirement, RequirementPack, section model, condition language. Breadth lives here. |
| `document.py` | What exists: subjects, entries, artifacts, provenance, confirmation. |
| `gaps.py` | Gap objects, stable ids, pure `evaluate()`, batching. |
| `resolvers.py` | Resolvers and **the evidential guard**. |
| `policy.py` | Build / Review / Compliance. Gating only — evaluation never changes. |
| `completion.py` | `CompletionSession` — the API the UI drives. |
| `packs.py` | Four packs: electrical NO, EU machinery, aquaculture, prototype build log. |

## Quick start

```python
from foldok_gaps import CompletionSession, Document, default_registry, packs

doc = Document(id="job_114", title="Ny kurs — Storgata 14", segment="electrical",
               jurisdiction="NO_IT_230", facts={"has_rcd": True})
doc.add_subject("board", "DB1", "Hovedtavle")
for i in range(1, 6):
    doc.add_subject("circuit", f"K{i}", f"Kurs {i}")

s = CompletionSession(doc, packs.NO_ELECTRICAL, default_registry(), mode="build")

s.progress()          # {'open': 35, 'label': '35 things Foldok can help with', ...}
s.batches()           # 5 x Insulation resistance, 5 x Continuity, ...
s.prepare_everything()  # 30 forms, capture tasks and scaffolds. 0 words authored.

gap = s.gaps().of_kind("measurement")[0]
art = s.resolve(gap.id, "measurement_form").artifact
s.fill(art.id, {"resistance_ohm": 0.21, "instrument": "Fluke 1664"}, by="J. R. Erikstad")

s.set_mode("compliance")
print(s.gate())       # blocked, with a reason and a fix for each item
```

## The rule that matters

```
A model may draft what someone intends.
A model may never author what someone observed.
```

Expository (method statements, scope, principle schematics) → Foldok drafts, marked AI,
does not resolve the gap until a person confirms it.

Evidential (measurements, as-built photos, serial numbers, signatures) → Foldok builds the
empty form and the instruction. Nothing else. Enforced in `ResolverRegistry.check()`,
not in a prompt.

## Rules the tests enforce

- Gap ids are content-addressed; resolving one never renumbers another.
- `evaluate()` is pure, so switching mode is retroactive over work already done.
- Generative resolvers are never offered for an evidential gap.
- A diagram scaffold places only parts that already have a source reference, and assumes no connections.
- "Not applicable" needs a reason and a name; some requirements cannot be waived at all.
- Nothing in build mode blocks; every build export is watermarked.
- No output ever claims compliance.

```
python -m pytest foldok_gaps/tests -q
```
