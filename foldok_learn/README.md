# foldok_learn

Tier 1 only. The tool gets better at **your** work, on **your** machine.

```python
learner.observe_standard(text, standard="NEK 400:2022", source="file_0031")
learner.observe_layout(session, document_id="job_114")
learner.observe_resolvers(session, document_id="job_114")

learner.proposals()          # what it noticed, with evidence counts
learner.accept(lesson_id)    # applies it
learner.revert(lesson_id)    # undoes it, always
```

## The line this package turns on

    You cannot keep what a standard SAYS.
    You can keep what it REQUIRES.

The sentence is copyrighted and selling access to it is the standards body's
entire business. The *fact* that §6-61 obliges an insulation resistance
measurement, per circuit, is a fact, and encoding it with a citation is what
compliance software has always been.

```
3 obligation(s) from 6 sentence(s) — 1 measurement, 1 signature, 1 photo

pack: local.nek_400_2022 | redistribution: reference_only | local_only: True
  blocking     Measurement required (§6-61)              per circuit  evidential
  recommended  Photographic record required (§8-1)       per board    evidential
```

Stored: clause id, obligation strength, artefact kind, repetition scope,
confidence, and how long the source sentence was — **a number, not the text**.
There is a test asserting no phrase from the standard survives anywhere.

## Three rules that make learning trustworthy

**Learn only from confirmed things.** A draft nobody accepted is evidence that
Foldok guessed, not evidence of preference. Template defaults are not evidence
either — they are what the user was given.

**Never generalise from one example.** Every lesson carries its evidence count
and a threshold. One hand-resized image is a hand-resized image; three is a
preference. A changed habit *restarts* the count rather than averaging two
preferences into one that is nobody's.

**Everything is visible and revertable.** A tool that silently changes its own
behaviour is worse than one that never learns, because the user cannot tell a
feature from a fault. `report()` lists every lesson, its evidence, and what it
would change.

## The sharing wall

Everything produced is born `local_only` and `reference_only`, so
`foldok_assets.seal()` refuses to package it — tested. `Learner.export()` exists
only to raise:

> Sharing needs consent, sanitising and a licence — build that deliberately, do
> not route through here.

Tier 2 and Tier 3 are separate deliberate builds, not a flag in this file.

## Files

| File | Contains |
|---|---|
| `model.py` | Lesson, Evidence, ClauseFinding, thresholds, the sharing guard. |
| `standards.py` | Clause extraction, bilingual NO/EN. Citations, never text. |
| `learner.py` | Observers, proposals, accept/reject/revert, local packs. |

```
python -m pytest foldok_learn/tests -q
```
