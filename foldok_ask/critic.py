"""Lightweight Document Critic — warnings before publish, not a score product."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .author_doc import SectionDraft


@dataclass
class CriticWarning:
    code: str
    message: str
    severity: str = "warn"  # info | warn


@dataclass
class CriticReport:
    warnings: list[CriticWarning] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(w.severity == "warn" for w in self.warnings)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "warnings": [
                {"code": w.code, "message": w.message, "severity": w.severity}
                for w in self.warnings
            ],
        }


FINDINGS_VOICE = re.compile(
    r"(?i)\b(the following findings|according to the documents|"
    r"the corpus contains|kildene beskriver også|påstand\s*\|\s*verdi)\b"
)


def review_document(
    drafts: list[SectionDraft],
    *,
    thesis: str = "",
    lang: str = "no",
) -> CriticReport:
    no = (lang or "no").startswith("no")
    report = CriticReport()
    body = [d for d in drafts if d.kind in ("teach", "standards", "framing") and d.prose]
    full = "\n".join(d.prose for d in drafts if d.prose)

    framing = next((d for d in drafts if d.kind == "framing"), None)
    if not framing or len((framing.prose or "").strip()) < 60:
        report.warnings.append(CriticWarning(
            "weak_lead",
            "Svak innledning — mangler tese/orientering." if no else
            "Weak introduction — missing thesis/orientation.",
        ))
    elif framing and re.match(
        r"(?i)^\s*.{0,40}\d+\s+indekserte filer",
        (framing.prose or "").split("\n")[0],
    ):
        report.warnings.append(CriticWarning(
            "file_count_lead",
            "Innledning ledes av filtelling." if no else "Introduction led by file count.",
        ))

    if not any(d.arc_beat == "conclusion" or d.author_intent == "conclude"
               or (d.heading or "").lower() in ("oppsummering", "conclusion")
               for d in drafts if d.prose):
        report.warnings.append(CriticWarning(
            "missing_conclusion",
            "Mangler oppsummering." if no else "Missing conclusion.",
            severity="info",
        ))

    if FINDINGS_VOICE.search(full):
        report.warnings.append(CriticWarning(
            "findings_voice",
            "Funn-/korpusstemme i prosa." if no else "Findings/corpus voice in prose.",
        ))

    # Citation coverage on body sections
    for d in body:
        if d.kind == "standards":
            continue
        if d.prose and "[" not in d.prose and d.kind == "teach":
            report.warnings.append(CriticWarning(
                "uncited_section",
                f"Seksjon «{d.heading}» mangler [n]-sitat." if no else
                f"Section “{d.heading}” lacks [n] citation.",
                severity="info",
            ))

    # Repetition heuristic: same 40-char span twice
    spans = re.findall(r".{40,80}", full)
    seen = set()
    for sp in spans:
        key = sp.lower().strip()
        if key in seen:
            report.warnings.append(CriticWarning(
                "repetition",
                "Mulig gjentatt formulering." if no else "Possible repeated wording.",
                severity="info",
            ))
            break
        seen.add(key)

    if thesis and framing and thesis.split(".")[0][:40].lower() not in (framing.prose or "").lower():
        # Soft — thesis may be paraphrased
        pass

    return report
