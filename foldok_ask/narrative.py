"""Narrative layer — decide WHAT story to tell before Author writes HOW.

Not a new product engine brand: elevates DocumentPlanner to thesis + arc +
section purposes. Knowledge answers "what do we know?"; Narrative answers
"what story explains this best?"; Author writes; Validator binds evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .plan import CorpusSketch, OutlineSection, SectionKind, corpus_sketch

AuthorIntent = Literal["explain", "argue", "specify", "recommend", "frame", "conclude", "list"]
ArcBeat = Literal[
    "problem", "context", "concepts", "evidence", "rules",
    "standards", "open", "conclusion", "appendix",
]


@dataclass
class DocumentIntent:
    """Direction for the whole document — story before facts."""
    purpose: str = "topic_brief"
    audience: str = "engineer"
    main_question: str = ""
    main_argument: str = ""
    desired_outcome: str = ""
    tone: str = "technical_report"
    thesis_provisional: bool = False

    def to_dict(self) -> dict:
        return {
            "purpose": self.purpose,
            "audience": self.audience,
            "main_question": self.main_question,
            "main_argument": self.main_argument,
            "desired_outcome": self.desired_outcome,
            "tone": self.tone,
            "thesis_provisional": self.thesis_provisional,
        }


@dataclass
class NarrativeSection:
    heading: str
    purpose: str
    role_in_argument: str
    retrieve_query: str
    author_intent: AuthorIntent
    arc_beat: ArcBeat
    kind: SectionKind
    optional: bool = True

    def to_outline(self) -> OutlineSection:
        return OutlineSection(
            heading=self.heading,
            purpose=self.purpose,
            retrieve_query=self.retrieve_query,
            kind=self.kind,
            optional=self.optional,
        )

    def to_dict(self) -> dict:
        return {
            "heading": self.heading,
            "purpose": self.purpose,
            "role_in_argument": self.role_in_argument,
            "retrieve_query": self.retrieve_query,
            "author_intent": self.author_intent,
            "arc_beat": self.arc_beat,
            "kind": self.kind,
            "optional": self.optional,
        }


@dataclass
class NarrativePlan:
    """The story: thesis + arc + section purposes. Not paragraphs."""
    title: str
    intent: DocumentIntent
    thesis: str
    arc: list[str] = field(default_factory=list)
    sections: list[NarrativeSection] = field(default_factory=list)
    sketch: CorpusSketch | None = None

    def to_outline(self) -> list[OutlineSection]:
        return [s.to_outline() for s in self.sections]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "intent": self.intent.to_dict(),
            "thesis": self.thesis,
            "arc": list(self.arc),
            "sections": [s.to_dict() for s in self.sections],
        }


def plan_narrative(
    document_type: str = "topic_brief",
    index=None,
    *,
    artifact=None,
    audience: str = "engineer",
    user_questions: list[str] | None = None,
    lang: str = "no",
    intent_override: DocumentIntent | None = None,
) -> NarrativePlan:
    """Build DocumentIntent + thesis + arc from corpus coverage.

    Guardrails: thesis supportable by overview themes/captions, else provisional.
    Empty-support arc beats are still planned; Author omits if retrieve empty.
    """
    sketch = corpus_sketch(index, artifact=artifact)
    no = (lang or "no").lower().startswith("no")
    dtype = (document_type or "topic_brief").strip().lower()
    title = sketch.title or ("Prosjekt" if no else "Project")

    intent = intent_override or _suggest_intent(sketch, dtype, audience, user_questions, no)
    thesis, provisional = _ground_thesis(sketch, intent, no)
    intent.thesis_provisional = provisional
    intent.main_argument = intent.main_argument or thesis

    sections = _arc_sections(sketch, intent, user_questions, no)
    arc_labels = []
    seen = set()
    for s in sections:
        if s.arc_beat not in seen and s.arc_beat not in ("appendix",):
            arc_labels.append(s.arc_beat)
            seen.add(s.arc_beat)

    return NarrativePlan(
        title=title,
        intent=intent,
        thesis=thesis,
        arc=arc_labels,
        sections=sections,
        sketch=sketch,
    )


def _suggest_intent(
    sketch: CorpusSketch,
    dtype: str,
    audience: str,
    user_questions: list[str] | None,
    no: bool,
) -> DocumentIntent:
    themes = sketch.themes[:3]
    theme_txt = ", ".join(themes) if themes else sketch.title
    uq = (user_questions or [None])[0]

    if no:
        main_q = uq or f"Hvilke prinsipper og begrensninger gjelder for {theme_txt}?"
        outcome = "Felles forståelse av designprinsipper og åpne spørsmål"
        if "emc" in sketch.theme_blob or "shield" in sketch.theme_blob:
            main_q = uq or (
                "Hvilke EMC-begrensninger styrer kabelhåndtering og skjerming i dette korpuset?"
            )
            argument = (
                "Installasjonsmetode, soner og klassevalg er like viktige som materialvalg "
                "for å begrense elektromagnetisk påvirkning."
            )
        elif "weld" in sketch.theme_blob or "sveis" in sketch.theme_blob:
            argument = (
                f"Krav og praksis for {theme_txt} må leses sammen — ikke som isolerte fakta."
            )
        else:
            argument = (
                f"Korpuset peker på {theme_txt} som sentrale temaer som bør forklares "
                f"som en sammenhengende teknisk fortelling."
            )
    else:
        main_q = uq or f"What principles and constraints govern {theme_txt}?"
        outcome = "Shared design principles and clear open questions"
        if "emc" in sketch.theme_blob or "shield" in sketch.theme_blob:
            main_q = uq or (
                "What EMC constraints drive cable management and shielding in this corpus?"
            )
            argument = (
                "Installation method, zoning, and class selection matter as much as "
                "tray material for controlling electromagnetic interference."
            )
        else:
            argument = (
                f"The corpus centres on {theme_txt}; these themes should be told as one "
                f"technical argument, not a fact list."
            )

    aud = "engineering_management" if (audience or "").lower().startswith("manag") else (
        "field_engineer" if (audience or "").lower().startswith("field") else "engineer"
    )
    return DocumentIntent(
        purpose=dtype,
        audience=aud,
        main_question=main_q,
        main_argument=argument,
        desired_outcome=outcome,
        tone="technical_report",
    )


def _ground_thesis(
    sketch: CorpusSketch,
    intent: DocumentIntent,
    no: bool,
) -> tuple[str, bool]:
    """Thesis from argument + caption support. Mark provisional if thin."""
    caps = " ".join(sketch.sample_captions[:6]).lower()
    blob = sketch.theme_blob
    argument = (intent.main_argument or "").strip()

    # Strong domain match → thesis is grounded enough (not TED invention)
    strong = any(
        n in blob for n in (
            "emc", "shield", "electromagnetic", "cable", "tray", "weld", "sveis",
            "skjerm", "kabel",
        )
    )
    tokens = [
        t for t in re.findall(r"[A-Za-zÆØÅæøå]{4,}", argument.lower())
        if t not in (
            "that", "this", "with", "from", "have", "were", "their", "like", "much",
            "also", "som", "viktige", "like", "mater", "for", "begrense",
        )
    ]
    hits = sum(1 for t in tokens[:14] if t in blob or t in caps)
    provisional = not strong and hits < 2 and sketch.file_count > 0

    if argument and not provisional:
        return argument, False
    if argument and provisional:
        if no:
            thesis = (
                f"Basert på tilgjengelige kilder ser {sketch.title} ut til å dreie seg om "
                f"{', '.join(sketch.themes[:3]) or 'tekniske krav'}; "
                f"tesen under er foreløpig og bør bekreftes. {argument}"
            )
        else:
            thesis = (
                f"From available sources, {sketch.title} appears to centre on "
                f"{', '.join(sketch.themes[:3]) or 'technical requirements'}; "
                f"the following thesis is provisional. {argument}"
            )
        return thesis, True

    if no:
        thesis = (
            f"{sketch.title} krever en samlet lesning av {', '.join(sketch.themes[:3]) or 'kildene'} "
            f"— ikke en opplisting av enkeltfakta."
        )
    else:
        thesis = (
            f"{sketch.title} needs a coherent reading of "
            f"{', '.join(sketch.themes[:3]) or 'the sources'} — not a listing of isolated facts."
        )
    return thesis, True


def _arc_sections(
    sketch: CorpusSketch,
    intent: DocumentIntent,
    user_questions: list[str] | None,
    no: bool,
) -> list[NarrativeSection]:
    """Documentary arc: problem → why → understand → evidence/rules → standards → open."""
    theme_q = " ".join(sketch.themes[:3]) if sketch.themes else sketch.title
    blob = sketch.theme_blob
    out: list[NarrativeSection] = []

    # 1. Frame / problem (thesis)
    out.append(NarrativeSection(
        heading="Innledning" if no else "Introduction",
        purpose=(
            "Åpne med tesen og hvorfor leseren skal bry seg — ikke filtelling."
            if no else
            "Open with the thesis and why the reader should care — not a file count."
        ),
        role_in_argument="States the central claim the rest of the document supports.",
        retrieve_query=f"{sketch.title} {theme_q} overview purpose why problem",
        author_intent="frame",
        arc_beat="problem",
        kind="framing",
        optional=False,
    ))

    # 2. Why it matters (context)
    if any(n in blob for n in ("emc", "shield", "electromagnetic", "skjerm", "interference")):
        out.append(NarrativeSection(
            heading="Hvorfor EMC er en designbegrensning" if no else "Why EMC is a design constraint",
            purpose=(
                "Forklar hvorfor elektromagnetisk kompatibilitet ikke er et tilleggskrav, "
                "men en primær designbegrensning i dette materialet."
                if no else
                "Explain why electromagnetic compatibility is a primary design constraint "
                "in this material, not an afterthought."
            ),
            role_in_argument="Motivates the thesis: why the problem exists.",
            retrieve_query="EMC shielding attenuation interference electromagnetic why matters",
            author_intent="argue",
            arc_beat="context",
            kind="teach",
        ))
    elif sketch.themes:
        t = sketch.themes[0]
        out.append(NarrativeSection(
            heading=f"Hvorfor {t} betyr noe" if no else f"Why {t} matters",
            purpose=(
                f"Sett {t} i kontekst: hva står på spill for leseren?"
                if no else
                f"Put {t} in context: what is at stake for the reader?"
            ),
            role_in_argument="Motivates attention before details.",
            retrieve_query=f"{t} {theme_q} purpose why important",
            author_intent="argue",
            arc_beat="context",
            kind="teach",
        ))

    # 3. Concepts
    if any(n in blob for n in ("cable", "tray", "class", "klasse", "segregation", "kabel")):
        out.append(NarrativeSection(
            heading="Kabelklasser og separasjon" if no else "Cable classes and separation",
            purpose=(
                "Forklar hvorfor kabelklasser finnes og hvordan de endrer "
                "installasjonsstrategi — ikke bare list klasser."
                if no else
                "Explain why cable classes exist and how they change installation "
                "strategy — do not merely list classes."
            ),
            role_in_argument="Gives the conceptual toolkit the design rules use.",
            retrieve_query="cable class segregation separation distance between circuits",
            author_intent="explain",
            arc_beat="concepts",
            kind="teach",
        ))
    if any(n in blob for n in ("earth", "jord", "ground", "bonding", "zone", "sone")):
        out.append(NarrativeSection(
            heading="Soner, jording og bonding" if no else "Zones, earthing and bonding",
            purpose=(
                "Koble soner og jording til EMC-argumentet: hvordan begrenses støyveier?"
                if no else
                "Tie zones and earthing to the EMC argument: how are noise paths limited?"
            ),
            role_in_argument="Extends concepts into system-level practice.",
            retrieve_query="earthing grounding bonding zone equipotential EMC",
            author_intent="explain",
            arc_beat="concepts",
            kind="teach",
        ))
    if any(n in blob for n in ("weld", "sveis", "ndt")):
        out.append(NarrativeSection(
            heading="Sveising og kontroll" if no else "Welding and inspection",
            purpose=(
                "Forklar kravkjeden sveising → kontroll slik den fremgår av kildene."
                if no else
                "Explain the welding → inspection requirement chain as sources show it."
            ),
            role_in_argument="Core technical concepts for this corpus.",
            retrieve_query="welding NDT inspection procedure requirement",
            author_intent="explain",
            arc_beat="concepts",
            kind="teach",
        ))

    # 4. Design rules / engineering considerations
    if any(n in blob for n in ("install", "mount", "design", "shield", "tray", "emc")):
        out.append(NarrativeSection(
            heading="Tekniske hensyn og designregler" if no else "Engineering considerations",
            purpose=(
                "Trekk ut praktiske designregler og hensyn som følger av konseptene — "
                "anbefal der kildene støtter det."
                if no else
                "Pull practical design rules and considerations that follow from the "
                "concepts — recommend only where sources support it."
            ),
            role_in_argument="Turns understanding into what an engineer should do.",
            retrieve_query=f"{theme_q} installation design rule shielding practice recommendation",
            author_intent="recommend",
            arc_beat="rules",
            kind="teach",
        ))

    # User questions as targeted evidence beats
    for uq in (user_questions or [])[:3]:
        uq = (uq or "").strip()
        if not uq:
            continue
        out.append(NarrativeSection(
            heading=uq[:80],
            purpose=(
                f"Besvar spørsmålet som del av hovedargumentet: {intent.main_argument[:120]}"
                if no else
                f"Answer as part of the main argument: {intent.main_argument[:120]}"
            ),
            role_in_argument="Addresses a reader-specific question inside the arc.",
            retrieve_query=uq,
            author_intent="explain",
            arc_beat="evidence",
            kind="teach",
        ))

    # 5. Standards
    if sketch.has_standards or any(
        t in blob for t in ("standard", "iec", "ieee", "mil", "en ", "nek", "astm")
    ):
        out.append(NarrativeSection(
            heading="Standarder og referanser" if no else "Standards and references",
            purpose=(
                "Vis hvilke standarder som underbygger argumentet — id, rolle, kilde."
                if no else
                "Show which standards underpin the argument — id, role, source."
            ),
            role_in_argument="Anchors claims in recognised references.",
            retrieve_query=f"{theme_q} standard IEC IEEE EN MIL ASTM specification",
            author_intent="list",
            arc_beat="standards",
            kind="standards",
        ))

    # 6. Conclusion (short — Author writes only if some body existed; always plan it)
    out.append(NarrativeSection(
        heading="Oppsummering" if no else "Conclusion",
        purpose=(
            "Lukk dokumentet: gjenta tesen kort, hva som er etablert, hva som er åpent."
            if no else
            "Close the document: restate thesis briefly, what is established, what remains open."
        ),
        role_in_argument="Closes the argument; no new ungrounded claims.",
        retrieve_query=f"{sketch.title} {theme_q} summary recommendation",
        author_intent="conclude",
        arc_beat="conclusion",
        kind="teach",
        optional=True,
    ))

    # 7. Open + appendix
    if not (intent.audience or "").startswith("engineering_management"):
        out.append(NarrativeSection(
            heading="Åpne punkter" if no else "Open points",
            purpose="Korte ærlige hull — ikke dokumentets hovedperson." if no else
                    "Short honest gaps — not the personality of the document.",
            role_in_argument="Honesty about coverage limits.",
            retrieve_query="",
            author_intent="list",
            arc_beat="open",
            kind="gaps",
            optional=False,
        ))

    out.append(NarrativeSection(
        heading="Kilder" if no else "Sources",
        purpose="Appendix of cited files.",
        role_in_argument="Traceability for auditors.",
        retrieve_query="",
        author_intent="list",
        arc_beat="appendix",
        kind="appendix",
        optional=False,
    ))

    # Ensure at least one concept section if nothing theme-matched
    teach = [s for s in out if s.kind == "teach" and s.arc_beat in ("concepts", "context", "rules")]
    if len(teach) <= 1 and sketch.themes:
        t = sketch.themes[0]
        out.insert(2, NarrativeSection(
            heading=f"Om {t}" if no else f"On {t}",
            purpose=(
                f"Forklar hva korpuset faktisk sier om {t}, som del av hovedfortellingen."
                if no else
                f"Explain what the corpus actually says about {t}, as part of the main story."
            ),
            role_in_argument="Provides substance for the thesis.",
            retrieve_query=t,
            author_intent="explain",
            arc_beat="concepts",
            kind="teach",
        ))

    return out
