"""Chunking.

Deterministic and structure-aware: split on headings and blank lines, pack up to
a character budget, overlap a little so a fact that straddles a boundary is still
findable, and carry the nearest heading into the chunk text so a retrieved
fragment says what it is about.

Chunk ids embed the document version, so a re-ingest produces new ids and the old
ones are deleted rather than shadowed.  Stale chunks surviving an edit is the
second most common cause of "the assistant is answering from the old file".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Chunk

HEADING = re.compile(r"^(#{1,6}\s+.+|[A-ZÆØÅ][^\n]{0,80}\n[=-]{3,})$", re.MULTILINE)


@dataclass(frozen=True)
class ChunkPolicy:
    target_chars: int = 1200
    overlap_chars: int = 160
    min_chars: int = 120
    keep_heading: bool = True

    def validate(self) -> None:
        if self.overlap_chars >= self.target_chars:
            raise ValueError("overlap must be smaller than the target size")


DEFAULT_POLICY = ChunkPolicy()


def chunk_text(
    text: str,
    doc_id: str,
    version: int = 1,
    policy: ChunkPolicy = DEFAULT_POLICY,
) -> list[Chunk]:
    policy.validate()
    blocks = _blocks(text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    heading = ""
    start = 0

    def flush(end: int) -> None:
        nonlocal buf, buf_len, start
        if not buf:
            return
        body = "\n\n".join(buf).strip()
        if not body:
            buf, buf_len = [], 0
            return
        prefix = f"{heading}\n\n" if (policy.keep_heading and heading and not body.startswith(heading)) else ""
        ordinal = len(chunks)
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}@v{version}#{ordinal}",
                doc_id=doc_id,
                ordinal=ordinal,
                text=prefix + body,
                heading=heading,
                start=start,
                end=end,
            )
        )
        tail = body[-policy.overlap_chars :] if policy.overlap_chars else ""
        buf = [tail] if tail else []
        buf_len = len(tail)
        start = max(0, end - len(tail))

    for block, offset, is_heading in blocks:
        if is_heading:
            if buf_len >= policy.min_chars:
                flush(offset)
            heading = block.lstrip("# ").strip()
        if buf_len + len(block) > policy.target_chars and buf_len >= policy.min_chars:
            flush(offset)
        buf.append(block)
        buf_len += len(block) + 2

    flush(len(text))

    # a document shorter than min_chars still deserves exactly one chunk
    if not chunks and text.strip():
        chunks.append(
            Chunk(
                chunk_id=f"{doc_id}@v{version}#0",
                doc_id=doc_id,
                ordinal=0,
                text=text.strip(),
                heading="",
                start=0,
                end=len(text),
            )
        )
    return chunks


def _blocks(text: str) -> list[tuple[str, int, bool]]:
    out: list[tuple[str, int, bool]] = []
    pos = 0
    for raw in re.split(r"\n{2,}", text):
        block = raw.strip()
        offset = text.find(raw, pos)
        pos = offset + len(raw) if offset >= 0 else pos
        if not block:
            continue
        is_heading = bool(re.match(r"^#{1,6}\s+\S", block)) and len(block) < 200
        out.append((block, max(offset, 0), is_heading))
    return out
