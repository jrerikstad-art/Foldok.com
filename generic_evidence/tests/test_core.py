from generic_evidence import (
    CandidateFact,
    DocumentRef,
    EvidenceEngine,
    EvidenceState,
    Observation,
    SourceLocation,
)


class TextExtractor:
    name = "text"

    def supports(self, document, payload):
        return document.media_type == "text/plain"

    def extract(self, document, payload):
        text = payload.decode("utf-8")
        return [
            Observation(
                label="Field A",
                value=text,
                source=SourceLocation(document=document, quote=text),
                extractor=self.name,
            )
        ]


class DemoDomainPack:
    name = "demo"
    version = "1"

    def map_observations(self, observations):
        o = observations[0]
        return [
            CandidateFact(
                kind="DEMO.VALUE",
                value=o.value,
                source_observation_ids=[o.observation_id],
                confidence=0.99,
                mapper="demo",
            )
        ]


def test_generic_pipeline_produces_traceable_canonical_fact():
    doc = DocumentRef("doc-1", media_type="text/plain")
    result = EvidenceEngine(
        extractors=[TextExtractor()],
        domain_pack=DemoDomainPack(),
    ).run(doc, b"hello")

    assert len(result.observations) == 1
    assert len(result.candidates) == 1
    assert len(result.facts) == 1
    fact = result.facts[0]
    assert fact.kind == "DEMO.VALUE"
    assert fact.value == "hello"
    assert fact.state == EvidenceState.CONFIRMED
    assert fact.source_observation_ids == [result.observations[0].observation_id]
    assert fact.source_candidate_ids == [result.candidates[0].candidate_id]
    assert fact.domain_pack == "demo@1"


def test_core_contains_no_product_domain_assumption():
    doc = DocumentRef("doc-x", media_type="text/plain")
    obs = Observation(
        label="Completely Unknown Label",
        value=17,
        unit="widgets",
        dimensions={"axis": "z"},
        source=SourceLocation(document=doc, page=9),
    )
    assert obs.label == "Completely Unknown Label"
    assert obs.unit == "widgets"
    assert obs.dimensions == {"axis": "z"}


def test_low_confidence_mapping_is_review_not_fact():
    class WeakPack:
        name = "weak"
        version = "1"
        def map_observations(self, observations):
            o = observations[0]
            return [CandidateFact("UNKNOWN", 1, [o.observation_id], confidence=0.2)]

    result = EvidenceEngine(
        extractors=[TextExtractor()],
        domain_pack=WeakPack(),
    ).run(DocumentRef("d", media_type="text/plain"), b"x")

    assert result.facts == []
    assert len(result.review) == 1
    assert any(i.code == "low_mapping_confidence" for i in result.issues)
