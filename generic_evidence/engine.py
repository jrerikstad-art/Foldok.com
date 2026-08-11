from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .contracts import DomainPack, EvidenceExtractor, EvidenceValidator
from .model import CanonicalFact, EvidenceDocument, Observation, ValidationIssue


@dataclass(frozen=True)
class EngineResult:
    document: EvidenceDocument
    observations: tuple[Observation, ...]
    facts: tuple[CanonicalFact, ...]
    issues: tuple[ValidationIssue, ...]
    extractor: str
    domain_pack: str


class EvidenceEngine:
    """Domain-neutral orchestration: extract -> map -> validate -> canonicalize.

    The engine never silently repairs evidence or guesses domain meaning.
    Extraction and domain interpretation are separate extension points.
    """

    def __init__(
        self,
        extractors: Sequence[EvidenceExtractor],
        validators: Sequence[EvidenceValidator],
    ) -> None:
        self._extractors = tuple(extractors)
        self._validators = tuple(validators)

    def run(
        self,
        document: EvidenceDocument,
        payload: bytes,
        domain_pack: DomainPack,
    ) -> EngineResult:
        extractor = next((x for x in self._extractors if x.supports(document)), None)
        if extractor is None:
            raise ValueError(f"No extractor supports media type {document.media_type!r}")

        observations = tuple(extractor.extract(document, payload))
        candidates = tuple(domain_pack.map_observations(document, observations))

        issues: list[ValidationIssue] = []
        for validator in self._validators:
            issues.extend(validator.validate(document, observations, candidates))

        facts: list[CanonicalFact] = []
        if not any(issue.severity == "error" for issue in issues):
            # Canonicalization is explicit. Validators may refuse facts instead of guessing.
            for validator in self._validators:
                produced = validator.canonicalize(document, observations, candidates, issues)
                if produced:
                    facts.extend(produced)
                    break

        return EngineResult(
            document=document,
            observations=observations,
            facts=tuple(facts),
            issues=tuple(issues),
            extractor=extractor.name,
            domain_pack=f"{domain_pack.name}@{domain_pack.version}",
        )
