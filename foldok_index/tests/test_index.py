"""Tests for the index.  Each one pins a failure mode that produces the symptom
"I uploaded files, they were indexed, and the assistant did not see them."

Run:  python -m pytest foldok_index/tests -q
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from foldok_index import Channel, HashingEmbedder, Index, Store, doc_id_for, extract, rrf


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "pump.md").write_text(
        "# Pump commissioning\n\n"
        "The circulation pump P-101 runs at 2900 rpm. Coolant is glycol at 30 percent.\n\n"
        "## Alarms\n\nHigh temperature alarm trips at 78 degrees.",
        encoding="utf-8",
    )
    (d / "wiring.md").write_text(
        "# Wiring\n\nThe heater is fed by two line conductors L1 and L2 with no neutral, "
        "protected by a C25 breaker. Conductors are 4 mm2.",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def index(tmp_path: Path, folder: Path) -> Index:
    ix = Index(tmp_path / "index.db")
    ix.ingest_dir(folder)
    return ix


# --- the reported symptom ---------------------------------------------
def test_new_document_is_visible_in_the_same_session(index: Index, folder: Path):
    """The cache-invalidation bug: a retriever holding a matrix loaded at start
    serves searches that cannot see anything ingested since."""
    assert not index.search("torque calibration", k=5)
    (folder / "torque.md").write_text(
        "# Torque\n\nAll flange bolts are tightened to 45 Nm in a star pattern.",
        encoding="utf-8",
    )
    index.ingest_file(folder / "torque.md")
    hits = index.search("torque flange bolts", k=5)
    assert any("torque.md" in h.doc.path for h in hits)


def test_new_document_is_visible_after_reopening(tmp_path: Path, folder: Path):
    db = tmp_path / "i.db"
    a = Index(db)
    a.ingest_dir(folder)
    (folder / "extra.md").write_text("# Extra\n\nThe gearbox oil is ISO VG 220.", encoding="utf-8")
    a.ingest_file(folder / "extra.md")
    a.close()
    b = Index(db)
    assert any("extra.md" in h.doc.path for h in b.search("gearbox oil", k=5))


def test_the_index_can_say_what_it_contains(index: Index, folder: Path):
    paths = {Path(d.path).name for d in index.store.documents()}
    assert paths == {"pump.md", "wiring.md"}
    assert index.store.document_by_path(str(folder / "pump.md")) is not None


def test_asking_what_is_new_does_not_involve_similarity(index: Index, folder: Path):
    """The query 'what is new' has no useful nearest neighbour. It is answered
    from the manifest by sequence number, or it is not answered at all."""
    mark = index.set_watermark("report_v3")
    (folder / "late.md").write_text(
        "# Late delivery\n\nThe replacement impeller arrived on 24 July.", encoding="utf-8"
    )
    index.ingest_file(folder / "late.md")
    fresh = index.new_since("report_v3")
    assert [Path(d.path).name for d in fresh] == ["late.md"]
    assert mark < index.head()


def test_context_for_update_returns_everything_new_in_full(index: Index, folder: Path):
    index.set_watermark("doc:report")
    (folder / "new1.md").write_text("# New one\n\nThe seal was replaced with a Viton item.", encoding="utf-8")
    (folder / "new2.md").write_text("# New two\n\nVibration measured 2.1 mm per second.", encoding="utf-8")
    index.ingest_file(folder / "new1.md")
    index.ingest_file(folder / "new2.md")

    ctx = index.context_for_update("doc:report")
    assert ctx["new_document_count"] == 2
    assert {Path(d["path"]).name for d in ctx["new_documents"]} == {"new1.md", "new2.md"}
    assert ctx["passages"] and all(p["citation"] for p in ctx["passages"])
    assert "Viton" in " ".join(p["text"] for p in ctx["passages"])


def test_context_for_update_says_plainly_when_there_is_nothing_new(index: Index):
    index.set_watermark("doc:report")
    ctx = index.context_for_update("doc:report")
    assert ctx["new_document_count"] == 0
    assert "Nothing has been indexed" in ctx["note"]


def test_context_for_update_surfaces_files_it_could_not_read(index: Index, folder: Path):
    index.set_watermark("doc:report")
    (folder / "scan.pdf").write_bytes(b"%PDF-1.4 not really a pdf")
    index.ingest_file(folder / "scan.pdf")
    ctx = index.context_for_update("doc:report")
    assert ctx["problems"], "a file that failed to extract must not be silently absent"
    assert "scan.pdf" in ctx["problems"][0]["path"]


# --- silent failures ---------------------------------------------------
def test_an_empty_extraction_is_never_reported_as_indexed(tmp_path: Path):
    ix = Index()
    blank = tmp_path / "scanned.md"
    blank.write_text("   \n\n  ", encoding="utf-8")
    result = ix.ingest_file(blank)
    assert result.action == "failed"
    assert result.doc.status == "empty"
    assert "OCR" in result.doc.error or "characters" in result.doc.error


def test_an_unsupported_format_says_so(tmp_path: Path):
    ix = Index()
    f = tmp_path / "photo.heic"
    f.write_bytes(b"\x00\x01\x02\x03" * 40)
    result = ix.ingest_file(f)
    assert result.doc.status == "unsupported"


def test_a_corrupt_pdf_fails_loudly(tmp_path: Path):
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"not a pdf at all")
    ex = extract(f)
    assert ex.status in ("failed", "unsupported", "empty")
    assert ex.detail


# --- staleness ---------------------------------------------------------
def test_editing_a_file_replaces_its_chunks_rather_than_adding_to_them(index: Index, folder: Path):
    before = index.store.chunk_count()
    p = folder / "pump.md"
    p.write_text("# Pump commissioning\n\nThe pump P-101 now runs at 1450 rpm.", encoding="utf-8")
    index.ingest_file(p)
    assert not index.search("2900 rpm", k=5) or all(
        "2900" not in h.chunk.text for h in index.search("2900 rpm", k=5)
    )
    assert index.store.chunk_count() <= before


def test_a_deleted_file_stops_being_retrievable(index: Index, folder: Path):
    assert index.search("glycol", k=5)
    index.delete(folder / "pump.md")
    assert not [h for h in index.search("glycol", k=5) if "pump.md" in h.doc.path]


def test_reingesting_an_unchanged_file_costs_nothing(index: Index, folder: Path):
    result = index.ingest_file(folder / "pump.md")
    assert result.action == "unchanged"
    forced = index.ingest_file(folder / "pump.md", force=True)
    assert forced.embedded == 0 and forced.cached > 0     # served from the embedding cache


# --- reconcile ---------------------------------------------------------
def test_reconcile_finds_a_file_that_was_never_indexed(index: Index, folder: Path):
    (folder / "missed.md").write_text("# Missed\n\nThis one was never ingested.", encoding="utf-8")
    report = index.reconcile()
    assert [d.path for d in report.of("not_indexed")] == [str(folder / "missed.md")]


def test_reconcile_finds_a_file_that_changed_since_indexing(index: Index, folder: Path):
    (folder / "pump.md").write_text("# Pump\n\nCompletely different content now.", encoding="utf-8")
    assert index.reconcile().of("stale")


def test_reconcile_finds_index_entries_whose_file_is_gone(index: Index, folder: Path):
    (folder / "wiring.md").unlink()
    orphans = index.reconcile().of("orphaned")
    assert any("wiring.md" in d.path for d in orphans)


def test_reconcile_is_clean_on_a_healthy_folder(index: Index):
    assert index.reconcile().ok


def test_every_drift_carries_a_fix(index: Index, folder: Path):
    (folder / "missed.md").write_text("# Missed\n\nnot ingested", encoding="utf-8")
    (folder / "wiring.md").unlink()
    for drift in index.reconcile().drift:
        assert drift.fix


# --- hybrid retrieval --------------------------------------------------
def test_lexical_channel_finds_an_exact_rare_token(index: Index):
    hits = index.search("P-101", k=5, mode="lexical")
    assert any("P-101" in h.chunk.text for h in hits)


def test_semantic_channel_finds_a_paraphrase_of_stored_text(index: Index):
    hits = index.search("the heater is supplied by two line conductors", k=5, mode="semantic")
    assert any("wiring.md" in h.doc.path for h in hits)


def test_hybrid_covers_both_and_reports_which_channel_ranked_what(index: Index):
    hits = index.search("C25 breaker 4 mm2", k=5)
    assert hits
    assert any(h.ranks for h in hits)
    assert all(h.citation for h in hits)


def test_rank_fusion_rewards_agreement_between_channels():
    both = Channel("lexical", [("a", 9.0), ("b", 8.0)])
    other = Channel("semantic", [("b", 0.9), ("c", 0.8)])
    fused = rrf([both, other], limit=3)
    assert fused[0][0] == "b"          # ranked by both, top of neither


def test_fusion_is_immune_to_score_scale():
    """Score-additive fusion breaks here: BM25 is unbounded, cosine is not."""
    huge = Channel("lexical", [("x", 4000.0), ("y", 3999.0)])
    small = Channel("semantic", [("y", 0.51), ("z", 0.50)])
    assert rrf([huge, small], limit=3)[0][0] == "y"


def test_a_hostile_query_does_not_take_the_lexical_channel_down(index: Index):
    for query in ['pump "unclosed', "OR AND NOT", "*", "", "  ", "L1/L2 (230V)"]:
        index.search(query, k=3)       # must not raise


def test_tombstoned_documents_never_appear_in_results(index: Index, folder: Path):
    index.delete(folder / "pump.md")
    assert all(h.doc.status != "tombstoned" for h in index.search("pump", k=10))


# --- integrity ---------------------------------------------------------
def test_misaligned_vectors_are_refused_rather_than_written(index: Index):
    from foldok_index.model import Chunk

    chunks = [Chunk(chunk_id="x#0", doc_id="x", ordinal=0, text="a")]
    with pytest.raises(ValueError):
        index.store.replace_chunks("x", chunks, [[0.1], [0.2]])


def test_changing_the_embedder_is_detected(tmp_path: Path, folder: Path):
    db = tmp_path / "i.db"
    Index(db, HashingEmbedder(dim=64)).ingest_dir(folder)
    other = Index(db, HashingEmbedder(dim=128))
    assert other.embedder_changed
    assert not other.diagnose(folder).ok


def test_diagnose_passes_on_a_healthy_index(index: Index, folder: Path):
    d = index.diagnose(folder)
    assert d.ok, str(d)


def test_diagnose_catches_a_desynced_lexical_index(index: Index, folder: Path):
    index.store.db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('delete-all')")
    index.store.db.commit()
    d = index.diagnose(folder)
    assert not d.ok
    assert any("lexical index" in c.name for c in d.failures)
    assert index.store.rebuild_fts() == index.store.chunk_count()
    assert index.diagnose(folder).ok


def test_diagnose_catches_documents_indexed_with_zero_chunks(index: Index, folder: Path):
    index.store.db.execute(
        "UPDATE documents SET chunk_count=0 WHERE path LIKE '%pump.md'"
    )
    index.store.db.commit()
    assert any("zero chunks" in c.name for c in index.diagnose(folder).failures)


def test_diagnose_complains_when_no_folder_is_registered():
    ix = Index()
    ix.ingest_text("loose", "some text that is long enough to survive the minimum length rule")
    d = ix.diagnose()
    assert any("registered" in c.name for c in d.failures)


def test_canary_is_cleaned_up_after_diagnosis(index: Index, folder: Path):
    before = index.store.chunk_count()
    index.diagnose(folder)
    assert index.store.chunk_count() == before
    assert not index.search("zylophonebracket", k=5)


# --- chunking ----------------------------------------------------------
def test_chunking_is_deterministic_and_ids_carry_the_version(index: Index, folder: Path):
    from foldok_index import chunk_text

    text = (folder / "pump.md").read_text(encoding="utf-8")
    a = chunk_text(text, "d", 1)
    b = chunk_text(text, "d", 1)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert chunk_text(text, "d", 2)[0].chunk_id != a[0].chunk_id


def test_a_chunk_knows_where_it_came_from(index: Index):
    hit = index.search("glycol", k=1)[0]
    assert "pump.md#chunk=" in hit.citation


def test_headings_travel_with_the_chunk(index: Index):
    hits = index.search("high temperature alarm", k=3)
    assert any(h.chunk.heading for h in hits)


# --- scale sanity ------------------------------------------------------
def test_a_few_thousand_chunks_stay_fast(tmp_path: Path):
    import time

    ix = Index(tmp_path / "big.db")
    for i in range(400):
        ix.ingest_text(
            f"doc{i}",
            f"Document {i}. " + " ".join(f"term{(i * 7 + j) % 500}" for j in range(120)),
        )
    assert ix.store.chunk_count() >= 400
    start = time.perf_counter()
    for _ in range(20):
        ix.search("term42 term101", k=10)
    elapsed = (time.perf_counter() - start) / 20
    assert elapsed < 0.25, f"{elapsed * 1000:.0f} ms per query"


def test_retrieval_returns_nothing_rather_than_junk(index: Index):
    """'Found nothing' and 'found junk' must not look the same to the agent."""
    assert index.search("orbital mechanics of cometary debris", k=5) == []
    assert index.search("glycol coolant", k=5)


def test_the_floor_can_be_lowered_deliberately(index: Index):
    assert index.search("orbital mechanics of cometary debris", k=5, min_similarity=-1.0)
