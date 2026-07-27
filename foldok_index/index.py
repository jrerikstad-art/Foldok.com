"""The index.

Public surface:

    index.ingest_dir(folder)          idempotent; unchanged files are not re-embedded
    index.reconcile(folder)           what is on disk but not in the index, and why
    index.search(query)               hybrid, with citations
    index.new_since(watermark)        exact answer to "what arrived since"
    index.context_for_update(doc_key) the call the agent makes before rewriting a document
    index.diagnose()                  end-to-end self-test

``context_for_update`` is the important one for the reported problem.  An agent
asked to "update this document with the new files" has to *decide to retrieve*,
and then has to pick a query that happens to surface files it has never seen.
Both steps fail routinely, and they fail silently: the agent answers from what it
already has and reports success.

So the agent should not be asked to guess.  Every document keeps a watermark —
the index sequence it was last written against.  Updating it is then a lookup,
not a search: everything with a higher sequence, in full, with citations.  No
embedding is involved and nothing can be missed.
"""

from __future__ import annotations

import fnmatch
import hashlib
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

from .chunk import DEFAULT_POLICY, ChunkPolicy, chunk_text
from .embed import Embedder, HashingEmbedder, text_key
from .extract import extract, supported_suffixes
from .hybrid import Channel, lexical, recency, rrf, semantic
from .model import (
    Chunk,
    Diagnosis,
    Drift,
    Hit,
    IngestResult,
    ReconcileReport,
    SourceDoc,
)
from .store import Store

DEFAULT_PATTERNS = ("*",)
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "build", ".dart_tool", ".idea"}


def doc_id_for(path: str | Path) -> str:
    """Identity is the path, so editing a file updates it instead of duplicating."""
    return hashlib.sha1(str(Path(path).resolve()).encode("utf-8")).hexdigest()[:16]


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


class Index:
    def __init__(
        self,
        path: str | Path = ":memory:",
        embedder: Embedder | None = None,
        policy: ChunkPolicy = DEFAULT_POLICY,
        clock=time.time,
    ) -> None:
        self.store = Store(path, clock=clock)
        self.embedder = embedder or HashingEmbedder()
        self.policy = policy
        self._clock = clock
        stored = self.store.get_meta("embedder")
        if stored is None:
            self.store.set_meta("embedder", self.embedder.id)
        self.embedder_changed = stored is not None and stored != self.embedder.id

    # ------------------------------------------------------------------
    # ingest
    # ------------------------------------------------------------------
    def ingest_file(self, path: str | Path, *, force: bool = False) -> IngestResult:
        p = Path(path)
        did = doc_id_for(p)
        existing = self.store.document(did)

        if not p.exists():
            if existing:
                self.store.delete_document(did)
                return IngestResult(existing, "deleted", detail="the file is gone")
            return IngestResult(
                SourceDoc(doc_id=did, path=str(p), status="failed", error="no such file"),
                "failed",
                detail="no such file",
            )

        raw = p.read_bytes()
        chash = content_hash(raw)
        stat = p.stat()

        if existing and existing.content_hash == chash and not force:
            if existing.status == "indexed" and existing.chunk_count > 0:
                return IngestResult(existing, "unchanged", chunks=existing.chunk_count)
            # previously failed or empty: retry, the extractor may have been fixed

        result = extract(p)
        version = (existing.version + 1) if existing else 1
        seq = self.store.next_seq()

        if not result.ok:
            doc = SourceDoc(
                doc_id=did, path=str(p), title=result.title or p.stem,
                content_hash=chash, bytes=stat.st_size, mtime=stat.st_mtime,
                version=version,
                status="empty" if result.status == "empty" else (
                    "unsupported" if result.status == "unsupported" else "failed"
                ),
                error=f"{result.detail} — {result.fix}" if result.fix else result.detail,
                chunk_count=0, ingested_at=self._clock(), seq=seq,
            )
            self.store.put_document(doc)
            self.store.replace_chunks(did, [], [], seq=seq)
            return IngestResult(doc, "failed", detail=doc.error)

        chunks = chunk_text(result.text, did, version, self.policy)
        vectors, embedded, cached = self._embed([c.text for c in chunks])

        doc = SourceDoc(
            doc_id=did, path=str(p), title=result.title or p.stem, content_hash=chash,
            bytes=stat.st_size, mtime=stat.st_mtime, version=version, status="indexed",
            error="", chunk_count=len(chunks), ingested_at=self._clock(), seq=seq,
            meta={"suffix": p.suffix.lower()},
        )
        self.store.put_document(doc)
        self.store.replace_chunks(did, chunks, vectors, seq=seq)
        return IngestResult(
            doc, "updated" if existing else "created",
            chunks=len(chunks), embedded=embedded, cached=cached,
        )

    def ingest_text(
        self,
        key: str,
        text: str,
        *,
        title: str = "",
        meta: dict[str, Any] | None = None,
    ) -> IngestResult:
        did = doc_id_for(key)
        existing = self.store.document(did)
        version = (existing.version + 1) if existing else 1
        seq = self.store.next_seq()
        chunks = chunk_text(text, did, version, self.policy)
        vectors, embedded, cached = self._embed([c.text for c in chunks])
        doc = SourceDoc(
            doc_id=did, path=str(key), title=title or str(key),
            content_hash=content_hash(text.encode("utf-8")), bytes=len(text),
            mtime=self._clock(), version=version,
            status="indexed" if chunks else "empty",
            error="" if chunks else "no text",
            chunk_count=len(chunks), ingested_at=self._clock(), seq=seq,
            meta=meta or {},
        )
        self.store.put_document(doc)
        self.store.replace_chunks(did, chunks, vectors, seq=seq)
        return IngestResult(doc, "updated" if existing else "created",
                            chunks=len(chunks), embedded=embedded, cached=cached)

    def ingest_dir(
        self,
        root: str | Path,
        patterns: Sequence[str] = DEFAULT_PATTERNS,
        *,
        force: bool = False,
        recursive: bool = True,
    ) -> list[IngestResult]:
        root = Path(root)
        self.store.add_root(str(root.resolve()), patterns)
        out: list[IngestResult] = []
        for p in self._walk(root, patterns, recursive):
            out.append(self.ingest_file(p, force=force))
        return out

    def delete(self, path: str | Path) -> bool:
        return self.store.delete_document(doc_id_for(path))

    def _walk(self, root: Path, patterns: Sequence[str], recursive: bool) -> list[Path]:
        if not root.exists():
            return []
        it = root.rglob("*") if recursive else root.glob("*")
        found: list[Path] = []
        for p in sorted(it):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.name.startswith("."):
                continue
            if patterns and not any(fnmatch.fnmatch(p.name, pat) for pat in patterns):
                continue
            found.append(p)
        return found

    def _embed(self, texts: list[str]) -> tuple[list[list[float]], int, int]:
        vectors: list[list[float]] = []
        to_embed: list[tuple[int, str, str]] = []
        cached = 0
        for i, text in enumerate(texts):
            key = text_key(text, self.embedder.id)
            hit = self.store.cached_vector(key)
            if hit is not None:
                vectors.append(hit)
                cached += 1
            else:
                vectors.append([])
                to_embed.append((i, key, text))
        if to_embed:
            fresh = self.embedder.embed([t for _, _, t in to_embed])
            for (i, key, _), vec in zip(to_embed, fresh):
                vectors[i] = list(vec)
                self.store.cache_vector(key, self.embedder.id, vec)
        return vectors, len(to_embed), cached

    # ------------------------------------------------------------------
    # reconcile — "is the indexer actually working"
    # ------------------------------------------------------------------
    def reconcile(
        self,
        root: str | Path | None = None,
        patterns: Sequence[str] = DEFAULT_PATTERNS,
    ) -> ReconcileReport:
        roots = [str(root)] if root else list(self.store.roots())
        if not roots:
            return ReconcileReport(root="(no root registered)", scanned=0, in_index=0)

        report = ReconcileReport(root=", ".join(roots))
        on_disk: dict[str, Path] = {}
        for r in roots:
            for p in self._walk(Path(r), patterns, recursive=True):
                on_disk[str(p.resolve())] = p

        indexed = {
            str(Path(d.path).resolve()): d
            for d in self.store.documents()
            if d.status != "tombstoned"
        }
        report.scanned = len(on_disk)
        report.in_index = len(indexed)

        for resolved, p in sorted(on_disk.items()):
            doc = indexed.get(resolved)
            if doc is None:
                report.drift.append(
                    Drift(
                        "not_indexed", str(p),
                        "on disk, absent from the index",
                        "run ingest_file on it and read the result — it will say why",
                    )
                )
                continue
            if doc.content_hash != content_hash(p.read_bytes()):
                report.drift.append(
                    Drift(
                        "stale", str(p),
                        f"the file changed since it was indexed (v{doc.version})",
                        "re-ingest; the old chunks are replaced, not added to",
                    )
                )
            if doc.status == "failed":
                report.drift.append(Drift("failed", str(p), doc.error, "fix the extractor or the file"))
            elif doc.status == "empty":
                report.drift.append(
                    Drift(
                        "empty", str(p), doc.error,
                        "no text came out; OCR it or convert it before indexing",
                    )
                )
            elif doc.status == "unsupported":
                report.drift.append(
                    Drift("unsupported", str(p), doc.error, f"supported: {supported_suffixes()}")
                )
            elif doc.chunk_count == 0:
                report.drift.append(
                    Drift(
                        "empty", str(p), "indexed with zero chunks",
                        "this is the failure that looks like success — re-ingest and check",
                    )
                )

        for resolved, doc in sorted(indexed.items()):
            if resolved not in on_disk:
                report.drift.append(
                    Drift(
                        "orphaned", doc.path,
                        "in the index, not on disk",
                        "delete it from the index, or the assistant will keep citing a file "
                        "nobody can open",
                    )
                )
        return report

    # ------------------------------------------------------------------
    # retrieval
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        k: int = 8,
        *,
        mode: str = "hybrid",
        since_seq: int | None = None,
        pool: int = 60,
        weights: dict[str, float] | None = None,
        min_similarity: float = 0.15,
    ) -> list[Hit]:
        weights = weights or {"lexical": 1.0, "semantic": 1.0, "recency": 0.6}
        channels: list[Channel] = []

        if mode in ("hybrid", "lexical"):
            channels.append(Channel("lexical", lexical(self.store, query, pool), weights.get("lexical", 1.0)))
        if mode in ("hybrid", "semantic"):
            qvec = self.embedder.embed([query])[0]
            channels.append(
                Channel(
                    "semantic",
                    semantic(self.store, qvec, pool, min_similarity),
                    weights.get("semantic", 1.0),
                )
            )
        if since_seq is not None:
            channels.append(Channel("recency", recency(self.store, since_seq, pool), weights.get("recency", 0.6)))

        fused = rrf(channels, limit=k)
        return self._hits(fused, mode)

    def _hits(self, fused: list[tuple[str, float, dict[str, int]]], channel: str) -> list[Hit]:
        out: list[Hit] = []
        for chunk_id, score, ranks in fused:
            ch = self.store.chunk(chunk_id)
            if ch is None:
                continue
            doc = self.store.document(ch.doc_id)
            if doc is None or doc.status == "tombstoned":
                continue
            out.append(Hit(chunk=ch, doc=doc, score=score, channel=channel, ranks=ranks))
        return out

    # ------------------------------------------------------------------
    # recency — the part that fixes "it didn't see the new files"
    # ------------------------------------------------------------------
    def head(self) -> int:
        return self.store.current_seq()

    def new_since(self, since: int | str, *, include_failed: bool = True) -> list[SourceDoc]:
        seq = self.store.watermark(since) if isinstance(since, str) else int(since)
        if seq is None:
            seq = 0
        docs = self.store.documents(since_seq=seq)
        if include_failed:
            return docs
        return [d for d in docs if d.usable]

    def set_watermark(self, key: str, seq: int | None = None, note: str = "") -> int:
        seq = self.head() if seq is None else seq
        self.store.set_watermark(key, seq, note)
        return seq

    def context_for_update(
        self,
        watermark_key: str,
        *,
        query: str | None = None,
        max_chunks: int = 60,
        k: int = 8,
    ) -> dict[str, Any]:
        """Everything an agent needs before rewriting a document.

        Deliberately not a search.  It returns, in full, every document that
        arrived after the watermark, plus the problems that would otherwise be
        invisible (files that failed to extract), plus an optional topical
        search as a *second* channel.  If the answer is "nothing new", that is
        a fact from the manifest rather than a search that found nothing.
        """
        since = self.store.watermark(watermark_key)
        first_time = since is None
        since = 0 if since is None else since
        docs = self.store.documents(since_seq=since)
        usable = [d for d in docs if d.usable]
        problems = [d for d in docs if d.status in ("failed", "empty", "unsupported")]

        passages: list[dict[str, Any]] = []
        for doc in usable:
            for ch in self.store.chunks_of(doc.doc_id):
                if len(passages) >= max_chunks:
                    break
                passages.append(
                    {
                        "citation": ch.citation(doc),
                        "path": doc.path,
                        "title": doc.title,
                        "heading": ch.heading,
                        "text": ch.text,
                        "seq": doc.seq,
                    }
                )

        related = [h.to_dict() for h in self.search(query, k=k)] if query else []
        return {
            "watermark": watermark_key,
            "since_seq": since,
            "head_seq": self.head(),
            "first_time": first_time,
            "new_documents": [d.to_dict() for d in usable],
            "new_document_count": len(usable),
            "passages": passages,
            "truncated": len(passages) >= max_chunks,
            "problems": [
                {"path": d.path, "status": d.status, "error": d.error} for d in problems
            ],
            "related": related,
            "note": (
                "Nothing has been indexed since this document was last written."
                if not usable and not problems
                else (
                    f"{len(usable)} document(s) arrived since the last update"
                    + (f"; {len(problems)} could not be read" if problems else "")
                )
            ),
        }

    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        return self.store.stats()

    def diagnose(self, root: str | Path | None = None) -> Diagnosis:
        from .diagnose import diagnose

        return diagnose(self, root)

    def close(self) -> None:
        self.store.close()
