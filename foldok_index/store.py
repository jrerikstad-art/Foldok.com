"""Storage — one SQLite file.

On the "do we need a vector database" question: at the scale of a project folder,
no.  A hundred thousand chunks at 384 dimensions is 150 MB of float32 and a
brute-force cosine pass over it takes single-digit milliseconds in numpy.  An ANN
index buys nothing until the collection is an order of magnitude larger, and it
costs the two things that actually matter here: a second system to keep in sync
with the manifest, and an approximate recall that makes "why did it not find my
document" unanswerable.  The bug in this class of system is almost always
bookkeeping, not nearest-neighbour search.

So: documents, chunks, FTS5 for lexical, vectors as blobs, all in one file that
can be copied, diffed by row count, and deleted to force a clean rebuild.

Two things in here exist specifically because of the reported symptom:

``_seq``
    A monotonic write counter stamped on every document and chunk.  It makes
    "what arrived since I last looked" exact.

``_invalidate()``
    The vector matrix is cached in memory for speed.  Every write drops it.  A
    retriever holding a matrix loaded at session start, serving searches that
    cannot see anything ingested since, is exactly the failure the user
    described, and ``test_new_document_is_visible_in_the_same_session`` pins it.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from .model import SCHEMA_VERSION, Chunk, SourceDoc

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id       TEXT PRIMARY KEY,
    path         TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    bytes        INTEGER NOT NULL DEFAULT 0,
    mtime        REAL    NOT NULL DEFAULT 0,
    version      INTEGER NOT NULL DEFAULT 1,
    status       TEXT    NOT NULL DEFAULT 'indexed',
    error        TEXT    NOT NULL DEFAULT '',
    chunk_count  INTEGER NOT NULL DEFAULT 0,
    ingested_at  REAL    NOT NULL DEFAULT 0,
    seq          INTEGER NOT NULL DEFAULT 0,
    meta         TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS documents_seq  ON documents(seq);
CREATE INDEX IF NOT EXISTS documents_stat ON documents(status);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id   TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    ordinal  INTEGER NOT NULL,
    text     TEXT NOT NULL,
    heading  TEXT NOT NULL DEFAULT '',
    start    INTEGER NOT NULL DEFAULT 0,
    finish   INTEGER NOT NULL DEFAULT 0,
    vector   BLOB,
    dim      INTEGER NOT NULL DEFAULT 0,
    seq      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS chunks_seq ON chunks(seq);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
    USING fts5(text, heading, content='chunks', content_rowid='rowid', tokenize='unicode61');

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text, heading) VALUES (new.rowid, new.text, new.heading);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, heading)
        VALUES ('delete', old.rowid, old.text, old.heading);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text, heading)
        VALUES ('delete', old.rowid, old.text, old.heading);
    INSERT INTO chunks_fts(rowid, text, heading) VALUES (new.rowid, new.text, new.heading);
END;

CREATE TABLE IF NOT EXISTS embed_cache (
    key        TEXT PRIMARY KEY,
    embedder   TEXT NOT NULL,
    dim        INTEGER NOT NULL,
    vector     BLOB NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS watermarks (
    key        TEXT PRIMARY KEY,
    seq        INTEGER NOT NULL,
    updated_at REAL NOT NULL,
    note       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS roots (
    root       TEXT PRIMARY KEY,
    patterns   TEXT NOT NULL DEFAULT '',
    added_at   REAL NOT NULL
);
"""


def _blob(vec: Sequence[float]) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def _vec(blob: bytes | None) -> np.ndarray | None:
    if not blob:
        return None
    return np.frombuffer(blob, dtype=np.float32)


class Store:
    def __init__(self, path: str | Path = ":memory:", clock=time.time) -> None:
        self.path = str(path)
        self._clock = clock
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.db.commit()
        self._matrix: np.ndarray | None = None
        self._matrix_ids: list[str] = []
        if self.get_meta("schema_version") is None:
            self.set_meta("schema_version", str(SCHEMA_VERSION))

    # -- meta -----------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.db.commit()

    def next_seq(self) -> int:
        cur = int(self.get_meta("seq") or "0") + 1
        self.set_meta("seq", str(cur))
        return cur

    def current_seq(self) -> int:
        return int(self.get_meta("seq") or "0")

    # -- cache invalidation ---------------------------------------------
    def _invalidate(self) -> None:
        """Called by every write.  Without this, a long-lived retriever serves
        searches from a matrix loaded before the new files arrived."""
        self._matrix = None
        self._matrix_ids = []

    # -- documents ------------------------------------------------------
    def put_document(self, doc: SourceDoc) -> SourceDoc:
        self.db.execute(
            """INSERT INTO documents
               (doc_id, path, title, content_hash, bytes, mtime, version, status,
                error, chunk_count, ingested_at, seq, meta)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(doc_id) DO UPDATE SET
                 path=excluded.path, title=excluded.title,
                 content_hash=excluded.content_hash, bytes=excluded.bytes,
                 mtime=excluded.mtime, version=excluded.version,
                 status=excluded.status, error=excluded.error,
                 chunk_count=excluded.chunk_count, ingested_at=excluded.ingested_at,
                 seq=excluded.seq, meta=excluded.meta""",
            (
                doc.doc_id, doc.path, doc.title, doc.content_hash, doc.bytes, doc.mtime,
                doc.version, doc.status, doc.error, doc.chunk_count, doc.ingested_at,
                doc.seq, json.dumps(doc.meta, sort_keys=True),
            ),
        )
        self.db.commit()
        self._invalidate()
        return doc

    def document(self, doc_id: str) -> SourceDoc | None:
        row = self.db.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        return _row_to_doc(row) if row else None

    def document_by_path(self, path: str) -> SourceDoc | None:
        row = self.db.execute("SELECT * FROM documents WHERE path=?", (str(path),)).fetchone()
        return _row_to_doc(row) if row else None

    def documents(
        self,
        *,
        status: str | None = None,
        since_seq: int | None = None,
        limit: int | None = None,
    ) -> list[SourceDoc]:
        sql = "SELECT * FROM documents WHERE 1=1"
        args: list[Any] = []
        if status:
            sql += " AND status=?"
            args.append(status)
        if since_seq is not None:
            sql += " AND seq>?"
            args.append(since_seq)
        sql += " ORDER BY seq DESC, path ASC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [_row_to_doc(r) for r in self.db.execute(sql, args)]

    def delete_document(self, doc_id: str, *, tombstone: bool = True) -> bool:
        doc = self.document(doc_id)
        if doc is None:
            return False
        self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        if tombstone:
            doc.status = "tombstoned"
            doc.chunk_count = 0
            doc.seq = self.next_seq()
            doc.error = ""
            self.put_document(doc)
        else:
            self.db.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        self.db.commit()
        self._invalidate()
        return True

    # -- chunks ---------------------------------------------------------
    def replace_chunks(
        self,
        doc_id: str,
        chunks: Iterable[Chunk],
        vectors: Sequence[Sequence[float]] | None = None,
        seq: int | None = None,
    ) -> int:
        """Delete then insert.  Never insert alongside: stale chunks that survive
        an edit are why an assistant answers from the previous version."""
        chunks = list(chunks)
        if vectors is not None and len(vectors) != len(chunks):
            raise ValueError(
                f"{len(vectors)} vectors for {len(chunks)} chunks — refusing to write a "
                "misaligned index"
            )
        seq = self.current_seq() if seq is None else seq
        self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        rows = []
        for i, ch in enumerate(chunks):
            vec = vectors[i] if vectors is not None else None
            rows.append(
                (
                    ch.chunk_id, ch.doc_id, ch.ordinal, ch.text, ch.heading,
                    ch.start, ch.end, _blob(vec) if vec is not None else None,
                    len(vec) if vec is not None else 0, seq,
                )
            )
        self.db.executemany(
            "INSERT INTO chunks(chunk_id, doc_id, ordinal, text, heading, start, finish,"
            " vector, dim, seq) VALUES(?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        self.db.commit()
        self._invalidate()
        return len(rows)

    def chunks_of(self, doc_id: str) -> list[Chunk]:
        rows = self.db.execute(
            "SELECT * FROM chunks WHERE doc_id=? ORDER BY ordinal", (doc_id,)
        )
        return [_row_to_chunk(r) for r in rows]

    def chunk(self, chunk_id: str) -> Chunk | None:
        row = self.db.execute("SELECT * FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        return _row_to_chunk(row) if row else None

    def chunk_count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"])

    def vector_count(self) -> int:
        return int(
            self.db.execute("SELECT COUNT(*) c FROM chunks WHERE vector IS NOT NULL").fetchone()["c"]
        )

    def fts_count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) c FROM chunks_fts").fetchone()["c"])

    def fts_selftest(self, sample: int = 5) -> tuple[int, int, str]:
        """Probe the lexical index with tokens taken from real chunks.

        A row count cannot detect a desynced FTS table — with external content
        it counts the content table. So take a distinctive token out of a few
        stored chunks and check the index can find them again.
        """
        import re as _re

        rows = self.db.execute(
            "SELECT chunk_id, text FROM chunks ORDER BY chunk_id LIMIT ?", (int(sample),)
        ).fetchall()
        checked = found = 0
        missing: list[str] = []
        for row in rows:
            tokens = [t for t in _re.findall(r"[0-9a-zA-ZÀ-ÿæøåÆØÅ_]{4,}", row["text"])]
            if not tokens:
                continue
            token = max(tokens, key=len)
            checked += 1
            hits = self.fts_search(token, limit=200)
            if any(cid == row["chunk_id"] for cid, _ in hits):
                found += 1
            else:
                missing.append(row["chunk_id"])
        detail = "" if checked == found else f"not findable: {', '.join(missing[:3])}"
        return checked, found, detail

    def integrity_check(self) -> str:
        try:
            self.db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('integrity-check')")
            return "ok"
        except sqlite3.DatabaseError as exc:
            return str(exc)

    def dims(self) -> list[int]:
        return [
            int(r["dim"])
            for r in self.db.execute("SELECT DISTINCT dim FROM chunks WHERE dim>0 ORDER BY dim")
        ]

    # -- search primitives ----------------------------------------------
    def matrix(self) -> tuple[np.ndarray, list[str]]:
        """All vectors as one array.  Rebuilt whenever anything was written."""
        if self._matrix is not None:
            return self._matrix, self._matrix_ids
        ids: list[str] = []
        vecs: list[np.ndarray] = []
        for row in self.db.execute(
            "SELECT chunk_id, vector FROM chunks WHERE vector IS NOT NULL ORDER BY chunk_id"
        ):
            v = _vec(row["vector"])
            if v is None:
                continue
            ids.append(row["chunk_id"])
            vecs.append(v)
        if not vecs:
            self._matrix = np.zeros((0, 0), dtype=np.float32)
            self._matrix_ids = []
            return self._matrix, self._matrix_ids
        width = max(v.shape[0] for v in vecs)
        matrix = np.zeros((len(vecs), width), dtype=np.float32)
        for i, v in enumerate(vecs):
            matrix[i, : v.shape[0]] = v
        self._matrix = matrix
        self._matrix_ids = ids
        return matrix, ids

    def fts_search(self, query: str, limit: int = 50) -> list[tuple[str, float]]:
        match = _fts_query(query)
        if not match:
            return []
        try:
            rows = self.db.execute(
                "SELECT c.chunk_id AS chunk_id, bm25(chunks_fts) AS score "
                "FROM chunks_fts JOIN chunks c ON c.rowid = chunks_fts.rowid "
                "WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?",
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        # bm25() returns lower-is-better; flip so higher is better everywhere
        return [(r["chunk_id"], -float(r["score"])) for r in rows]

    # -- embedding cache -------------------------------------------------
    def cached_vector(self, key: str) -> list[float] | None:
        row = self.db.execute("SELECT vector FROM embed_cache WHERE key=?", (key,)).fetchone()
        if not row:
            return None
        v = _vec(row["vector"])
        return v.tolist() if v is not None else None

    def cache_vector(self, key: str, embedder: str, vector: Sequence[float]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO embed_cache(key, embedder, dim, vector, created_at) "
            "VALUES(?,?,?,?,?)",
            (key, embedder, len(vector), _blob(vector), self._clock()),
        )
        self.db.commit()

    def clear_cache(self, embedder: str | None = None) -> int:
        cur = (
            self.db.execute("DELETE FROM embed_cache WHERE embedder=?", (embedder,))
            if embedder
            else self.db.execute("DELETE FROM embed_cache")
        )
        self.db.commit()
        return cur.rowcount

    # -- watermarks ------------------------------------------------------
    def set_watermark(self, key: str, seq: int, note: str = "") -> None:
        self.db.execute(
            "INSERT INTO watermarks(key, seq, updated_at, note) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET seq=excluded.seq, updated_at=excluded.updated_at, "
            "note=excluded.note",
            (key, int(seq), self._clock(), note),
        )
        self.db.commit()

    def watermark(self, key: str) -> int | None:
        row = self.db.execute("SELECT seq FROM watermarks WHERE key=?", (key,)).fetchone()
        return int(row["seq"]) if row else None

    def watermarks(self) -> dict[str, int]:
        return {
            r["key"]: int(r["seq"])
            for r in self.db.execute("SELECT key, seq FROM watermarks ORDER BY key")
        }

    # -- roots -----------------------------------------------------------
    def add_root(self, root: str, patterns: Sequence[str] = ()) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO roots(root, patterns, added_at) VALUES(?,?,?)",
            (str(root), json.dumps(list(patterns)), self._clock()),
        )
        self.db.commit()

    def roots(self) -> dict[str, list[str]]:
        return {
            r["root"]: json.loads(r["patterns"] or "[]")
            for r in self.db.execute("SELECT root, patterns FROM roots ORDER BY root")
        }

    # -- housekeeping -----------------------------------------------------
    def stats(self) -> dict[str, Any]:
        by_status = {
            r["status"]: r["n"]
            for r in self.db.execute(
                "SELECT status, COUNT(*) n FROM documents GROUP BY status ORDER BY status"
            )
        }
        return {
            "path": self.path,
            "documents": sum(by_status.values()),
            "by_status": by_status,
            "chunks": self.chunk_count(),
            "vectors": self.vector_count(),
            "fts_rows": self.fts_count(),
            "dims": self.dims(),
            "seq": self.current_seq(),
            "embedder": self.get_meta("embedder") or "",
            "cache_rows": int(
                self.db.execute("SELECT COUNT(*) c FROM embed_cache").fetchone()["c"]
            ),
            "roots": list(self.roots()),
            "watermarks": self.watermarks(),
        }

    def rebuild_fts(self) -> int:
        self.db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        self.db.commit()
        return self.fts_count()

    def close(self) -> None:
        self.db.commit()
        self.db.close()


# ----------------------------------------------------------------------
def _row_to_doc(row: sqlite3.Row) -> SourceDoc:
    return SourceDoc(
        doc_id=row["doc_id"],
        path=row["path"],
        title=row["title"],
        content_hash=row["content_hash"],
        bytes=int(row["bytes"]),
        mtime=float(row["mtime"]),
        version=int(row["version"]),
        status=row["status"],
        error=row["error"],
        chunk_count=int(row["chunk_count"]),
        ingested_at=float(row["ingested_at"]),
        seq=int(row["seq"]),
        meta=json.loads(row["meta"] or "{}"),
    )


def _row_to_chunk(row: sqlite3.Row) -> Chunk:
    return Chunk(
        chunk_id=row["chunk_id"],
        doc_id=row["doc_id"],
        ordinal=int(row["ordinal"]),
        text=row["text"],
        heading=row["heading"],
        start=int(row["start"]),
        end=int(row["finish"]),
        seq=int(row["seq"]),
    )


def _fts_query(query: str) -> str:
    """FTS5 syntax is unforgiving; a raw user string with a stray quote or a
    bare OR raises and takes the whole lexical channel down silently."""
    import re

    terms = [t for t in re.findall(r"[0-9a-zA-ZÀ-ÿæøåÆØÅ_]{2,}", query)]
    if not terms:
        return ""
    return " OR ".join(f'"{t}"' for t in terms)
