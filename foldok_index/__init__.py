"""Foldok index — local-first hybrid retrieval that can prove what it contains.

    index.ingest_dir(folder)            idempotent; unchanged files are not re-embedded
    index.reconcile(folder)             what is on disk but not in the index, and why
    index.search(query)                 lexical + semantic, fused by rank, with citations
    index.new_since(watermark)          exact answer to "what arrived since"
    index.context_for_update(key)       what the agent needs before rewriting a document
    index.diagnose()                    nine checks, including a live end-to-end canary

The design assumption worth knowing: the bug in a system like this is almost
always bookkeeping, not nearest-neighbour search. So the manifest is the primary
artifact and the vectors are secondary.
"""

from .chunk import ChunkPolicy, chunk_text
from .diagnose import diagnose
from .embed import CallableEmbedder, Embedder, HashingEmbedder
from .extract import Extraction, extract, supported_suffixes
from .hybrid import Channel, lexical, recency, rrf, semantic
from .index import Index, content_hash, doc_id_for
from .model import (
    Check,
    Chunk,
    Diagnosis,
    Drift,
    Hit,
    IngestResult,
    ReconcileReport,
    SourceDoc,
)
from .store import Store

__all__ = [
    "CallableEmbedder", "Channel", "Check", "Chunk", "ChunkPolicy", "Diagnosis",
    "Drift", "Embedder", "Extraction", "HashingEmbedder", "Hit", "Index",
    "IngestResult", "ReconcileReport", "SourceDoc", "Store", "chunk_text",
    "content_hash", "diagnose", "doc_id_for", "extract", "lexical", "recency",
    "rrf", "semantic", "supported_suffixes",
]

__version__ = "0.65.0"
