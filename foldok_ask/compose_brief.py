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
    blueprint = narrative.as_blueprint()
    critic = review_document(
        drafts,
        thesis=narrative.thesis,
        lang=lang,
        main_argument=blueprint.main_argument,
        blueprint=blueprint,
    )

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
    gaps_body = gaps or (
        "Ingen kritiske dekningshull notert." if no else "No critical gaps noted."
    )
    if narrative.volume_note:
        gaps_body = (
            f"{narrative.volume_note}\n\n{gaps_body}"
            if gaps_body else narrative.volume_note
        )

    pipeline = None
    try:
        from foldok_budget import check_pipeline
        usable = sum(1 for e in (index or []) if e.get("kind") != "skipped" and e.get("file"))
        claims_n = 0
        try:
            from foldok_claims import claims_from_index
            claims_n = len(claims_from_index(index or [], min_confidence=0.35))
        except Exception:
            claims_n = sum(len(e.get("facts") or []) for e in (index or []))
        body_drafts = [d for d in drafts if d.kind not in ("appendix", "gaps") and not d.omitted]
        cited = int(getattr(cites, "_total", 0) or len(getattr(cites, "files", []) or []))
        pipeline = check_pipeline(
            files_indexed=len(index or []),
            files_usable=usable,
            claims_extracted=claims_n,
            sections_planned=len(narrative.sections or []),
            sections_with_content=sum(1 for d in body_drafts if (d.prose or "").strip()),
            claims_cited=cited,
            gap_ledger_entries=None,
        )
        if pipeline.first_failure() is not None:
            note = (
                f"Pipeline: {pipeline.first_failure().stage} — {pipeline.first_failure().detail}"
            )
            gaps_body = f"{note}\n\n{gaps_body}" if gaps_body else note
    except Exception:
        pipeline = None

    return {
        "overview": overview or (
            "Ingen innledning kunne skrives." if no else "No introduction could be written."
        ),
        "answers": "\n\n".join(body_parts) if body_parts else (
            "Ingen seksjoner med dekning i fortellingen." if no else
            "No sections with coverage in the narrative."
        ),
        "gaps": gaps_body,
        "source_register": sources or "\n".join(cites.appendix_lines(lang=lang)),
        "_narrative": narrative.to_dict(),
        "_blueprint": blueprint.to_dict(),
        "_outline": [s.to_dict() for s in narrative.sections],
        "_drafts": drafts,
        "_cites": cites,
        "_critic": critic.to_dict(),
        "_thesis": narrative.thesis,
        "_volume_note": narrative.volume_note,
        "_pipeline": pipeline.to_dict() if pipeline is not None else None,
        "_cite_stats": cites.stats() if hasattr(cites, "stats") else None,
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
