"""Narrative layer — Document Brain before Author writes.

Knowledge answers "what do we know?"; NarrativeBlueprint answers
"what story explains this best and why each section exists?";
Author writes with continuity bridges; Validator binds evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .plan import CorpusSketch, OutlineSection, SectionKind, corpus_sketch

AuthorIntent = Literal["explain", "argue", "specify", "recommend", "frame", "conclude", "list"]
ArcBeat = Literal[
    "frame", "problem", "context", "concepts", "evidence", "rules",
    "standards", "open", "conclusion", "close", "appendix",
]

_BEAT_TO_ARC_ID = {
    "frame": "frame",
    "problem": "frame",
    "context": "concepts",
    "concepts": "concepts",
    "evidence": "evidence",
    "rules": "rules",
    "standards": "standards",
    "open": "open",
    "conclusion": "close",
    "close": "close",
}


@dataclass
class DocumentIntent:
    """Direction for the whole document — story before facts."""
    purpose: str = "topic_brief"
    audience: str = "engineer"
    main_question: str = ""
    main_argument: str = ""
    desired_outcome: str = ""
    reader_should_leave_with: str = ""
    tone: str = "technical_report"
    thesis_provisional: bool = False

    def to_dict(self) -> dict:
        return {
            "purpose": self.purpose,
            "audience": self.audience,
            "main_question": self.main_question,
            "main_argument": self.main_argument,
            "desired_outcome": self.desired_outcome,
            "reader_should_leave_with": self.reader_should_leave_with,
            "tone": self.tone,
            "thesis_provisional": self.thesis_provisional,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "DocumentIntent":
        d = d or {}
        return cls(
            purpose=d.get("purpose") or "topic_brief",
            audience=d.get("audience") or "engineer",
            main_question=d.get("main_question") or "",
            main_argument=d.get("main_argument") or "",
            desired_outcome=d.get("desired_outcome") or "",
            reader_should_leave_with=d.get("reader_should_leave_with") or "",
            tone=d.get("tone") or "technical_report",
            thesis_provisional=bool(d.get("thesis_provisional")),
        )


@dataclass
class ArcStep:
    """One beat in the document argument — why this section exists."""
    id: str
    purpose: str
    heading: str = ""
    role_in_argument: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "purpose": self.purpose,
            "heading": self.heading,
            "role_in_argument": self.role_in_argument,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "ArcStep":
        d = d or {}
        return cls(
            id=d.get("id") or "",
            purpose=d.get("purpose") or "",
            heading=d.get("heading") or "",
            role_in_argument=d.get("role_in_argument") or "",
        )


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
    arc_id: str = ""
    proposed: bool = False  # foldok_volume — corpus-widened; safe to delete
    volume_evidence: list[dict] = field(default_factory=list)

    def resolved_arc_id(self) -> str:
        return self.arc_id or _BEAT_TO_ARC_ID.get(self.arc_beat, self.arc_beat)

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
            "arc_id": self.resolved_arc_id(),
            "kind": self.kind,
            "optional": self.optional,
            "proposed": self.proposed,
            "volume_evidence": list(self.volume_evidence or []),
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "NarrativeSection":
        d = d or {}
        return cls(
            heading=d.get("heading") or "",
            purpose=d.get("purpose") or "",
            role_in_argument=d.get("role_in_argument") or "",
            retrieve_query=d.get("retrieve_query") or "",
            author_intent=d.get("author_intent") or "explain",  # type: ignore[arg-type]
            arc_beat=d.get("arc_beat") or "concepts",  # type: ignore[arg-type]
            kind=d.get("kind") or "teach",  # type: ignore[arg-type]
            optional=bool(d.get("optional", True)),
            arc_id=d.get("arc_id") or "",
            proposed=bool(d.get("proposed")),
            volume_evidence=list(d.get("volume_evidence") or []),
        )


@dataclass
class NarrativeBlueprint:
    """Document Brain — the whole generate path must obey this."""
    title: str
    reader: str
    main_question: str
    main_argument: str
    reader_should_leave_with: str
    thesis: str
    arc: list[ArcStep] = field(default_factory=list)
    sections: list[NarrativeSection] = field(default_factory=list)
    provisional: bool = False
    purpose: str = "topic_brief"
    sketch: CorpusSketch | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "reader": self.reader,
            "main_question": self.main_question,
            "main_argument": self.main_argument,
            "reader_should_leave_with": self.reader_should_leave_with,
            "thesis": self.thesis,
            "arc": [a.to_dict() for a in self.arc],
            "sections": [s.to_dict() for s in self.sections],
            "provisional": self.provisional,
            "purpose": self.purpose,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "NarrativeBlueprint":
        d = d or {}
        return cls(
            title=d.get("title") or "",
            reader=d.get("reader") or "engineer",
            main_question=d.get("main_question") or "",
            main_argument=d.get("main_argument") or "",
            reader_should_leave_with=d.get("reader_should_leave_with") or "",
            thesis=d.get("thesis") or "",
            arc=[ArcStep.from_dict(a) for a in (d.get("arc") or [])],
            sections=[NarrativeSection.from_dict(s) for s in (d.get("sections") or [])],
            provisional=bool(d.get("provisional")),
            purpose=d.get("purpose") or "topic_brief",
        )

    def to_plan(self) -> "NarrativePlan":
        intent = DocumentIntent(
            purpose=self.purpose,
            audience=self.reader,
            main_question=self.main_question,
            main_argument=self.main_argument,
            desired_outcome=self.reader_should_leave_with,
            reader_should_leave_with=self.reader_should_leave_with,
            thesis_provisional=self.provisional,
        )
        return NarrativePlan(
            title=self.title,
            intent=intent,
            thesis=self.thesis,
            arc=[a.id for a in self.arc],
            sections=list(self.sections),
            sketch=self.sketch,
            blueprint=self,
        )


@dataclass
class NarrativePlan:
    """Planner output; serialises to NarrativeBlueprint for persistence."""
    title: str
    intent: DocumentIntent
    thesis: str
    arc: list[str] = field(default_factory=list)
    sections: list[NarrativeSection] = field(default_factory=list)
    sketch: CorpusSketch | None = None
    blueprint: NarrativeBlueprint | None = None
    volume_note: str = ""  # foldok_volume coverage summary

    def to_outline(self) -> list[OutlineSection]:
        return [s.to_outline() for s in self.sections]

    def as_blueprint(self) -> NarrativeBlueprint:
        if self.blueprint is not None:
            return self.blueprint
        leave = (
            self.intent.reader_should_leave_with
            or self.intent.desired_outcome
            or self.thesis
        )
        steps: list[ArcStep] = []
        seen_ids: set[str] = set()
        for s in self.sections:
            if s.kind == "appendix" or s.arc_beat == "appendix":
                continue
            aid = s.resolved_arc_id()
            if aid in seen_ids and aid not in ("concepts", "evidence"):
                continue
            if aid not in seen_ids:
                seen_ids.add(aid)
            steps.append(ArcStep(
                id=aid,
                purpose=s.purpose,
                heading=s.heading,
                role_in_argument=s.role_in_argument,
            ))
        bp = NarrativeBlueprint(
            title=self.title,
            reader=self.intent.audience,
            main_question=self.intent.main_question,
            main_argument=self.intent.main_argument or self.thesis,
            reader_should_leave_with=leave,
            thesis=self.thesis,
            arc=steps,
            sections=list(self.sections),
            provisional=self.intent.thesis_provisional,
            purpose=self.intent.purpose,
            sketch=self.sketch,
        )
        self.blueprint = bp
        return bp

    def to_dict(self) -> dict:
        d = {
            "title": self.title,
            "intent": self.intent.to_dict(),
            "thesis": self.thesis,
            "arc": list(self.arc),
            "sections": [s.to_dict() for s in self.sections],
            "blueprint": self.as_blueprint().to_dict(),
        }
        if self.volume_note:
            d["volume_note"] = self.volume_note
        return d


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
    """Build DocumentIntent + thesis + arc from corpus coverage."""
    sketch = corpus_sketch(index, artifact=artifact)
    no = (lang or "no").lower().startswith("no")
    dtype = (document_type or "topic_brief").strip().lower()
    title = sketch.title or ("Prosjekt" if no else "Project")

    intent = intent_override or _suggest_intent(sketch, dtype, audience, user_questions, no)
    thesis, provisional = _ground_thesis(sketch, intent, no)
    intent.thesis_provisional = provisional
    intent.main_argument = intent.main_argument or thesis
    if not intent.reader_should_leave_with:
        intent.reader_should_leave_with = _leave_with(intent, no)

    sections = _arc_sections(sketch, intent, user_questions, no)
    volume_note = ""
    try:
        from foldok_volume import analyse, widen
        claims = _claims_from_index(index)
        # Critical: framing/meta retrieve_query dumps every theme (theme_q), which
        # made _covered_by claim Innledning already covers "separation"/"cable"/…
        # — so justified() was always empty and the document never grew.
        outline = _outline_for_volume(sections)
        report = analyse(claims, outline)
        volume_note = report.summary(lang=lang)
        existing = {s.heading.lower() for s in sections}
        # Insert proposed sections before conclusion / open / appendix
        insert_at = len(sections)
        for i, s in enumerate(sections):
            if s.arc_beat in ("conclusion", "close", "open", "appendix") or s.kind in ("gaps", "appendix"):
                insert_at = i
                break
        extra: list[NarrativeSection] = []
        for row in widen(outline, report):
            if not row.get("proposed"):
                continue
            title = str(row.get("title") or row.get("key") or "").strip()
            if not title or title.lower() in existing:
                continue
            existing.add(title.lower())
            theme = str(row.get("query") or row.get("theme") or title)
            # Drop filler themes the grammar filter still lets through ("punkt", "graders")
            if len(theme) < 8 or theme.lower() in {
                "punkt", "graders", "kabler", "skal", "utføres", "krever", "angitt",
            }:
                continue
            evidence = list(row.get("evidence") or [])
            if len(evidence) < 3:
                continue
            quotes = " ".join(
                str(e.get("quote") or "")[:80] for e in evidence[:4] if isinstance(e, dict)
            )
            extra.append(NarrativeSection(
                heading=title,
                purpose=str(row.get("purpose") or f"Material in the folder about {theme}"),
                role_in_argument=(
                    "Udekket materiale i mappen — slett seksjonen hvis du ikke trenger den."
                    if no else
                    "Uncovered corpus material — delete the section if you do not need it."
                ),
                retrieve_query=f"{title} {theme} {quotes}"[:400],
                author_intent="explain",
                arc_beat="evidence",
                kind="teach",
                # Must be authored (not silently omitted). User deletes in the editor.
                optional=False,
                proposed=True,
                volume_evidence=evidence,
            ))
        if extra:
            sections[insert_at:insert_at] = extra
            volume_note = (
                f"{volume_note} · +{len(extra)} seksjon(er) lagt til"
                if no else
                f"{volume_note} · +{len(extra)} section(s) added"
            )
    except Exception:
        pass

    for s in sections:
        if not s.arc_id:
            s.arc_id = _BEAT_TO_ARC_ID.get(s.arc_beat, s.arc_beat)

    arc_labels = []
    seen = set()
    for s in sections:
        aid = s.resolved_arc_id()
        if aid not in seen and s.arc_beat not in ("appendix",):
            arc_labels.append(aid)
            seen.add(aid)

    plan = NarrativePlan(
        title=title,
        intent=intent,
        thesis=thesis,
        arc=arc_labels,
        sections=sections,
        sketch=sketch,
        volume_note=volume_note,
    )
    plan.as_blueprint()
    return plan


def _outline_for_volume(sections: list[NarrativeSection]) -> list[dict]:
    """Outline terms for coverage analysis — without theme-stuffed framing queries.

    Framing retrieve_query includes every sketch theme, so every corpus theme
    looked "already covered" and widen() never added sections.
    """
    out: list[dict] = []
    for s in sections:
        meta = (
            s.kind in ("framing", "gaps", "appendix")
            or s.arc_beat in ("frame", "conclusion", "close", "open", "appendix")
        )
        if meta:
            out.append({
                "key": s.heading,
                "title": s.heading,
                "purpose": "",
                "query": "",
            })
        else:
            # Title + short purpose only — not the full retrieve_query theme dump
            out.append({
                "key": s.heading,
                "title": s.heading,
                "purpose": (s.purpose or "")[:160],
                "query": s.heading,
            })
    return out


def _claims_from_index(index) -> list[dict]:
    """Claim-shaped rows for foldok_volume — prefer foldok_claims, else facts/captions."""
    out: list[dict] = []
    try:
        from foldok_claims import claims_from_index
        for c in claims_from_index(index or [], min_confidence=0.35):
            text = (
                getattr(c, "text", None)
                or getattr(c, "text_no", None)
                or (c.get("text") if isinstance(c, dict) else None)
                or ""
            )
            src = (
                getattr(c, "source", None)
                or getattr(c, "file", None)
                or getattr(c, "file_id", None)
                or (c.get("source") if isinstance(c, dict) else None)
                or "?"
            )
            text = str(text).strip()
            if len(text) >= 8:
                out.append({
                    "text": text,
                    "source": str(src),
                    "type": str(getattr(c, "type", None) or getattr(c, "kind", None) or "claim"),
                })
    except Exception:
        pass
    if len(out) >= 12:
        return out
    for e in index or []:
        src = str(e.get("file") or "?")
        if e.get("kind") == "skipped" or not e.get("file"):
            continue
        for f in e.get("facts") or []:
            if not isinstance(f, dict):
                continue
            text = f"{f.get('key') or ''}: {f.get('value') or ''}".strip(": ").strip()
            if len(text) >= 8:
                out.append({"text": text, "source": src, "type": "fact"})
        cap = str(e.get("caption") or "").strip()
        if len(cap) >= 12:
            out.append({"text": cap, "source": src, "type": "caption"})
        for t in e.get("content_tags") or []:
            tag = str(t).strip()
            if len(tag) >= 5:
                out.append({"text": tag, "source": src, "type": "tag"})
    return out


def plan_blueprint(document_type: str = "topic_brief", index=None, **kwargs) -> NarrativeBlueprint:
    """NarrativeBlueprint the generate path must obey."""
    return plan_narrative(document_type, index, **kwargs).as_blueprint()


def propose_arc_expansion(
    blueprint: NarrativeBlueprint,
    chip: str,
    *,
    lang: str = "no",
) -> ArcStep | None:
    """Expand-chip to a proposed new arc step (user-confirmed; not auto-written)."""
    no = (lang or "no").startswith("no")
    c = (chip or "").strip().lower()
    if not c:
        return None
    if any(x in c for x in ("class", "klasse", "matrix", "matrise")):
        return ArcStep(
            id="concepts",
            purpose=(
                "Legg inn en kabelklasse-matrise som del av begrepssteget."
                if no else
                "Add a cable-class matrix as part of the concepts beat."
            ),
            heading="Kabelklassematris" if no else "Cable class matrix",
            role_in_argument="Makes segregation rules concrete for the reader.",
        )
    if any(x in c for x in ("standard", "50174", "iec")):
        return ArcStep(
            id="standards",
            purpose=(
                "Utvid standardsteget med navngitt rolle i hovedargumentet."
                if no else
                "Expand the standards beat with a named role in the main argument."
            ),
            heading=chip[:80],
            role_in_argument="Anchors the argument in a specific reference.",
        )
    return ArcStep(
        id="evidence",
        purpose=(
            f"Utvid fortellingen med: {chip[:120]}"
            if no else
            f"Expand the narrative with: {chip[:120]}"
        ),
        heading=chip[:80],
        role_in_argument="User-confirmed expansion inside the existing argument.",
    )


def _leave_with(intent: DocumentIntent, no: bool) -> str:
    arg = (intent.main_argument or "").strip()
    if no:
        if "EMC" in arg or "installasjons" in arg.lower() or "elektromagnet" in arg.lower():
            return "Behandle EMC som en systemdesignbegrensning, ikke et katalogvalg."
        return intent.desired_outcome or "Sitte igjen med én klar teknisk tråd — ikke en filliste."
    if "installation" in arg.lower() or "EMC" in arg or "shield" in arg.lower():
        return "Treat EMC as a system design constraint, not a catalog option."
    return intent.desired_outcome or "Leave with one clear technical thread — not a file list."


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
        leave = "Sitte igjen med én klar teknisk tråd — ikke en filliste."
        if "emc" in sketch.theme_blob or "shield" in sketch.theme_blob:
            main_q = uq or "Hva styrer EMC-ytelse i tray-baserte kabelsystemer?"
            argument = (
                "Installasjonsmetode, soner og klassevalg er like viktige som materialvalg "
                "for å begrense elektromagnetisk påvirkning."
            )
            leave = "Behandle EMC som en systemdesignbegrensning, ikke et katalogvalg."
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
        leave = "Leave with one clear technical thread — not a file list."
        if "emc" in sketch.theme_blob or "shield" in sketch.theme_blob:
            main_q = uq or "What drives EMC performance in tray-based cable systems?"
            argument = (
                "Installation method, zoning, and class selection matter as much as "
                "tray material for controlling electromagnetic interference."
            )
            leave = "Treat EMC as a system design constraint, not a catalog option."
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
        reader_should_leave_with=leave,
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
            "Lead Generator: orientér leseren i ½–1 side — korpusets karakter, "
            "arbeidstese, veikart og grenser. Ikke filtelling som historie."
            if no else
            "Lead Generator: orient the reader in ½–1 page — corpus character, "
            "working thesis, roadmap and limits. Not a file-count story."
        ),
        role_in_argument="States the central claim the rest of the document supports.",
        retrieve_query=(
            f"{sketch.title} {theme_q} overview purpose scope introduction "
            f"abstract executive EMC requirements why problem"
        ),
        author_intent="frame",
        arc_beat="frame",
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
