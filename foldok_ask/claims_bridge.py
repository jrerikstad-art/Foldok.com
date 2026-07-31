"""Bridge: workbench index → foldok_claims → Author / gaps / standards.

Prefer foldok_claims.integrate (0.88+) when available: claims_from_index,
standards_register, coherence_section. Author consumes Claim sentences.
"""
from __future__ import annotations

import re
from pathlib import Path

from foldok_claims import Claim, ClaimSet, check, claims_from_index, coherence_section
from foldok_claims.coherence import CoherenceReport

# Map section purpose → preferred claim types
_PURPOSE_TYPES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("kabelklasse", "cable class", "separa", "segregat", "klasse"),
     ("classification", "rule", "practice", "constraint")),
    (("sone", "zone", "jord", "earth", "bonding"),
     ("rule", "practice", "constraint", "distinction")),
    (("emc", "skjerm", "shield", "designbegrens"),
     ("rule", "quantity", "distinction", "definition", "risk")),
    (("anbefal", "recommend", "designregel", "hensyn"),
     ("practice", "rule", "constraint", "quantity")),
    (("hypotese", "hypothesis", "risiko", "risk"),
     ("hypothesis", "risk")),
    (("standard", "referanse"),
     ("reference", "rule")),
]


def corpus_claims(index, *, min_confidence: float = 0.4) -> tuple[ClaimSet, CoherenceReport]:
    indexed = claims_from_index(index, min_confidence=min_confidence)
    claims = ClaimSet([c for c in indexed.claims.claims if c.confidence >= min_confidence])
    return claims, check(claims)


def claims_for_section(
    claims: ClaimSet,
    *,
    purpose: str = "",
    heading: str = "",
    retrieve_query: str = "",
    used_ids: set[str] | None = None,
    limit: int = 3,
) -> list[Claim]:
    used = used_ids or set()
    blob = f"{purpose} {heading} {retrieve_query}".lower()
    prefer_types: tuple[str, ...] = ()
    for needles, types in _PURPOSE_TYPES:
        if any(n in blob for n in needles):
            prefer_types = types
            break
    if not prefer_types:
        prefer_types = ("rule", "classification", "quantity", "practice", "distinction")

    pool = [c for c in claims.claims if c.id not in used]
    q_toks = set(re.findall(r"[a-zæøå0-9]{3,}", retrieve_query.lower()))
    ranked = sorted(
        pool,
        key=lambda c: (
            0 if c.type in prefer_types else 1,
            0 if c.binding else 1,
            -sum(1 for t in q_toks if t in c.text.lower()) if q_toks else 0,
            -c.confidence,
            0 if c.scope.known else 1,
        ),
    )
    out: list[Claim] = []
    seen_src: set[str] = set()
    for c in ranked:
        if c.source in seen_src and len(out) >= 1:
            continue
        out.append(c)
        seen_src.add(c.source)
        if len(out) >= limit:
            break
    return out


def section_needs_types(purpose: str, heading: str, retrieve_query: str) -> set[str]:
    blob = f"{purpose} {heading} {retrieve_query}".lower()
    for needles, types in _PURPOSE_TYPES:
        if any(n in blob for n in needles):
            return set(types)
    return set()


def has_type_coverage(claims: ClaimSet, types: set[str]) -> bool:
    if not types:
        return bool(claims)
    return any(c.type in types for c in claims.claims)


def format_claim_sentence(claim: Claim, *, lang: str = "no") -> str:
    text = (claim.text or "").strip().rstrip(".")
    if not text:
        return ""
    if re.match(r"(?i)^[a-z0-9_ ]{3,40}:\s+\S", text):
        text = text.split(":", 1)[1].strip()
    no = (lang or "no").startswith("no")
    if no:
        text = re.sub(r"(?i)\bshall\b", "skal", text)
        text = re.sub(r"(?i)\bmust\b", "må", text)
        text = re.sub(r"(?i)\bis required\b", "er påkrevd", text)
        text = re.sub(r"(?i)\bmå provide\b", "må gi", text)
        text = re.sub(r"(?i)\bmå be\b", "må være", text)
        text = re.sub(r"(?i)\bskal be\b", "skal være", text)
    return text


def coherence_gap_lines(report: CoherenceReport, *, lang: str = "no", limit: int = 8) -> list[str]:
    lines = []
    for f in (report.findings or [])[:limit]:
        q = f.question or f.summary
        lines.append(f"- [{f.severity}] {f.kind}: {q}")
    return lines


def coherence_markdown(claims: ClaimSet, *, lang: str = "no") -> str:
    return coherence_section(claims, lang=lang)


def standards_markdown(claims: ClaimSet, *, lang: str = "no") -> str:
    from foldok_claims import register_markdown, standards_register
    return register_markdown(standards_register(claims), lang=lang)
