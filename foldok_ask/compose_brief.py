"""Compose topic_brief: Narrative → Author → Validator → Critic → appendix."""
from __future__ import annotations

from .author_doc import author_document
from .critic import review_document
from .model import Question
from .narrative import plan_narrative
from .suggest import suggest_questions


def default_brief_questions(index, *, lang: str = "no", limit: int = 4) -> list[Question]:
    return suggest_questions(index, lang=lang, limit=limit)


def compose_topic_brief(
    index,
    questions: list[str | Question] | None = None,
    *,
    artifact=None,
    lang: str = "no",
    audience: str = "engineer",
) -> dict:
    """Document = engineering story with evidence under it.

    Overview = thesis-led framing.
    Answers = arc sections (context → concepts → rules → standards → conclusion).
    Gaps / sources = short end matter.
    """
    user_qs: list[str] = []
    if questions:
        for q in questions:
            text = q.text if isinstance(q, Question) else str(q)
            text = (text or "").strip()
            if not text:
                continue
            low = text.lower()
            if any(w in low for w in ("omfang", "korpus", "handler dette", "what is this")):
                continue
            user_qs.append(text)

    narrative = plan_narrative(
        "topic_brief",
        index,
        artifact=artifact,
        audience=audience,
        user_questions=user_qs or None,
        lang=lang,
    )
    drafts, cites = author_document(
        narrative=narrative, index=index, artifact=artifact, lang=lang,
    )
    critic = review_document(drafts, thesis=narrative.thesis, lang=lang)

    overview = ""
    body_parts = []
    gaps = ""
    sources = ""
    for d in drafts:
        if d.kind == "framing":
            overview = d.prose
        elif d.kind == "appendix":
            sources = d.prose
        elif d.kind == "gaps":
            gaps = d.prose
        else:
            block = f"### {d.heading}\n\n"
            if d.gap and not d.prose:
                block += d.gap
            else:
                block += d.prose
                if d.gap:
                    block += f"\n\n*{d.gap}*"
            body_parts.append(block)

    no = (lang or "no").startswith("no")
    return {
        "overview": overview or (
            "Ingen innledning kunne skrives." if no else "No introduction could be written."
        ),
        "answers": "\n\n".join(body_parts) if body_parts else (
            "Ingen seksjoner med dekning i fortellingen." if no else
            "No sections with coverage in the narrative."
        ),
        "gaps": gaps or (
            "Ingen kritiske dekningshull notert." if no else "No critical gaps noted."
        ),
        "source_register": sources or "\n".join(cites.appendix_lines(lang=lang)),
        "_narrative": narrative.to_dict(),
        "_outline": [s.to_dict() for s in narrative.sections],
        "_drafts": drafts,
        "_cites": cites,
        "_critic": critic.to_dict(),
        "_thesis": narrative.thesis,
    }


def render_brief_markdown(
    index,
    questions: list[str | Question] | None = None,
    *,
    artifact=None,
    lang: str = "no",
) -> str:
    parts = compose_topic_brief(index, questions, artifact=artifact, lang=lang)
    no = (lang or "no").startswith("no")
    blocks = [
        f"## {'Innledning' if no else 'Introduction'}\n\n{parts['overview']}",
        f"## {'Teknisk diskusjon' if no else 'Technical discussion'}\n\n{parts['answers']}",
        f"## {'Åpne punkter' if no else 'Open points'}\n\n{parts['gaps']}",
        f"## {'Kilder' if no else 'Sources'}\n\n{parts['source_register']}",
    ]
    return "\n\n".join(blocks)
