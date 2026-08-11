from __future__ import annotations

from typing import Protocol, Sequence

from .model import CandidateFact, CanonicalFact, EvidenceDocument, Observation, ValidationIssue


class EvidenceExtractor(Protocol):
    """Extract domain-neutral observations from a document."""

    name: str

    def supports(self, document: EvidenceDocument) -> bool: ...

    def extract(self, document: EvidenceDocument, payload: bytes) -> Sequence[Observation]: ...


class DomainPack(Protocol):
    """Maps generic observations into product/domain candidate facts."""

    name: str
    version: str

    def map_observations(
        self,
        document: EvidenceDocument,
        observations: Sequence[Observation],
    ) -> Sequence[CandidateFact]: ...


class EvidenceValidator(Protocol):
    """Validates evidence and candidates without inventing missing facts."""

    name: str

    def validate(
        self,
        document: EvidenceDocument,
        observations: Sequence[Observation],
        candidates: Sequence[CandidateFact],
    ) -> Sequence[ValidationIssue]: ...

    def canonicalize(
        self,
        document: EvidenceDocument,
        observations: Sequence[Observation],
        candidates: Sequence[CandidateFact],
        issues: Sequence[ValidationIssue],
    ) -> Sequence[CanonicalFact]: ...
