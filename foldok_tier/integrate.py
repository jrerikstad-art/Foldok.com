"""Bridge: prose / workbench index → TierReport + retrieve chunks.

Candidates are emitted as ``kind="candidate"`` chunks — lower confidence than
pattern-matched claims, but available when a section would otherwise be empty.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .tier import TierReport, TieredSentence, fill_section, section_terms, tier_sentences

TEXT_FIELDS = ("detail_summary", "text", "body", "caption", "summary")


def tier_from_prose(
    prose: str,
    *,
    source: str = "",
    strong_ids: Mapping[str, str] | None = None,
    topics: Iterable[str] = (),
) -> TierReport:
    """Reflow → sentences → tier. Safe when foldok_reflow / claims are absent."""
    text = prose or ""
    try:
        from foldok_reflow import reflow, split_sentences
        text = reflow(text).text or text
        sents = split_sentences(text)
    except Exception:
        sents = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 25]

    strong = dict(strong_ids or {})
    if not strong:
        try:
            from foldok_claims import extract as ce
            found = ce(text, source=source or "doc")
            strong = {c.text: c.type for c in found.claims}
        except Exception:
            strong = {}

    topic_set = {t.lower() for t in topics}
    if not topic_set:
        for claim_text in strong:
            topic_set.update(
                w.lower() for w in re.findall(r"[A-Za-zÀ-ÿÆØÅæøå]{5,}", claim_text)
            )
        topic_set.update(w.lower() for w in re.findall(r"[A-Za-zÀ-ÿÆØÅæøå]{5,}", source))

    return tier_sentences(
        sents, source=source, strong_ids=strong, topics=topic_set,
    )


def candidate_chunks(
    report: TierReport,
    *,
    paths: Mapping[str, str] | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Candidates in retrieve.py chunk shape (kind=candidate)."""
    paths = paths or {}
    out: list[dict[str, Any]] = []
    for sent in report.of("candidate")[:limit]:
        file_id = sent.source or ""
        cid = hashlib.sha1(f"candidate|{sent.id}".encode()).hexdigest()[:16]
        out.append({
            "chunk_id": cid,
            "file_id": file_id,
            "path": paths.get(file_id, file_id),
            "text": sent.text,
            "pages": "",
            "kind": "candidate",
            "tags": "candidate description",
            "fact_key": "description",
            "claim_type": "description",
            "claim_modality": "is",
            "claim_binding": False,
            "claim_tier": "candidate",
            "claim_provenance": sent.provenance(lang="en"),
            "confidence": 0.42,
        })
    return out


def tier_report_from_index(
    index: Iterable[Mapping[str, Any]],
    *,
    max_files: int = 80,
) -> TierReport:
    """Merge per-file tier reports from workbench index prose fields."""
    merged = TierReport()
    for entry in list(index or [])[:max_files]:
        if entry.get("kind") == "skipped":
            continue
        path = str(entry.get("file") or "")
        if not path:
            continue
        file_id = Path(path).name
        prose = "\n".join(str(entry.get(f) or "") for f in TEXT_FIELDS).strip()
        if len(prose) < 40:
            continue
        extra_topics = re.findall(r"[A-Za-zÀ-ÿÆØÅæøå]{4,}", f"{file_id} {entry.get('caption') or ''}")
        report = tier_from_prose(prose, source=file_id, topics=extra_topics)
        merged.sentences.extend(report.sentences)
    return merged


def fill_for_section(
    report: TierReport,
    section_key: str,
    *,
    want: int = 6,
    extra_terms: Sequence[str] = (),
) -> list[TieredSentence]:
    """Strong-first fill using known section vocabulary."""
    terms = section_terms(section_key, *extra_terms)
    if not terms:
        terms = list(extra_terms) or ["cable", "system", "shield"]
    return fill_section(report, section_terms=terms, want=want)
