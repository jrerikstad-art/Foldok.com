# foldok_volume

Document length decided by the corpus, not by a template.

## The arithmetic

```
_plan_topic_brief  ->  6 OutlineSection(...)
_plan_install      ->  7 OutlineSection(...)
extract_claims(hits, limit=6)
```

Six or seven fixed sections, at most six claims each. **Forty claims, whatever
the folder holds.** The outline is a template, so the document's size is settled
before the corpus is read — four files and four hundred produce the same shape.

```
5 av 39 utsagn (13%) passer i den faste disposisjonen;
6 seksjon(er) foreslås for resten — slett det du ikke vil ha

  + Ekvipotensialforbindelse — 8 utsagn fra 4 kilde(r)
  + Kabelklasser            — 7 utsagn fra 3 kilde(r)
  + Separasjonsavstand      — 7 utsagn fra 3 kilde(r)

outline: 2 -> 8 sections
```

## Why generate wide

**Deleting a section costs a click. Discovering a section is missing costs a site
visit** — or a rejected handover, or a conversation with an inspector. The two
errors are not equally expensive, so the default should not sit in the middle.

## What it will not do

Pad. Volume from repetition is worse than brevity: it buries the real content and
teaches the reader to skim. A section needs **three statements from two
different documents** before it is proposed, so a one-off mention never becomes a
heading and a single chatty source cannot inflate a document on its own.

## Themes are topics, not filler

Picking the longest word per claim gave *"Punkt"* and *"Mellom"*. Requiring
cross-document recurrence removed some of it and left *"Utføres"* and *"Krever"*
— because **frequency cannot separate a verb from a noun.** Engineering prose
repeats "shall be carried out" as reliably as it repeats "earthing". So the
grammar is filtered, not the statistics.

## Proposals are marked, never blended in

A document that grew for reasons nobody can see is worse than a short one. Every
proposed section carries `proposed: True`, its weight, its sources, and the
statements behind it — so the editor can show it differently and a user striking
it knows exactly what they are dropping.

```
python -m pytest foldok_volume/tests -q
```
