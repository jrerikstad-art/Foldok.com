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
    main_argument: str = "",
    blueprint=None,
) -> CriticReport:
    no = (lang or "no").startswith("no")
    report = CriticReport()
    body = [d for d in drafts if d.kind in ("teach", "standards", "framing") and d.prose]
    full = "\n".join(d.prose for d in drafts if d.prose)
    argument = (
        main_argument
        or (getattr(blueprint, "main_argument", "") if blueprint else "")
        or thesis
    )

    framing = next((d for d in drafts if d.kind == "framing"), None)
    if not framing or len((framing.prose or "").strip()) < 60:
        report.warnings.append(CriticWarning(
            "weak_lead",
            "Svak innledning — mangler tese/orientering." if no else
            "Weak introduction — missing thesis/orientation.",
        ))
    elif framing and re.match(
        r"(?i)^\s*.{0,40}\d+\s+(indekserte\s+)?filer",
        (framing.prose or "").split("\n")[0],
    ):
        report.warnings.append(CriticWarning(
            "file_count_lead",
            "Innledning ledes av filtelling." if no else "Introduction led by file count.",
        ))
    elif framing:
        words = len(re.findall(r"\S+", framing.prose or ""))
        if words < 100:
            report.warnings.append(CriticWarning(
                "thin_lead",
                "Innledning er tynn (<100 ord) — Lead Generator bør gi ½ side."
                if no else
                "Introduction is thin (<100 words) — Lead Generator should deliver ~½ page.",
            ))
        if re.search(r"(?i)comprehensive technical documentation", framing.prose or ""):
            report.warnings.append(CriticWarning(
                "abstract_paste",
                "Innledning limer PDF-abstract." if no else "Introduction pastes a PDF abstract.",
            ))

    if not any(d.arc_beat in ("conclusion", "close") or d.author_intent == "conclude"
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

    # Section serves main_argument?
    if argument:
        arg_toks = {
            t for t in re.findall(r"[a-zæøå]{4,}", argument.lower())
            if t not in ("that", "this", "with", "from", "have", "like", "much",
                         "also", "som", "viktige", "like", "mater", "begrense", "for")
        }
        for d in body:
            if d.kind == "framing" or not d.prose or d.gap:
                continue
            blob = f"{d.purpose} {d.prose}".lower()
            hits = sum(1 for t in arg_toks if t in blob)
            if arg_toks and hits == 0 and d.kind == "teach":
                report.warnings.append(CriticWarning(
                    "off_argument",
                    f"Seksjon «{d.heading}» ser ikke ut til å tjene hovedargumentet."
                    if no else
                    f"Section “{d.heading}” does not appear to serve the main argument.",
                    severity="info",
                ))

    # Same citation repeated heavily in body
    cite_counts: dict[str, int] = {}
    for m in re.finditer(r"\[(\d+)\]", full):
        cite_counts[m.group(1)] = cite_counts.get(m.group(1), 0) + 1
    for n, c in cite_counts.items():
        if c >= 4:
            report.warnings.append(CriticWarning(
                "cite_repetition",
                f"Sitat [{n}] gjentas {c} ganger — vurder å spre evidens."
                if no else
                f"Citation [{n}] repeats {c} times — consider spreading evidence.",
            ))
            break

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

    return report
