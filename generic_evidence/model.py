from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any
from uuid import uuid4


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class EvidenceState(str, Enum):
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    REVIEW = "review"
    REJECTED = "rejected"
    CONFLICTED = "conflicted"
    STALE = "stale"


@dataclass(frozen=True)
class DocumentRef:
    document_id: str
    version: int = 1
    content_hash: str | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class SourceLocation:
    document: DocumentRef
    page: int | None = None
    section: str | None = None
    start: int | None = None
    end: int | None = None
    quote: str | None = None
    coordinates: tuple[float, float, float, float] | None = None


@dataclass
class Observation:
    """A source-faithful statement before domain interpretation.

    `label`, `value`, and `dimensions` describe what the source appears to say.
    The core does not decide what the observation *means* in a domain.
    """

    label: str
    value: Any
    source: SourceLocation
    unit: str | None = None
    dimensions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    extractor: str = "unknown"
    observation_id: str = field(default_factory=lambda: _id("OBS"))

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("Observation.label must be non-empty")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("Observation.confidence must be between 0 and 1")
        if isinstance(self.value, float) and not isfinite(self.value):
            raise ValueError("Observation.value must be finite")


@dataclass
class CandidateFact:
    """A domain pack's proposed interpretation of one or more observations."""

    kind: str
    value: Any
    source_observation_ids: list[str]
    unit: str | None = None
    dimensions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    mapper: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)
    candidate_id: str = field(default_factory=lambda: _id("CAND"))

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("CandidateFact.kind must be non-empty")
        if not self.source_observation_ids:
            raise ValueError("CandidateFact must reference at least one observation")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("CandidateFact.confidence must be between 0 and 1")


@dataclass
class CanonicalFact:
    """Validated domain fact produced by the engine, never by free-form prose."""

    kind: str
    value: Any
    source_observation_ids: list[str]
    source_candidate_ids: list[str]
    state: EvidenceState
    unit: str | None = None
    dimensions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    domain_pack: str = "unknown"
    validation_codes: list[str] = field(default_factory=list)
    fact_id: str = field(default_factory=lambda: _id("FACT"))


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "review"  # review | reject | conflict
    candidate_id: str | None = None


@dataclass
class ValidationResult:
    accepted: list[CandidateFact] = field(default_factory=list)
    review: list[CandidateFact] = field(default_factory=list)
    rejected: list[CandidateFact] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.review and not self.rejected and not any(
            i.severity in {"reject", "conflict"} for i in self.issues
        )
