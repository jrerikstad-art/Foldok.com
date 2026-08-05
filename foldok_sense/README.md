# foldok_sense

Make sense of this folder — the first step, which was never built.

## What was wrong with the order

Everything before this answered *"what fills the Installation section?"* A
template names the sections, retrieval hunts for matching sentences, and when the
hunt fails the section is reported empty:

```
Shielding      strict 6 → loose 6
Installation   strict 0 → loose 0
```

Loosening the claim filter moved usable sentences from 103 to 252 and left
Installation at zero — because a 40-page document about EMC background contains
no installation prose. **No amount of loosening creates content that is not
there.**

The opposite motion is what a new engineer needs: read everything, see what is
in there, group it, and let the groups *be* the document.

```
1 file → 14 topics, 214 cited sentences, 20 figures.
Not covered by this folder: installasjon, montering

  Connection      97 sentences,  4 figures,  51% strong
  Cable           59 sentences,  2 figures,  53% strong
  Shielding       56 sentences,  1 figure,   50% strong
  Earth           32 sentences,  0 figures,  41% strong
```

That discovers the folder contains shielding, bonding, protection classes and
ground loops — **and no installation procedure**, which is the truth and more
useful than an empty heading.

## Three rules

**Topics come from cross-source recurrence.** Within one document a writer
repeats their own vocabulary; between documents, only the subject matter recurs.
A single-file folder falls back to frequency, because a folder of one file is
still a folder somebody wants sense made of.

**Strong passages lead, descriptive ones follow and are marked** with `^` and a
footnote. The user deletes, so the user has to see which is which. Provenance is
honest about the difference: `(rule, EN 50174-2.pdf)` for a matched claim,
`(EN 50174-2.pdf)` for a sentence that merely appeared there.

**A figure with no matching topic stays unplaced.** Dropping it into the nearest
group would be a quiet lie; unplaced figures are listed at the end.

## Inflection

`Cable` and `Cables` as two headings about the same thing is what the stemmer
prevents — bilingual, including the Norwegian epenthetic *e* (`kabel` → `kabler`).
Order matters: strip the inflection first, then the vowel, or `kabler` becomes
`kablr`. Headings show the commonest surface form, never the stem.

Document furniture — *page*, *figure*, *section*, *annex* — is excluded, because
"See figure 4 on page 17" appears in every cross-reference and `Page` was
becoming a topic.

## What it deliberately does not do

Name a document type, check completeness, or claim readiness. Those come
afterwards, on a draft that exists.

```
python -m pytest foldok_sense/tests -q
```
