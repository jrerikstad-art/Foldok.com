#!/usr/bin/env python3
"""Generate capabilities.json from the live templates tree (COLD_START_SPEC §2).

Run at release time (and locally after template changes):
  python scripts/build_caps.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
OUT = ROOT / "capabilities.json"
VERSION_FILE = ROOT / "VERSION"

ROLE_NO = {
    "overview": "oversiktsbilde / produktfoto",
    "nameplate": "bilde av merkeskilt",
    "environment": "bilde av arbeidssted",
    "safety": "sikkerhetsfoto",
    "damage": "skadefoto",
    "drawing": "tegning (PDF)",
    "site_plan": "situasjonsplan",
    "schematic": "skjema / snitt",
    "sketch": "skisse",
    "certificate": "sertifikat / attest",
    "test_result": "testrapport",
    "wiring": "koblingsskjema",
    "contract_clause": "kontraktutdrag",
}

PRIVACY = [
    "Filene dine ligger på din maskin. Foldok laster dem aldri opp til "
    "noen Foldok-sky og lagrer ingen kopier hos oss.",
    "Når jeg analyserer en fil, sendes utdrag av innholdet (tekst eller "
    "bilde) til AI-tjenesten for behandling av akkurat det kallet — du "
    "ser kostnaden i €-måleren. Originalene blir hvor de er.",
    "Ferdige og signerte PDF-er lagres heller ikke hos oss — de er dine.",
]

PRIVACY_EN = [
    "Your files stay on your machine. Foldok never uploads them to a "
    "Foldok cloud or keeps copies on our side.",
    "When I analyse a file, excerpts (text or image) are sent to the AI "
    "service for that call only — you see the cost in the € meter. The "
    "originals stay put.",
    "Finished and signed PDFs are not stored with us either — they are yours.",
]

CANNOT = [
    "verifisere beregninger",
    "gi juridisk råd",
    "gi juridisk vurdering",
    "håndtere beviskjede/chain of custody",
    "utforme juridisk tekst",
    "lese native CAD (DWG/STEP)",
    "signere for deg",
    "finne på verdier som ikke finnes i kilder",
    "tegne eller modellere i 3D",
]

# WORKORDER_0.23 A — money claims must match this block verbatim
PRICING = {
    "index_per_file_eur": [0.001, 0.01],
    "export_tiers_eur": {"basic": 9, "standard": 19, "complex": 49},
    "included": "redigering og AI-hjelp i dokumentet",
    "included_en": "editing and AI help inside the document",
    "free_tier": "1 prosjekt, ~50 filer, forhåndsvisning med vannmerke",
    "free_tier_en": "1 project, ~50 files, watermarked preview",
    "reexport": "gratis for betalte dokumenter",
    "reexport_en": "free for paid documents",
    "contract_tier_note": "contract reviews are typically the €49 tier",
    "contract_tier_note_no": "kontraktsgjennomgang er typisk €49-nivået",
}

# Approved legal-audience framing (WORKORDER_0.23 B2) — agent may quote, not invent
LEGAL_FRAMING = {
    "en": (
        "Foldok does document review and extraction: parties, obligations, "
        "deadlines and penalties with verbatim clause citations, plus "
        "cross-document conflict detection. It records what the documents "
        "say and what could not be found. It is not legal advice, and the "
        "legal assessment stays with you."
    ),
    "no": (
        "Foldok gjør dokumentgjennomgang og ekstraksjon: parter, forpliktelser, "
        "frister og sanksjoner med ordrette klausulsitater, pluss konfliktdeteksjon "
        "på tvers av dokumenter. Den registrerer hva dokumentene sier og hva som "
        "ikke ble funnet. Det er ikke juridisk råd — den juridiske vurderingen er din."
    ),
}

FORBIDDEN_LEGAL_PHRASES = [
    "evidence handling",
    "bevishåndtering",
    "admissible",
    "chain of custody",
    "beviskjede",
]

# Grounded scale facts for hub answers (COLD_START §2 / §3) — keep in sync
# with local_app/server.py estimate_cost and the indexer worker count.
# Money amounts here must stay within PRICING.index_per_file_eur (WO 0.23 A2).
SCALE = {
    # WORKORDER_0.20 C6 canonical keys
    "per_file_index_cost_eur": [0.001, 0.01],
    "parallel_workers": 5,
    "cache": "sha256, re-index is free",
    "multi_folder": True,
    "recommendation": (
        "Very large corpora (1000+ files) run better as several focused "
        "projects (one per workstream) than one index."
    ),
    # Compat aliases used by hub_chat.scale_reply
    "index_cost_eur_per_file_min": 0.001,
    "index_cost_eur_per_file_max": 0.01,
    "typical_doc_eur": 0.01,   # high end of index range (not a separate invent)
    "typical_photo_eur": 0.008,
    "multi_folder_note": "Several folders link into one project; each file indexes once.",
    "example_files": 2000,
    "example_time": "a few hours, one time",
    "large_corpus_recommendation": (
        "most large diligence / review work runs better as several focused "
        "projects (one per workstream) than one giant index"
    ),
    "large_corpus_recommendation_no": (
        "de fleste store diligence-/gjennomgangsjobber kjører bedre som flere "
        "fokuserte prosjekter (ett per arbeidsspor) enn én gigantindeks"
    ),
}


def one_liner(t: dict) -> str:
    d = (t.get("description") or "").strip()
    if not d:
        return t.get("name_no") or t.get("name") or t.get("template_key", "")
    # first sentence, capped
    cut = d.split(". ")[0].strip()
    if len(cut) > 140:
        cut = cut[:137] + "…"
    if not cut.endswith("."):
        cut += "."
    return cut


def collect_needs(t: dict, limit: int = 8) -> list:
    needs, seen = [], set()
    for s in sorted(t.get("sections") or [], key=lambda x: x.get("position", 99)):
        for f in s.get("fields") or []:
            if not f.get("required"):
                continue
            lab = f.get("label_no") or f.get("label") or f.get("key")
            if not lab or lab in seen:
                continue
            seen.add(lab)
            needs.append(lab)
            if len(needs) >= limit:
                return needs
        for rf in s.get("required_facts") or []:
            if rf.get("severity") == "info":
                continue
            lab = rf.get("label_no") or rf.get("label") or rf.get("key")
            if not lab or lab in seen:
                continue
            seen.add(lab)
            needs.append(lab)
            if len(needs) >= limit:
                return needs
        media = s.get("required_media") or {}
        for role in media.get("preferred_roles") or []:
            lab = ROLE_NO.get(role, role.replace("_", " "))
            if lab in seen:
                continue
            seen.add(lab)
            needs.append(lab)
            if len(needs) >= limit:
                return needs
        if media.get("min_photos"):
            lab = f"minst {media['min_photos']} foto(s)"
            if lab not in seen:
                seen.add(lab)
                needs.append(lab)
            if len(needs) >= limit:
                return needs
    return needs


def checklist_lines(t: dict) -> list:
    """Zero-token shopping list for SJEKKLISTE.txt."""
    lines = []
    for item in collect_needs(t, limit=20):
        lines.append(f"□ {item}")
    return lines or ["□ Prosjektfiler (PDF, bilder, notater)"]


def build(extra_dirs=None) -> dict:
    version = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.0.0"
    templates = []
    seen = set()
    dirs = [TEMPLATES] + list(extra_dirs or [])
    # Always include local company templates next to the workbench
    company = ROOT / "local_app" / "company_templates"
    if company not in dirs:
        dirs.append(company)
    for d in dirs:
        if not Path(d).is_dir():
            continue
        for p in sorted(Path(d).glob("*.json")):
            if p.name.startswith("_") or p.name in seen:
                continue
            seen.add(p.name)
            t = json.loads(p.read_text(encoding="utf-8"))
            key = t.get("template_key") or p.stem
            templates.append({
                "key": key,
                "file": p.name,
                "name_no": t.get("name_no") or t.get("name") or key,
                "name": t.get("name") or t.get("name_no") or key,
                "one_liner": one_liner(t),
                "description": (t.get("description") or "")[:500],
                "needs": collect_needs(t),
                "checklist": checklist_lines(t),
                "applies_to": t.get("applies_to") or [],
                "group": _group(key, t),
                "document_species": t.get("document_species") or "narrative",
                "owned": "company_templates" in str(p.parent).replace("\\", "/"),
                "origin": t.get("origin"),
                "badge": t.get("badge"),
            })
    return {
        "version": version,
        "templates": templates,
        "file_types": {
            "reads": ["PDF", "bilder (JPG/PNG/WEBP/HEIC)", "Word/Excel via markitdown", "PowerPoint"],
            "cad_policy": "tegnings-PDF, ikke DWG",
        },
        "cannot": CANNOT,
        "privacy": PRIVACY,
        "privacy_en": PRIVACY_EN,
        "scale": SCALE,
        "pricing": PRICING,
        "pricing_line": "Gratis å prøve — betal per eksportert dokument (€9 / €19 / €49).",
        "pricing_line_en": "Free to try — pay per exported document (€9 / €19 / €49).",
        "legal_framing": LEGAL_FRAMING,
        "forbidden_legal_phrases": FORBIDDEN_LEGAL_PHRASES,
        "forbidden_privacy_phrases": [
            "helt offline",
            "ingenting forlater maskinen",
            "vi har ikke tilgang til dataene dine",
            "completely offline",
            "nothing leaves your machine",
        ],
    }


def _group(key: str, t: dict) -> str:
    k = key.lower()
    applies = " ".join(t.get("applies_to") or []).lower()
    name = (t.get("name_no") or "").lower()
    blob = f"{k} {applies} {name}"
    if any(w in blob for w in ("sja", "sikker", "hazard")):
        return "HMS / arbeid"
    if any(w in blob for w in ("samsvar", "conform", "el_", "elektr")):
        return "Samsvar / sertifisering"
    if any(w in blob for w in ("building", "design", "structural", "tegning", "bygg", "spec")):
        return "Bygg / prosjektering"
    if any(w in blob for w in ("contract", "tender", "kontrakt", "diligence", "compliance", "anbud")):
        return "Kontrakt / anbud"
    if any(w in blob for w in ("phd", "research", "thesis")):
        return "Forskning"
    if "plan" in blob:
        return "Planlegging"
    if "free" in blob:
        return "Åpent"
    return "Teknisk dokumentasjon"


def main():
    data = build()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(data['templates'])} templates, v{data['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
