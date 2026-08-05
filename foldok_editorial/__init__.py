"""Editorial QA — review assembled prose; never rewrite.

See EDITORIAL_QA.md. Deterministic checks only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

SCHEMA_VERSION = 1

Severity = Literal["info", "warn", "fail"]

# Continuity spam — section-isolated models invent these.
_TRANSITION_RX = re.compile(
    r"(?im)^\s*(?:"
    r"Etter\s+dette|Videre|Neste(?:\s+steg)?|Til\s+slutt|"
    r"Having\s+established|Next(?:\s+step)?|Finally|Furthermore|"
    r"In\s+addition|Moreover|As\s+a\s+next\s+step"
    r")\b"
)

_NO_WORD_RX = re.compile(
    r"(?i)\b("
    r"og|eller|ikke|dette|denne|skal|må|bør|med|til|fra|som|"
    r"installasjon|kabel|jording|krav|seksjonen|dokumentet|"
    r"følgende|beskriver|viser|består"
    r")\b"
)
_EN_WORD_RX = re.compile(
    r"(?i)\b("
    r"the|and|or|not|this|shall|must|with|from|that|which|"
    r"installation|cable|earthing|requirement|section|document|"
    r"following|describes|shows|consists"
    r")\b"
)

_SLUG_LINE_RX = re.compile(
    r"(?im)^\s*[A-Za-z][\w]*(?:_[A-Za-z0-9]+)+\.?\s*(?:\[\d+\]\s*)*\s*$"
)
_KEY_VALUE_RX = re.compile(
    r"(?im)^\s*[A-Za-z][\w]*(?:_[A-Za-z0-9]+)+\s*:\s+\S"
)


@dataclass
class Finding:
    code: str
    message: str
    severity: Severity = "warn"
    section: str = ""
    action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "section": self.section,
            "action": self.action,
        }


@dataclass
class EditorialReport:
    language: str = "en"
    findings: list[Finding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(f.severity == "fail" for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": self.ok,
            "language": self.language,
            "metrics": dict(self.metrics),
            "findings": [f.to_dict() for f in self.findings],
        }

    def report_text(self) -> str:
        lines = [
            f"EDITORIAL QA [{'PASS' if self.ok else 'FAIL'}] lang={self.language}",
            f"  metrics: {self.metrics}",
        ]
        for f in self.findings:
            loc = f" [{f.section}]" if f.section else ""
            lines.append(f"  [{f.severity}] {f.code}{loc}: {f.message}")
            if f.action:
                lines.append(f"         → {f.action}")
        return "\n".join(lines)


def _norm_lang(lang: str | None) -> str:
    s = (lang or "en").strip().lower()
    if s.startswith("n"):
        return "no"
    return "en"


def _iter_sections(sections: Mapping[str, Any] | Sequence[Any] | None):
    """Yield (heading, prose) from doc.sections dict or draft-like objects."""
    if not sections:
        return
    if isinstance(sections, Mapping):
        for key, sec in sections.items():
            if key.startswith("_"):
                continue
            if isinstance(sec, Mapping):
                yield str(key), str(sec.get("md") or sec.get("prose") or "")
            else:
                yield str(key), str(getattr(sec, "prose", "") or getattr(sec, "md", "") or "")
        return
    for d in sections:
        heading = (
            getattr(d, "heading", None)
            or (d.get("heading") if isinstance(d, Mapping) else None)
            or ""
        )
        prose = (
            getattr(d, "prose", None)
            or (d.get("prose") or d.get("md") if isinstance(d, Mapping) else None)
            or ""
        )
        yield str(heading), str(prose)


def review_markdown(
    text: str,
    *,
    language: str = "en",
    sections: Mapping[str, Any] | Sequence[Any] | None = None,
    assets_available: int | None = None,
    assets_used: int | None = None,
) -> EditorialReport:
    """Review full draft markdown (and optional per-section bodies)."""
    lang = _norm_lang(language)
    report = EditorialReport(language=lang)
    body = text or ""
    sec_list = list(_iter_sections(sections)) if sections is not None else []
    if not sec_list and body:
        # Split assembled draft on ## headings
        parts = re.split(r"(?m)^##\s+", body)
        for part in parts[1:]:
            lines = part.splitlines()
            heading = (lines[0] if lines else "").strip()
            prose = "\n".join(lines[1:]) if lines else ""
            sec_list.append((heading, prose))

    # --- Repeated transitions -------------------------------------------------
    opener_hits: dict[str, list[str]] = {}
    for heading, prose in sec_list:
        for m in _TRANSITION_RX.finditer(prose or ""):
            token = re.sub(r"\s+", " ", m.group(0).strip().lower())
            opener_hits.setdefault(token, []).append(heading or "(body)")
    repeated = 0
    for token, where in opener_hits.items():
        count_in_body = body.lower().count(token)
        if len(where) >= 2 or count_in_body >= 2:
            repeated += max(len(where), 2 if count_in_body >= 2 else 1)
            report.findings.append(Finding(
                code="repeated_transition",
                severity="fail",
                section=where[0],
                message=(
                    f"Transition «{token}» appears across sections: {', '.join(where[:4])}."
                ),
                action="Strip openers; future Transition Engine owns continuity.",
            ))
    # Also catch spam inside a single blob (stacked Etter dette)
    stacked = len(re.findall(r"(?i)(?:Etter\s+dette\s*[—–\-]+\s*){2,}", body))
    if stacked:
        repeated += stacked
        report.findings.append(Finding(
            code="stacked_bridge",
            severity="fail",
            message=f"Stacked «Etter dette —» run found ({stacked}).",
            action="Run scrub_authored_prose / regenerate with scrub-v4+.",
        ))

    # --- Slug / Key:value body ------------------------------------------------
    slug_n = 0
    for heading, prose in sec_list or [("(document)", body)]:
        for line in (prose or "").splitlines():
            ln = line.strip()
            if _SLUG_LINE_RX.match(ln) or _KEY_VALUE_RX.match(ln):
                slug_n += 1
                report.findings.append(Finding(
                    code="slug_as_body",
                    severity="fail",
                    section=heading,
                    message=f"Topic key / fact printer as prose: {ln[:80]}",
                    action="Omit line or write one grounded sentence + cites.",
                ))
    # Cap finding spam
    if slug_n > 6:
        report.findings = [f for f in report.findings if f.code != "slug_as_body"][:3] + [
            Finding(
                code="slug_as_body",
                severity="fail",
                message=f"{slug_n} snake_case / Key:value body lines.",
                action="Ban slug emission in author; scrub on assemble.",
            )
        ]

    # --- Language mix --------------------------------------------------------
    mixed = 0
    sentences = re.split(r"(?<=[.!?])\s+", body)
    for sent in sentences:
        s = sent.strip()
        if len(s) < 20:
            continue
        no_n = len(_NO_WORD_RX.findall(s))
        en_n = len(_EN_WORD_RX.findall(s))
        if lang == "en" and no_n >= 3 and no_n > en_n:
            mixed += 1
        elif lang == "no" and en_n >= 3 and en_n > no_n:
            mixed += 1
    if mixed:
        report.findings.append(Finding(
            code="mixed_language",
            severity="fail" if mixed >= 3 else "warn",
            message=f"{mixed} sentence(s) look like the wrong document language ({lang}).",
            action="Enforce DocumentContext.language on every author stage.",
        ))

    # --- Assets ---------------------------------------------------------------
    unused = 0
    if assets_available is not None and assets_used is not None:
        unused = max(0, int(assets_available) - int(assets_used))
        if assets_available > 0 and assets_used == 0:
            report.findings.append(Finding(
                code="unused_assets",
                severity="warn",
                message=(
                    f"{assets_available} asset(s) in corpus; none used in the draft."
                ),
                action="Bind figures via foldok_select — do not claim photos are missing.",
            ))

    total_words = len(re.findall(r"\S+", body))
    report.metrics = {
        "repeated_phrases": repeated,
        "slug_body_lines": slug_n,
        "mixed_language": mixed,
        "unused_relevant_assets": unused,
        "word_count": total_words,
        "language_consistency": (
            round(1.0 - (mixed / max(len(sentences), 1)), 3) if sentences else 1.0
        ),
        "sections_reviewed": len(sec_list),
    }
    return report


def review_doc_state(
    state: Mapping[str, Any] | None,
    *,
    language: str | None = None,
    assembled_md: str = "",
    assets_available: int | None = None,
    assets_used: int | None = None,
) -> EditorialReport:
    """Convenience: pull lang + sections from .feltdok_state-like dict."""
    st = state or {}
    lang = language or st.get("lang") or "en"
    sections = ((st.get("doc") or {}).get("sections") or {})
    return review_markdown(
        assembled_md,
        language=str(lang),
        sections=sections,
        assets_available=assets_available,
        assets_used=assets_used,
    )
