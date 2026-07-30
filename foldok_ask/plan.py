"""Document Planner — outline what the document should teach.

Plans from intent + corpus sketch + optional user questions.
Not from fact-key inventory or domain YAML packs.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


SectionKind = Literal["framing", "teach", "standards", "gaps", "appendix"]


@dataclass
class OutlineSection:
    heading: str
    purpose: str
    retrieve_query: str
    kind: SectionKind
    optional: bool = False  # omit entirely if retrieval empty (else one gap line)

    def to_dict(self) -> dict:
        return {
            "heading": self.heading,
            "purpose": self.purpose,
            "retrieve_query": self.retrieve_query,
            "kind": self.kind,
            "optional": self.optional,
        }


@dataclass
class CorpusSketch:
    file_count: int = 0
    title: str = ""
    themes: list[str] = field(default_factory=list)
    sample_captions: list[str] = field(default_factory=list)
    has_standards: bool = False
    theme_blob: str = ""

    def to_dict(self) -> dict:
        return {
            "file_count": self.file_count,
            "title": self.title,
            "themes": list(self.themes),
            "has_standards": self.has_standards,
        }


STD_HINT_RX = re.compile(
    r"(?i)\b(EN|IEC|ISO|NEK|MIL[-\s]?STD|IEEE|ASTM|UL|HD|NEMA|NS)\s*[\dA-Z]"
)


def corpus_sketch(index, *, artifact=None) -> CorpusSketch:
    art = artifact or {}
    usable = [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]
    title = str(art.get("name") or "").strip()
    if not title and usable:
        title = Path(usable[0].get("file") or "project").stem

    tag_c: Counter = Counter()
    captions = []
    has_std = False
    for e in usable[:100]:
        for t in e.get("content_tags") or []:
            t = str(t).strip().lower().replace("-", " ")
            if t and len(t) > 2 and t not in ("doc", "document", "pdf", "email"):
                tag_c[t] += 1
        cap = (e.get("caption") or "").strip()
        if cap:
            captions.append(cap[:160])
            if STD_HINT_RX.search(cap):
                has_std = True
        for f in e.get("facts") or []:
            blob = f"{f.get('key') or ''} {f.get('value') or ''}"
            if STD_HINT_RX.search(blob):
                has_std = True

    themes = [t for t, _ in tag_c.most_common(6)]
    if not themes:
        bag: Counter = Counter()
        for cap in captions[:40]:
            for tok in re.findall(r"[A-Za-zÆØÅæøå]{5,}", cap.lower()):
                if tok not in ("document", "report", "product", "system", "guide"):
                    bag[tok] += 1
        themes = [t for t, _ in bag.most_common(5)]

    blob = " ".join(themes) + " " + " ".join(captions[:12]).lower()
    return CorpusSketch(
        file_count=len(usable),
        title=title or "Prosjekt",
        themes=themes,
        sample_captions=captions[:8],
        has_standards=has_std,
        theme_blob=blob,
    )


def plan_document(
    intent: str = "topic_brief",
    index=None,
    *,
    artifact=None,
    audience: str = "engineer",
    user_questions: list[str] | None = None,
    lang: str = "no",
) -> list[OutlineSection]:
    """Build outline. Prefer NarrativePlan (thesis + arc); this returns OutlineSections."""
    intent = (intent or "topic_brief").strip().lower()
    if intent in ("install_manual", "installation_manual"):
        sketch = corpus_sketch(index, artifact=artifact)
        no = (lang or "no").lower().startswith("no")
        theme_q = " ".join(sketch.themes[:3]) if sketch.themes else (sketch.title or "project")
        return _plan_install(sketch, theme_q, user_questions, no)
    # Default: narrative layer owns the story
    from .narrative import plan_narrative
    return plan_narrative(
        intent, index, artifact=artifact, audience=audience,
        user_questions=user_questions, lang=lang,
    ).to_outline()


def _plan_topic_brief(sketch, theme_q, user_questions, audience, no: bool) -> list[OutlineSection]:
    mgr = (audience or "").lower().startswith("manag")
    out: list[OutlineSection] = []

    out.append(OutlineSection(
        heading="Innledning" if no else "Introduction",
        purpose=(
            "Orientér leseren: hva prosjektet/korpuset handler om, hvorfor det betyr noe, "
            "og hva briefen dekker — naturlig prosa, ikke filtelling."
            if no else
            "Orient the reader: what this corpus is about, why it matters, and what the brief covers."
        ),
        retrieve_query=f"{sketch.title} {theme_q} overview purpose scope why",
        kind="framing",
    ))

    # Theme-led teaching sections (generic probes from sketch — not fixed EMC YAML)
    teach_specs = _teach_specs_from_sketch(sketch, no)
    for heading, purpose, query in teach_specs:
        out.append(OutlineSection(
            heading=heading,
            purpose=purpose,
            retrieve_query=query,
            kind="teach",
            optional=True,
        ))

    # User questions become teach sections
    for uq in (user_questions or [])[:4]:
        uq = (uq or "").strip()
        if not uq:
            continue
        out.append(OutlineSection(
            heading=uq[:80],
            purpose=("Besvar spørsmålet med forklart prosa fra kilder."
                     if no else "Answer the question in explained prose from sources."),
            retrieve_query=uq,
            kind="teach",
            optional=True,
        ))

    if sketch.has_standards or any(
        t in sketch.theme_blob for t in ("standard", "iec", "ieee", "mil", "en ", "nek")
    ):
        out.append(OutlineSection(
            heading="Standarder og referanser" if no else "Standards and references",
            purpose=(
                "List relevante standarder med én linjes rolle — ikke bare filnavn."
                if no else
                "List relevant standards with a one-line role — not bare filenames."
            ),
            retrieve_query=f"{theme_q} standard IEC IEEE EN MIL ASTM specification",
            kind="standards",
            optional=True,
        ))

    if not mgr:
        out.append(OutlineSection(
            heading="Åpne punkter" if no else "Open points",
            purpose=("Korte, ærlige hull — ikke dokumentets hovedperson."
                     if no else "Short honest gaps — not the personality of the document."),
            retrieve_query="",
            kind="gaps",
        ))

    out.append(OutlineSection(
        heading="Kilder" if no else "Sources",
        purpose="Appendix of cited files.",
        retrieve_query="",
        kind="appendix",
    ))
    return out


def _teach_specs_from_sketch(sketch: CorpusSketch, no: bool) -> list[tuple[str, str, str]]:
    """Pick 2–4 teaching angles from themes present in the index."""
    blob = sketch.theme_blob
    specs = []

    def add(needles, heading_no, heading_en, purpose_no, purpose_en, query):
        if any(n in blob for n in needles):
            specs.append((
                heading_no if no else heading_en,
                purpose_no if no else purpose_en,
                query,
            ))

    add(
        ("emc", "electromagnetic", "shield", "skjerm"),
        "Hvorfor EMC og skjerming betyr noe",
        "Why EMC and shielding matter",
        "Forklar praktisk betydning av EMC/skjerming i dette korpuset.",
        "Explain the practical meaning of EMC/shielding in this corpus.",
        "EMC shielding attenuation electromagnetic interference why matters",
    )
    add(
        ("cable", "tray", "kabel", "class", "klasse", "segregation"),
        "Kabelklasser og separasjon",
        "Cable classes and separation",
        "Forklar klasse-/separasjonsprinsipper slik kildene beskriver dem.",
        "Explain class/separation principles as the sources describe them.",
        "cable class segregation separation distance between circuits",
    )
    add(
        ("earth", "jord", "ground", "bonding"),
        "Jording og bonding",
        "Earthing and bonding",
        "Oppsummer jording-/bondingpraksis fra kildene.",
        "Summarise earthing/bonding practice from the sources.",
        "earthing grounding bonding equipotential",
    )
    add(
        ("install", "mount", "monter", "safety", "sikker"),
        "Installasjon og forsiktighet",
        "Installation and cautions",
        "Praktiske installasjons- og sikkerhetspunkter fra kildene.",
        "Practical installation and safety points from the sources.",
        "installation mounting safety caution clearance",
    )
    add(
        ("weld", "sveis", "ndt"),
        "Sveising og kontroll",
        "Welding and inspection",
        "Krav og praksis for sveising/NDT slik de fremgår.",
        "Welding/NDT requirements as they appear in sources.",
        "welding NDT inspection procedure",
    )

    # Always at least one theme teach if we have themes but nothing matched
    if not specs and sketch.themes:
        t = sketch.themes[0]
        specs.append((
            f"Om {t}" if no else f"On {t}",
            (f"Forklar hva kildene sier om {t}."
             if no else f"Explain what the sources say about {t}."),
            t,
        ))
    return specs[:4]


def _plan_install(sketch, theme_q, user_questions, no: bool) -> list[OutlineSection]:
    out = [
        OutlineSection(
            heading="Formål" if no else "Purpose",
            purpose="What this install covers.",
            retrieve_query=f"{sketch.title} installation purpose scope",
            kind="framing",
        ),
        OutlineSection(
            heading="Forberedelser" if no else "Preparation",
            purpose="Preconditions and materials.",
            retrieve_query=f"{theme_q} preparation tools materials before install",
            kind="teach",
            optional=True,
        ),
        OutlineSection(
            heading="Montering" if no else "Mounting",
            purpose="Mounting steps from sources only.",
            retrieve_query=f"{theme_q} mounting installation steps procedure",
            kind="teach",
            optional=True,
        ),
        OutlineSection(
            heading="Sikkerhet" if no else "Safety",
            purpose="Warnings present in sources.",
            retrieve_query=f"{theme_q} safety warning caution hazard",
            kind="teach",
            optional=True,
        ),
        OutlineSection(
            heading="Åpne punkter" if no else "Open points",
            purpose="Gaps.",
            retrieve_query="",
            kind="gaps",
        ),
        OutlineSection(
            heading="Kilder" if no else "Sources",
            purpose="Appendix.",
            retrieve_query="",
            kind="appendix",
        ),
    ]
    for uq in (user_questions or [])[:3]:
        if uq.strip():
            out.insert(-2, OutlineSection(
                heading=uq.strip()[:80],
                purpose="User question.",
                retrieve_query=uq.strip(),
                kind="teach",
                optional=True,
            ))
    return out
