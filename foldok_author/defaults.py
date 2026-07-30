"""Map Foldok section keys / document species → authoring intents (0.86).

Procedural intents (install, hazard, troubleshoot, process) are *named*
so Foldok can refuse generation and keep the fact ledger / AUTHOR placeholders
instead of inventing fluent steps.
"""
from __future__ import annotations

from typing import Any

from .model import AUTHORED_NOT_GENERATED, Fact

# Section-key heuristics (templates may override via writing_rules.intent)
SECTION_INTENT: dict[str, str] = {
    "system_overview": "summarize_system",
    "identification": "identify_product",
    "spec_overview": "specify_parameters",
    "bom": "specify_parameters",
    "safety": "warn_hazard",
    "hazards": "warn_hazard",
    "installation": "instruct_procedure",
    "install_sequence": "instruct_procedure",
    "commissioning": "instruct_procedure",
    "control_commissioning": "instruct_procedure",
    "operation": "instruct_procedure",
    "maintenance": "instruct_procedure",
    "troubleshooting": "troubleshoot",
    "fault_finding": "troubleshoot",
    "declaration": "declare_conformity",
    "conformity": "declare_conformity",
    "evidence": "record_evidence",
    "test_results": "record_evidence",
    "doc_control": "record_evidence",
    "method": "explain_process",
    "process": "explain_process",
    "assumptions": "describe_component",
    "requirements": "describe_component",
}

SPECIES_DEFAULT: dict[str, str] = {
    "narrative": "describe_component",
    "form_fill": "record_evidence",
    "sketch": "summarize_system",
}


def resolve_intent(
    section: dict[str, Any] | None = None,
    *,
    sec_key: str = "",
    document_species: str = "",
) -> str:
    """Profile/template may set writing_rules.intent; else section key / species."""
    section = section or {}
    wr = section.get("writing_rules") or {}
    explicit = (wr.get("intent") or section.get("intent") or "").strip()
    if explicit:
        return explicit

    key = (sec_key or section.get("section_key") or "").strip().lower()
    if key in SECTION_INTENT:
        return SECTION_INTENT[key]

    for needle, intent in (
        ("install", "instruct_procedure"),
        ("safety", "warn_hazard"),
        ("hazard", "warn_hazard"),
        ("troubleshoot", "troubleshoot"),
        ("fault", "troubleshoot"),
        ("declare", "declare_conformity"),
        ("conform", "declare_conformity"),
        ("overview", "summarize_system"),
        ("identif", "identify_product"),
        ("param", "specify_parameters"),
        ("spec", "specify_parameters"),
        ("bom", "specify_parameters"),
        ("test", "record_evidence"),
        ("evidence", "record_evidence"),
        ("process", "explain_process"),
        ("method", "explain_process"),
    ):
        if needle in key:
            return intent

    species = (document_species or "").strip().lower()
    if species in SPECIES_DEFAULT:
        return SPECIES_DEFAULT[species]
    return "describe_component"


def is_authored_not_generated(intent_id: str) -> bool:
    return intent_id in AUTHORED_NOT_GENERATED


def facts_from_foldok(
    fact_ids: list[str],
    by_id: dict[str, dict[str, Any]],
) -> list[Fact]:
    """Adapt Foldok index fact dicts into Authoring Fact objects."""
    out: list[Fact] = []
    for fid in fact_ids:
        raw = by_id.get(fid) or {}
        if not raw and fid not in by_id:
            continue
        val = raw.get("value")
        if val is None:
            val = raw.get("text") or raw.get("snippet") or ""
        cite = ""
        src = raw.get("source") or raw.get("file") or ""
        if isinstance(src, dict):
            cite = str(src.get("file") or src.get("id") or "")
        elif src:
            cite = str(src).split("/").pop().split("\\").pop()
        label = (
            raw.get("label")
            or (raw.get("key") or "").replace("_", " ")
            or str(fid)
        )
        out.append(
            Fact(
                id=str(fid),
                key=str(raw.get("key") or fid),
                value=val,
                unit=str(raw.get("unit") or ""),
                label=str(label),
                citation=str(cite or ""),
            )
        )
    return out


def inject_fact_citations(prose: str, facts: list[Fact]) -> str:
    """Append {{fact:id}} after the first occurrence of each fact value (Foldok postprocess)."""
    text = prose or ""
    for f in facts:
        marker = "{{fact:" + f.id + "}}"
        if marker in text:
            continue
        needle = f"{f.value} {f.unit}".strip() if f.unit else str(f.value)
        if not needle or needle not in text:
            needle = str(f.value)
        if needle and needle in text:
            text = text.replace(needle, f"{needle} {marker}", 1)
    return text
