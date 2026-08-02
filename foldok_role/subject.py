"""What the document is about — decided by the artifact, weighted by role.

Two defects in ``plan.corpus_sketch``, both small and both consequential.

**The title comes from file sort order**::

    title = Path(usable[0].get("file") or "project").stem

Whatever sorts first names the document. Not the artifact, not the project — the
first filename alphabetically.

**Themes are one vote per tag per file**, so the densest-tagged document wins.
That is usually the vendor brochure, because a published technical document is
tagged confidently and a site photograph is not.

``weighted_themes`` keeps the same counting and multiplies each file's votes by
its role weight: project 1.0, unknown 0.5, reference 0.15. A reference document
still contributes — it should, it is where the shielding knowledge is — but
fifteen of them cannot outvote the project.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .classify import ROLE_WEIGHT, Classification, RoleReport, classify_index

STOP_TAGS = {"doc", "document", "pdf", "email", "file", "report", "product",
             "system", "guide", "information", "technical"}


@dataclass
class Subject:
    title: str
    source: str                       # artifact | project | folder | asked
    themes: list[str] = field(default_factory=list)
    theme_weights: dict[str, float] = field(default_factory=dict)
    confident: bool = True
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title, "source": self.source, "themes": list(self.themes),
            "confident": self.confident, "note": self.note,
            "theme_weights": {k: round(v, 2) for k, v in self.theme_weights.items()},
        }


def weighted_themes(
    index: Iterable[Mapping[str, Any]],
    roles: RoleReport | Mapping[str, Classification] | None = None,
    *,
    limit: int = 6,
    project_terms: Sequence[str] = (),
) -> tuple[list[str], dict[str, float]]:
    """Themes, with reference material informing rather than deciding."""
    entries = [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]
    if roles is None:
        roles = classify_index(entries, project_terms=project_terms)
    by_file = roles.by_file() if isinstance(roles, RoleReport) else dict(roles)

    scores: Counter = Counter()
    for entry in entries[:200]:
        weight = ROLE_WEIGHT.get(
            by_file.get(str(entry.get("file")), Classification(file="")).role, 0.5
        )
        for tag in entry.get("content_tags") or []:
            tag = str(tag).strip().lower().replace("-", " ")
            if len(tag) > 2 and tag not in STOP_TAGS:
                scores[tag] += weight

    ranked = scores.most_common(limit)
    return ([t for t, _ in ranked], {t: round(w, 3) for t, w in ranked})


def decide_subject(
    index: Iterable[Mapping[str, Any]],
    *,
    artifact: Mapping[str, Any] | None = None,
    project_name: str = "",
    folder: str = "",
    roles: RoleReport | None = None,
) -> Subject:
    """The artifact names the document. Never ``usable[0]``.

    If nothing names it, that is reported as a question rather than resolved by
    filename order — a document titled after whichever file sorted first is worse
    than one that asks.
    """
    entries = [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]
    roles = roles or classify_index(entries, project_terms=_terms(project_name, folder))
    themes, weights = weighted_themes(entries, roles)

    artifact_name = str((artifact or {}).get("name") or "").strip()
    if artifact_name:
        return Subject(artifact_name, "artifact", themes, weights)
    if project_name.strip():
        return Subject(project_name.strip(), "project", themes, weights)
    if folder.strip():
        return Subject(Path(folder).name, "folder", themes, weights,
                       note="taken from the folder name — set the artifact name to override")

    project_files = roles.of("project")
    guess = Path(project_files[0].file).stem if project_files else "Prosjekt"
    return Subject(
        guess, "asked", themes, weights, confident=False,
        note=(
            "nothing names this document — the artifact has no name and no project "
            "was given. Ask, rather than letting file order decide."
        ),
    )


def sketch_patch(
    index: Iterable[Mapping[str, Any]],
    *,
    artifact: Mapping[str, Any] | None = None,
    project_name: str = "",
    folder: str = "",
) -> dict[str, Any]:
    """Drop-in replacement values for ``CorpusSketch``.

    Returned as a dict so ``plan.corpus_sketch`` can adopt them without this
    package importing foldok_ask — the dependency should point one way.
    """
    entries = [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]
    roles = classify_index(entries, project_terms=_terms(project_name, folder))
    subject = decide_subject(entries, artifact=artifact, project_name=project_name,
                             folder=folder, roles=roles)
    captions = [
        str(e.get("caption") or "").strip()[:160]
        for e in entries
        if roles.by_file().get(str(e.get("file")), Classification("")).role != "reference"
        and e.get("caption")
    ]
    if not captions:                  # a folder of pure reference material
        captions = [str(e.get("caption") or "").strip()[:160]
                    for e in entries if e.get("caption")]
    return {
        "title": subject.title,
        "title_source": subject.source,
        "title_confident": subject.confident,
        "themes": subject.themes,
        "theme_weights": subject.theme_weights,
        "sample_captions": captions[:8],
        "file_count": len(entries),
        "project_files": len(roles.of("project")),
        "reference_files": len(roles.of("reference")),
        "role_note": roles.summary(),
    }


def _terms(project_name: str, folder: str) -> list[str]:
    out: list[str] = []
    for source in (project_name, Path(folder).name if folder else ""):
        for token in re.findall(r"[A-Za-zÆØÅæøå0-9]{4,}", source or ""):
            out.append(token)
    return out
