"""Foldok reflow — PDF line-wrapping into sentences.

    raw = foldok_index.extract(path).text
    text = reflow(raw).text          # sentences, not visual rows

A PDF has no sentences. pypdf emits one line per visual row, so a sentence
spanning four rows arrives as four lines and any newline-based splitter produces
fragments. Every downstream engine then starves on unusable claims.
"""

from .assets import (
    AssetHarvest,
    Figure,
    Table,
    find_tables,
    harvest,
)
from .reflow import (
    SCHEMA_VERSION,
    Reflowed,
    ReflowStats,
    quality,
    reflow,
    split_sentences,
)

__all__ = [
    "AssetHarvest", "Figure", "Reflowed", "ReflowStats", "SCHEMA_VERSION", "Table",
    "find_tables", "harvest", "quality", "reflow", "split_sentences",
]

__version__ = "0.112.0"
