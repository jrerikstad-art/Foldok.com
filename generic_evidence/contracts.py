from __future__ import annotations

from typing import Protocol, Sequence

from .model import CandidateFact, DocumentRef, Observation, ValidationResult


class Extractor(Protocol):
    """Project-agnostic source extractor.

    Implementations may use native text, layout parsing, vision, OCR, or another
    strategy. They return source-faithful Observations and do not assign domain
    meaning.
    """

    name: str

    def supports(self, document: DocumentRef, payload: bytes) -> bool: ...

    def extract(self, document: DocumentRef, payload: bytes) -> Sequence[Observation]: ...


class DomainPack(Protocol):
    """Maps generic observations into domain candidate facts."""

    name: str
    version: str

    def map_observations(self, observations: Sequence[Observation]) -> Sequence[CandidateFact]: ...


class Validator(Protocol):
    """Deterministically evaluates candidate facts.

    Core validators may enforce generic invariants. Domain packs can supply
    additional validators for domain-specific arithmetic, relationships, units,
    ranges, or legal/technical constraints.
    """

    name: str

    def validate(
        self,
        candidates: Sequence[CandidateFact],
        observations: Sequence[Observation],
    ) -> ValidationResult: ...
