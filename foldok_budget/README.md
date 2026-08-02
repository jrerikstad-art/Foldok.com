# foldok_budget

The blocker that kept every document thin — and the contracts that stop it
happening again silently.

## What was holding it back

`author_doc.py:494`

```python
if not cites.unused(local.file_id) and out:
    continue
```

`_body_used` is **document-wide**. Once a file has been cited anywhere, every
other claim from it is discarded for the rest of the document. A 30-page EMC
basis of design contributes one sentence and is spent. `_pick_claims` has a
second copy of the same rule (`files: set[str]`), so a file cannot contribute
twice even within one section.

Run against the real numbers:

```
PIPELINE [BROKEN]
  [ ok ] index: 51 → 44
  [ ok ] extract: 44 → 380
  [ ok ] plan: 380 → 7
  [ ok ] author: 7 → 7
  [thin] cite: 380 → 14
         366 of 380 claims were discarded before reaching the page
  [FAIL] completeness: 0 → 0
         zero requirements were checked, so zero gaps were found.
         'No gaps' here means 'nothing was examined'.

EXPORT: blocked
```

**The engines were working. The author was throwing away 96% of their output.**

It also explains the other two symptoms. Project files were consumed early, so by
the time an installation sequence was authored the only "unused" files left were
vendor manuals — a four-word aside from page 23 of a supplier PDF became step 1
because the project's own material was *banned*, not outranked. And adding
sections made it worse, because each new section drew from the least-touched, and
therefore least relevant, source.

## The fix is scope, not removal

The intent was right: do not let one document dominate. The scope was wrong. A
rich source *should* be quotable many times across a document.

```
per section       3 citations from one file
per document      45% share before it reads as a monoculture
```

One file: **1 sentence → 12**, and the document-share ceiling still stops any
single source taking over.

`rank_key` puts **role before keywords**, so a vendor manual can only ever be a
fallback.

## Contracts, because one weak link takes the document down

Both failures here were silent. Discarding claims is not an error condition, and
neither is finding zero gaps in an empty ledger — that one *reported success*.

`check_pipeline` judges each boundary on what the next stage needs, names the
first real failure rather than six downstream symptoms, and treats **unchecked as
not exportable**. A document whose completeness ledger was never populated is not
complete; it is unexamined, and saying "ready to export" about it is the worst
output this product can produce.

```
python -m pytest foldok_budget/tests -q
```
