# foldok_role

Three located bugs, three fixes.

## 1. A vendor brochure decided what the document was about

`plan.corpus_sketch` counted one vote per tag per file:

```python
for e in usable[:100]:
    for t in e.get("content_tags") or []:
        tag_c[t] += 1
themes = [t for t, _ in tag_c.most_common(6)]
```

A published technical document is tagged densely and confidently. A site
photograph is not. So reference material out-votes the project:

```
OLD (one vote per tag): shielding, emc, esd, functional earth, cable routing, sensor
NEW (role-weighted)   : cable routing, emc, separation, cable tray, measurement, verification
```

Files get a role — `project` / `reference` / `unknown` — weighted 1.0 / 0.15 /
0.5. Reference material still contributes, because that is where the shielding
knowledge lives. It just cannot decide the subject.

Signals, weighted rather than chained: a publication number like
`8027032/2022-07-19` (projects do not have those), a manufacturer name, phrases
like *"subject to change without notice"*, a standard as the subject rather than
a citation, and whether the project or client is named anywhere.

Note the asymmetry: **not finding the project's name is a signal only when you
knew the name to look for.** Absence is evidence only if you were looking.

## 2. File sort order named the document

```python
title = Path(usable[0].get("file") or "project").stem
```

Whatever sorted first. Now the artifact names it, then the project, then the
folder — and if nothing does, that is reported as a question rather than
resolved alphabetically.

## 3. A photo was reported missing while it sat in the folder

`PhotoCaptureResolver.can_handle` asks only `requirement.kind == "photo"`. It
never asks whether a photo already exists, because the gap engine's world is
`Document.entries` and an indexed file never becomes one.

```
Photograph of the finished board — Hovedtavle: 2 bilde(r) i mappen kan passe
— bekreft hvilket, eller ta et nytt.
  - hovedtavle_ferdig.jpg — nevner board, hovedtavle, labels
  - kabelbro_gang.jpg — ligger i prosjektmappen

1 av 1 bildekrav har kandidater i mappen. Ingen er bundet automatisk — du bekrefter.
```

**Nothing is bound automatically.** Foldok ranks and explains; a person confirms.
Deciding that *this* photograph proves *that* requirement is the evidential line
the product is built on, and a confident wrong binding is worse than a capture
task. Every photo in the folder is offered even with no overlap — "ligger i
prosjektmappen" — because the user is about to look at the list anyway.

## Wiring

```python
patch  = sketch_patch(index, artifact=artifact, project_name=name)  # -> CorpusSketch
offers = offers_for(session.gaps(), index)                          # before capture tasks
```

`sketch_patch` returns a dict rather than a `CorpusSketch`, so this package does
not import `foldok_ask` — the dependency points one way.

```
python -m pytest foldok_role/tests -q
```
