"""Retrieve + answer-aware rerank over workbench index cache.

Chunks from caption / detail_summary / fact text — not domain facet packs.
Rerank asks: does this chunk help *answer* the question? Weak / number-only hits drop.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .model import RetrievalHit

CONTACT_RX = re.compile(
    r"(?i)([\w.+-]+@[\w-]+\.[\w.-]+|https?://\S+|www\.\S|"
    r"\+?\d[\d\s().-]{7,}\d|"
    r"\b(phone|telefon|email|e-post|fax|linkedin)\b)"
)

STOP = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "og", "i", "på", "av", "til", "en", "et", "de", "det", "som", "er", "om",
    "what", "how", "hva", "hvordan", "which", "hvilke", "hvilken", "dette",
    "korpuset", "korpus", "handler", "about", "project", "prosjekt",
}

# Synonym expansion for retrieval — NOT a document schema. No bare numbers.
_EXPAND = {
    "kabelklasse": ["cable", "class", "classes", "category", "segregation"],
    "kabelklass": ["cable", "class", "classes", "category", "segregation"],
    "kabel": ["cable"],
    "klasse": ["class", "classes", "category"],
    "avstand": ["separation", "segregation", "spacing"],
    "avstandskrav": ["separation", "segregation", "spacing", "distance"],
    "separa": ["separation", "segregation"],
    "sone": ["zone", "zoning", "shield", "emc"],
    "soner": ["zone", "zoning", "shield", "emc"],
    "skjerm": ["shield", "shielding", "attenuation"],
    "skjerming": ["shield", "shielding", "attenuation"],
    "jording": ["earth", "earthing", "ground", "grounding", "bonding"],
    "jord": ["earth", "earthing", "ground"],
    "bonding": ["bonding", "equipotential", "earth"],
}

# Install-clearance noise: only keep when the question is about mounting clearances
_INSTALL_CLEARANCE_RX = re.compile(
    r"(?i)\b(ceiling|ceil|wall|floor|gulv|tak|vegg|"
    r"tray\s+to\s+ceiling|parallel\s+trays|installation\s+distance|"
    r"monteringsavstand|avstand\s+til\s+(tak|vegg|gulv))\b"
)
_CLEARANCE_QUESTION_RX = re.compile(
    r"(?i)\b(ceiling|tak|vegg|wall|floor|gulv|monteringsavstand|"
    r"installation\s+distance|tray\s+to\s+ceiling|clearance\s+to)\b"
)

_CLASS_SIGNAL_RX = re.compile(
    r"(?i)\b(class\s*[1-6]|cable\s*class|kabelklasse|category\s*[1-6]|"
    r"segregation|separation\s+between\s+(cable|circuit|class)|"
    r"signal\s+cable|power\s+cable|fibre|fiber)\b"
)
_SHIELD_SIGNAL_RX = re.compile(
    r"(?i)\b(shield|skjerm|attenuation|zone|sone|emc|faraday|mil[-\s]?std)\b"
)
_EARTH_SIGNAL_RX = re.compile(
    r"(?i)\b(earth|jord|ground|bonding|equipotential|pe\b)\b"
)


def _stem(t: str) -> str:
    if t.endswith("ene") and len(t) > 5:
        return t[:-3]
    if t.endswith("er") and len(t) > 4:
        return t[:-2]
    if t.endswith("s") and len(t) > 4:
        return t[:-1]
    return t


def _tokens(text: str, *, expand: bool = True) -> list[str]:
    raw = re.findall(r"[a-z0-9æøå]+", (text or "").lower())
    out = []
    for t in raw:
        if t in STOP or len(t) < 2:
            continue
        # Skip pure numbers as query/chunk tokens for overlap (prevents 300-mm hijack)
        if t.isdigit():
            continue
        stem = _stem(t)
        out.append(stem)
        if expand:
            for extra in _EXPAND.get(stem, []) + _EXPAND.get(t, []):
                out.append(extra)
    return out


def _core_tokens(question: str) -> list[str]:
    out = []
    for t in re.findall(r"[a-z0-9æøå]+", (question or "").lower()):
        if t in STOP or len(t) < 2 or t.isdigit():
            continue
        out.append(_stem(t))
    return list(dict.fromkeys(out))


def index_to_chunks(index) -> list[dict]:
    """Flatten workbench cache entries into searchable passage chunks.

    Also injects ``kind=claim`` chunks from foldok_claims so sections retrieve
    statements about the subject, not only captions about documents.
    """
    chunks: list[dict] = []
    for e in index or []:
        if e.get("kind") in ("skipped",):
            continue
        path = e.get("file") or ""
        if not path:
            continue
        file_id = Path(path).name
        base_tags = " ".join(e.get("content_tags") or [])

        def _add(kind: str, text: str, pages: str = "", extra_id: str = "", key: str = ""):
            text = (text or "").strip()
            if not text or len(text) < 12:
                return
            if CONTACT_RX.search(text):
                return
            cid = hashlib.sha1(f"{path}|{kind}|{extra_id}|{text[:80]}".encode()).hexdigest()[:16]
            chunks.append({
                "chunk_id": cid,
                "file_id": file_id,
                "path": path,
                "text": text[:1200],
                "pages": pages or "",
                "kind": kind,
                "tags": base_tags,
                "fact_key": key,
            })

        _add("caption", e.get("caption") or "")
        _add("detail", e.get("detail_summary") or "")
        for f in e.get("facts") or []:
            key = str(f.get("key") or "").strip()
            val = str(f.get("value") or "").strip()
            if not val:
                continue
            if key.lower() in ("phone", "email", "website", "address", "fax"):
                continue
            unit = f.get("unit") or ""
            shown = f"{key.replace('_', ' ')}: {val}" + (f" {unit}" if unit else "")
            excerpt = str(f.get("source_excerpt") or "").strip()
            blob = shown
            if excerpt and excerpt.lower() not in shown.lower():
                blob = f"{shown} — {excerpt[:200]}"
            _add(
                "fact",
                blob,
                pages=str(f.get("source_location") or ""),
                extra_id=str(f.get("id") or key),
                key=key.lower(),
            )

    # Subject-grain claims outrank document captions in ranking
    try:
        from foldok_claims import as_chunks, claims_from_index
        indexed = claims_from_index(index)
        paths = {
            Path(e.get("file") or "").name: (e.get("file") or "")
            for e in (index or []) if e.get("file")
        }
        chunks.extend(as_chunks(indexed.claims, paths=paths))
    except Exception:
        pass
    return chunks


def _lexical_score(question: str, chunk: dict) -> float:
    q_toks = _tokens(question)
    if not q_toks:
        return 0.0
    q_core = _core_tokens(question)
    text = f"{chunk.get('text') or ''} {chunk.get('tags') or ''} {chunk.get('file_id') or ''}"
    t_toks = set(_tokens(text))
    if not t_toks:
        return 0.0
    overlap = [t for t in q_toks if t in t_toks]
    if not overlap:
        return 0.0
    core_hit = sum(
        1 for t in q_core
        if t in t_toks or any(e in t_toks for e in _EXPAND.get(t, []))
    )
    cover = core_hit / max(len(q_core), 1)
    density = len(set(overlap)) / max(len(t_toks), 1)
    score = 0.70 * cover + 0.20 * min(1.0, density * 8)
    fname = (chunk.get("file_id") or "").lower()
    if any(t in fname for t in set(q_toks) if len(t) > 3):
        score += 0.10
    # --- claims outrank summaries -------------------------------------
    # A caption is a sentence about a document; a claim is a sentence about the
    # subject. Ranking them equally is why a section about cable classes filled
    # up with file abstracts instead of classes.
    if chunk.get("kind") == "claim":
        score += 0.18
        if chunk.get("claim_binding"):
            score += 0.07          # a requirement beats a loose statement
    elif chunk.get("kind") in ("caption", "detail"):
        score += 0.05
    if len(q_core) >= 2 and cover < 0.34:
        score *= 0.55
    return min(score, 1.0)


def answer_relevance(question: str, chunk: dict) -> float:
    """Second-pass score: does this chunk actually help answer the question?"""
    q = (question or "").lower()
    text = (chunk.get("text") or "")
    text_l = text.lower()
    key = (chunk.get("fact_key") or "").lower()
    kind = chunk.get("kind") or ""

    # Number-only / install-clearance hijack
    if _INSTALL_CLEARANCE_RX.search(text) or _INSTALL_CLEARANCE_RX.search(key):
        if not _CLEARANCE_QUESTION_RX.search(q):
            return 0.0

    # Pure numeric fact with no conceptual overlap with question intent
    if kind == "fact" and re.fullmatch(r"(?i)[\d\s.,/\-]+(mm|cm|m|db|%|deg|°)?", 
                                         re.sub(r"^[^:]+:\s*", "", text).strip()):
        # keep only if question asks for that kind of measure AND text has conceptual words
        if not any(w in q for w in ("avstand", "distance", "separation", "mm", "clearance", "klasse", "class")):
            return 0.05

    intent_boost = 0.0
    if any(w in q for w in ("klasse", "class", "kabel", "cable", "avstand", "separa")):
        if _CLASS_SIGNAL_RX.search(text) or _CLASS_SIGNAL_RX.search(key):
            intent_boost += 0.45
        elif re.search(r"(?i)\b(300\s*mm|installation\s+distance|ceiling|wall)\b", text):
            # distance number without class/segregation language → weak for class questions
            if "klasse" in q or "class" in q:
                intent_boost -= 0.35
    if any(w in q for w in ("sone", "zone", "skjerm", "emc", "shield")):
        if _SHIELD_SIGNAL_RX.search(text):
            intent_boost += 0.40
    if any(w in q for w in ("jord", "earth", "ground", "bonding")):
        if _EARTH_SIGNAL_RX.search(text):
            intent_boost += 0.40

    # Captions that name the topic beat stray fact rows
    # A claim that matches the question's intent is the best possible hit.
    if kind == "claim" and intent_boost > 0:
        intent_boost += 0.14
    elif kind in ("caption", "detail") and intent_boost > 0:
        intent_boost += 0.08

    base = _lexical_score(question, chunk)
    return max(0.0, min(1.0, base * 0.55 + intent_boost + base * 0.20))


def retrieve(question: str, index, *, k: int = 8, min_score: float = 0.32) -> list[RetrievalHit]:
    """Retrieve → answer-relevance rerank → drop weak hits."""
    chunks = index_to_chunks(index)
    pool: list[tuple[float, dict]] = []
    for ch in chunks:
        lex = _lexical_score(question, ch)
        if lex < 0.18:
            continue
        rel = answer_relevance(question, ch)
        if rel < min_score:
            continue
        pool.append((rel, ch))
    pool.sort(key=lambda x: (-x[0], x[1].get("file_id") or ""))

    out, per_file = [], {}
    for score, ch in pool:
        fid = ch["file_id"]
        n = per_file.get(fid, 0)
        if n >= 2:
            continue
        per_file[fid] = n + 1
        out.append(RetrievalHit(
            chunk_id=ch["chunk_id"],
            score=score,
            file_id=fid,
            path=ch.get("path") or "",
            text=ch.get("text") or "",
            pages=ch.get("pages") or "",
        ))
        if len(out) >= k:
            break
    return out


def search(index, query: str, k: int = 8, *, min_score: float = 0.32) -> list[RetrievalHit]:
    return retrieve(query, index, k=k, min_score=min_score)
