# foldok_claims

Engineering knowledge is mostly not quantities.

## The failure this exists for

Given a folder of EMC standards and cable tray datasheets, Foldok's extractor
returned **eight facts**: an author, a product name, a test lab,
`measurement equipment capability = 100 dB`. NotebookLM, on the same folder,
produced a six-class cable taxonomy, the conducted/radiated distinction,
aggressor versus victim, three explicit hypotheses and five ranked risks.

Count how many of those are `(key, value, unit, source)`. **Zero.**

They are definitions, classifications, conditional rules, distinctions,
hypotheses and risks. The fact schema had nowhere to put any of them, so the
extractor asked for parameters, faithfully returned the only eight it could find,
and every section downstream had nothing else to say.

```
21 claim(s) from the same text:
  8 rule   3 hypothesis   2 classification   2 risk
  2 quantity   1 definition   1 distinction   1 practice   1 reference
```

## Two fields do the work

`modality` — shall / should / may / is / hypothesis. An obligation is not a
description and a hypothesis is not a finding. Collapsing them is how a proposal
gets read as a requirement.

`scope` — frequency band, cable class, environment. Two claims only conflict if
their scopes overlap, and without scope every comparison is a guess.

## Coherence: what free synthesis structurally cannot do

A summary *reconciles by construction* — it produces one coherent account and the
disagreements dissolve into it. Claims held apart can be compared. Run against
the real EMC notes plus a Chalfant datasheet:

```
21 claim(s) from 2 source(s); 2 finding(s)

[high] contested: a hypothesis runs against a binding requirement
                  (trådstige vs lukket bane)
   hypothesis:  Trådstiger kan i visse frekvensområder gi bedre resultater
                enn lukkede baner.
   requirement: For å møte Hard Spec fra Aker er hovedregelen at fullstendig
                lukkede systemer er påkrevd.
   → the requirement governs until the hypothesis is tested — is that written
     down anywhere the customer can see?

[medium] scope_gap: required DC–1 GHz, evidenced 150 kHz–1 GHz
                    — below 150 kHz uncovered
   → is the uncovered band out of scope, or untested?
```

Six checks: `contradicts`, `contested`, `unsupported`, `scope_gap`,
`duplicate`, `inadequate`. Every finding ends in a question a person can answer.

## Files

| File | Contains |
|---|---|
| `model.py` | Claim, Modality, Scope, Quantity. Comparability lives here. |
| `extract.py` | Deterministic bilingual patterns. Nine claim families. |
| `coherence.py` | The six conflict checks. |

## Things it was taught not to do

- Print a regex into a user-facing finding (`trådstige`, not `tr[åa]dstige\w*`).
- State a frequency as `0–1000000000 Hz`.
- Treat a bare measured assertion as nothing — *"Attenuation is 70–120 dB across
  150 kHz to 1 GHz"* matched no family in the first version and produced no claim
  at all, which was the single most useful line in the datasheet.
- Miss a Norwegian obligation because the adjective is at the end of the clause.
- Keep phone numbers, emails and marketing as claims.

```
python -m pytest foldok_claims/tests -q
```
