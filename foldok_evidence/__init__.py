"""Project evidence assets — first-class, fact-shaped, never decorations.

Distinct from ``foldok_assets`` (registry: symbols, templates, packs).
These are *this project's* photos, drawings, tables, and standards.

    lib = build_library(index, identity=blueprint.identity)
    lib.of("photo")           # admissible photos
    lib.for_topic("earthing") # scored against identity + topic
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

AssetType = Literal[
    "photo", "drawing", "diagram", "table", "standard",
    "procedure", "document", "other",
]
Relevance = Literal["relevant", "somewhat", "background", "ignore"]

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}
DRAWING_EXT = {".dwg", ".dxf", ".step", ".stp"}
TABLE_EXT = {".xlsx", ".xls", ".csv", ".tsv", ".ods"}

_STAGE_RX = [
    (re.compile(r"prepar|forbered|before|før\b", re.I), "preparation"),
    (re.compile(r"install|montage|montering|mount", re.I), "installation"),
    (re.compile(r"verif|test|commission|måling|befaring", re.I), "verification"),
    (re.compile(r"maintain|vedlikehold|service", re.I), "maintenance"),
    (re.compile(r"safety|sikker|hazard|fare", re.I), "safety"),
]


@dataclass
class EvidenceAsset:
    """One project asset the composer can bind to a section."""

    id: str
    type: AssetType
    file: str
    caption: str = ""
    depicts: str = ""
    confidence: float = 0.5
    relevance: Relevance = "somewhat"
    engineering_domain: str = ""
    installation_stage: str = ""
    components: list[str] = field(default_factory=list)
    role: str = "unknown"
    tags: list[str] = field(default_factory=list)
    facts_count: int = 0

    @property
    def name(self) -> str:
        return Path(self.file).name

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "file": self.file,
            "caption": self.caption,
            "depicts": self.depicts,
            "confidence": round(self.confidence, 2),
            "relevance": self.relevance,
            "engineering_domain": self.engineering_domain,
            "installation_stage": self.installation_stage,
            "components": list(self.components),
            "role": self.role,
            "tags": list(self.tags),
            "facts_count": self.facts_count,
        }


@dataclass
class EvidenceLibrary:
    assets: list[EvidenceAsset] = field(default_factory=list)
    excluded: list[dict[str, str]] = field(default_factory=list)

    def of(self, *types: str) -> list[EvidenceAsset]:
        wanted = {t.lower() for t in types}
        return [a for a in self.assets if a.type in wanted]

    def admissible(self) -> list[EvidenceAsset]:
        return [a for a in self.assets if a.relevance != "ignore"]

    def for_topic(self, topic: str, *, limit: int = 12) -> list[EvidenceAsset]:
        t = (topic or "").lower()
        scored: list[tuple[int, EvidenceAsset]] = []
        for a in self.admissible():
            blob = " ".join([a.depicts, a.caption, a.engineering_domain, " ".join(a.tags)]).lower()
            hit = 2 if t and t in blob else 0
            hit += {"relevant": 3, "somewhat": 1, "background": 0}.get(a.relevance, 0)
            if a.role == "project":
                hit += 1
            scored.append((hit, a))
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [a for _, a in scored[:limit]]

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for a in self.assets:
            out[a.type] = out.get(a.type, 0) + 1
        out["excluded"] = len(self.excluded)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "summary": self.summary(),
            "assets": [a.to_dict() for a in self.assets],
            "excluded": list(self.excluded),
        }


def build_library(
    index: Sequence[Mapping[str, Any]] | None,
    *,
    identity: Any = None,
    project_terms: Sequence[str] = (),
) -> EvidenceLibrary:
    """Build evidence assets from the project index. Deterministic."""
    entries = [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]

    # Prefer foldok_select curation so sales material stays out.
    excluded: list[dict[str, str]] = []
    curated_files: set[str] | None = None
    try:
        from foldok_select import build_context
        terms = list(project_terms or [])
        if identity is not None:
            terms = list(getattr(identity, "project_terms", None) or terms)
        ctx = build_context(entries, project_terms=terms)
        curated_files = {a.file for a in ctx.all()}
        excluded = [ex.to_dict() for ex in ctx.excluded]
    except Exception:
        curated_files = None

    roles: dict[str, str] = {}
    try:
        from foldok_role import classify_index
        terms = list(project_terms or [])
        if identity is not None:
            terms = list(getattr(identity, "project_terms", None) or terms)
        report = classify_index(entries, project_terms=terms)
        roles = {c.file: c.role for c in report.classifications}
    except Exception:
        pass

    assets: list[EvidenceAsset] = []
    for i, e in enumerate(entries):
        path = str(e.get("file") or "")
        if curated_files is not None and path not in curated_files:
            continue
        role = roles.get(path, "unknown")
        if role == "ignore":
            excluded.append({"file": path, "reason": "role ignore", "role": "ignore"})
            continue

        asset = _from_entry(e, i, role=role)
        asset.relevance = _score_relevance(asset, identity)
        if asset.relevance == "ignore" and role == "reference":
            # Keep in library as background — director may still cite standards.
            if asset.type != "standard":
                asset.relevance = "background"
        assets.append(asset)

    return EvidenceLibrary(assets=assets, excluded=excluded)


def _from_entry(entry: Mapping[str, Any], idx: int, *, role: str) -> EvidenceAsset:
    path = str(entry.get("file") or "")
    name = Path(path).name
    caption = str(entry.get("caption") or "").strip()
    tags = [str(t) for t in (entry.get("content_tags") or []) if t]
    hints = [str(h).lower() for h in (entry.get("doc_role_hints") or [])]
    facts = entry.get("facts") or []
    kind = str(entry.get("kind") or "").lower()
    ext = Path(path).suffix.lower()

    atype: AssetType = "document"
    if kind == "photo" or ext in IMAGE_EXT:
        atype = "photo"
        if any(h in " ".join(hints + tags + [caption]).lower()
               for h in ("drawing", "tegning", "plan", "layout")):
            atype = "drawing"
    elif ext in DRAWING_EXT or "drawing" in hints or "tegning" in hints:
        atype = "drawing"
    elif "diagram" in hints or "skjema" in " ".join(tags).lower():
        atype = "diagram"
    elif ext in TABLE_EXT or "test_report" in hints:
        atype = "table"
    elif "standard" in hints or re.search(r"\b(en|iec|iso|nek)\s*\d", caption, re.I):
        atype = "standard"
    elif "procedure" in caption.lower() or "prosedyre" in caption.lower():
        atype = "procedure"

    depicts = caption or name
    # Prefer a short engineering reading of the caption.
    if caption and len(caption) > 20:
        depicts = caption[:160]

    domain = ""
    for t in tags[:3]:
        domain = t
        break

    stage = ""
    blob = f"{caption} {' '.join(tags)} {' '.join(hints)}"
    for rx, st in _STAGE_RX:
        if rx.search(blob):
            stage = st
            break

    components = [t for t in tags if t.lower() not in {"doc", "pdf", "photo", "image"}][:6]
    conf = 0.55
    if caption:
        conf += 0.15
    if facts:
        conf += 0.1
    if role == "project":
        conf += 0.1

    return EvidenceAsset(
        id=f"A{idx + 1:03d}",
        type=atype,
        file=path,
        caption=caption,
        depicts=depicts,
        confidence=min(0.95, conf),
        role=role,
        tags=tags,
        facts_count=len(facts) if isinstance(facts, list) else 0,
        engineering_domain=domain,
        installation_stage=stage,
        components=components,
    )


def _score_relevance(asset: EvidenceAsset, identity: Any) -> Relevance:
    if identity is None:
        return "somewhat" if asset.role != "reference" else "background"
    try:
        from foldok_identity import score_topic
        topics = list(getattr(identity, "primary_topics", None) or [])
        blob = " ".join([asset.depicts, asset.caption, " ".join(asset.tags)]).lower()
        best: Relevance = "background" if asset.role == "reference" else "somewhat"
        rank = {"ignore": 0, "background": 1, "somewhat": 2, "relevant": 3}
        for topic in topics:
            if topic.lower() in blob:
                r = score_topic(topic, identity)
                if rank[r] > rank[best]:
                    best = r
        for topic in getattr(identity, "excluded_topics", None) or []:
            if topic.lower() in blob and topic.lower() not in " ".join(topics).lower():
                return "ignore"
        if asset.type == "standard":
            return "somewhat" if best == "ignore" else best
        if asset.role == "project" and best == "background":
            return "somewhat"
        return best
    except Exception:
        return "somewhat"
