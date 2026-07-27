# WO 0.65 — Index: diagnosis, manifest, and the recency channel

**Target build:** 0.65
**Engine source:** `foldok_index/` (attached — 38 tests green; 112 across all three engines)
**Symptom this addresses:** files uploaded and reported indexed; the agent, asked to update a document with them, saw nothing.

---

## 1. First, the honest part

I can't tell you whether your hybrid index is working — I've never seen it. Anyone who answers that question without reading your code is guessing.

What I can tell you is that the symptom you described is **six different bugs wearing one face**, that they are cheap to tell apart, and that your instinct about the manifest is the right one. If the index cannot answer *"is this file in you, and when did it arrive"* without running a search, then nothing downstream can be trusted, and every debugging session starts from zero.

So this WO is a diagnostic first and a rebuild second. Run the diagnostic against your current index before deciding whether to replace anything.

---

## 2. The six failure points

Between "user drops a file in a folder" and "agent uses it", these are the joints, in order:

| # | Joint | Failure | How it looks |
|---|---|---|---|
| 1 | **Extract** | scanned PDF, wrong extension, encrypted file → zero text | "indexed: ok", zero chunks |
| 2 | **Chunk** | empty text → zero chunks, no error raised | same |
| 3 | **Embed** | API failure mid-batch, or length mismatch | some chunks vectorless, or every vector after the gap misaligned |
| 4 | **Write** | written to a different collection, session scope vs project scope, not committed | present in one place, queried in another |
| 5 | **Visible** | retriever holds an in-memory matrix loaded at session start | works after restart, not before — the classic |
| 6 | **Retrieved** | agent never called the tool, or called it with a query that cannot surface an unseen file | confident answer from stale context |

**My money is on 6, then 1, then 5.** Here's why 6 is first.

---

## 3. The thing no amount of hybrid tuning fixes

"Update the document with the knowledge from the new files" is **not a semantic query**. The nearest neighbours of the word *new* are nothing in particular. A perfectly healthy hybrid index fails this request, because the agent has to (a) decide to retrieve at all, and (b) invent a query that happens to surface documents it has never seen. Both steps fail routinely, and they fail *silently* — the agent answers from what it already has and reports success. Which is exactly what you saw.

**Recency is a manifest question, not a similarity question.**

Every write gets a monotonic sequence number. Every document records the index sequence it was last written against. Updating it is then a lookup:

```python
ctx = index.context_for_update("doc:manual_v3")
# -> every document with seq > watermark, in full, with citations
# -> plus the files that FAILED to extract, which are otherwise invisible
# -> plus an optional topical search as a second channel
```

Nothing is embedded, nothing is ranked, nothing can be missed. And when there is genuinely nothing new, the agent is told so as a fact from the manifest rather than a search that came back empty — which is a different claim and should read differently.

Live output from the attached build:

```
note: 1 document(s) arrived since the last update; 2 could not be read
new : ['project/addendum.md#chunk=0 (Addendum 2026-07)']
bad : [('scan.pdf', 'failed'), ('notes.heic', 'unsupported')]
```

Those two unreadable files are the interesting part. In the old shape they were "indexed" and invisible forever.

---

## 4. Do we need a vector database?

Probably not, and I'd resist adding one.

A hundred thousand chunks at 384 dimensions is ~150 MB of float32. A brute-force cosine pass over that in numpy is single-digit milliseconds. An ANN index buys nothing at your scale and costs the two things that actually matter here: a second system to keep in sync with the manifest, and approximate recall that makes *"why didn't it find my document"* unanswerable. You cannot debug a probabilistic miss.

The attached build is one SQLite file: documents, chunks, FTS5 for lexical, vectors as blobs. Copyable, diffable by row count, deletable to force a clean rebuild. Local-first, same discipline as the rest of Foldok. Revisit ANN at ~1M chunks, not before.

**Two things in your current hybrid worth checking regardless of what you keep:**

**Fusion.** If BM25 and cosine scores are combined by addition or weighted sum, one channel dominates and which one changes as the corpus grows — cosine is bounded in [-1,1], BM25 is unbounded and corpus-dependent. Fuse by *rank*: `Σ w/(k + rank)`, k=60. Two tests in the suite pin this.

**Incremental lexical updates.** BM25 needs corpus statistics. If your lexical side is a hand-rolled index that isn't recomputing IDF on add, recall quietly degrades as documents arrive. SQLite FTS5 handles it correctly; that's most of why I used it.

**A floor on the semantic channel.** Without one it returns the top-k of whatever exists, however unrelated — so "found nothing" and "found junk" look identical to the agent. Default 0.15 here, and `search()` returns `[]` rather than filler. There's a test for it.

---

## 5. Run this tonight

Against the attached build, pointed at a copy of the real folder:

```python
from foldok_index import Index
ix = Index("foldok_index.db")
ix.ingest_dir("/path/to/the/folder")
print(ix.reconcile())       # what's on disk, what's in the index, and every disagreement
print(ix.diagnose())        # 11 checks, including a live end-to-end canary
```

`diagnose()` ingests a synthetic document with a rare token, finds it lexically, semantically and by recency, then deletes it — inside the call. It tests the live path rather than inspecting metadata. If your real index has the same shape, port the checks; if it can't answer them, that's the answer.

The check that matters most for your symptom is the canary's third leg: *a document written a moment ago is retrievable without reopening the index*. Failure #5 passes every metadata inspection.

---

## 6. Tasks

### T1 — Manifest, before anything else
Every indexed file gets a row: path, content hash, mtime, version, **status**, error, chunk count, ingest time, sequence. Status is `indexed | empty | failed | unsupported | tombstoned` — and **zero chunks is never `indexed`**. A pipeline that reports success after producing nothing is the single most common cause of this complaint, and it's the one lie the model here can't tell.

**Done when:** the app can answer "is this file in the index, and when did it arrive" without a search.

### T2 — Reconcile in the UI
`reconcile(folder)` returns `not_indexed | stale | orphaned | failed | empty | unsupported`, each with a fix. Put it behind a visible "Check index" button on the project screen with the counts. Users should never have to trust that indexing worked.

### T3 — Watermarks and `context_for_update`
Every generated document stores the sequence it was written against. "Update with new knowledge" calls `context_for_update`, not `search`. Show the user the file list before rewriting, including the unreadable ones.

**Done when:** the reported bug is structurally impossible — a new file either appears in the update context or appears in `problems`.

### T4 — Failure surfacing
A file that failed to extract must be visible where the user uploaded it, not only in a log. "3 of 12 files could not be read" with the reasons. Scanned PDFs need OCR; say so in those words.

### T5 — Retrieval contract
Every hit carries `path#chunk=n`. Anything a retrieval puts into a document enters as **unconfirmed AI content with the citation as `provenance.ref`** — the same rule as WO 0.64. That closes the loop: a claim in a compliance document can name the file it came from, and can't be exported until a person confirms it.

### T6 — Reindex triggers
Store the embedder id. If it changes, refuse to serve blended results and require a reindex. Mixed-embedder vectors produce plausible-looking similarity over meaningless geometry — nothing errors, results are simply wrong.

### T7 — CI
```
python -m pytest foldok_index/tests foldok_gaps/tests foldok_diagram/tests -q   # 112
```

---

## 7. Do not build

- An ANN index at this scale.
- Score-additive hybrid fusion.
- A semantic channel with no relevance floor.
- Any path where extraction failure produces a success status.
- "What's new" answered by embedding similarity.
- Chunk insertion on re-ingest without deleting the previous version's chunks — stale chunks surviving an edit is why an assistant answers from the old file.

---

## 8. What I need from you to go further

- The result of `reconcile()` and `diagnose()` against the real folder. That converts my guess into a finding.
- How the current index is scoped — per session, per project, or global? Failure #4 lives entirely in that answer, and it's the one I can't reason about blind.
- Whether the agent's retrieval is a tool it chooses to call, or a step that always runs before a document write. If it's the former, that alone explains the symptom, and T3 fixes it without touching the index at all.
