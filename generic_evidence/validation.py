from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from .model import CandidateFact, Observation, ValidationIssue, ValidationResult


class GenericInvariantValidator:
    """Domain-neutral invariants only.

    This validator intentionally knows nothing about tax, payroll, engineering,
    Foldok, or any product. Domain-specific checks belong in separate validators.
    """

    name = "generic_invariants"

    def validate(
        self,
        candidates: Sequence[CandidateFact],
        observations: Sequence[Observation],
    ) -> ValidationResult:
        observation_ids = {o.observation_id for o in observations}
        accepted: list[CandidateFact] = []
        review: list[CandidateFact] = []
        rejected: list[CandidateFact] = []
        issues: list[ValidationIssue] = []

        for candidate in candidates:
            missing = [x for x in candidate.source_observation_ids if x not in observation_ids]
            if missing:
                rejected.append(candidate)
                issues.append(
                    ValidationIssue(
                        code="missing_source_observation",
                        message=f"Candidate references unknown observation(s): {missing}",
                        severity="reject",
                        candidate_id=candidate.candidate_id,
                    )
                )
                continue

            if candidate.confidence < 0.5:
                review.append(candidate)
                issues.append(
                    ValidationIssue(
                        code="low_mapping_confidence",
                        message="Candidate mapping confidence is below 0.5",
                        severity="review",
                        candidate_id=candidate.candidate_id,
                    )
                )
                continue

            accepted.append(candidate)

        return ValidationResult(accepted, review, rejected, issues)


class ConflictValidator:
    """Find conflicting values for the same domain key and dimensions."""

    name = "generic_conflicts"

    def validate(
        self,
        candidates: Sequence[CandidateFact],
        observations: Sequence[Observation],
    ) -> ValidationResult:
        groups: dict[tuple, list[CandidateFact]] = defaultdict(list)
        for candidate in candidates:
            dims = tuple(sorted((str(k), repr(v)) for k, v in candidate.dimensions.items()))
            groups[(candidate.kind, candidate.unit, dims)].append(candidate)

        conflict_ids: set[str] = set()
        issues: list[ValidationIssue] = []
        for key, group in groups.items():
            values = {repr(c.value) for c in group}
            if len(values) <= 1:
                continue
            for candidate in group:
                conflict_ids.add(candidate.candidate_id)
                issues.append(
                    ValidationIssue(
                        code="conflicting_candidates",
                        message=f"Multiple values exist for canonical key {key[0]}",
                        severity="conflict",
                        candidate_id=candidate.candidate_id,
                    )
                )

        accepted = [c for c in candidates if c.candidate_id not in conflict_ids]
        review = [c for c in candidates if c.candidate_id in conflict_ids]
        return ValidationResult(accepted=accepted, review=review, issues=issues)


class ValidationChain:
    """Compose validators without coupling the core to any domain."""

    def __init__(self, validators):
        self.validators = list(validators)

    def validate(self, candidates, observations) -> ValidationResult:
        active = list(candidates)
        all_review: list[CandidateFact] = []
        all_rejected: list[CandidateFact] = []
        all_issues: list[ValidationIssue] = []

        for validator in self.validators:
            result = validator.validate(active, observations)
            active = list(result.accepted)
            all_review.extend(result.review)
            all_rejected.extend(result.rejected)
            all_issues.extend(result.issues)

        return ValidationResult(
            accepted=active,
            review=all_review,
            rejected=all_rejected,
            issues=all_issues,
        )
