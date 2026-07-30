"""WORKORDER_0.27 A/D — rung-3 drafting, curated templates, document shells."""
from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone

import doc_state as ds


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


INSTALL_MANUAL_RE = re.compile(
    r"\b(installation\s+manual|installasjonsmanual|installasjons\s+manual|"
    r"installasjonsveiledning|installation\s+guide|"
    r"i need a(?:n)?\s+installation\s+manual|installasjon\s+manual|"
    r"lag\s+(?:en\s+)?installasjonsmanual|trenger\s+(?:en\s+)?installasjonsmanual)\b",
    re.I,
)

COMMISSIONING_RE = re.compile(
    r"\b(idriftsettelsesrapport|idrifts[øo]ttelsesrapport|commissioning\s+report)\b",
    re.I,
)


def is_installation_manual_ask(text: str) -> bool:
    return bool(INSTALL_MANUAL_RE.search(text or ""))


def is_commissioning_ask(text: str) -> bool:
    return bool(COMMISSIONING_RE.search(text or ""))


INSPECTION_RE = re.compile(
    r"\b(inspeksjonssjekkliste|inspection\s+checklist|kontrollskjema|"
    r"egenkontroll|multipoint\s+inspection)\b",
    re.I,
)


def is_inspection_checklist_ask(text: str) -> bool:
    return bool(INSPECTION_RE.search(text or ""))


RESEARCH_ASK_RE = re.compile(
    r"\b(phd|ph\.?d|forskning|research\s+project|forskningsprosjekt|"
    r"thesis|avhandling|progress\s+report|prosjektrapport|"
    r"selficon|selficom|preregistration)\b",
    re.I,
)


def is_research_ask(text: str) -> bool:
    return bool(RESEARCH_ASK_RE.search(text or ""))


TOPIC_BRIEF_ASK_RE = re.compile(
    r"\b(temabrief|topic\s*brief|fagpakke|emc\s*brief|sone(?:r)?|"
    r"kabelklasse|cable\s*class|earthing\s*brief|sitert\s*pakke)\b",
    re.I,
)

SPEC_COHERENCE_ASK_RE = re.compile(
    r"\b(spesifikasjonsgjennomgang|spec\s*coherence|konflikt(?:er)?\s*mellom\s*standard)\b",
    re.I,
)


def is_topic_brief_ask(text: str) -> bool:
    return bool(TOPIC_BRIEF_ASK_RE.search(text or ""))


def is_spec_coherence_ask(text: str) -> bool:
    return bool(SPEC_COHERENCE_ASK_RE.search(text or ""))


def match_curated_template(text: str, caps: dict) -> dict | None:
    if is_installation_manual_ask(text):
        for t in caps.get("templates") or []:
            if t.get("key") == "installation_manual":
                return t
    if is_inspection_checklist_ask(text):
        for t in caps.get("templates") or []:
            if t.get("key") == "inspection_checklist":
                return t
    if is_topic_brief_ask(text):
        for t in caps.get("templates") or []:
            if t.get("key") == "topic_brief":
                return t
    if is_spec_coherence_ask(text):
        for t in caps.get("templates") or []:
            if t.get("key") == "spec_coherence_review":
                return t
    if is_research_ask(text):
        for key in ("research_project_report", "project_plan", "phd_materials_draft"):
            for t in caps.get("templates") or []:
                if t.get("key") == key:
                    return t
    if is_commissioning_ask(text):
        return None
    return None


def tier_eur_for_template(template: dict, caps: dict) -> int:
    pr = caps.get("pricing_json") or {}
    tiers = pr.get("export_tiers_eur") or {}
    tier = template.get("export_price_tier") or "standard"
    return int(tiers.get(tier, 19))


def format_draft_structure_card(template: dict, lang: str = "no") -> str:
    sections = template.get("sections") or []
    parts = []
    for i, s in enumerate(sections, 1):
        label = s.get("title_no") if lang == "no" else s.get("title")
        parts.append(f"{i}. {label or s.get('section_key')}")
    numbered = " · ".join(parts)
    need = template.get("name_no") if lang == "no" else template.get("name")
    if lang == "en":
        return (
            f"No finished template for **{need}** — proposed structure:\n"
            f"{numbered}"
        )
    return (
        f"Ingen ferdig mal for **{need}** — forslag til struktur:\n"
        f"{numbered}"
    )


def document_created_reply(template: dict, *, lang: str = "no", tier_eur: int = 19,
                           optional_question: str | None = None) -> str:
    import form_model as fm
    name = template.get("name_no") if lang == "no" else template.get("name")
    if fm.is_form_fill(template):
        if lang == "en":
            return (
                f"Created **{name}** — identification prefilled from the index where known; "
                f"ratings and measures are empty for you to fill. No generation cost."
            )
        return (
            f"Opprettet **{name}** — identifikasjon forhåndsutfylt fra indeksen der den finnes; "
            f"vurderinger og målinger er tomme for deg å fylle. Ingen genereringskostnad."
        )
    if lang == "en":
        text = (
            f"Created **{name}** with section shells ready. "
            f"Generation is ~€{tier_eur} — say **yes** to start."
        )
        q = optional_question or "Should I run generation now?"
    else:
        text = (
            f"Opprettet **{name}** med seksjonsskall klare. "
            f"Generering er ~€{tier_eur} — si **ja** for å starte."
        )
        q = optional_question or "Skal jeg kjøre genereringen nå?"
    return f"{text} {q}"


def create_document_shell(state: dict, template_file: str, template: dict) -> dict:
    """Open document with empty section shells — no generation tokens."""
    import form_model as fm
    stem = template_file.replace(".json", "") if template_file.endswith(".json") else template_file
    doc = {
        "template_file": template_file,
        "sections": {},
        "structure_overlay": (state.get("doc") or {}).get("structure_overlay") or {},
        "document_species": template.get("document_species") or "narrative",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # WORKORDER 0.58 §0 — never reuse section bodies from a *different* template
    prev_doc = state.get("doc") or {}
    same_tpl = (prev_doc.get("template_file") or "") == template_file
    for s in template.get("sections") or []:
        sk = s["section_key"]
        prev = prev_doc.get("sections", {}).get(sk) if same_tpl else None
        if prev and (prev.get("fields") or prev.get("md")):
            doc["sections"][sk] = prev
        else:
            doc["sections"][sk] = fm.init_section_shell(s) if fm.is_form_fill(template) else {"md": "", "files": []}
    state["doc"] = doc
    state["template"] = template_file
    state["active_template"] = template_file
    state["template_key"] = template.get("template_key")
    docs = [d for d in state.get("documents", []) if d.get("template") != template_file]
    docs.append({
        "template": template_file,
        "key": stem,
        "name_no": template.get("name_no") or template.get("name") or stem,
        "document_species": template.get("document_species") or "narrative",
        "gaps": len(state.get("gaps") or []),
        "blocking": sum(1 for g in (state.get("gaps") or []) if g.get("severity") == "blocking"),
        "created_at": doc["created_at"],
    })
    state["documents"] = docs
    label = template.get("name_no") or template.get("name") or stem
    ds.add_version(state, "user", "doc", f"Opprettet dokument {label}")
    return {"template": template_file, "key": stem, "name_no": label}


def offline_stub_commissioning_template(story: str, lang: str = "no") -> dict:
    """Regression / offline — deterministic rung-3 structure without API."""
    return {
        "template_key": "commissioning_report_draft",
        "name": "Commissioning Report",
        "name_no": "Idriftsettelsesrapport",
        "description": story[:200],
        "origin": "ai_drafted",
        "ai_drafted": True,
        "badge": "AI-foreslått struktur",
        "version": 1,
        "language_default": lang,
        "export_price_tier": "standard",
        "sections": [
            {"section_key": "identification", "title": "Identification", "title_no": "Identifikasjon",
             "position": 1, "required": True, "gap_severity": "warning",
             "required_facts": [
                 {"key": "project_name", "severity": "warning", "label_no": "Prosjektnavn"},
                 {"key": "site_address", "severity": "warning", "label_no": "Anleggsadresse"},
                 {"key": "system_type", "severity": "warning", "label_no": "Anleggstype"},
             ],
             "required_media": {}, "writing_rules": {"structure": "table", "fact_citation": "required"}},
            {"section_key": "scope", "title": "Scope", "title_no": "Omfang", "position": 2,
             "required": True, "gap_severity": "warning", "required_facts": [],
             "required_media": {}, "writing_rules": {"structure": "prose", "fact_citation": "required"}},
            {"section_key": "commissioning_sequence", "title": "Commissioning", "title_no": "Idriftsettelse",
             "position": 3, "required": True, "gap_severity": "warning", "required_facts": [],
             "required_media": {},
             "writing_rules": {"structure": "numbered_list", "fact_citation": "required", "prescriptive": True},
             "required_content": ["prescriptive_banner", "author_placeholder_per_phase"]},
            {"section_key": "verification", "title": "Verification", "title_no": "Kontroll og verifikasjon",
             "position": 4, "required": True, "gap_severity": "warning", "required_facts": [],
             "required_media": {},
             "writing_rules": {"structure": "checklist", "fact_citation": "required", "prescriptive": True}},
            {"section_key": "source_register", "title": "Source Register", "title_no": "Kilderegister",
             "position": 5, "required": True, "gap_severity": "info", "required_facts": [],
             "required_media": {}, "writing_rules": {"structure": "table", "fact_citation": "optional"}},
        ],
    }


def accept_draft_actions(lang: str = "no") -> list:
    label = "Use this" if lang == "en" else "Bruk denne"
    return [{"id": "accept_draft", "label": label}]


def filter_templates_for_project(templates: list, project: dict | None = None,
                                 *, tags=None) -> list:
    """Exclude domain-locked vehicle forms unless project tag = vehicle."""
    import form_model as fm
    return fm.filter_templates_for_project(templates, project, tags=tags)


def filter_capabilities_templates(caps: dict, project: dict | None = None,
                                  *, tags=None) -> dict:
    """Return a shallow-copied caps dict with vehicle fixtures filtered out."""
    import form_model as fm
    caps = dict(caps or {})
    caps["templates"] = fm.filter_templates_for_project(
        list(caps.get("templates") or []), project, tags=tags)
    return caps
