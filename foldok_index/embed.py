"""Embedding.

The embedder carries an ``id``, and that id is stored in the index.  If it ever
changes without a reindex, every stored vector is measuring a different space
from every query vector, similarity scores stay plausible-looking, and retrieval
quietly returns nonsense.  ``diagnose()`` checks for exactly this, because it is
invisible from the outside: nothing errors, results are simply wrong.

``HashingEmbedder`` is a real, deterministic, dependency-free embedder — it is
lexical rather than semantic, so it will not match "cutting fluid" to "coolant".
It exists so the pipeline is testable offline and so the index degrades to
something usable rather than to nothing when the embedding API is unreachable.
Wire a proper model in production and let the id change trigger the reindex.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

TOKEN = re.compile(r"[0-9a-zA-ZÀ-ÿæøåÆØÅ_]+")


@runtime_checkable
class Embedder(Protocol):
    id: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(text)]


@dataclass
class HashingEmbedder:
    """Hashed bag of words with sublinear term frequency and L2 normalisation."""

    dim: int = 384
    ngrams: tuple[int, ...] = (1, 2)

    def __post_init__(self) -> None:
        self.id = f"hashing-{self.dim}-ng{'_'.join(str(n) for n in self.ngrams)}-v1"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = tokenize(text)
        counts: dict[str, int] = {}
        for n in self.ngrams:
            for i in range(len(tokens) - n + 1):
                gram = " ".join(tokens[i : i + n])
                counts[gram] = counts.get(gram, 0) + 1
        for gram, count in counts.items():
            h = int.from_bytes(hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest(), "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 63) & 1 else -1.0
            vec[idx] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


@dataclass
class CallableEmbedder:
    """Wrap a real model.  ``fn`` takes a list of strings and returns vectors."""

    fn: Callable[[list[str]], list[list[float]]]
    id: str
    dim: int
    batch: int = 64

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            batch = texts[i : i + self.batch]
            vectors = self.fn(batch)
            if len(vectors) != len(batch):
                raise RuntimeError(
                    f"embedder '{self.id}' returned {len(vectors)} vectors for {len(batch)} texts; "
                    "a silent length mismatch would misalign every vector after it"
                )
            for v in vectors:
                if len(v) != self.dim:
                    raise RuntimeError(
                        f"embedder '{self.id}' returned dim {len(v)}, expected {self.dim}"
                    )
            out.extend(vectors)
        return out


def normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    return vec if norm == 0.0 else [v / norm for v in vec]


def text_key(text: str, embedder_id: str) -> str:
    return hashlib.sha1(f"{embedder_id}|{text}".encode("utf-8")).hexdigest()
