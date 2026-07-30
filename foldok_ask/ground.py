"""Ground — claims only from retrieval hits for this question."""
from __future__ import annotations

import re
from collections import defaultdict

from .model import Gap, GroundClaim, GroundSet, Question, RetrievalHit

NUM_RX = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:mm|cm|m|dB|db|kHz|MHz|GHz|V|A|°|deg)?\b", re.I)
KEYVAL_RX = re.compile(
    r"(?i)^\s*([a-z0-9æøå][a-z0-9æøå _/-]{1,48})\s*:\s*(.+)$"
)


def ground(question: Question, hits: list[RetrievalHit]) -> GroundSet:
    claims: list[GroundClaim] = []
    gaps: list[Gap] = []  # attached later by ask()

    if not hits:
        return GroundSet(question_id=question.id, hits=[], claims=[])

    for h in hits:
        text = (h.text or "").strip()
        if not text:
            continue
        m = KEYVAL_RX.match(text.split("—")[0].strip())
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            val = m.group(2).strip()
            # Split trailing excerpt
            if " — " in text:
                quote = text.split(" — ", 1)[1][:200]
            else:
                quote = text[:200]
            claims.append(GroundClaim(
                key=key, value=val, chunk_id=h.chunk_id, file_id=h.file_id, quote=quote,
            ))
            continue
        # Passage claim — use first number-bearing sentence or short quote
        nums = NUM_RX.findall(text)
        claims.append(GroundClaim(
            key="passage",
            value=(nums[0] if nums else text[:160]),
            chunk_id=h.chunk_id,
            file_id=h.file_id,
            quote=text[:240],
        ))

    # Dedup by (key, value, file)
    seen, uniq = set(), []
    for c in claims:
        sig = (c.key, c.value.lower(), c.file_id)
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(c)

    return GroundSet(question_id=question.id, hits=list(hits), claims=uniq[:20])


def conflict_gaps(ground_set: GroundSet) -> list[Gap]:
    """Same metric key, different values across files → conflict gaps."""
    by_key: dict[str, list[GroundClaim]] = defaultdict(list)
    for c in ground_set.claims:
        if c.key in ("passage", "") or not c.value:
            continue
        by_key[c.key].append(c)
    gaps = []
    for key, items in by_key.items():
        vals = {}
        for c in items:
            vals.setdefault(c.value.lower(), c)
        if len(vals) >= 2:
            a, b = list(vals.values())[:2]
            gaps.append(Gap(
                kind="conflict",
                detail=f"{key}: {a.value} ({a.file_id}) vs {b.value} ({b.file_id})",
                file_ids=[a.file_id, b.file_id],
            ))
    return gaps
