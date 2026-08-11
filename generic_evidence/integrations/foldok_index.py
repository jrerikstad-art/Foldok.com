from __future__ import annotations

from typing import Iterable

from generic_evidence.model import DocumentRef, Observation, SourceLocation


def observations_from_chunks(doc, chunks: Iterable) -> list[Observation]:
    """Bridge existing Foldok index chunks into generic observations.

    This module may know Foldok's runtime shape; the core package does not.
    It intentionally treats chunk text as source observations, not as domain facts.
    """

    document = DocumentRef(
        document_id=str(doc.doc_id),
        version=int(getattr(doc, "version", 1)),
        content_hash=getattr(doc, "content_hash", None) or None,
        media_type=(getattr(doc, "meta", {}) or {}).get("media_type"),
    )
    out: list[Observation] = []
    for chunk in chunks:
        text = str(getattr(chunk, "text", "") or "").strip()
        if not text:
            continue
        out.append(
            Observation(
                label=str(getattr(chunk, "heading", "") or f"chunk {getattr(chunk, 'ordinal', 0)}"),
                value=text,
                source=SourceLocation(
                    document=document,
                    section=getattr(chunk, "heading", "") or None,
                    start=getattr(chunk, "start", None),
                    end=getattr(chunk, "end", None),
                    quote=text[:500],
                ),
                dimensions={
                    "chunk_ordinal": int(getattr(chunk, "ordinal", 0)),
                    "source_seq": int(getattr(chunk, "seq", 0)),
                },
                confidence=1.0,
                extractor="foldok_index_chunk_bridge",
            )
        )
    return out
