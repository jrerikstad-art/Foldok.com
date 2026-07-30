"""Compose thin document shells from grounded answers."""
from __future__ import annotations

from pathlib import Path

from .ask import ask, ask_many, synthesize_scope
from .model import Answer, Question
from .suggest import suggest_questions


def default_brief_questions(index, *, lang: str = "no", limit: int = 4) -> list[Question]:
    """Job default: scope + suggested probes (not fixed EMC sections)."""
    return suggest_questions(index, lang=lang, limit=limit)


def _source_register(answers: list[Answer], index, *, lang: str = "no") -> str:
    files = []
    seen = set()
    for a in answers:
        for c in a.citations:
            if c.file_id in seen:
                continue
            seen.add(c.file_id)
            files.append(c.file_id)
    n = sum(1 for e in (index or []) if e.get("kind") != "skipped" and e.get("file"))
    no = lang.startswith("no")
    if not files:
        # Still list a sample of corpus when nothing cited yet
        for e in (index or [])[:15]:
            if e.get("kind") == "skipped":
                continue
            fn = Path(e.get("file") or "").name
            if fn and fn not in seen:
                files.append(fn)
                seen.add(fn)
        if not files:
            return "Ingen kilder i indeksen." if no else "No sources in index."
    headers = ["Dokument", "Bruk"] if no else ["Document", "Use"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for fn in files[:40]:
        use = "Sitert / i korpus" if no else "Cited / in corpus"
        lines.append(f"| {fn} | {use} |")
    if n > len(files):
        rest = n - len(files)
        lines.append(
            f"| {'Øvrige ' + str(rest) + ' filer' if no else 'Remaining ' + str(rest) + ' files'} | "
            f"{'Bakgrunn' if no else 'Background'} |"
        )
    return "\n".join(lines)


def _conflicts_section(answers: list[Answer], *, lang: str = "no") -> str:
    rows = []
    for a in answers:
        for g in a.gaps:
            if g.kind == "conflict":
                rows.append([a.question_text[:40], g.detail])
    no = lang.startswith("no")
    if not rows:
        for a in answers:
            if a.question_text and _is_scopeish(a.question_text):
                continue
            if not a.grounded:
                for g in a.gaps:
                    rows.append([a.question_text[:40], g.detail])
        if not rows:
            return (
                "Ingen verdikonflikter eller dekningshull i de stilte spørsmålene."
                if no else
                "No value conflicts or coverage gaps in the asked questions."
            )
    headers = ["Spørsmål", "Gap / konflikt"] if no else ["Question", "Gap / conflict"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for r in rows[:20]:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(lines)


def _is_scopeish(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ("omfang", "korpus", "handler dette", "what is this"))


def compose_topic_brief(
    index,
    questions: list[str | Question] | None = None,
    *,
    artifact=None,
    lang: str = "no",
) -> dict[str, str]:
    """topic_brief = omfang (corpus) + ask() answers + gaps + sources."""
    art = artifact or {}
    no = lang.lower().startswith("no")
    qs = list(questions) if questions else default_brief_questions(index, lang=lang)

    # Always synthesize omfang from index — never MANGLER when files exist
    overview_ans = synthesize_scope(index, artifact=art, lang=lang)
    overview = overview_ans.prose

    # Remaining questions via ask (skip duplicate scope)
    rest = []
    for q in qs:
        text = q.text if isinstance(q, Question) else str(q)
        if _is_scopeish(text):
            continue
        rest.append(q)
    answers = ask_many(index, rest, lang=lang, artifact=art)

    qa_parts = []
    for a in answers:
        qa_parts.append(f"### {a.question_text}\n\n{a.markdown(lang=lang)}")

    dynamic = "\n\n".join(qa_parts) if qa_parts else (
        "Ingen ytterligere spørsmål bekreftet." if no else "No further questions confirmed."
    )

    all_answers = [overview_ans] + list(answers)
    return {
        "overview": overview,
        "answers": dynamic,
        "gaps": _conflicts_section(all_answers, lang=lang),
        "source_register": _source_register(all_answers, index, lang=lang),
        "_answers": all_answers,
        "_questions": qs,
    }


def render_brief_markdown(
    index,
    questions: list[str | Question] | None = None,
    *,
    artifact=None,
    lang: str = "no",
) -> str:
    parts = compose_topic_brief(index, questions, artifact=artifact, lang=lang)
    no = lang.startswith("no")
    blocks = [
        f"## {'Omfang og korpus' if no else 'Scope & corpus'}\n\n{parts['overview']}",
        f"## {'Temasvar' if no else 'Topic answers'}\n\n{parts['answers']}",
        f"## {'Mangler og konflikter' if no else 'Gaps & conflicts'}\n\n{parts['gaps']}",
        f"## {'Kilderegister' if no else 'Source register'}\n\n{parts['source_register']}",
    ]
    return "\n\n".join(blocks)
