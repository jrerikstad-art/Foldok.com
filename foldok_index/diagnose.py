"""Diagnosis — run this before changing anything.

"The indexer is not working" is six different bugs wearing one symptom.  This
walks them in order and tells you which one you have:

    1  store reachable and schema current
    2  embedder identity matches what wrote the vectors
    3  documents that failed, or were indexed with zero chunks
    4  vectors present for every chunk, all the same width
    5  FTS row count matches the chunk count
    6  the folder agrees with the manifest
    7  canary: a fresh document is findable lexically
    8  canary: the same document is findable semantically
    9  canary: the same document appears in the recency channel — and is
       visible without reopening the index, which is the failure that looks
       exactly like "the indexer did not run"

The canary is ingested, searched, and removed inside the call, so it is a real
end-to-end test of the live index rather than an inspection of its metadata.
"""

from __future__ import annotations

from pathlib import Path

from .model import Diagnosis

CANARY_KEY = "__foldok_canary__"
CANARY_TOKEN = "zylophonebracket"
CANARY_TEXT = (
    f"Foldok index self test. The unique marker for this check is {CANARY_TOKEN}. "
    "It exists only to prove that a document written a moment ago can be found "
    "again immediately, through every retrieval channel, without restarting."
)


def diagnose(index, root: str | Path | None = None) -> Diagnosis:
    d = Diagnosis()
    store = index.store
    stats = store.stats()
    d.stats = stats

    # 1 -----------------------------------------------------------------
    schema = store.get_meta("schema_version")
    d.add(
        "store reachable",
        schema is not None,
        f"{stats['path']}, schema {schema}, {stats['documents']} document(s)",
        "the database file is missing or unreadable",
    )

    # 2 -----------------------------------------------------------------
    stored_embedder = store.get_meta("embedder") or ""
    d.add(
        "embedder identity matches the stored vectors",
        not index.embedder_changed,
        f"index was written by '{stored_embedder}', now using '{index.embedder.id}'",
        "vectors from a different model are not comparable and similarity will look "
        "plausible while being meaningless — reindex with force=True, then update the "
        "stored embedder id",
    )

    # 3 -----------------------------------------------------------------
    by_status = stats["by_status"]
    broken = sum(by_status.get(s, 0) for s in ("failed", "empty", "unsupported"))
    detail = ", ".join(f"{k}={v}" for k, v in by_status.items()) or "none"
    d.add(
        "no document failed to extract",
        broken == 0,
        detail,
        "these files were accepted but produced no text; a scanned PDF is the usual "
        "cause. They are the files the assistant cannot see. Run reconcile() for the list",
    )

    zero = [doc for doc in store.documents(status="indexed") if doc.chunk_count == 0]
    d.add(
        "no document is indexed with zero chunks",
        not zero,
        f"{len(zero)} document(s): " + ", ".join(x.path for x in zero[:5]),
        "this is the failure that reports success — re-ingest them",
    )

    # 4 -----------------------------------------------------------------
    chunks, vectors, dims = stats["chunks"], stats["vectors"], stats["dims"]
    d.add(
        "every chunk has a vector",
        chunks == vectors,
        f"{vectors} vector(s) for {chunks} chunk(s)",
        "embedding failed part way through; re-ingest the affected documents",
    )
    d.add(
        "all vectors have the same width",
        len(dims) <= 1,
        f"dims present: {dims}",
        "vectors of different widths mean two embedders wrote into one index; "
        "reindex with force=True",
    )

    # 5 -----------------------------------------------------------------
    checked, found, detail = store.fts_selftest()
    d.add(
        "lexical index can find text that is stored",
        checked == found,
        f"{found}/{checked} sampled chunk(s) found by their own words"
        + (f" — {detail}" if detail else ""),
        "call store.rebuild_fts(); a desynced FTS table halves hybrid recall silently, "
        "and a row count will not reveal it because external-content FTS counts the "
        "content table",
    )
    d.add(
        "lexical index passes its own integrity check",
        store.integrity_check() == "ok",
        store.integrity_check(),
        "rebuild it",
    )

    # 6 -----------------------------------------------------------------
    roots = [str(root)] if root else list(store.roots())
    if roots:
        report = index.reconcile(roots[0] if root else None)
        d.add(
            "the folder agrees with the index",
            report.ok,
            str(report.summary()) if report.drift else f"{report.scanned} file(s), no drift",
            "reconcile() lists every disagreement and what to do about each",
        )
    else:
        d.add(
            "a folder is registered for reconciliation",
            False,
            "no root has been registered",
            "call ingest_dir(folder) at least once, or reconcile(folder) explicitly — "
            "without a registered root nothing can answer 'is this file in the index'",
        )

    # 7/8/9 --------------------------------------------------------------
    head_before = index.head()
    try:
        index.ingest_text(CANARY_KEY, CANARY_TEXT, title="Foldok canary")

        lex = index.search(CANARY_TOKEN, k=5, mode="lexical")
        d.add(
            "canary: a new document is found lexically",
            any(CANARY_TOKEN in h.chunk.text for h in lex),
            f"{len(lex)} hit(s)",
            "the FTS table is not being written or not being queried; "
            "check the triggers on the chunks table",
        )

        sem = index.search(CANARY_TEXT[:120], k=5, mode="semantic")
        d.add(
            "canary: a new document is found semantically",
            any(h.doc.title == "Foldok canary" for h in sem),
            f"{len(sem)} hit(s)",
            "vectors are not reaching the search path — check that the in-memory matrix "
            "is invalidated on write",
        )

        fresh = index.new_since(head_before)
        d.add(
            "canary: a new document appears in the recency channel",
            any(x.title == "Foldok canary" for x in fresh),
            f"{len(fresh)} document(s) since seq {head_before}",
            "sequence numbers are not being stamped on write; without them 'what is new' "
            "has to be guessed by similarity, which is why new uploads get missed",
        )
    finally:
        index.store.delete_document(
            __import__("foldok_index.index", fromlist=["doc_id_for"]).doc_id_for(CANARY_KEY),
            tombstone=False,
        )

    return d
