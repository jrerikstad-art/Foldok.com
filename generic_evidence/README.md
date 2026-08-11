# Generic Evidence Engine — Alpha 10 foundation

This package is the project-agnostic evidence core shared by products that need to turn source material into traceable, validated facts.

## Hard boundary

The core must not know about Foldok, tax, payroll, engineering, or any other product/domain vocabulary.

Products integrate through:

- `Extractor` — source bytes to source-faithful `Observation` objects;
- `DomainPack` — observations to domain `CandidateFact` objects;
- `Validator` — deterministic domain checks;
- `EvidenceEngine` — orchestration into `CanonicalFact` objects.

Product/runtime bridges live under `generic_evidence.integrations`, outside the core model and contracts.

## Data flow

```text
source bytes
   ↓
Extractor
   ↓
Observation[]
   ↓
DomainPack
   ↓
CandidateFact[]
   ↓
Generic validators + domain validators
   ↓
CanonicalFact[] / REVIEW / REJECTED
```

## Why Observation comes first

An observation records what the source appears to contain without assigning domain meaning. This prevents a parser from discarding an unfamiliar field simply because a domain pack does not recognize it yet.

Example source observations can be a text row, a table cell, a diagram label, a measured value, or a paragraph. The same core object can later be mapped differently by different domain packs.

## Provenance

Every candidate must reference one or more observation IDs. Every canonical fact retains both observation IDs and candidate IDs. Source locations retain document identity/version and may include page, section, character span, quote, or coordinates.

## First integration

`generic_evidence.integrations.foldok_index.observations_from_chunks()` bridges current `foldok_index` chunks into observations without making the generic core depend on Foldok.

This is intentionally only the first extraction slice. Existing Foldok indexing/retrieval remains untouched while the shared evidence model is introduced alongside it.

## Next slices

1. Add native-text/layout extractors that implement `Extractor` directly.
2. Add an extraction status/fallback contract (`native → layout → vision → OCR`) without product semantics.
3. Add a domain-pack registry and version/invalidation metadata.
4. Adapt Foldok claim/verification paths to consume canonical facts where useful.
5. Build Skatteassistent payroll/tax mapping as a separate domain pack, not inside this package.
