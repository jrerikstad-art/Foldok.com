"""NarrativeBlueprint and ProjectIdentity.

The section market scores *availability*. This module scores *relevance to the
story*. A claim about a sensor OEM can be available and still Irrelevant when the
identity is an installation handover.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

Relevance = Literal["relevant", "somewhat", "background", "ignore"]

# Document-kind arcs — purpose, not decoration. Same folder, different stories.
ARCS: dict[str, tuple[str, ...]] = {
    "installation": (
        "purpose", "safety", "preparation", "installation",
        "verification", "maintenance",
    ),
    "research": (
        "question", "theory", "method", "results", "discussion",
    ),
    "inspection": (
        "scope", "observations", "findings", "nonconformities", "actions",
    ),
    "compliance": (
        "requirements", "evidence", "gaps", "declaration",
    ),
    "failure": (
        "incident", "evidence", "analysis", "root_cause", "corrective_actions",
    ),
    "decision": (
        "context", "options", "decision", "justification", "consequences",
    ),
    "generic": (
        "frame", "basis", "body", "evidence", "exception", "close",
    ),
}

# Soft signals from artifact type / name — never a named real project.
_KIND_RX: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"install|montage|montering|handover|overlever|as[- ]?built", re.I),
     "installation"),
    (re.compile(r"research|forskning|thesis|avhandling|studie|paper", re.I),
     "research"),
    (re.compile(r"inspect|befaring|tilsyn|audit|revisjon\s*rapport", re.I),
     "inspection"),
    (re.compile(r"complian|samsvar|conform|declaration|erklæring", re.I),
     "compliance"),
    (re.compile(r"failure|root\s*cause|avviksundersøk|incident|havari", re.I),
     "failure"),
    (re.compile(r"decision|beslutning|valg\s*og\s*begrunn", re.I),
     "decision"),
]


@dataclass
class ProjectIdentity:
    """What this work is fundamentally trying to communicate."""

    document_kind: str = "generic"
    audience: str = ""
    purpose: str = ""
    central_question: str = ""
    primary_topics: list[str] = field(default_factory=list)
    secondary_topics: list[str] = field(default_factory=list)
    excluded_topics: list[str] = field(default_factory=list)
    project_terms: list[str] = field(default_factory=list)
    title_hint: str = ""
    source: str = "inferred"  # artifact | project | inferred | asked
    confident: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "document_kind": self.document_kind,
            "audience": self.audience,
            "purpose": self.purpose,
            "central_question": self.central_question,
            "primary_topics": list(self.primary_topics),
            "secondary_topics": list(self.secondary_topics),
            "excluded_topics": list(self.excluded_topics),
            "project_terms": list(self.project_terms),
            "title_hint": self.title_hint,
            "source": self.source,
            "confident": self.confident,
            "notes": list(self.notes),
        }


@dataclass
class NarrativeBlueprint:
    """The arc the author must serve. Everything else consumes this."""

    identity: ProjectIdentity
    preferred_arc: tuple[str, ...] = ()
    required_sections: list[str] = field(default_factory=list)
    required_assets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "identity": self.identity.to_dict(),
            "preferred_arc": list(self.preferred_arc),
            "required_sections": list(self.required_sections),
            "required_assets": list(self.required_assets),
        }


def identify_project(
    *,
    artifact: Mapping[str, Any] | None = None,
    project_name: str = "",
    folder: str = "",
    themes: Sequence[str] | None = None,
    reference_themes: Sequence[str] | None = None,
    audience: str = "",
    purpose: str = "",
) -> NarrativeBlueprint:
    """Derive identity from what the user already named — never from vendor PDFs.

    ``themes`` should already be *role-weighted* (project material first).
    ``reference_themes`` are demoted to secondary / excluded unless they also
    appear in project themes.
    """
    art = dict(artifact or {})
    themes = [t for t in (themes or []) if t]
    ref_themes = [t for t in (reference_themes or []) if t]

    title = str(art.get("name") or art.get("title") or "").strip()
    art_type = str(art.get("artifact_type") or art.get("doc_type") or "").strip()
    blob = f"{title} {art_type} {project_name} {purpose}"

    kind = "generic"
    for rx, k in _KIND_RX:
        if rx.search(blob):
            kind = k
            break

    terms = _terms(project_name, folder, title)
    primary = list(themes[:6])
    # Reference-only themes must not become the story.
    primary_set = {p.lower() for p in primary}
    secondary: list[str] = []
    excluded: list[str] = []
    for t in ref_themes:
        if t.lower() in primary_set:
            continue
        if len(secondary) < 4:
            secondary.append(t)
        else:
            excluded.append(t)

    source = "inferred"
    confident = False
    notes: list[str] = []
    if title:
        source = "artifact"
        confident = True
        notes.append("title comes from the artifact the user named")
    elif project_name.strip():
        source = "project"
        confident = True
        notes.append("identity anchored on the project name, not file order")
    else:
        notes.append("ask for a document purpose before treating vendor PDFs as the subject")

    aud = (audience or str(art.get("audience") or "")).strip()
    pur = (purpose or str(art.get("purpose") or "")).strip()
    if not pur and kind == "installation":
        pur = "Install safely and hand over a verifiable system"
        if not aud:
            aud = "Field engineers"
    elif not pur and kind == "research":
        pur = "Answer a research question from the gathered sources"

    identity = ProjectIdentity(
        document_kind=kind,
        audience=aud,
        purpose=pur,
        central_question=str(art.get("research_question") or art.get("central_question") or "").strip(),
        primary_topics=primary,
        secondary_topics=secondary,
        excluded_topics=excluded,
        project_terms=terms,
        title_hint=title or project_name.strip() or (Path(folder).name if folder else ""),
        source=source,
        confident=confident,
        notes=notes,
    )
    return NarrativeBlueprint(
        identity=identity,
        preferred_arc=ARCS.get(kind, ARCS["generic"]),
        required_sections=_default_required(kind),
        required_assets=_default_assets(kind),
    )


def score_topic(topic: str, identity: ProjectIdentity) -> Relevance:
    """Where a topic sits relative to the story."""
    t = (topic or "").strip().lower()
    if not t:
        return "ignore"
    if any(t == x.lower() or t in x.lower() or x.lower() in t for x in identity.excluded_topics):
        return "ignore"
    if any(t == x.lower() or t in x.lower() or x.lower() in t for x in identity.primary_topics):
        return "relevant"
    if any(t == x.lower() or t in x.lower() or x.lower() in t for x in identity.secondary_topics):
        return "somewhat"
    # Reference-flavoured leftovers when we have a confident install/research identity.
    if identity.confident and identity.document_kind in ("installation", "inspection", "compliance"):
        return "background"
    return "somewhat"


def score_offer(
    offer: Mapping[str, Any] | Any,
    identity: ProjectIdentity,
) -> Relevance:
    """Score a section offer against identity using titles, keys, and samples."""
    if hasattr(offer, "to_dict"):
        offer = offer.to_dict()
    blob = " ".join([
        str(offer.get("key") or ""),
        str(offer.get("title") or ""),
        " ".join(str(s) for s in (offer.get("samples") or [])[:3]),
        " ".join(str(c) for c in (offer.get("claim_types") or [])),
    ]).lower()
    best: Relevance = "somewhat"
    rank = {"ignore": 0, "background": 1, "somewhat": 2, "relevant": 3}
    for topic in identity.primary_topics + identity.secondary_topics + identity.excluded_topics:
        if topic.lower() in blob:
            r = score_topic(topic, identity)
            if rank[r] > rank[best]:
                best = r
            if r == "ignore":
                return "ignore"
    # Frame/basis sections stay relevant for any confident identity.
    band = str(offer.get("band") or "")
    if identity.confident and band in ("frame", "basis", "close"):
        return "relevant" if best != "ignore" else best
    return best


def _default_required(kind: str) -> list[str]:
    if kind == "installation":
        return ["sec.practice", "sec.condition", "sec.sequence"]
    if kind == "research":
        return ["sec.hypothesis", "sec.quantity"]
    if kind == "failure":
        return ["sec.problem", "sec.justification"]
    return []


def _default_assets(kind: str) -> list[str]:
    if kind == "installation":
        return ["drawing", "photo", "procedure"]
    if kind == "inspection":
        return ["photo", "protocol"]
    return []


def _terms(project_name: str, folder: str, title: str) -> list[str]:
    out: list[str] = []
    for source in (project_name, title, Path(folder).name if folder else ""):
        for part in re.split(r"[\s_/.\-]+", source or ""):
            p = part.strip()
            if len(p) >= 3 and p.lower() not in {"the", "and", "for", "pdf", "doc"}:
                out.append(p)
    # Preserve order, drop dupes.
    seen: set[str] = set()
    uniq: list[str] = []
    for t in out:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq
