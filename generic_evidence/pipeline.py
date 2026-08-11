from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .contracts import DomainPack, Extractor, Validator
from .model import (
    CandidateFact,
    CanonicalFact,
    DocumentRef,
    EvidenceState,
    Observation,
    ValidationIssue,
)
from .validation import ConflictValidator, GenericInvariantValidator, ValidationChain


@dataclass
class EngineResult:
    document: DocumentRef
    observations: list[Observation] = field(default_factory=list)
    candidates: list[CandidateFact] = field(default_factory=list)
    facts: list[CanonicalFact] = field(default_factory=list)
    review: list[CandidateFact] = field(default_factory=list)
    rejected: list[CandidateFact] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    extractor: str | None = None
    domain_pack: str | None = None


class EvidenceEngine:
    """Project-agnostic orchestration layer.

    Core responsibility:
        source -> observations -> domain candidates -> deterministic validation
        -> canonical facts

    It deliberately has no knowledge of any concrete product or domain.
    """

    def __init__(
        self,
        *,
        extractors: Sequence[Extractor],
        domain_pack: DomainPack,
        validators: Sequence[Validator] = (),
    ):
        self.extractors = list(extractors)
        self.domain_pack = domain_pack
        self.validation = ValidationChain(
            [GenericInvariantValidator(), ConflictValidator(), *validators]
        )

    def run(self, document: DocumentRef, payload: bytes) -> EngineResult:
        extractor = self._select_extractor(document, payload)
        observations = list(extractor.extract(document, payload))
        candidates = list(self.domain_pack.map_observations(observations))
        validated = self.validation.validate(candidates, observations)

        issue_codes: dict[str, list[str]] = {}
        for issue in validated.issues:
            if issue.candidate_id:
                issue_codes.setdefault(issue.candidate_id, []).append(issue.code)

        facts = [
            CanonicalFact(
                kind=c.kind,
                value=c.value,
                unit=c.unit,
                dimensions=dict(c.dimensions),
                source_observation_ids=list(c.source_observation_ids),
                source_candidate_ids=[c.candidate_id],
                state=EvidenceState.CONFIRMED,
                confidence=c.confidence,
                domain_pack=f"{self.domain_pack.name}@{self.domain_pack.version}",
                validation_codes=issue_codes.get(c.candidate_id, []),
            )
            for c in validated.accepted
        ]

        return EngineResult(
            document=document,
            observations=observations,
            candidates=candidates,
            facts=facts,
            review=list(validated.review),
            rejected=list(validated.rejected),
            issues=list(validated.issues),
            extractor=getattr(extractor, "name", extractor.__class__.__name__),
            domain_pack=f"{self.domain_pack.name}@{self.domain_pack.version}",
        )

    def _select_extractor(self, document: DocumentRef, payload: bytes) -> Extractor:
        for extractor in self.extractors:
            if extractor.supports(document, payload):
                return extractor
        raise ValueError(
            f"No extractor supports document {document.document_id}"
            + (f" ({document.media_type})" if document.media_type else "")
        )
