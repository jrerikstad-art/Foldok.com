"""Content Director — decides what belongs in the story.

Project Intelligence → Content Director → Narrative Blueprint → Author → Renderer

Deterministic. The LLM fills slots this module opens; it does not invent the subject.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1

# Soft mapping from arc stage → section-title needles (generic, no project names).
_ARC_NEEDLES: dict[str, tuple[str, ...]] = {
    "purpose": ("purpose", "formål", "scope", "omfang", "introduction", "innledning"),
    "safety": ("safety", "sikker", "hazard", "fare", "warning", "advarsel"),
    "preparation": ("prepar", "forbered", "material", "tools", "utstyr"),
    "installation": ("install", "montage", "montering", "mount", "procedure", "prosedyre"),
    "verification": ("verif", "test", "commission", "kontroll", "måling", "accept"),
    "maintenance": ("maintain", "vedlikehold", "service", "drift"),
    "question": ("question", "spørsmål", "objective", "mål"),
    "theory": ("theory", "teori", "background", "bakgrunn"),
    "method": ("method", "metode"),
    "results": ("result", "resultat", "finding", "funn"),
    "discussion": ("discuss", "diskusjon", "conclus", "konklusjon"),
    "frame": ("identif", "scope", "purpose", "formål"),
    "basis": ("krav", "requirement", "standard", "condition", "forutset"),
    "body": ("install", "design", "system", "description", "beskriv"),
    "evidence": ("evidence", "dokument", "test", "måling", "observ"),
    "exception": ("avvik", "exception", "open", "åpen"),
    "close": ("handover", "overlever", "declar", "erklær", "ansvar", "responsib"),
}


@dataclass
class Coverage:
    evidence: float = 0.0
    figures: float = 0.0
    standards: float = 0.0
    warnings: float = 0.0
    open_questions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": round(self.evidence, 2),
            "figures": round(self.figures, 2),
            "standards": round(self.standards, 2),
            "warnings": round(self.warnings, 2),
            "open_questions": self.open_questions,
        }

    @property
    def weakest(self) -> str:
        scores = {
            "evidence": self.evidence,
            "figures": self.figures,
            "standards": self.standards,
            "warnings": self.warnings,
        }
        return min(scores, key=scores.get)


@dataclass
class DirectedSection:
    """One section clip on the composition timeline."""

    key: str
    title: str
    purpose: str = ""
    arc_stage: str = ""
    band: str = "body"
    status: str = "empty"  # empty | partial | complete
    asset_ids: list[str] = field(default_factory=list)
    fact_count: int = 0
    standard_ids: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    coverage: Coverage = field(default_factory=Coverage)
    relevance: str = "somewhat"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "purpose": self.purpose,
            "arc_stage": self.arc_stage,
            "band": self.band,
            "status": self.status,
            "asset_ids": list(self.asset_ids),
            "fact_count": self.fact_count,
            "standard_ids": list(self.standard_ids),
            "suggestions": list(self.suggestions),
            "coverage": self.coverage.to_dict(),
            "relevance": self.relevance,
        }


@dataclass
class ChecklistItem:
    key: str
    label: str
    done: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "label": self.label,
            "done": self.done, "detail": self.detail,
        }


@dataclass
class CompositionPlan:
    """Everything the Compose UI needs — Knowledge | Narrative | Preview data."""

    identity: dict[str, Any] = field(default_factory=dict)
    blueprint: dict[str, Any] = field(default_factory=dict)
    checklist: list[ChecklistItem] = field(default_factory=list)
    sections: list[DirectedSection] = field(default_factory=list)
    library: dict[str, Any] = field(default_factory=dict)
    knowledge: dict[str, Any] = field(default_factory=dict)
    overall_coverage: Coverage = field(default_factory=Coverage)
    ready_to_draft: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "identity": self.identity,
            "blueprint": self.blueprint,
            "checklist": [c.to_dict() for c in self.checklist],
            "sections": [s.to_dict() for s in self.sections],
            "library": self.library,
            "knowledge": self.knowledge,
            "overall_coverage": self.overall_coverage.to_dict(),
            "ready_to_draft": self.ready_to_draft,
            "notes": list(self.notes),
        }


def direct(
    index: Sequence[Mapping[str, Any]] | None,
    *,
    artifact: Mapping[str, Any] | None = None,
    template: Mapping[str, Any] | None = None,
    project_name: str = "",
    folder: str = "",
    existing_sections: Mapping[str, Any] | None = None,
    lang: str = "en",
) -> CompositionPlan:
    """Build a composition plan. No LLM. Identity first, then assets, then slots."""
    art = dict(artifact or {})
    tpl = dict(template or {})
    existing = dict(existing_sections or {})

    # --- Project Intelligence -------------------------------------------------
    blueprint = None
    identity_obj = None
    themes: list[str] = []
    ref_themes: list[str] = []
    try:
        from foldok_role import sketch_patch
        patch = sketch_patch(
            index or [], artifact=art, project_name=project_name, folder=folder,
        )
        themes = list(patch.get("themes") or [])
        idict = patch.get("identity") or {}
        # secondary/excluded already computed in identity block when present
        from foldok_identity import identify_project
        if idict.get("identity"):
            # rebuild from identify_project for a live object
            inn = idict["identity"]
            blueprint = identify_project(
                artifact=art,
                project_name=project_name,
                folder=folder,
                themes=list(inn.get("primary_topics") or themes),
                reference_themes=list(inn.get("secondary_topics") or [])
                + list(inn.get("excluded_topics") or []),
                audience=str(inn.get("audience") or ""),
                purpose=str(inn.get("purpose") or ""),
            )
        else:
            blueprint = identify_project(
                artifact=art, project_name=project_name, folder=folder, themes=themes,
            )
        identity_obj = blueprint.identity
    except Exception as exc:
        notes_early = [f"identity fallback: {exc}"]
        blueprint = None
        identity_obj = None
    else:
        notes_early = []

    # --- Evidence library -----------------------------------------------------
    library = None
    try:
        from foldok_evidence import build_library
        library = build_library(
            index,
            identity=identity_obj,
            project_terms=list(getattr(identity_obj, "project_terms", None) or []),
        )
    except Exception as exc:
        notes_early.append(f"evidence fallback: {exc}")
        library = None

    # --- Section timeline from template + arc ---------------------------------
    tpl_sections = sorted(
        list(tpl.get("sections") or []),
        key=lambda s: s.get("position", 99),
    )
    arc = tuple(getattr(blueprint, "preferred_arc", ()) or ()) if blueprint else ()
    directed: list[DirectedSection] = []

    for sec in tpl_sections:
        key = str(sec.get("key") or sec.get("id") or "").strip()
        if not key:
            continue
        title = str(sec.get("title") or sec.get("title_no") or key)
        purpose = str(sec.get("purpose") or sec.get("description") or "").strip()
        stage = _match_arc(title + " " + purpose + " " + key, arc)
        band = _band_for_stage(stage)

        facts_n, asset_ids, std_ids = _bind_evidence(
            title, purpose, stage, library, identity_obj,
        )
        # Count facts from index loosely matching section
        if facts_n == 0 and index:
            facts_n = _count_facts(index, title, purpose)

        cov = _coverage_for(
            facts_n, asset_ids, std_ids, title, purpose, library, existing.get(key),
        )
        status = _status(cov, existing.get(key))
        suggestions = _suggestions(cov, title, stage, lang)

        relevance = "relevant"
        if identity_obj is not None:
            try:
                from foldok_identity import score_offer
                relevance = score_offer(
                    {"key": key, "title": title, "band": band, "samples": [purpose]},
                    identity_obj,
                )
            except Exception:
                pass

        directed.append(DirectedSection(
            key=key,
            title=title,
            purpose=purpose or _default_purpose(stage, lang),
            arc_stage=stage,
            band=band,
            status=status,
            asset_ids=asset_ids,
            fact_count=facts_n,
            standard_ids=std_ids,
            suggestions=suggestions,
            coverage=cov,
            relevance=relevance,
        ))

    # Drop ignored sections from default narrative (user can still open template)
    kept = [s for s in directed if s.relevance != "ignore"]
    if not kept:
        kept = directed

    overall = _overall(kept)
    checklist = _checklist(identity_obj, blueprint, library, kept, art, overall, lang)
    ready = all(c.done for c in checklist[:4]) and overall.evidence >= 0.35

    knowledge = {
        "primary_topics": list(getattr(identity_obj, "primary_topics", None) or themes)[:8],
        "secondary_topics": list(getattr(identity_obj, "secondary_topics", None) or [])[:6],
        "excluded_topics": list(getattr(identity_obj, "excluded_topics", None) or [])[:6],
        "asset_summary": library.summary() if library else {},
        "source_count": len([e for e in (index or []) if e.get("file")]),
        "fact_total": sum(
            len(e.get("facts") or []) for e in (index or [])
        ),
    }

    notes = list(notes_early)
    if identity_obj and not identity_obj.confident:
        notes.append(
            "Sett dokumentets formål og tittel før OEM-PDFer får styre historien"
            if lang.startswith("no") else
            "Set document purpose and title before OEM PDFs drive the story"
        )

    return CompositionPlan(
        identity=identity_obj.to_dict() if identity_obj else {},
        blueprint=blueprint.to_dict() if blueprint else {},
        checklist=checklist,
        sections=kept,
        library=library.to_dict() if library else {},
        knowledge=knowledge,
        overall_coverage=overall,
        ready_to_draft=ready,
        notes=notes,
    )


# --- helpers ------------------------------------------------------------------

def _match_arc(blob: str, arc: Sequence[str]) -> str:
    low = blob.lower()
    for stage in arc:
        for needle in _ARC_NEEDLES.get(stage, (stage,)):
            if needle in low:
                return stage
    return arc[len(arc) // 2] if arc else "body"


def _band_for_stage(stage: str) -> str:
    if stage in ("purpose", "question", "frame", "scope"):
        return "frame"
    if stage in ("safety", "preparation", "theory", "basis", "method"):
        return "basis"
    if stage in ("evidence", "results", "verification", "observations"):
        return "evidence"
    if stage in ("exception", "open", "gaps"):
        return "exception"
    if stage in ("close", "discussion", "declaration", "maintenance", "actions"):
        return "close"
    return "body"


def _bind_evidence(title, purpose, stage, library, identity):
    if library is None:
        return 0, [], []
    topic = title
    if identity is not None:
        prim = list(getattr(identity, "primary_topics", None) or [])
        if prim:
            topic = prim[0]
    picks = library.for_topic(topic, limit=8)
    # Prefer stage match
    staged = [a for a in picks if a.installation_stage == stage] or picks
    asset_ids = [a.id for a in staged if a.type in ("photo", "drawing", "diagram", "table", "procedure")][:6]
    std_ids = [a.id for a in library.of("standard") if a.relevance != "ignore"][:4]
    facts_n = sum(a.facts_count for a in staged)
    return facts_n, asset_ids, std_ids


def _count_facts(index, title, purpose) -> int:
    needles = [w for w in (title + " " + purpose).lower().split() if len(w) > 3][:5]
    n = 0
    for e in index or []:
        for f in e.get("facts") or []:
            blob = f"{f.get('key', '')} {f.get('value', '')} {f.get('caption', '')}".lower()
            if any(w in blob for w in needles):
                n += 1
    return n


def _coverage_for(facts_n, asset_ids, std_ids, title, purpose, library, existing) -> Coverage:
    evidence = min(1.0, facts_n / 8.0) if facts_n else (0.4 if existing else 0.0)
    if existing and (existing.get("md") or existing.get("content")):
        evidence = max(evidence, 0.55)
    figures = min(1.0, len(asset_ids) / 3.0)
    standards = 1.0 if std_ids else (0.5 if "standard" not in (title + purpose).lower() else 0.0)
    warn_need = any(w in (title + purpose).lower() for w in ("safety", "sikker", "hazard", "warning"))
    warnings = 0.8 if not warn_need else (0.9 if facts_n else 0.2)
    open_q = 0
    if evidence < 0.4:
        open_q += 1
    if figures < 0.5 and any(w in (title + purpose).lower() for w in ("install", "montage", "procedure")):
        open_q += 1
    return Coverage(
        evidence=evidence, figures=figures, standards=standards,
        warnings=warnings, open_questions=open_q,
    )


def _status(cov: Coverage, existing) -> str:
    if existing and (existing.get("md") or existing.get("content")):
        if cov.evidence >= 0.7 and cov.figures >= 0.5:
            return "complete"
        return "partial"
    if cov.evidence >= 0.5 or cov.figures >= 0.5:
        return "partial"
    return "empty"


def _suggestions(cov: Coverage, title: str, stage: str, lang: str) -> list[str]:
    no = lang.startswith("no")
    out: list[str] = []
    if cov.figures < 0.7:
        out.append("Sett inn relevant bilde/tegning" if no else "Insert a relevant photo/drawing")
    if cov.evidence < 0.6:
        out.append("Knytt flere fakta til seksjonen" if no else "Bind more facts to this section")
    if cov.standards < 0.5 and stage in ("installation", "safety", "basis"):
        out.append("Legg til standardhenvisning" if no else "Add a standards reference")
    if cov.warnings < 0.5:
        out.append("Vurder advarsel / forutsetning" if no else "Consider a warning / precondition")
    if stage == "installation" and cov.evidence < 0.8:
        out.append("Sjekk jording / moment / rekkefølge" if no else "Check earthing / torque / sequence")
    return out[:4]


def _default_purpose(stage: str, lang: str) -> str:
    no = lang.startswith("no")
    table = {
        "purpose": ("Forklar formål og omfang", "State purpose and scope"),
        "safety": ("Sikkerhetskrav før arbeid", "Safety requirements before work"),
        "preparation": ("Forberedelser og materiell", "Preparation and materials"),
        "installation": ("Hvordan systemet installeres", "How the system is installed"),
        "verification": ("Kontroll og idriftsettelse", "Verification and commissioning"),
        "maintenance": ("Drift og vedlikehold", "Operation and maintenance"),
    }
    pair = table.get(stage, ("Dekk dette steget i fortellingen", "Cover this step in the narrative"))
    return pair[0 if no else 1]


def _overall(sections: Sequence[DirectedSection]) -> Coverage:
    if not sections:
        return Coverage()
    n = len(sections)
    return Coverage(
        evidence=sum(s.coverage.evidence for s in sections) / n,
        figures=sum(s.coverage.figures for s in sections) / n,
        standards=sum(s.coverage.standards for s in sections) / n,
        warnings=sum(s.coverage.warnings for s in sections) / n,
        open_questions=sum(s.coverage.open_questions for s in sections),
    )


def _checklist(identity, blueprint, library, sections, art, overall, lang) -> list[ChecklistItem]:
    no = lang.startswith("no")
    ident = identity
    title = (getattr(ident, "title_hint", None) or art.get("name") or "") if ident else art.get("name")
    purpose = getattr(ident, "purpose", "") if ident else art.get("purpose")
    audience = getattr(ident, "audience", "") if ident else art.get("audience")
    has_lib = bool(library and library.admissible())
    has_outline = bool(sections)
    has_assets = bool(library and (library.of("photo") or library.of("drawing")))
    has_draft = any(s.status != "empty" for s in sections)

    return [
        ChecklistItem("purpose", "Formål" if no else "Purpose",
                      done=bool(purpose or title), detail=str(purpose or title or "")[:80]),
        ChecklistItem("audience", "Målgruppe" if no else "Audience",
                      done=bool(audience) or bool(getattr(ident, "document_kind", None)),
                      detail=str(audience or getattr(ident, "document_kind", "") or "")),
        ChecklistItem("story", "Historie / identitet" if no else "Story / identity",
                      done=bool(ident and getattr(ident, "confident", False)),
                      detail=(getattr(ident, "document_kind", "") if ident else "")),
        ChecklistItem("outline", "Disposisjon" if no else "Outline",
                      done=has_outline, detail=f"{len(sections)} seksjoner"),
        ChecklistItem("assets", "Assets",
                      done=has_assets or has_lib,
                      detail=str((library.summary() if library else {}) or "")[:60]),
        ChecklistItem("requirements", "Krav" if no else "Requirements",
                      done=overall.standards >= 0.4 or overall.evidence >= 0.4,
                      detail=f"standards {overall.standards:.0%}"),
        ChecklistItem("evidence", "Evidens" if no else "Evidence",
                      done=overall.evidence >= 0.4,
                      detail=f"{overall.evidence:.0%}"),
        ChecklistItem("draft", "Utkast" if no else "Draft",
                      done=has_draft, detail="partial/complete" if has_draft else "empty"),
    ]
