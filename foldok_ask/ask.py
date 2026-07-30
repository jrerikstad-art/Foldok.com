"""ask() — retrieve → rerank → ground → synthesize cited prose → verify."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Sequence

from .ground import conflict_gaps, ground
from .model import Answer, Citation, Gap, GroundSet, Question, RetrievalHit
from .retrieve import retrieve

CONTACT_RX = re.compile(
    r"(?i)([\w.+-]+@[\w-]+\.[\w.-]+|\+?\d[\d\s().-]{7,}\d)"
)

SCOPE_RX = re.compile(
    r"(?i)\b(omfang|korpus|handler\s+dette|what\s+is\s+this\s+(corpus|project|folder)|"
    r"scope|overview\s+of\s+(the\s+)?(project|corpus)|hva\s+handler)\b"
)

ENUM_LIST_RX = re.compile(
    r"(?i)\b(class\s*[1-6]\b.*class\s*[1-6]|kabelklasse\s*[1-6]|"
    r"category\s*[1-6].*category\s*[1-6]|"
    r"(^|\n)\s*[-•]\s+.+\n\s*[-•]\s+)",
    re.S,
)


def _qid(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def _is_scope_question(text: str) -> bool:
    return bool(SCOPE_RX.search(text or ""))


def synthesize_scope(index, *, artifact=None, lang: str = "no") -> Answer:
    """Omfang from file count + tags/captions — never MANGLER when index non-empty."""
    art = artifact or {}
    no = (lang or "no").lower().startswith("no")
    usable = [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]
    n = len(usable)
    qid = _qid("omfang")
    title = str(art.get("name") or "").strip() or (
        Path(usable[0]["file"]).stem if usable else ("Prosjekt" if no else "Project")
    )
    if n <= 0:
        return Answer(
            question_id=qid,
            question_text="Omfang" if no else "Scope",
            prose="",
            gaps=[Gap(kind="weak_retrieve", detail="MANGLER: ingen indekserte filer" if no else "MISSING: no indexed files")],
            grounded=False,
        )

    tag_c: Counter = Counter()
    for e in usable[:80]:
        for t in e.get("content_tags") or []:
            t = str(t).strip().lower().replace("-", " ")
            if t and len(t) > 2 and t not in ("doc", "document", "pdf", "email"):
                tag_c[t] += 1
    themes = [t for t, _ in tag_c.most_common(4)]
    if not themes:
        # Fall back to frequent caption nouns
        bag: Counter = Counter()
        for e in usable[:30]:
            for tok in re.findall(r"[A-Za-zÆØÅæøå]{5,}", e.get("caption") or ""):
                bag[tok.lower()] += 1
        themes = [t for t, _ in bag.most_common(3)]

    theme_txt = ", ".join(themes[:3]) if themes else ("tekniske kilder" if no else "technical sources")
    if no:
        s1 = f"{title} er en kildesamling med {n} indekserte filer."
        s2 = f"Hovedtema i korpuset er {theme_txt}."
    else:
        s1 = f"{title} is a source collection with {n} indexed files."
        s2 = f"Main themes in the corpus are {theme_txt}."
    prose = f"{s1} {s2}"
    cites = []
    for e in usable[:5]:
        fn = Path(e.get("file") or "").name
        if fn:
            cites.append(Citation(span=(e.get("caption") or "")[:80], chunk_id=fn, file_id=fn))
    return Answer(
        question_id=qid,
        question_text="Hva handler dette korpuset om?" if no else "What is this corpus about?",
        prose=prose,
        citations=cites,
        grounded=True,
        hits=[],
    )


def _looks_like_structured_list(hits: list[RetrievalHit]) -> bool:
    blob = "\n".join(h.text for h in hits[:6])
    if ENUM_LIST_RX.search(blob):
        return True
    # Multiple class N mentions across hits
    classes = set(re.findall(r"(?i)\bclass\s*([1-6])\b", blob))
    return len(classes) >= 3


def _passage_facts(hits: list[RetrievalHit]):
    """Turn top hits into AuthoringEngine facts (quotes), not key:value walls."""
    from foldok_author import Fact
    facts = []
    for i, h in enumerate(hits[:6]):
        quote = (h.text or "").strip()
        # Prefer caption side of fact lines
        if " — " in quote:
            quote = quote.split(" — ", 1)[-1].strip() or quote
        if re.match(r"(?i)^[a-z0-9_ ]+:\s+", quote):
            # Keep value+context but shorten key noise for summarize
            quote = re.sub(r"(?i)^[a-z0-9_ ]+:\s+", "", quote).strip()
        quote = quote[:220]
        if len(quote) < 20:
            continue
        facts.append(Fact(
            id=h.chunk_id or f"h{i}",
            key="source_note",
            value=quote,
            label="kildeutdrag",
            citation=h.file_id,
        ))
    return facts


def _synthesize_prose(question: Question, hits: list[RetrievalHit]) -> str:
    """Short cited understanding from top chunks — not a claim table."""
    lang = question.locale or "no"
    no = lang.lower().startswith("no")
    facts = _passage_facts(hits)
    if not facts:
        return ""

    prose = ""
    try:
        from foldok_author import AuthoringEngine
        engine = AuthoringEngine(lang=lang)
        result = engine.author("summarize_system", facts, title=question.text[:80])
        prose = (result.prose or "").strip()
        if getattr(result, "claims", None):
            kept = [
                c.text for c in result.claims
                if c.status != "ungrounded"
            ]
            if kept:
                prose = " ".join(kept[:4])
    except Exception:
        prose = ""

    # Prefer short cited quotes over fact-printer voice ("kildeutdrag er …")
    if (
        not prose
        or prose.lower().startswith("tabellen under")
        or "kildeutdrag er" in prose.lower()
        or "kildeutdrag is" in prose.lower()
    ):
        bits = [f"{f.value.rstrip('.')} [{f.citation}]" for f in facts[:3]]
        if no:
            prose = f"For «{question.text}» treffer korpuset dette: " + "; ".join(bits[:2]) + "."
            if len(bits) > 2:
                prose += f" Videre: {bits[2]}."
        else:
            prose = f"For “{question.text}” the corpus supports: " + "; ".join(bits[:2]) + "."
            if len(bits) > 2:
                prose += f" Additionally: {bits[2]}."

    lines = []
    for ln in prose.splitlines():
        if CONTACT_RX.search(ln):
            continue
        # Only drop snake_case fact-printer lines, not titled sentences
        if re.match(r"(?i)^\s*[a-z][a-z0-9_]{3,40}:\s+\S+", ln) and " er " not in ln and " is " not in ln:
            continue
        lines.append(ln)
    prose = " ".join(" ".join(lines).split())
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    return " ".join(s for s in sentences[:4] if s).strip()


def _optional_table(question: Question, hits: list[RetrievalHit], gs: GroundSet) -> list[dict]:
    """Tables only when sources contain a structured list relevant to the question."""
    if not _looks_like_structured_list(hits):
        return []
    no = (question.locale or "no").lower().startswith("no")
    rows = []
    for c in gs.claims:
        if c.key in ("passage", ""):
            continue
        if not re.search(r"(?i)class|klasse|categor|segregat|separat", c.key + " " + c.value):
            continue
        rows.append([c.key.replace("_", " "), c.value[:100], c.file_id])
    if len(rows) < 2:
        return []
    return [{
        "title": "Strukturert liste i kilder" if no else "Structured list in sources",
        "headers": ["Punkt", "Verdi", "Kilde"] if no else ["Item", "Value", "Source"],
        "rows": rows[:8],
    }]


def _verify_numbers(prose: str, gs: GroundSet) -> tuple[str, list[Gap]]:
    if not prose:
        return prose, []
    ground_blob = " ".join(f"{c.value} {c.quote}" for c in gs.claims).lower()
    ground_blob += " " + " ".join(h.text for h in gs.hits).lower()
    gaps = []
    kept = []
    for sent in re.split(r"(?<=[.!?])\s+", prose):
        nums = re.findall(r"\b\d+(?:[.,]\d+)?\b", sent)
        if any(n not in ground_blob for n in nums):
            gaps.append(Gap(
                kind="insufficient_coverage",
                detail="Fjernet setning med usitert tall",
            ))
            continue
        kept.append(sent)
    return " ".join(kept).strip(), gaps


def ask(
    index,
    question: str | Question,
    *,
    k: int = 8,
    min_score: float = 0.32,
    lang: str = "no",
    artifact=None,
) -> Answer:
    """Full pipeline: retrieve → answer-rerank → ground → synthesize → verify."""
    if isinstance(question, Question):
        q = question
    else:
        q = Question(id=_qid(question), text=str(question).strip(), locale=lang, source="user")

    if not (q.text or "").strip():
        return Answer(
            question_id=q.id,
            question_text="",
            gaps=[Gap(kind="weak_retrieve", detail="Tomt spørsmål" if lang.startswith("no") else "Empty question")],
            grounded=False,
        )

    # Scope / omfang — corpus summary, never MANGLER when files exist
    if _is_scope_question(q.text):
        return synthesize_scope(index, artifact=artifact, lang=q.locale or lang)

    hits = retrieve(q.text, index, k=k, min_score=min_score)
    if not hits:
        detail = (
            f"MANGLER: ingen relevante kilder for «{q.text}»"
            if (lang or "no").startswith("no") else
            f"MISSING: no relevant sources for “{q.text}”"
        )
        return Answer(
            question_id=q.id,
            question_text=q.text,
            gaps=[Gap(kind="weak_retrieve", detail=detail)],
            grounded=False,
            hits=[],
        )

    gs = ground(q, hits)
    conflicts = conflict_gaps(gs)
    prose = _synthesize_prose(q, hits)
    tables = _optional_table(q, hits, gs)
    prose, num_gaps = _verify_numbers(prose, gs)

    citations = []
    seen = set()
    for h in hits:
        if h.file_id in seen:
            continue
        seen.add(h.file_id)
        citations.append(Citation(span=h.text[:120], chunk_id=h.chunk_id, file_id=h.file_id))

    grounded = bool(prose.strip())
    gaps = list(conflicts) + list(num_gaps)
    if not grounded:
        gaps.insert(0, Gap(
            kind="insufficient_coverage",
            detail=(
                f"Treff for «{q.text}», men ikke nok til å forankre svar"
                if (lang or "no").startswith("no") else
                f"Hits for “{q.text}”, but not enough to ground an answer"
            ),
            file_ids=[h.file_id for h in hits[:4]],
        ))

    return Answer(
        question_id=q.id,
        question_text=q.text,
        prose=prose,
        tables=tables,
        citations=citations,
        gaps=gaps,
        grounded=grounded,
        hits=hits,
    )


def ask_many(
    index,
    questions: Sequence[str | Question],
    *,
    lang: str = "no",
    k: int = 8,
    artifact=None,
) -> list[Answer]:
    return [ask(index, q, lang=lang, k=k, artifact=artifact) for q in questions]
