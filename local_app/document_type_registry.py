"""Document Type Registry — look up document types, materialise templates.

The agent does not hard-code document knowledge. It loads YAML definitions
from registry/document-types/ via ENGINE_TOOLS:
  list_document_types · get_document_type · materialise_template
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("PyYAML required for Document Type Registry — pip install pyyaml") from e

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "registry" / "document-types"

SECTION_TITLES = {
    "cover": ("Cover", "Forside"),
    "legal": ("Legal / Standards", "Juridisk / standarder"),
    "symbols": ("Symbols & Callouts", "Symboler"),
    "summary": ("Summary", "Sammendrag"),
    "glossary": ("Glossary", "Ordliste"),
    "product_description": ("Product Description", "Produktbeskrivelse"),
    "technical_specifications": ("Technical Specifications", "Tekniske spesifikasjoner"),
    "identification": ("Identification", "Identifikasjon"),
    "revision_history": ("Revision History", "Revisjonshistorikk"),
    "assembly": ("Assembly", "Montering"),
    "installation": ("Installation", "Installasjon"),
    "operation": ("Operation", "Betjening"),
    "maintenance": ("Maintenance", "Vedlikehold"),
    "transport_storage": ("Transport & Storage", "Transport og lagring"),
    "interface": ("Interface", "Grensesnitt"),
    "system_overview": ("System Overview", "Systemoversikt"),
    "missing_facts": ("Information Still Required", "Manglende informasjon"),
    "features": ("Features", "Egenskaper"),
    "tools_required": ("Tools Required", "Verktøy"),
    "safety": ("Safety", "Sikkerhet"),
    "verification": ("Verification", "Verifikasjon"),
    "spare_parts": ("Spare Parts", "Reservedeler"),
    "troubleshooting": ("Troubleshooting", "Feilsøking"),
    "scope": ("Scope", "Omfang"),
    "standards": ("Standards & Regulations", "Standarder og forskrifter"),
    "declaration": ("Declaration", "Erklæring"),
    "signature": ("Signature", "Signatur"),
    "references": ("References", "Referanser"),
    "attachments": ("Attachments", "Vedlegg"),
    "results": ("Results", "Resultater"),
    "conclusion": ("Conclusion", "Konklusjon"),
    "method": ("Method", "Metode"),
    "deviations": ("Deviations", "Avvik"),
    "recommendations": ("Recommendations", "Anbefalinger"),
    "executive_summary": ("Executive Summary", "Sammendrag"),
    "problem_and_context": ("Problem & Context", "Problem og kontekst"),
    "stakeholders": ("Stakeholders", "Interessenter"),
    "current_situation": ("Current Situation", "Nåsituasjon"),
    "evaluation_or_impact": ("Evaluation / Impact", "Evaluering / påvirkning"),
    "proposed_approach": ("Proposed Approach", "Foreslått tilnærming"),
    "comparison": ("Comparison", "Sammenligning"),
    "next_steps": ("Next Steps", "Neste steg"),
    "technical_details": ("Technical Details", "Tekniske detaljer"),
    "appendices": ("Appendices", "Vedlegg"),
    "location_map": ("Location Map", "Lokasjonskart"),
    "photo_evidence": ("Photo Evidence", "Fotobevis"),
    "checklist": ("Checklist", "Sjekkliste"),
    "measurements": ("Measurements", "Målinger"),
    "risk_assessment": ("Risk Assessment", "Risikovurdering"),
    "design_documentation": ("Design Documentation", "Designdokumentasjon"),
    "user_instructions": ("User Instructions", "Bruksanvisning"),
    "hazard_identification": ("Hazard Identification", "Fareidentifikasjon"),
    "risk_evaluation": ("Risk Evaluation", "Risikoevaluering"),
    "residual_risk": ("Residual Risk", "Restrisiko"),
    "mitigations": ("Mitigations", "Tiltak"),
    "as_built_documentation": ("As-built Documentation", "As-built dokumentasjon"),
    "declarations": ("Declarations", "Erklæringer"),
    "matrix": ("Traceability Matrix", "Sporbarhetsmatrise"),
    "equipment": ("Equipment", "Utstyr"),
    "training": ("Training", "Opplæring"),
    "parties": ("Parties", "Parter"),
    "purpose": ("Purpose of disclosure", "Formål med utlevering"),
    "definition": ("Definition of confidential information", "Definisjon av konfidensiell informasjon"),
    "recipient_obligations": ("Recipient obligations", "Mottakers forpliktelser"),
    "term_and_return": ("Term, return, residual", "Varighet, tilbakelevering, residual"),
    "signatures": ("Signatures", "Signaturer"),
    "industry_background": ("Industry background", "Bransjebakgrunn"),
    "competitive_analysis": ("Competitive analysis", "Konkurranseanalyse"),
    "market_analysis": ("Market analysis", "Markedsanalyse"),
    "mission_vision": ("Mission and vision", "Misjon og visjon"),
    "value_proposition": ("Value proposition", "Verdiproposisjon"),
    "strategy_overview": ("Product strategy overview", "Produktstrategi — oversikt"),
    "product_vs_solution": ("Product vs solution", "Produkt vs løsning"),
    "strategic_pillars": ("Strategic pillars", "Strategiske pilarer"),
    "portfolio_and_priorities": ("Portfolio and priorities", "Portefølje og prioriteringer"),
    "roadmap": ("Roadmap", "Veikart"),
    "innovation_practice": ("Innovation practice", "Innovasjonspraksis"),
    "success_measures": ("Success measures", "Suksessmål"),
    "governance": ("Governance", "Styring"),
}

BLOCK_TO_STRUCTURE = {
    "EngineeringTable": "table",
    "ParameterGrid": "table",
    "FeatureGrid": "table",
    "EvaluationMatrix": "table",
    "ComparisonTable": "table",
    "StakeholderCard": "list",
    "Rating": "prose",
    "Procedure": "numbered_list",
    "CalloutBox": "list",
    "RevisionHistory": "table",
    "Paragraph": "prose",
    "ImageBlock": "prose",
    "DiagramBlock": "prose",
}


def _fold(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


@lru_cache(maxsize=1)
def _load_all() -> dict[str, dict]:
    out = {}
    if not REGISTRY_DIR.is_dir():
        return out
    for path in sorted(REGISTRY_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        tid = data.get("id") or path.stem
        data["id"] = tid
        data["_path"] = str(path.relative_to(ROOT).as_posix())
        # YAML 1.1: bare `no` becomes False — restore region code
        if isinstance(data.get("regions"), list):
            data["regions"] = ["no" if x is False else x for x in data["regions"]]
        out[tid] = data
    return out


def reload_registry() -> None:
    """Clear cache (tests / hot-reload)."""
    _load_all.cache_clear()


def list_document_types(
    industry: str | None = None,
    region: str | None = None,
    domain: str | None = None,
) -> list[dict]:
    """ENGINE_TOOLS list_document_types — optional industry / region / domain filters."""
    industry_f = _fold(industry) if industry else None
    region_f = _fold(region) if region else None
    domain_f = _fold(domain) if domain else None
    rows = []
    for tid, d in _load_all().items():
        industries = list(d.get("industries") or [])
        regions = list(d.get("regions") or [])
        domains = list(d.get("domains") or [])
        if industry_f and industry_f not in [_fold(x) for x in industries]:
            continue
        if region_f and regions and region_f not in [_fold(x) for x in regions]:
            continue
        if domain_f and domains and domain_f not in [_fold(x) for x in domains]:
            continue
        rows.append({
            "id": tid,
            "name": d.get("name") or tid,
            "aliases": list(d.get("aliases") or []),
            "industries": industries,
            "regions": regions,
            "domains": domains,
            "obligation_types": list(d.get("obligation_types") or []),
            "evidence_types": list(d.get("evidence_types") or []),
            "description": (d.get("description") or "").strip(),
        })
    return rows


def get_document_type(type_id: str) -> dict | None:
    """ENGINE_TOOLS get_document_type — full definition."""
    if not type_id:
        return None
    all_types = _load_all()
    key = _fold(type_id).replace(" ", "_").replace("-", "_")
    if key in all_types:
        return dict(all_types[key])
    # alias / name match
    for tid, d in all_types.items():
        aliases = [_fold(a) for a in (d.get("aliases") or [])]
        if key == _fold(d.get("name") or "") or key in aliases or key == _fold(tid):
            return dict(d)
    return None


def match_document_types(query: str, limit: int = 5) -> list[dict]:
    """Rank types by alias / name / id hit for the router skill."""
    q = _fold(query)
    if not q:
        return []
    scored = []
    for row in list_document_types():
        score = 0
        tid = _fold(row["id"])
        name = _fold(row["name"])
        aliases = [_fold(a) for a in row["aliases"]]
        if q == tid or q == name or q in aliases:
            score = 100
        elif tid in q or name in q or any(a in q for a in aliases if len(a) >= 3):
            score = 80
        elif any(tok and (tok in tid or tok in name or any(tok in a for a in aliases))
                 for tok in q.split() if len(tok) > 3):
            score = 40
        if score:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [r for _, r in scored[:limit]]


def _section_shell(section_key: str, required: bool, preferred_blocks: dict, position: int) -> dict:
    title_en, title_no = SECTION_TITLES.get(
        section_key,
        (section_key.replace("_", " ").title(), section_key.replace("_", " ").title()),
    )
    blocks = list((preferred_blocks or {}).get(section_key) or [])
    structure = "prose"
    for b in blocks:
        if b in BLOCK_TO_STRUCTURE:
            structure = BLOCK_TO_STRUCTURE[b]
            break
    return {
        "section_key": section_key,
        "title": title_en,
        "title_no": title_no,
        "position": position,
        "required": required,
        "gap_severity": "blocking" if required else "info",
        "preferred_blocks": blocks,
        "required_facts": [],
        "required_media": {},
        "required_content": ["no_uncited_specs"] if required else [],
        "writing_rules": {
            "structure": structure,
            "fact_citation": "required" if required else "preferred",
        },
    }


def materialise_template(
    type_id: str,
    project_id: str | None = None,
    overrides: dict | None = None,
    *,
    include: str = "required+recommended",
) -> dict:
    """ENGINE_TOOLS materialise_template — concrete instance for CompositionEngine.

    include: "required" | "required+recommended" | "all"
    """
    definition = get_document_type(type_id)
    if not definition:
        raise LookupError(f"Unknown document type: {type_id}")

    structure = definition.get("structure") or {}
    preferred = definition.get("preferred_blocks") or {}
    overrides = overrides or {}

    keys: list[tuple[str, bool]] = []
    for k in structure.get("required") or []:
        keys.append((k, True))
    if include in ("required+recommended", "all"):
        for k in structure.get("recommended") or []:
            keys.append((k, False))
    if include == "all":
        for k in structure.get("optional") or []:
            keys.append((k, False))

    # Allow overrides to drop / add / rename sections
    drop = set(overrides.get("drop_sections") or [])
    extra = list(overrides.get("extra_sections") or [])
    keys = [(k, req) for k, req in keys if k not in drop]
    for ek in extra:
        if isinstance(ek, str):
            keys.append((ek, False))
        elif isinstance(ek, dict) and ek.get("section_key"):
            keys.append((ek["section_key"], bool(ek.get("required"))))

    sections = []
    for i, (sk, req) in enumerate(keys, start=1):
        shell = _section_shell(sk, req, preferred, i)
        sec_over = (overrides.get("sections") or {}).get(sk)
        if isinstance(sec_over, dict):
            shell.update({k: v for k, v in sec_over.items() if k != "section_key"})
        sections.append(shell)

    name = overrides.get("name") or definition.get("name")
    name_no = overrides.get("name_no") or name
    template = {
        "template_key": definition["id"],
        "document_type": definition["id"],
        "name": name,
        "name_no": name_no,
        "description": (definition.get("description") or "").strip(),
        "version": 1,
        "language_default": overrides.get("language_default") or "no",
        "registry_id": definition["id"],
        "registry_path": definition.get("_path"),
        "compliance_notes": list(definition.get("compliance_notes") or []),
        "skills": dict(definition.get("skills") or {}),
        "tools": list(definition.get("tools") or []),
        "preferred_blocks": dict(preferred),
        "workbench_template": definition.get("workbench_template"),
        "project_id": project_id,
        "sections": sections,
        "form_sections": list(definition.get("sections") or []),
        "gaps": list(definition.get("gaps") or []),
        "disclaimer": (definition.get("disclaimer") or "").strip(),
        "project_evidence": dict(definition.get("project_evidence") or {}),
        "composition": dict(definition.get("composition") or {}),
        "summary_block": dict(definition.get("summary_block") or {}),
        "source": "document_type_registry",
    }
    return template


def document_type_gaps(type_id: str, values: dict | None = None) -> list[dict]:
    """Evaluate document-type gap profile against supplied field values."""
    definition = get_document_type(type_id)
    if not definition:
        return []
    values = values or {}
    raw = definition.get("gaps") or []
    defined = {g["id"]: g for g in raw if isinstance(g, dict) and g.get("id")}
    open_ids: list[str] = []

    if type_id == "confidentiality_agreement":
        if not (values.get("disclosing_party") or "").strip() or not (
            values.get("recipient") or ""
        ).strip():
            open_ids.append("parties_incomplete")
        if not (values.get("permitted_purpose") or "").strip():
            open_ids.append("purpose_missing")
        if not (values.get("confidential_info_scope") or "").strip():
            open_ids.append("definition_missing")
        if not all(
            (values.get(k) or "").strip()
            for k in ("care_standard", "use_limitation", "non_disclosure")
        ):
            open_ids.append("obligations_missing")
        if not (values.get("disclosing_signatory") or "").strip() or not (
            values.get("recipient_signatory") or ""
        ).strip():
            open_ids.append("signatures_missing")

    if type_id == "opportunity_description":
        industry_keys = (
            "existing_products_services",
            "industry_size_shape",
            "industry_trends",
            "barriers_to_entry",
        )
        if not all((values.get(k) or "").strip() for k in industry_keys):
            open_ids.append("industry_incomplete")
        competitors = values.get("competitors") or []
        named = [
            c for c in competitors
            if isinstance(c, dict) and (c.get("name") or "").strip()
        ]
        if not named:
            open_ids.append("competitors_missing")
        if not (values.get("differentiation") or "").strip():
            open_ids.append("differentiation_missing")
        if (values.get("market_size_growth") or "").strip() and not (
            values.get("sources") or []
        ):
            open_ids.append("market_size_unsupported")
        if not (values.get("target_market") or "").strip():
            open_ids.append("target_market_missing")
        if not (values.get("value_proposition") or "").strip():
            open_ids.append("value_proposition_missing")

    if type_id == "product_strategy":
        if not (values.get("mission") or "").strip() or not (values.get("vision") or "").strip():
            open_ids.append("mission_vision_missing")
        if not (values.get("value_for_customers") or "").strip() or not (
            values.get("value_for_organization") or ""
        ).strip():
            open_ids.append("value_proposition_incomplete")
        if not (values.get("strategy_summary") or "").strip():
            open_ids.append("strategy_summary_missing")
        if not (values.get("positioning_choice") or "").strip():
            open_ids.append("product_solution_unclear")
        focus_areas = values.get("focus_areas") or []
        named_focus = [
            f for f in focus_areas
            if isinstance(f, dict) and (f.get("name") or "").strip()
        ]
        if not named_focus:
            open_ids.append("no_focus_areas")
        themes = values.get("themes") or []
        named_themes = [
            t for t in themes
            if isinstance(t, dict) and (t.get("theme") or "").strip()
        ]
        roadmap_touched = any(
            values.get(k)
            for k in ("time_horizon", "dependencies", "themes")
        )
        if roadmap_touched and not (values.get("time_horizon") or "").strip() and not named_themes:
            open_ids.append("roadmap_empty")

    return [
        {
            "id": gid,
            "severity": defined[gid].get("severity", "blocking"),
            "description": defined[gid].get("description", gid.replace("_", " ")),
            "type": "document_field",
        }
        for gid in open_ids
        if gid in defined
    ]


def format_type_brief(definition: dict) -> str:
    """Short chat-safe summary (≤120 words target)."""
    struct = definition.get("structure") or {}
    req = ", ".join(struct.get("required") or [])
    skills = definition.get("skills") or {}
    primary = ", ".join(skills.get("primary") or [])
    return (
        f"**{definition.get('name')}** (`{definition.get('id')}`)\n"
        f"{(definition.get('description') or '').strip()}\n"
        f"Required: {req or '—'}\n"
        f"Skills: {primary or '—'}"
    )
