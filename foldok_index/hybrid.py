"""Hybrid retrieval.

**Fuse by rank, not by score.**  Cosine similarity lives in [-1, 1]; BM25 is
unbounded and corpus-dependent.  Adding or weighting them directly means one
channel silently dominates, and which one it is changes as the corpus grows.
Reciprocal rank fusion only looks at position:

    score(d) = Σ  w_c / (k + rank_c(d))

Every channel contributes on the same scale, a document found by both rises, and
adding a third channel later needs no re-tuning.

**Recency is a channel, not a query.**  "What is new since the last version of
this document" cannot be answered by similarity — the nearest neighbours of the
word "new" are nothing in particular.  This is the specific reason a perfectly
healthy hybrid index still fails the request "update the document with the
knowledge from the files I just uploaded".  So recency is served from the
manifest, exactly, by sequence number, and fused in like any other channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .store import Store

DEFAULT_K = 60.0


@dataclass
class Channel:
    name: str
    results: list[tuple[str, float]]     # (chunk_id, score) best first
    weight: float = 1.0


def semantic(
    store: Store,
    query_vector: Sequence[float],
    limit: int = 50,
    min_similarity: float = 0.0,
) -> list[tuple[str, float]]:
    """Nearest neighbours above a floor.

    The floor matters more than it looks. Without it this channel returns the
    top-k of whatever exists no matter how unrelated, the agent receives
    confident-looking context for a question the corpus cannot answer, and
    "retrieval ran and found nothing" becomes indistinguishable from
    "retrieval ran and found junk".
    """
    matrix, ids = store.matrix()
    if matrix.size == 0 or not ids:
        return []
    q = np.asarray(query_vector, dtype=np.float32)
    if q.shape[0] < matrix.shape[1]:
        q = np.pad(q, (0, matrix.shape[1] - q.shape[0]))
    elif q.shape[0] > matrix.shape[1]:
        q = q[: matrix.shape[1]]
    norm = float(np.linalg.norm(q))
    if norm == 0.0:
        return []
    q = q / norm
    row_norms = np.linalg.norm(matrix, axis=1)
    row_norms[row_norms == 0.0] = 1.0
    scores = (matrix @ q) / row_norms
    top = np.argsort(-scores)[:limit]
    return [
        (ids[int(i)], float(scores[int(i)]))
        for i in top
        if float(scores[int(i)]) >= min_similarity
    ]


def lexical(store: Store, query: str, limit: int = 50) -> list[tuple[str, float]]:
    return store.fts_search(query, limit)


def recency(store: Store, since_seq: int, limit: int = 50) -> list[tuple[str, float]]:
    """Chunks from documents written after ``since_seq``, newest first."""
    rows = store.db.execute(
        "SELECT c.chunk_id AS chunk_id, d.seq AS seq FROM chunks c "
        "JOIN documents d ON d.doc_id = c.doc_id "
        "WHERE d.seq > ? AND d.status='indexed' "
        "ORDER BY d.seq DESC, c.ordinal ASC LIMIT ?",
        (int(since_seq), int(limit)),
    ).fetchall()
    return [(r["chunk_id"], float(r["seq"])) for r in rows]


def rrf(
    channels: Sequence[Channel],
    k: float = DEFAULT_K,
    limit: int = 10,
) -> list[tuple[str, float, dict[str, int]]]:
    fused: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    for ch in channels:
        for position, (chunk_id, _score) in enumerate(ch.results, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + ch.weight / (k + position)
            ranks.setdefault(chunk_id, {})[ch.name] = position
    ordered = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [(cid, score, ranks.get(cid, {})) for cid, score in ordered]
