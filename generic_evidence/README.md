# Generic Evidence Engine — Alpha 10 foundation

This package is deliberately **product- and domain-neutral**.

It provides the shared machinery for turning source material into traceable evidence:

`Document -> Observation -> CandidateFact -> Validation -> CanonicalFact`

## Hard boundary

Core MUST NOT contain:

- Foldok concepts
- tax/payroll concepts
- engineering concepts
- project-specific labels, thresholds or rules
- product database/auth/runtime state

Products integrate through `DomainPack`, extractor, validator, persistence and runtime adapters.

**Products may share engine technology. Products never share case state.**

## Why Observation comes first

Unknown information must survive extraction. A row or field that no installed domain pack understands remains an `Observation`; it is not discarded merely because an allow-list has no canonical fact type for it.

This lets a payroll document, an engineering datasheet and another structured document use the same extraction/evidence layer while interpreting the observations differently.

## Provenance

Every accepted fact can carry one or more `SourceLocation` objects. Downstream agents should be able to distinguish:

1. source observation,
2. domain interpretation,
3. deterministic derivation,
4. client-reported context,
5. agent inference.

The core does not collapse those categories.

## Validation principle

Validators may reject, conflict or defer evidence. They must not manufacture missing evidence to make a calculation pass.

## Next integration steps

1. Adapt Foldok's existing extraction/index primitives behind these contracts rather than moving Foldok semantics into core.
2. Add structure-preserving extractors for tables/sections/rows/cells.
3. Add generic arithmetic and relationship validators.
4. Build product-specific domain packs outside this package.
5. Add an evidence graph/invalidation layer so corrected observations invalidate dependent facts and derivations.
6. Add regression tests proving that two unrelated domain packs can consume the same core without importing each other.
