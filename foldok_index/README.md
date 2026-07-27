# foldok_index

Local-first hybrid retrieval that can prove what it contains. One SQLite file.
Only dependency is numpy.

    index.ingest_dir(folder)            idempotent; unchanged files are not re-embedded
    index.reconcile(folder)             what is on disk but not in the index, and why
    index.search(query)                 lexical + semantic, fused by rank, with citations
    index.new_since(watermark)          exact answer to "what arrived since"
    index.context_for_update(key)       what the agent needs before rewriting a document
    index.diagnose()                    11 checks, including a live end-to-end canary

## Files

| File | Contains |
|---|---|
| `model.py` | Manifest records with explicit status. Zero chunks is never "indexed". |
| `extract.py` | Extraction that fails loudly. Empty output is a failure, not a success. |
| `chunk.py` | Deterministic chunking; ids carry the document version. |
| `embed.py` | Embedder protocol, offline fallback, identity tracking. |
| `store.py` | SQLite: documents, chunks, FTS5, vectors, embed cache, watermarks. |
| `hybrid.py` | Reciprocal rank fusion + the recency channel. |
| `index.py` | The facade, including `context_for_update`. |
| `diagnose.py` | Eleven checks that isolate which of six joints broke. |

## Diagnose first

```python
from foldok_index import Index

ix = Index("foldok_index.db")
ix.ingest_dir("/path/to/project/files")

print(ix.reconcile())     # not_indexed | stale | orphaned | failed | empty | unsupported
print(ix.diagnose())      # ingests a canary, finds it three ways, deletes it
```

## Updating a document with new knowledge

Not a search. A lookup.

```python
ix.set_watermark("doc:manual_v3")           # when the document is written
...                                          # files arrive later
ctx = ix.context_for_update("doc:manual_v3")
ctx["new_documents"]   # everything with a higher sequence, in full
ctx["passages"]        # chunks with citations, ready to cite
ctx["problems"]        # files that could not be read — otherwise invisible
ctx["note"]            # "Nothing has been indexed since this document was last written."
```

## Rules the tests enforce

- A document ingested a moment ago is retrievable without reopening the index.
- Zero extracted text is `empty`, never `indexed`.
- Re-ingesting replaces chunks; the previous version's text stops being findable.
- Unchanged files cost no embedding calls.
- Retrieval returns `[]` rather than junk when the corpus cannot answer.
- Rank fusion is immune to score scale; a hostile query cannot take the lexical channel down.
- A desynced FTS index is caught by probing it, not by counting rows.
- Changing the embedder is detected and reported.

```
python -m pytest foldok_index/tests -q
```
