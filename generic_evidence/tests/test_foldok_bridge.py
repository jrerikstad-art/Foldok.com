from foldok_index.model import Chunk, SourceDoc
from generic_evidence.integrations.foldok_index import observations_from_chunks


def test_foldok_chunk_bridge_preserves_source_traceability():
    doc = SourceDoc(
        doc_id="doc-1",
        path="example.md",
        title="Example",
        content_hash="abc",
        version=3,
        meta={"media_type": "text/markdown"},
    )
    chunks = [
        Chunk(
            chunk_id="doc-1@v3#0",
            doc_id="doc-1",
            ordinal=0,
            text="Design pressure is 16 bar.",
            heading="Design basis",
            start=10,
            end=36,
            seq=12,
        )
    ]

    observations = observations_from_chunks(doc, chunks)

    assert len(observations) == 1
    obs = observations[0]
    assert obs.value == "Design pressure is 16 bar."
    assert obs.source.document.document_id == "doc-1"
    assert obs.source.document.version == 3
    assert obs.source.document.content_hash == "abc"
    assert obs.source.section == "Design basis"
    assert obs.dimensions["chunk_ordinal"] == 0
    assert obs.extractor == "foldok_index_chunk_bridge"
