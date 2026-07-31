# foldok_scan

Why isn't my file in the index?

```python
print(scan("/path/to/project").report())
```

## The bug this came from

A folder reported **"51 files found, 6 indexed"** and explained none of the other
45. It was reported as *"it does not include subfolders"* — a reasonable read of
the evidence, and wrong. `source_files()` does `root.rglob("*")`; recursion was
never the problem.

```
DOC_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".rtf"}
```

No `.doc`, no `.xls`, no `.ppt`, no `.msg`. In a standards library written over
fifteen years those are everywhere, and each one becomes `file_kind() ==
"skipped"` and disappears without a line of explanation.

**The real limitation is not any single filter. It is that a folder can lose 88%
of its material silently, and the only clue is a document that reads thin.**

```
EMC: 12 of 26 files indexed (46%), depth 2
  by folder depth:
    root         2 indexed,   2 dropped
    level 1     10 indexed,   7 dropped
    level 2      0 indexed,   5 dropped
    → level 2 has files but none supported — the folder IS read,
      the formats are not
  dropped because:
      4  '.doc' is not in the supported list
      2  '.dat' is not in the supported list
      2  '.xls' is not in the supported list
      2  '.msg' is not in the supported list
      1  folder 'assets' is on the skip list
      1  hidden file
      1  '.zip' is not indexable (archive — expand it and index the contents)

  Biggest single win: support .doc and recover 4 files
  (legacy Word — readable with the same extractor as .docx).
```

The depth breakdown is the line that matters. A level with files and nothing
indexed reads exactly like a recursion bug from outside; the report says which
it is.

## Widening, measured

```python
before, after = compare(root, widened_doc_ext(scan(root)))
#  12 indexed → 23 indexed  (46% → 88%)
```

`widened_doc_ext` **returns** the set rather than applying it. What counts as a
document has consequences downstream, and that decision should be made once and
deliberately rather than by a scanner.

## What stays dropped, and says so

Archives are told to be expanded. Videos, fonts, executables and databases are
named as not indexable. Files with no extension are *offered* — "may still be
text, check one before deciding" — rather than assumed either way.

```
python -m pytest foldok_scan/tests -q
```
