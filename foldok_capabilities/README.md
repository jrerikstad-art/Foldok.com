# foldok_capabilities

Derived from the engines, reconciled with the manifest.

```python
rec = reconcile(".")
print(rec.report())
write_manifest("capabilities.json", merge_into(load_manifest("."), rec.capabilities))
```

## The bug this exists for

A user asked for a schematic. Foldok answered:

> Correct. I have no drawing tools, only text.

The same build ships 45 diagram symbols across four domains, orthogonal routing,
SVG output and green golden tests.

**Nothing was broken.** `hub_chat.py` tells the model, as a hard rule, that
capability claims must come from `capabilities.json` — and that file contained
the word *diagram* exactly zero times. The anti-hallucination guardrail was
stricter than the capability list was complete, so it suppressed a real feature.
Correct behaviour, wrong inputs, and it would have answered that way for every
user forever.

```
6 capability(ies) found in the engines, 0 declared in the manifest
4 blocking, 1 advisory
  [undeclared] 'diagrams' ships (45 symbols) but the manifest never mentions it
      fix: add the generated block — until then the assistant is instructed
           never to claim it, and will deny it to every user
  [unqualified_denial] 'tegne eller modellere i 3D' uses a broad verb
           (draw, model) with nothing tying it down
```

## Two decisions

**Capabilities are derived, not declared.** Symbol counts come from the files on
disk, requirement counts from the packs, page sizes from the layout engine. A
hand-maintained list falls behind the code and nothing notices — which is
exactly what happened.

**A limit belongs to its capability.** The old `cannot` list carried
`tegne eller modellere i 3D`, written to disclaim CAD. A model reading it under
pressure drops the *3D* and concludes it cannot draw. Attached to its capability,
the same fact cannot over-generalise:

```
diagrams: single-line, interconnection and piping diagrams
  not: board-level electronics — no microcontroller, header-pin or GPIO symbols;
       Foldok produces a structured pin table instead
  not: native CAD is not read or written (DWG, STEP)
  not: no 3D modelling — the engine is 2D on a page grid
```

Generation moves covered denials out of `cannot` and into limits, across
languages.

## Four kinds of drift

| code | meaning | severity |
|---|---|---|
| `undeclared` | the engine ships it, the manifest never says so | fail |
| `contradicted` | the `cannot` list denies something that ships | fail |
| `unqualified_denial` | a bare broad verb with nothing pinning it down | warn |
| `overclaimed` | the manifest promises what no engine provides | warn |

## Three false positives it was taught not to make

An **input checklist is not a claim** — a template asking for `□ koblingsskjema`
requests a file from the user; reading it as a capability is how a checker misses
the gap it exists to find.

A **domain word is not a declaration** — "electrical" in a template name says
nothing about diagrams.

A **capability's verb is declared, not inferred from prose** — the privacy
summary says "every model request", which made a denial about 3D *modelling*
look like a contradiction.

## Files

| File | Contains |
|---|---|
| `model.py` | Capability, Limit, Denial, Drift, verb normalisation. |
| `discover.py` | Reads the engines. Counts, never assertions. |
| `reconcile.py` | The four drift checks. |
| `render.py` | Manifest block and prompt lines from one source. |

```
python -m pytest foldok_capabilities/tests -q
```
