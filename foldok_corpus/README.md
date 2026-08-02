# foldok_corpus

The folder proposes, the user disposes, the engine holds the order.

## Why five documents looked identical

Two causes, and they were being confused.

**Three pages** was the citation blocker — see `foldok_budget`. Fixed separately.

**The sameness** is this: a template asks *"what document are you making?"*
before anything has been read, and then its section list becomes a ceiling. A
folder with fourteen topics loses eight of them whichever template is chosen, and
every template draws from the same narrow pool.

Worse, the pool itself was narrow. `foldok_claims` recognises ten types — quantity,
definition, classification, rule, constraint, practice, distinction, hypothesis,
risk, reference — and **every one answers "what is true?"** No matter how sections
were selected, they were all built from statements of fact about the same subject.

## Extraction is the core

Ten more types, none propositional, each seeding a section a fact-only extractor
cannot produce:

```
decision        "vi valgte lukkede baner framfor trådstiger"  → Valg og begrunnelse
problem         "korrosjon i skjøtene ble oppdaget i mai"     → Problemer og funn
consequence     "dette gir 40 mm større bøyeradius"           → Konsekvenser
condition       "ved temperaturer under -20 °C gjelder ikke"  → Forutsetninger
responsibility  "leverandøren skal levere sertifikat"         → Ansvar og roller
change          "revidert fra 4 mm² til 6 mm² i rev C"        → Endringslogg
open_question   "ikke avklart om broen skal jordes"           → Åpne punkter
exception       "unntatt sone 2"                              → Avvik og unntak
sequence        "etter at broen er montert, trekkes kabel"    → Rekkefølge
justification   "fordi armering skjermer dårlig ved HF"       → Begrunnelse
```

**One sentence can be two kinds.** *"Vi valgte X fordi Y"* is a decision *and* a
justification, and they feed different sections — forcing one reading is part of
what made documents alike.

## Naming the label goes last — identity does not

Identity (purpose, audience, primary vs secondary topics) comes from
`foldok_identity` *before* the market runs. What goes last is only the document
*name* / template label.

```
Mappen støtter 5 seksjon(er) fra 18 utsagn i 2 kilder.
Ingen dokumenttype er valgt.

  Grunnlag
    Krav — 3 utsagn fra 2 kilder
    Forutsetninger og gyldighet — 2 utsagn fra 2 kilder
    Valg og begrunnelse — 2 utsagn fra 2 kilder
  Dokumentasjon
    Problemer og funn — 2 utsagn fra 2 kilder
  Avvik og åpne punkter
    Åpne punkter — 2 utsagn fra 2 kilder

Slett det du ikke vil ha. Dokumentet blir det du beholder.
```

**Two statements from two different sources is enough.** Requiring three
suppressed exactly the sections that make documents differ — decisions,
conditions, problems, open questions are rarer than requirements by nature, not
less important. A single source can still carry a section if it says enough
(four statements).

## Abundance still needs an arc

A pile of sections in no order is not a document. Sections sit in bands —
`frame → basis → body → evidence → exception → close` — and weight orders
*within* a band, never across one. The *preferred arc* (installation vs research
vs failure analysis) comes from `NarrativeBlueprint`, not from band decoration
alone. `check_order` reports an outline where evidence precedes its basis,
because that reads as a mistake even when every sentence is correct.

See also `PROJECT_IDENTITY.md`.

## Honest about overlap

```
2 dokument(er) fra samme mappe:
  Kravdokument: 3 seksjon(er), 2 unik (sec.condition, sec.problem)
  Beslutningsnotat: 3 seksjon(er), 2 unik (sec.decision, sec.open_question)
  felles for alle: 1 seksjon(er)
```

Abundance cannot manufacture distinctness that is not in the corpus. When two
selections are identical it says so — *"dokumentene er identiske i innhold"* —
rather than hiding it behind two names.

## Templates invert

Instead of *"installation manual = these six sections"*, a template becomes
*"a handover package must contain a declaration and test records"* — a
**requirement over the selection** rather than a recipe for it. That is
`foldok_gaps` already, and it puts the relationship the right way round: the user
knows what they need, Foldok checks whether they have it.

```
python -m pytest foldok_corpus/tests -q
```
