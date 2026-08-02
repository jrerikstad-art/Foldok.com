"""Photos that exist, offered against photo requirements that are open.

The engine reported a picture missing while the picture sat in the folder. Not a
retrieval failure — a scope one. ``PhotoCaptureResolver.can_handle`` asks only::

    return requirement.kind == "photo"

It never asks whether a photo already exists, because the gap engine's world is
``Document.entries`` and an indexed file never becomes one. So a photo
requirement is unmet by construction and the single offer is "go and take it",
which is an insulting thing to say to somebody who took it last week.

What this does **not** do is decide the match. Foldok should not conclude that
*this* photograph proves *that* requirement — that is the evidential line the
whole product is built on, and a confident wrong binding is worse than a capture
task. It ranks candidates, shows why each was suggested, and a person confirms.

The ranking is deliberately dull: caption and filename overlap with the
requirement's own words, plus the subject it belongs to. Dull is right here,
because the user is about to see every candidate anyway.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PHOTO_KINDS = ("photo", "image")
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}

STOP = {
    "the", "and", "for", "with", "photo", "photograph", "picture", "image", "bilde",
    "foto", "fotografi", "av", "og", "med", "som", "til", "der", "det", "den",
    "skal", "must", "shall", "each", "every", "hver", "hvert", "requirement", "krav",
}


@dataclass
class Candidate:
    file: str
    score: float
    reasons: tuple[str, ...] = ()
    caption: str = ""

    @property
    def name(self) -> str:
        return Path(self.file).name

    def explain(self, *, lang: str = "no") -> str:
        why = self.reasons[0] if self.reasons else ("ligger i mappen" if lang.startswith("no") else "in the folder")
        return f"{self.name} — {why}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file, "score": round(self.score, 3),
            "reasons": list(self.reasons), "caption": self.caption,
        }


@dataclass
class Offer:
    gap_id: str
    requirement_key: str
    title: str
    subject: str = ""
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def has_candidates(self) -> bool:
        return bool(self.candidates)

    def message(self, *, lang: str = "no") -> str:
        """What the user is asked. Never an assertion that the match is right."""
        if not self.candidates:
            return (
                f"{self.title}: fant ingen bilder i mappen som ser ut til å passe. "
                "Ta bildet, eller pek på en fil."
                if lang.startswith("no") else
                f"{self.title}: no photo in the folder looks like a match. "
                "Take it, or point at a file."
            )
        head = (
            f"{self.title}: {len(self.candidates)} bilde(r) i mappen kan passe — "
            "bekreft hvilket, eller ta et nytt."
            if lang.startswith("no") else
            f"{self.title}: {len(self.candidates)} photo(s) in the folder may match — "
            "confirm which, or take a new one."
        )
        return head + "\n" + "\n".join(
            f"  - {c.explain(lang=lang)}" for c in self.candidates[:5]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id, "requirement_key": self.requirement_key,
            "title": self.title, "subject": self.subject,
            "candidates": [c.to_dict() for c in self.candidates],
        }


def photos_in(index: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in index or []:
        path = str(entry.get("file") or "")
        if not path:
            continue
        kind = str(entry.get("kind") or "").lower()
        if kind in PHOTO_KINDS or Path(path).suffix.lower() in PHOTO_EXT:
            out.append(dict(entry))
    return out


def rank(
    photos: Sequence[Mapping[str, Any]],
    *,
    requirement_text: str,
    subject_label: str = "",
    minimum: float = 0.0,
) -> list[Candidate]:
    """Caption and filename overlap. Everything scores, because the user sees
    them all — a photo with no overlap is still a photo in the folder."""
    want = _terms(f"{requirement_text} {subject_label}")
    out: list[Candidate] = []

    for photo in photos:
        path = str(photo.get("file") or "")
        caption = str(photo.get("caption") or "")
        tags = " ".join(str(t) for t in (photo.get("content_tags") or []))
        have = _terms(f"{Path(path).stem} {caption} {tags}")
        shared = want & have

        score = 0.25 * len(shared)
        reasons: list[str] = []
        if shared:
            reasons.append("nevner " + ", ".join(sorted(shared)[:3]))
        if subject_label and _terms(subject_label) & have:
            score += 0.4
            reasons.append(f"knyttet til {subject_label}")
        if not reasons:
            reasons.append("ligger i prosjektmappen")

        if score >= minimum:
            out.append(Candidate(file=path, score=round(score, 3),
                                 reasons=tuple(reasons), caption=caption[:120]))

    out.sort(key=lambda c: (-c.score, c.name))
    return out


def offers_for(
    gaps: Iterable[Any],
    index: Iterable[Mapping[str, Any]],
    *,
    limit: int = 6,
) -> list[Offer]:
    """Open photo gaps, each with the photos already in the folder.

    Call this before offering a capture task, so "take this photo" is only ever
    said when there is genuinely nothing to point at.
    """
    photos = photos_in(index)
    out: list[Offer] = []
    for gap in gaps or []:
        requirement = getattr(gap, "requirement", None)
        if requirement is None or requirement.kind != "photo":
            continue
        if not getattr(gap, "open", True):
            continue
        subject = getattr(gap, "subject", None)
        label = (subject.label or subject.id) if subject is not None else ""
        text = " ".join(filter(None, [
            requirement.title, requirement.capture_prompt, requirement.description,
        ]))
        out.append(Offer(
            gap_id=gap.id,
            requirement_key=requirement.key,
            title=gap.title,
            subject=label,
            candidates=rank(photos, requirement_text=text, subject_label=label)[:limit],
        ))
    return out


def summary(offers: Sequence[Offer], *, lang: str = "no") -> str:
    with_any = [o for o in offers if o.has_candidates]
    if not offers:
        return ""
    if lang.startswith("no"):
        return (
            f"{len(with_any)} av {len(offers)} bildekrav har kandidater i mappen. "
            "Ingen er bundet automatisk — du bekrefter."
        )
    return (
        f"{len(with_any)} of {len(offers)} photo requirements have candidates in the "
        "folder. None is bound automatically — you confirm."
    )


def _terms(text: str) -> set[str]:
    return {
        w.lower() for w in re.findall(r"[A-Za-zÆØÅæøå0-9]{3,}", text or "")
    } - STOP
