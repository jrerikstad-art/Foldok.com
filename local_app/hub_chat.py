"""Cold-start hub replies — grounded ONLY in capabilities.json (COLD_START_SPEC).

Capability *claims* are grounded in the manifest.
Capability *matching* is inference from user words → listed templates.
Never invent unlisted features; never shrug when a listed template fits.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPS_PATH = ROOT / "capabilities.json"
SETTINGS_PATH = Path(__file__).resolve().parent / "workbench_settings.json"

SKELETON_DIRS = ("Bilder", "Tegninger", "Rapporter", "Notater")

# Topic aliases → boost templates whose key/blob contains these markers
TOPIC_ALIASES = {
    "teknisk": ["teknisk dokument", "dokumentasjonspakke", "technical documentation", "tech pack",
                "rov", "subsea", "undervann", "subsea vehicle", "remotely operated"],
    "designgrunnlag": ["designgrunnlag", "design basis", "rov", "subsea"],
    "spec": ["specification", "spesifikasjon", "norsok", "coherence", "conflict", "subsea", "rov"],
    "multi_folder": ["mange foldere", "mange mapper", "many folders", "multiple folders",
                     "flere mapper", "stort team", "large team"],
    "prosjektplan": ["prosjektplan", "framdriftsplan", "project plan", "schedule"],
    "kontrakt": ["kontrakt", "kontraktsgjennomgang", "contract review", "obligations",
                 "forpliktelse", "clause"],
    "due_diligence": [
        "due diligence", "duediligence", " dd ", "dd,", "dd?",
        "diligence", "dataroom", "data room", "virtual data room", "vdr",
        "obligation register", "obligations register", "compliance matrix",
        "requirement vs evidence", "requirements matrix", "conflict detection",
        "spec coherence", "specification review", "tender compliance",
        "anbudssamsvar", "spesifikasjonsgjennomgang",
        "forsikring", "insurance", "endelig rapport", "final report",
        "due-diligence", "gjennomgang av kontrakt",
    ],
    "konstruksjon": ["konstruksjonsrapport", "structural", "structural design"],
    "phd": ["phd", "ph.d", "avhandling", "thesis", "research project"],
    "tender": ["tender", "anbud", "rfq", "bid compliance", "itt"],
    "sja": ["sja", "sikker jobbanalyse", "safe job", "job safety"],
    "samsvar": ["samsvar", "samsvarserklaering", "conformity", "declaration of conformity"],
    "brukermanual": ["brukermanual", "bruksanvisning", "user manual", "instructions for use"],
    "inspection_checklist": [
        "inspeksjonssjekkliste", "inspection checklist", "kontrollskjema",
        "egenkontroll", "multipoint",
    ],
    "installation_manual": [
        "installasjonsmanual", "installation manual", "installasjons manual",
        "installasjon manual", "idriftsmanual", "commissioning manual",
    ],
}


def load_capabilities():
    if not CAPS_PATH.exists():
        try:
            import sys
            sys.path.insert(0, str(ROOT / "scripts"))
            from build_caps import build
            data = build()
            CAPS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
            return data
        except Exception:
            return {"version": "?", "templates": [], "cannot": [], "privacy": [],
                    "file_types": {}, "pricing_line": "", "scale": {},
                    "forbidden_privacy_phrases": []}
    return json.loads(CAPS_PATH.read_text(encoding="utf-8"))


def load_settings():
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return {}


def save_settings(settings):
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9æøå]+", " ", s.lower()).strip()


def detect_lang(message: str) -> str:
    """Mirror the user's language. Default Norwegian when ambiguous."""
    raw = message or ""
    q = raw.lower()
    if re.search(r"[æøå]", q):
        return "no"
    en_hits = len(re.findall(
        r"\b(the|and|are|is|can|you|your|what|where|how|handle|files?|folders?|"
        r"thousands?|hundreds?|projects?|documents?|contracts?|review|scale|"
        r"yes|please|need|want|about|across|many|large|would|could|should|"
        r"my|stored?|privacy|offline|with|from|this|that|have|does|do)\b", q))
    no_hits = len(re.findall(
        r"\b(jeg|du|kan|hva|hvordan|lage|mappe|filer?|prosjekt|dokument|"
        r"mal|samsvar|kontrakt|trenger|vil|om|med|til|fra|ikke|eller|"
        r"handtere|tvers|hundrevis|tusenvis|pa|paa|skal|dette|denne|"
        r"hvor|lagres|behandl)\b", q))
    # Strong Norwegian sentence shape wins even with English loanwords
    # ("due diligence", "data room") embedded in NO.
    if no_hits >= 3 and en_hits < no_hits:
        return "no"
    if any(p in q for p in (
        "can you", "what can you", "thousands of", "hundreds of",
        "how many files", "due diligence", "data room", "virtual data room",
        "compliance matrix", "obligations register", "requirement vs evidence",
        "where are my", "where do you store", "my files",
        "what does it cost", "how much", "i am a lawyer", "dummy contract",
        "i need a schematic", "schematic drawing", "block diagram",
    )):
        return "en"
    if en_hits >= no_hits + 2 and en_hits >= 3:
        return "en"
    return "no"


def _needs_line(t: dict, lang: str = "no") -> str:
    needs = t.get("needs") or []
    if not needs:
        return ("files you already have (PDFs, photos, notes)" if lang == "en"
                else "filer du allerede har (PDF, bilder, notater)")
    if len(needs) == 1:
        return needs[0]
    joiner = ", and " if lang == "en" else ", og "
    return ", ".join(needs[:-1]) + joiner + needs[-1]


def _template_blob(t: dict) -> str:
    return _fold(" ".join([
        t.get("key") or "",
        t.get("name_no") or "",
        t.get("name") or "",
        t.get("one_liner") or "",
        t.get("description") or "",
        " ".join(t.get("applies_to") or []),
        t.get("group") or "",
    ]))


def score_template(query: str, t: dict) -> int:
    q = _fold(query)
    if not q:
        return 0
    q_tokens = set(tok for tok in q.split() if len(tok) >= 4)
    key = (t.get("key") or "").lower()
    blob = _template_blob(t)
    blob_tokens = set(blob.split())
    s = 0
    if key and key.replace("_", " ") in q:
        s += 6
    for name_field in (t.get("name_no"), t.get("name")):
        name = _fold(name_field or "")
        if name and name in q:
            s += 5
        for tok in name.split():
            if len(tok) > 3 and tok in q_tokens:
                s += 1
    # Token overlap with applies_to / description — whole tokens only
    # (avoid "tegne" ⊆ "tegninger" false positives)
    for tok in q_tokens:
        if tok in blob_tokens:
            s += 1
    for alias_key, words in TOPIC_ALIASES.items():
        hit_q = any(_fold(w) in q or w.strip() in q for w in words)
        if not hit_q:
            continue
        # Does this template belong to the topic?
        markers = {
            "due_diligence": ("contract_review", "spec_coherence", "tender_compliance",
                              "contract", "tender", "obligation", "compliance", "coherence"),
            "kontrakt": ("contract", "obligation", "tender"),
            "tender": ("tender", "bid", "rfq", "compliance"),
            "spec": ("spec_coherence", "specification", "coherence"),
            "sja": ("sja", "sikker", "hazard"),
            "samsvar": ("samsvar", "conform"),
            "brukermanual": ("user_manual", "brukermanual", "bruksanvisning"),
            "inspection_checklist": ("inspection_checklist", "kontrollskjema", "sjekkliste"),
            "installation_manual": ("installation_manual", "installasjon", "commissioning"),
            "teknisk": ("technical_doc", "teknisk", "bom", "design_basis"),
            "multi_folder": ("technical_doc", "design_basis", "spec_coherence", "bom"),
            "prosjektplan": ("project_plan", "plan"),
            "designgrunnlag": ("design_basis", "designgrunnlag"),
            "konstruksjon": ("structural", "konstruksjon"),
            "phd": ("phd", "thesis", "research"),
        }.get(alias_key, (alias_key,))
        if any(m in key or m in blob for m in markers):
            # Prefer exact template for brukermanual — never silently boost technical_doc_package
            if alias_key == "brukermanual":
                if key == "user_manual" or "user_manual" in key:
                    s += 8
                elif "technical_doc" in key:
                    continue  # do not score technical_doc_package for brukermanual intent
                else:
                    s += 3
            else:
                boost = 5 if alias_key in ("due_diligence", "teknisk", "multi_folder") else 3
                s += boost
    return s


def match_template(query: str, caps: dict):
    scored = match_templates(query, caps, limit=1)
    if not scored:
        return None, 0
    t, s = scored[0]
    return (t, s) if s >= 3 else (None, s)


def match_templates(query: str, caps: dict, limit: int = 3, min_score: int = 3,
                    project: dict | None = None, *, tags=None):
    """Score templates against query. Vehicle fixtures filtered unless tagged."""
    import form_model as fm
    ranked = []
    templates = fm.filter_templates_for_project(
        list(caps.get("templates") or []), project, tags=tags)
    for t in templates:
        if t.get("key") == "free_document":
            continue
        s = score_template(query, t)
        if s >= min_score:
            ranked.append((t, s))
    ranked.sort(key=lambda x: -x[1])
    return ranked[:limit]


def is_privacy_question(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "hvor lagres", "lagres fil", "privat", "personvern", "sky", "cloud",
        "offline", "forlater", "behandl", "filene mine", "dataene mine",
        "hvordan behandles", "sikkerhet", "where are my files", "where do you store",
        "privacy", "is it offline", "leave my machine",
    ))


def is_catalog_question(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "hva kan du", "hva lager du", "hvilke mal", "katalog", "hva bygger",
        "hva kan foldok", "hvilke dokument", "what can you", "what do you build",
        "which templates", "show me capabilities", "what documents",
    ))


def is_scale_question(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "thousands of files", "hundreds of folders", "tusenvis", "hundrevis",
        "scale", "skaler", "hvor mange fil", "how many files", "large corpus",
        "stor mengde", "mange mapper", "many folders", "big project",
        "2 000", "2000", "thousand files", "hundred folders",
    )) or (
        any(w in q for w in ("thousand", "hundreds", "tusenvis", "hundrevis"))
        and any(w in q for w in ("file", "folder", "fil", "mappe", "document", "dokument"))
    )


def is_pricing_question(q: str) -> bool:
    q = _fold(q)
    if is_scale_question(q):
        return False
    return any(w in q for w in (
        "what does it cost", "how much does", "how much is", "pricing",
        "what is the price", "hva koster", "hva er prisen", "kostnad",
        "betaler jeg", "do i pay", "export cost", "eksportpris",
    )) or (
        any(w in q for w in ("cost", "price", "pris", "koster"))
        and any(w in q for w in ("what", "hva", "how", "document", "dokument", "export", "eksport"))
    )


def is_demo_request(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "dummy", "sample", "demo", "demosak", "syntetisk", "fiktiv",
        "test data", "testdata", "example contract", "dummy contract",
        "sample contract", "example files", "show me an example",
        "uten a laste", "without uploading", "nervous about upload",
        "ikke laste opp", "ikke sende fil", "lag demosak", "create demo",
    ))


def is_draft_legal_request(q: str) -> bool:
    """Ask to draft real legal text — not a marked demo."""
    if is_demo_request(q):
        return False
    q = _fold(q)
    return bool(re.search(
        r"(draft|write|utform|skriv)\s+.*(contract|kontrakt|avtale)|"
        r"(lag|make)\s+(en\s+)?(kontrakt|avtale|contract)\b|"
        r"(contract|kontrakt|avtale).*(for meg|for me|from scratch)",
        q,
    ))


def is_legal_prospect(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "lawyer", "attorney", "counsel", "advokat", "jurist", "legal team",
        "law firm", "advokatfirma",
    )) and any(w in q for w in (
        "case", "sak", "matter", "help", "hjelp", "review", "gjennomgang",
        "large", "stor", "many", "mange",
    ))


def is_can_you_make(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "kan du lage", "kan dere lage", "klarer du", "har du mal",
        "trenger", "vil ha", "lage en", "lage et", "bygge en",
        "can you", "can you make", "can you do", "do you handle",
        "can foldok", "are you able", "help with", "support for",
        "due diligence", "contract review", "compliance matrix",
    )) or bool(re.search(r"\b(sja|samsvar|manual|rapport|plan|tender|dd)\b", q))


def is_documentation_domain(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "dokument", "document", "rapport", "report", "mal", "template",
        "kontrakt", "contract", "anbud", "tender", "spesifikasjon", "specification",
        "samsvar", "compliance", "due diligence", "register", "matrix", "matrise",
        "gjennomgang", "review", "pakke", "manual", "plan", "sja", "phd",
        "forsknings", "research", "obligat", "krav", "requirement",
    ))


def match_cannot(q: str, caps: dict):
    q = _fold(q)
    checks = [
        # Narrow CAD refusal (foldok_route 0.85): bare "3d" / "modellere" were
        # catching wiring-diagram asks. Keep real CAD refusals only.
        (("dwg", "step", "solidworks", "native cad", "3d model", "3d-modell",
          "tegne hus", "draw my house"),
         "tegne eller modellere i 3D",
         "lese native CAD (DWG/STEP)"),
        (("beregn", "verifiser beregn", "regn ut", "statikk", "verify calculations"),
         "verifisere beregninger", None),
        (("legal advice", "gi meg juridisk rad", "lovtolk for meg"),
         "gi juridisk råd", None),
        (("juridisk vurdering", "legal assessment for me", "advise me legally"),
         "gi juridisk vurdering", None),
        (("chain of custody", "beviskjede", "evidence handling", "bevishandtering"),
         "håndtere beviskjede/chain of custody", None),
        (("signer for meg", "sign for me", "signatur for meg"),
         "signere for deg", None),
        (("finn pa", "dikte opp", "hallusin", "make up values"),
         "finne på verdier som ikke finnes i kilder", None),
    ]
    # Drafting real legal text (not demo)
    if is_draft_legal_request(q):
        return "utforme juridisk tekst"
    cannot = caps.get("cannot") or []
    for words, primary, secondary in checks:
        if any(w in q for w in words):
            if primary in cannot:
                return primary
            if secondary and secondary in cannot:
                return secondary
    return None


def try_diagram_route(message: str, lang: str = "no", *,
                      spec=None, components=()) -> dict | None:
    """foldok_route 0.85 — keyword branch before match_cannot (no model)."""
    try:
        from foldok_route import diagram_route
    except ImportError:
        return None
    if not diagram_route.is_diagram_request(message):
        return None
    routed = diagram_route.handle(
        message, spec=spec, components=components or (), lang=lang)
    if not routed.handled:
        return None
    out = {
        "reply": routed.reply,
        "kind": "diagram_route",
        "lang": lang,
        "actions": [],
        "model_called": False,
    }
    if routed.svg:
        out["svg"] = routed.svg
    if routed.spec_needed:
        out["spec_needed"] = True
        out["missing"] = list(routed.missing or ())
    if routed.warnings:
        out["warnings"] = list(routed.warnings)
    return out


def _shipped_capability(caps: dict, cap_id: str) -> dict | None:
    for c in caps.get("capabilities") or []:
        if isinstance(c, dict) and c.get("id") == cap_id:
            return c
    return None


def nearest_capability(cannot_hit: str, caps: dict, lang: str = "no") -> str:
    h = cannot_hit or ""
    diagrams = _shipped_capability(caps, "diagrams")
    if lang == "en":
        if "beregn" in h or "calculat" in h:
            return ("I can still gather every input value with sources, ready for your "
                    "engineer to check — e.g. in a technical documentation pack.")
        if "cad" in h or "3d" in h or "tegne" in h or "modellere" in h:
            if diagrams and diagrams.get("summary"):
                return (
                    f"I can {diagrams['summary'].lower().rstrip('.')}. "
                    "Native DWG/STEP and 3D modelling are out of scope."
                )
            return ("I can build documentation around drawing PDFs and photos you have — "
                    "design basis, structural report, or a technical pack.")
        if "juridisk" in h or "legal" in h or "utforme" in h or "bevis" in h or "custody" in h:
            return ("For a first look I can open a marked synthetic demo case "
                    "([Create demo case]) — never unmarked contract text.")
        if "signer" in h:
            return "The document is prepared for you to sign — the signature is always yours."
        return "Tell me what document you need and I'll show the closest template."
    if "beregn" in h:
        return ("Men jeg kan samle alle inputverdier med kilder, klare til kontroll — "
                "f.eks. i en teknisk dokumentasjonspakke eller konstruksjonsrapport.")
    if "cad" in h or "3d" in h or "tegne" in h or "modellere" in h:
        if diagrams and diagrams.get("summary"):
            summary = diagrams["summary"].rstrip(".")
            return (
                f"Men jeg kan {summary[0].lower()}{summary[1:]}. "
                "Native DWG/STEP og 3D-modellering er utenfor scope."
            )
        return ("Men jeg kan bygge dokumentasjon rundt tegnings-PDF-er og bilder du har — "
                "designgrunnlag, konstruksjonsrapport eller teknisk dokumentasjonspakke.")
    if "juridisk" in h or "utforme" in h or "bevis" in h or "custody" in h:
        return ("Jeg kan åpne en merket syntetisk demosak ([Lag demosak]) "
                "så du ser ekstraksjonen — aldri umerket juridisk tekst.")
    if "signer" in h:
        return "Dokumentet blir klart for deg å signere — signaturen er alltid din."
    return "Si hva slags dokument du trenger, så viser jeg nærmeste mal."


def catalog_reply(caps: dict, lang: str = "no") -> str:
    groups = {}
    for t in caps.get("templates") or []:
        if t.get("key") == "free_document":
            continue
        g = t.get("group") or ("Other" if lang == "en" else "Annet")
        groups.setdefault(g, []).append(t)
    if lang == "en":
        lines = ["I can build, among other things:"]
        for g in sorted(groups.keys()):
            names = ", ".join((t.get("name") or t["name_no"]) for t in groups[g][:6])
            lines.append(f"• **{g}:** {names}")
        lines.append("…and your company's own forms — upload their template.")
    else:
        lines = ["Jeg kan bygge blant annet:"]
        for g in sorted(groups.keys()):
            names = ", ".join(t["name_no"] for t in groups[g][:6])
            lines.append(f"• **{g}:** {names}")
        lines.append("…og firmaets egne skjemaer — last opp malen deres.")
    if caps.get("pricing_line"):
        lines.append(caps["pricing_line"])
    return "\n".join(lines)


def privacy_reply(caps: dict, lang: str = "no") -> str:
    if lang == "en":
        parts = list(caps.get("privacy_en") or [])
        if not parts:
            parts = [
                "Your files stay on your machine. Foldok never uploads them to a Foldok "
                "cloud or keeps copies on our side.",
                "When I analyse a file, excerpts (text or image) are sent to the AI service "
                "for that call only — you see the cost in the € meter. The originals stay put.",
                "Finished and signed PDFs are not stored with us either — they are yours.",
            ]
    else:
        parts = list(caps.get("privacy") or [])
    ft = caps.get("file_types") or {}
    if ft.get("cad_policy"):
        reads = ", ".join(ft.get("reads") or [])
        if lang == "en":
            parts.append(f"File types: I read {reads}. CAD: {ft['cad_policy']}.")
        else:
            parts.append(f"Filtyper: jeg leser {reads}. CAD: {ft['cad_policy']}.")
    return "\n\n".join(parts)


def scale_reply(caps: dict, lang: str = "no", matched: list | None = None) -> dict:
    """Grounded answer for 'hundreds of folders / thousands of files'."""
    sc = caps.get("scale") or {}
    pr = caps.get("pricing") or {}
    idx = pr.get("index_per_file_eur") or [
        sc.get("index_cost_eur_per_file_min", 0.001),
        sc.get("index_cost_eur_per_file_max", 0.01),
    ]
    lo, hi = idx[0], idx[-1]
    workers = sc.get("parallel_workers", 5)
    ex_n = sc.get("example_files", 2000)
    ex_time = sc.get("example_time", "a few hours, one time")
    if lang == "en":
        rec = sc.get("large_corpus_recommendation") or (
            "most large diligence work runs better as several focused projects "
            "(one per workstream) than one giant index"
        )
    else:
        rec = sc.get("large_corpus_recommendation_no") or (
            "de fleste store diligence-/gjennomgangsjobber kjører bedre som flere "
            "fokuserte prosjekter (ett per arbeidsspor) enn én gigantindeks"
        )

    names = []
    for t, _ in (matched or [])[:3]:
        names.append(t.get("name") if lang == "en" else t.get("name_no"))
    if not names:
        by_key = {t.get("key"): t for t in caps.get("templates") or []}
        for k in ("contract_review", "spec_coherence_review", "tender_compliance_matrix"):
            if k in by_key:
                t = by_key[k]
                names.append(t.get("name") if lang == "en" else t.get("name_no"))

    if lang == "en":
        head = ""
        if names:
            head = (
                f"Yes — that's what the contract and specification templates are built for: "
                f"{', '.join(names)}. Obligations registers, requirement matrices, "
                f"and conflict detection across document sets — every finding cited to its clause.\n\n"
            )
        else:
            head = "Yes — Foldok is built for large document sets with cited findings.\n\n"
        text = (
            f"{head}"
            f"On scale: hundreds of folders is fine (they're linked per project, indexed once "
            f"at ~€{lo}–{hi} per file, cached forever by sha256). "
            f"Thousands of files is a cost and time question, not a limit — "
            f"e.g. {ex_n:,} files at the same per-file rate, typically {ex_time}. "
            f"Indexing runs with {workers} parallel workers.\n\n"
            f"Practically, {rec}. Want me to sketch how I'd split it?"
        )
        actions = []
    else:
        head = ""
        if names:
            head = (
                f"Ja — det er det kontrakts- og spesifikasjonsmalene er laget for: "
                f"{', '.join(names)}. Forpliktelsesregistre, kravmatriser og "
                f"konfliktdeteksjon på tvers av dokumentsett — hvert funn sitert til klausul.\n\n"
            )
        else:
            head = "Ja — Foldok er laget for store dokumentsett med siterte funn.\n\n"
        text = (
            f"{head}"
            f"Om skala: hundrevis av mapper går fint (knyttes per prosjekt, indekseres én gang "
            f"til ~€{lo}–{hi} per fil, caches for alltid med sha256). "
            f"Tusenvis av filer er et kostnads- og tidsspørsmål, ikke en grense — "
            f"f.eks. {ex_n} filer til samme per-fil-sats, typisk {ex_time}. "
            f"Indeksering kjører med {workers} parallelle arbeidere.\n\n"
            f"I praksis: {rec}. Skal jeg skissere hvordan jeg ville delt det?"
        )
        actions = []
    return {
        "reply": text,
        "kind": "scale",
        "lang": lang,
        "template_key": (matched[0][0].get("key") if matched else "contract_review"),
        "offer_folder": True,
        "actions": actions,
    }


def template_yes_reply(t: dict, lang: str = "no", also: list | None = None) -> dict:
    needs = _needs_line(t, lang)
    name = (t.get("name") if lang == "en" else t.get("name_no")) or t.get("name_no")
    also_names = []
    for o in (also or [])[:2]:
        also_names.append(o.get("name") if lang == "en" else o.get("name_no"))
    also_bit = ""
    if also_names:
        if lang == "en":
            also_bit = f" Related: {', '.join(also_names)}."
        else:
            also_bit = f" Relatert: {', '.join(also_names)}."
    if lang == "en":
        text = (
            f"Yes — I have a template for **{name}**. Best results with: {needs}."
            f"{also_bit} Say **Start with {name}** and I create the project folder."
        )
        actions = [
            {"id": "link_folder", "label": "I already have a folder"},
        ]
    else:
        text = (
            f"Ja — jeg har en mal for **{name}**. Best resultat med: {needs}."
            f"{also_bit} Si **Start med {name}** så oppretter jeg prosjektmappen."
        )
        actions = [
            {"id": "link_folder", "label": "Jeg har allerede en mappe"},
        ]
    return {
        "reply": text,
        "kind": "template_match",
        "lang": lang,
        "template_key": t.get("key"),
        "template_file": t.get("file"),
        "offer_folder": True,
        "actions": actions,
    }


def due_diligence_reply(matched: list, caps: dict, lang: str = "no") -> dict:
    """DD / contract-at-volume — capability matching, not invention."""
    # Prefer the full scale answer when we have the DD suite
    return scale_reply(caps, lang=lang, matched=matched)


def is_structure_ask(q: str) -> bool:
    q = _fold(q)
    return any(w in q for w in (
        "foresla struktur", "foreslå struktur", "foresla en struktur",
        "foreslå en struktur", "propose a structure", "propose structure",
        "hvordan en endelig rapport", "hvordan rapporten", "sett ut",
        "forslag til", "forslag til en", "struktur for", "outline a",
        "bruk denne strukturen",
    )) or bool(re.search(r"\b(endelig rapport|final report|rapport.*forslag|forslag.*rapport)\b", q))


def is_check_capability(q: str) -> bool:
    """Follow-ups like 'sjekk først om du kan' after a prior ask."""
    q = _fold(q)
    return any(w in q for w in (
        "sjekk forst", "sjekk først", "sjekk om du kan", "check first",
        "check if you can", "forst om du kan", "først om du kan",
    )) or bool(re.search(r"\bsjekk\b.*\bkan\b|\bcheck\b.*\bcan\b", q))


def list_capabilities(caps: dict, project: dict | None = None, *, tags=None) -> list:
    """Manifest as a tool — full catalog entries for reasoning.

    Domain-locked vehicle fixtures are excluded unless project tag = vehicle.
    """
    import form_model as fm
    templates = fm.filter_templates_for_project(
        list(caps.get("templates") or []), project, tags=tags)
    return [t for t in templates if t.get("key") != "free_document"]


def structure_for_domain(msg: str, lang: str = "no") -> list:
    q = _fold(msg)
    if any(w in q for w in (
        "due diligence", "forsikring", "insurance", "kontrakt", "contract",
        "anbud", "tender", "compliance", "endelig rapport", "final report",
    )):
        if lang == "en":
            return [
                "Executive summary",
                "Parties and agreements",
                "Obligations and deadlines",
                "Open items and risk",
                "Source register",
            ]
        return [
            "Sammendrag",
            "Partsforhold og avtaler",
            "Forpliktelser og frister",
            "Åpne punkter og risiko",
            "Kilderegister",
        ]
    if any(w in q for w in ("phd", "forskning", "research", "thesis")):
        if lang == "en":
            return ["Cover / identification", "Objective", "Method", "Data", "Findings", "Sources"]
        return ["Forside / identifikasjon", "Mål", "Metode", "Data", "Funn", "Kilder"]
    if lang == "en":
        return ["Summary", "Scope", "Findings", "Open items", "Source register"]
    return ["Sammendrag", "Omfang", "Funn", "Åpne punkter", "Kilderegister"]


def structure_reply(caps: dict, lang: str = "no", msg: str = "",
                    matched: list | None = None) -> dict:
    """C4 — render the structure in chat; buttons accompany, never replace."""
    sections = structure_for_domain(msg, lang)
    numbered = " · ".join(f"{i}. {s}" for i, s in enumerate(sections, 1))
    names = []
    for t, _ in (matched or [])[:3]:
        names.append(t.get("name") if lang == "en" else t.get("name_no"))
    if not names:
        by_key = {t.get("key"): t for t in list_capabilities(caps)}
        q = _fold(msg)
        if any(w in q for w in (
            "due diligence", "forsikring", "insurance", "kontrakt", "endelig",
            "final report", "compliance", "anbud",
        )):
            for k in ("contract_review", "spec_coherence_review", "tender_compliance_matrix"):
                if k in by_key:
                    t = by_key[k]
                    names.append(t.get("name") if lang == "en" else t.get("name_no"))

    if lang == "en":
        head = ""
        if names:
            head = (
                f"Closest finished templates: {', '.join(names)}. "
                f"For a final diligence-style report I would structure it like this:\n\n"
            )
        else:
            head = "No exact finished template — here is a structure we can build with you:\n\n"
        text = f"{head}Proposal: {numbered}"
        actions = [
            {"id": "use_structure", "label": "Use this structure",
             "template_key": (matched[0][0].get("key") if matched else "contract_review")},
        ]
    else:
        head = ""
        if names:
            head = (
                f"Nærmeste ferdige maler: {', '.join(names)}. "
                f"For en endelig diligence-/gjennomgangsrapport ville jeg strukturert slik:\n\n"
            )
        else:
            head = "Ingen eksakt ferdig mal — her er en struktur vi kan bygge med deg:\n\n"
        text = f"{head}Forslag: {numbered}"
        actions = [
            {"id": "use_structure", "label": "Bruk denne strukturen",
             "template_key": (matched[0][0].get("key") if matched else "contract_review")},
        ]
    return {
        "reply": text,
        "kind": "structure",
        "lang": lang,
        "template_key": actions[0].get("template_key"),
        "offer_folder": True,
        "actions": actions,
        "structure": sections,
    }


def check_can_reply(caps: dict, lang: str = "no", history: list | None = None) -> dict:
    """Follow-up 'sjekk om du kan' — name real templates; never repeat prior shrug."""
    matched = []
    prev = ""
    for turn in reversed(history or []):
        role = (turn.get("role") or "").lower()
        text = turn.get("text") or turn.get("message") or ""
        if role in ("user", "human") and text and not is_check_capability(text):
            matched = match_templates(text, caps, limit=3, min_score=1)
            prev = text
            break
        if role in ("bot", "assistant") and text:
            prev = text  # last bot — we must not repeat it
            break
    if not matched:
        matched = match_templates(
            prev or "due diligence contract review compliance", caps, limit=3, min_score=1)
    # Prefer DD suite for insurance/diligence contexts
    dd = match_templates("due diligence contract tender compliance", caps, limit=3, min_score=1)
    use = matched or dd
    names = []
    for t, _ in use[:3]:
        names.append(t.get("name") if lang == "en" else t.get("name_no"))
    if not names:
        for t in list_capabilities(caps)[:3]:
            names.append(t.get("name") if lang == "en" else t.get("name_no"))
    if lang == "en":
        text = (
            f"Yes — I can. Closest templates: {', '.join(names)}. "
            f"They produce obligations registers, requirement-vs-evidence matrices, "
            f"and conflict findings cited to clause. Want a sketched report structure?"
        )
    else:
        text = (
            f"Ja — det kan jeg. Nærmeste maler: {', '.join(names)}. "
            f"De lager forpliktelsesregistre, krav-mot-evidens-matriser og "
            f"konfliktfunn sitert til klausul. Skal jeg skissere en rapportstruktur?"
        )
    # Guard: must not equal previous bot reply
    if prev and text.strip() == prev.strip():
        text = text + (" (Confirming capability from the live catalog.)" if lang == "en"
                       else " (Bekreftet mot gjeldende kapabilitetskatalog.)")
    return {
        "reply": text,
        "kind": "check_can",
        "lang": lang,
        "template_key": use[0][0].get("key") if use else "contract_review",
        "actions": [
            {"id": "rung3", "label": "Propose a structure" if lang == "en" else "Foreslå struktur"},
        ],
    }


def rung3_reply(lang: str = "no", msg: str = "", caps: dict | None = None,
                matched: list | None = None) -> dict:
    """Documentation domain, no exact match — SHOW structure inline (C4)."""
    return structure_reply(caps or {}, lang=lang, msg=msg, matched=matched)


def cannot_reply(hit: str, caps: dict, lang: str = "no") -> dict:
    import manifest_claims as mc
    # Drafting boundary → demo offer (C3), not flat refuse alone
    if hit and "utforme" in hit:
        out = mc.demo_offer_reply(lang, kind="contract")
        out["kind"] = "out_of_scope_demo"
        return out
    near = nearest_capability(hit, caps, lang=lang)
    if lang == "en":
        en_map = {
            "tegne eller modellere i 3D": "draw or model in 3D",
            "lese native CAD (DWG/STEP)": "read native CAD (DWG/STEP)",
            "verifisere beregninger": "verify calculations",
            "gi juridisk råd": "give legal advice",
            "gi juridisk vurdering": "give a legal assessment",
            "håndtere beviskjede/chain of custody": "handle chain of custody / evidence chain",
            "utforme juridisk tekst": "draft legal text",
            "signere for deg": "sign for you",
            "finne på verdier som ikke finnes i kilder": "invent values not present in sources",
        }
        label = en_map.get(hit, hit)
        # B4: lead with the boundary (one direction)
        reply = f"I can't {label}. {near}"
    else:
        reply = f"Jeg kan ikke {hit}. {near}"
    return {
        "reply": reply,
        "kind": "out_of_scope",
        "lang": lang,
        "offer_folder": False,
        "actions": [{"id": "create_demo", "label": "Lag demosak" if lang == "no"
                     else "Create demo case", "kind": "contract"}]
        if ("juridisk" in (hit or "") or "bevis" in (hit or "") or "custody" in (hit or ""))
        else [],
    }


FORBIDDEN_HUB = re.compile(
    r"Jeg holder meg til det som st[åa]r i kapabilitetslisten|"
    r"I stay within the published capability list|"
    r"Jeg er ikke sikker",
    re.I,
)

HUB_POLICY = """
You are Foldok's cold-start assistant (no project folder yet).

LENGTH (HARD — WORKORDER_0.21):
- Default ≤120 words. Hard ceiling 200 unless user asks for list/overview/forklar.
- No markdown headings (##). Bold only the document/template name.
- Max ONE short list, ≤5 items. Longer lists belong in SJEKKLISTE.txt (create folder).
- Shape: [what fits / what I did] → [one next step or € offer] → [≤1 question].
- Capability answers: name template(s), one line each on what it produces, the offer.
  Not a curriculum. Do not restate the user's message. No closing pleasantries.

ACT, DON'T DESCRIBE (HARD):
- NEVER tell the user to «lag en ny mappe», «dra inn filene», «velg templaten»,
  «opprett dokumentet» — those are YOUR tools. If they say Start/Lag/Opprett/
  Bruk a template, the engine executes create_project_with_skeleton; you do not
  write an intake essay.
- Banned closers when intent was explicit: «Klar til å starte?», «Skal vi gjøre det?»,
  «Si fra når du er klar».

MONEY (HARD — WORKORDER_0.23):
- € amounts ONLY from the pricing block in CAPABILITIES CONTEXT.
  Index: €0.001–0.01 per file. Export: €9 / €19 / €49. Never invent or arithmetic-ize.
- Never call the index cost an export price.

LEGAL PHRASING (HARD — WORKORDER_0.23):
- Forbidden: evidence handling, bevishåndtering, admissible, chain of custody,
  offering «legal advice».
- Use legal_framing from the manifest when talking to lawyers.
- Do not draft contracts; offer a marked demo project ([Lag demosak]) instead.
- Never «I can X. However, my role is not X.» — one direction per opener.

THE MANIFEST IS A TOOL, NOT A WALL:
- Capability CLAIMS MUST come from CAPABILITIES CONTEXT — never invent features.
- Capability MATCHING is required: map user words to closest listed templates.
  · due diligence / insurance → contract_review, spec_coherence_review, tender_compliance_matrix
  · ROV / subsea / large team / many folders → technical_doc_package, design_basis, spec_coherence_review
  · lawyer / large case → contract_review + legal_framing
- NEVER say you are unsure when any template plausibly matches.
- NEVER use «Jeg holder meg til det som står i kapabilitetslisten» / capability-list shrug.

Scale questions: use the scale block numbers (€ and workers) — index rate only, no invented totals.
Mirror USER LANGUAGE (NO/EN). Voice: warm, professional. No emoji.
""".strip()

BANNED_USER_INSTRUCTIONS = re.compile(
    r"lag en ny mappe|dra inn (alle )?fil|velg templaten|opprett dokumentet|"
    r"legg til bildet|create a new folder|drag (in|the) files|pick the template",
    re.I,
)
BANNED_CLOSERS = re.compile(
    r"klar til [åa] starte\s*\?|skal vi gj[øo]re det\s*\?|"
    r"si fra n[åa]r du er klar|ready to (start|begin)\s*\?|"
    r"shall we (do|start) (it|that)\s*\?",
    re.I,
)


def build_cold_start_context(caps: dict, history: list | None = None) -> str:
    """WORKORDER_0.20 C5 — manifest + full catalog + pricing + scale + history."""
    import hub_session as hses
    session = hses.load_session()
    lines = [
        "=== CAPABILITIES CONTEXT (engine-owned; claims must come from here) ===",
        f"version: {caps.get('version')}",
        f"pricing_json: {json.dumps(caps.get('pricing') or {}, ensure_ascii=False)}",
        f"pricing_no: {caps.get('pricing_line') or ''}",
        f"pricing_en: {caps.get('pricing_line_en') or ''}",
        f"legal_framing: {json.dumps(caps.get('legal_framing') or {}, ensure_ascii=False)}",
        f"forbidden_legal_phrases: {json.dumps(caps.get('forbidden_legal_phrases') or [], ensure_ascii=False)}",
        f"scale_json: {json.dumps(caps.get('scale') or {}, ensure_ascii=False)}",
        f"cannot: {json.dumps(caps.get('cannot') or [], ensure_ascii=False)}",
        f"file_types: {json.dumps(caps.get('file_types') or {}, ensure_ascii=False)}",
        f"privacy_no: {json.dumps(caps.get('privacy') or [], ensure_ascii=False)}",
        f"privacy_en: {json.dumps(caps.get('privacy_en') or [], ensure_ascii=False)}",
    ]
    moved = caps.get("cannot_moved_to_limits") or []
    if moved:
        lines.append(
            f"cannot_moved_to_limits: {json.dumps(moved, ensure_ascii=False)} "
            "(scoped inside engine capabilities — do not treat as global denials)"
        )
    shipped = caps.get("capabilities") or []
    if shipped:
        lines.extend([
            "",
            "SHIPPED CAPABILITIES (engine-owned — you MAY claim these when the user asks):",
        ])
        for c in shipped:
            if not isinstance(c, dict):
                continue
            lines.append(
                f"- id={c.get('id')} | summary: {c.get('summary') or c.get('object') or ''}"
            )
            if c.get("produces"):
                lines.append(f"  produces: {', '.join(c['produces'])}")
            if c.get("anchors"):
                lines.append(f"  anchors: {', '.join(c['anchors'][:8])}")
            for lim in c.get("limits") or []:
                if isinstance(lim, dict) and lim.get("text"):
                    lines.append(f"  not: {lim['text']}")
    lines.extend([
        "",
        hses.format_events_for_prompt(session),
        "",
        "TEMPLATES (full catalog — match user intent to these):",
    ])
    for t in list_capabilities(caps):
        lines.append(
            f"- key={t.get('key')} | NO: {t.get('name_no')} | EN: {t.get('name')}"
        )
        if t.get("one_liner"):
            lines.append(f"  one_liner: {t['one_liner']}")
        if t.get("description"):
            lines.append(f"  description: {(t.get('description') or '')[:480]}")
        if t.get("applies_to"):
            lines.append(f"  applies_to: {', '.join(t['applies_to'])}")
        if t.get("needs"):
            lines.append(f"  needs: {', '.join(t['needs'][:8])}")
        if t.get("group"):
            lines.append(f"  group: {t['group']}")
    hist = history or []
    lines.append("")
    lines.append("HUB CONVERSATION HISTORY:")
    if not hist:
        lines.append("(empty)")
    else:
        for turn in hist[-16:]:
            role = (turn.get("role") or "?").upper()
            text = (turn.get("text") or turn.get("message") or "").strip()
            if len(text) > 500:
                text = text[:500] + "…"
            if text:
                lines.append(f"{role}: {text}")
    lines.append("=== END CAPABILITIES CONTEXT ===")
    return "\n".join(lines)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def heading_count(text: str) -> int:
    return len(re.findall(r"(?m)^#{1,6}\s", text or ""))


def enforce_reply_budget(text: str, *, max_words: int = 120, hard_ceiling: int = 200,
                         allow_long: bool = False) -> str:
    """WORKORDER_0.21 B — strip headings, banned closers/instructions, cap length."""
    if not text:
        return text
    # Drop markdown headings
    text = re.sub(r"(?m)^#{1,6}\s+.*$", "", text)
    text = BANNED_CLOSERS.sub("", text)
    text = BANNED_USER_INSTRUCTIONS.sub("", text)
    text = FORBIDDEN_HUB.sub("", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # Collapse overlong bullet lists to 5 items
    lines = text.splitlines()
    bullets, out_lines, bullet_n = [], [], 0
    for ln in lines:
        if re.match(r"^\s*([-*•]|\d+\.)\s+", ln):
            bullet_n += 1
            if bullet_n <= 5:
                out_lines.append(ln)
            elif bullet_n == 6:
                out_lines.append("…")
        else:
            bullet_n = 0
            out_lines.append(ln)
    text = "\n".join(out_lines).strip()
    limit = hard_ceiling if allow_long else max_words
    if hard_ceiling and word_count(text) > hard_ceiling:
        limit = hard_ceiling
    if word_count(text) <= limit:
        return text
    # Truncate at sentence boundary near limit
    words = re.findall(r"\S+|\s+", text)
    kept, n = [], 0
    for tok in words:
        if tok.strip():
            n += 1
            if n > limit:
                break
        kept.append(tok)
    cut = "".join(kept).rstrip(" ,;:")
    # Prefer ending on . ! ? if nearby
    m = re.search(r"^(.*[.!?])\s", cut + " ", re.S)
    if m and word_count(m.group(1)) >= max(20, limit // 3):
        cut = m.group(1)
    return cut.strip()


def scrub_hub_reply(text: str, *, allow_long: bool = False) -> str:
    text = enforce_reply_budget(text, allow_long=allow_long)
    return text


def checklist_preview(caps_entry: dict | None, limit: int = 4) -> tuple:
    """Return (count, preview_csv) from template checklist / needs."""
    items = []
    if caps_entry:
        for line in caps_entry.get("checklist") or []:
            items.append(re.sub(r"^[□\[\]\s]+", "", line).strip())
        if not items:
            items = list(caps_entry.get("needs") or [])
    items = [x for x in items if x]
    preview = ", ".join(items[:limit])
    if len(items) > limit:
        preview += "…"
    return len(items) or 0, preview or "prosjektfiler"


def infer_project_name(history: list | None, template: dict | None, msg: str = "") -> str:
    """Name like 'ROV — Design Basis' from hub history + chosen template."""
    blob = _fold(" ".join(
        (t.get("text") or t.get("message") or "") for t in (history or [])
    ) + " " + (msg or ""))
    prefix = ""
    if "rov" in blob or "subsea" in blob or "undervann" in blob:
        prefix = "ROV"
    elif "forsikring" in blob or "insurance" in blob:
        prefix = "Due diligence"
    elif "phd" in blob or "forskning" in blob:
        prefix = "PhD"
    t = template or {}
    # Prefer short EN name for Design Basis; else first clause of name_no
    label = (t.get("name") or "").strip()
    if not label or len(label) > 40:
        label = (t.get("name_no") or t.get("key") or "Prosjekt").split("/")[0].strip()
    if prefix:
        return f"{prefix} — {label}"
    return label


def is_start_instruction(msg: str) -> bool:
    """«Start med Design Basis» / «Opprett …» / «Lag prosjekt med …»."""
    q = _fold(msg)
    if not q:
        return False
    if re.search(r"\b(start|opprett|lag|bruk|sett|generer)\b", q):
        # Must point at a document/template, not a vague chat
        if any(w in q for w in (
            "design basis", "designgrunnlag", "designgrunn", "sja", "samsvar",
            "kontrakt", "contract", "manual", "rapport", "dokument", "mal",
            "technical", "teknisk", "tender", "anbud", "prosjektmappe", "mappe",
            "template", "basis",
        )):
            return True
        if re.search(r"\bstart med\b", q):
            return True
    return False


def resolve_start_template(msg: str, caps: dict) -> dict | None:
    """Pick the template the user told us to start with."""
    q = _fold(msg)
    by_key = {t.get("key"): t for t in list_capabilities(caps)}
    # Explicit well-known names first
    aliases = [
        (("design basis", "designgrunnlag", "designgrunn"), "design_basis"),
        (("brukermanual", "bruksanvisning", "user manual", "instructions for use"), "user_manual"),
        (("inspeksjonssjekkliste", "inspection checklist", "kontrollskjema", "egenkontroll"),
         "inspection_checklist"),
        (("installasjonsmanual", "installation manual"), "installation_manual"),
        (("technical doc", "teknisk dokument", "dokumentasjonspakke"), "technical_doc_package"),
        (("spec coherence", "spesifikasjonsgjennomgang"), "spec_coherence_review"),
        (("contract review", "kontraktsgjennomgang", "obligations"), "contract_review"),
        (("tender", "anbudssamsvar"), "tender_compliance_matrix"),
        (("sja", "sikker jobbanalyse"), "sja"),
        (("samsvarserklaering", "samsvarserklæring", "declaration of conformity"), "samsvarserklaering"),
    ]
    for words, key in aliases:
        if any(w in q for w in words) and key in by_key:
            return by_key[key]
    # Fuzzy: strip imperative prefix and match
    cleaned = re.sub(
        r"^(start med|opprett|lag|bruk|sett i gang med|generer)\s+",
        "", q, flags=re.I,
    ).strip()
    if cleaned:
        ranked = match_templates(cleaned, caps, limit=1, min_score=2)
        if ranked:
            return ranked[0][0]
    ranked = match_templates(msg, caps, limit=1, min_score=3)
    return ranked[0][0] if ranked else None


def created_folder_reply(name: str, caps_entry: dict | None, lang: str = "no") -> str:
    """WORKORDER_0.21 reference shape — ~60 words, one action, one question."""
    n, preview = checklist_preview(caps_entry, limit=4)
    if lang == "en":
        return (
            f"Created project folder **{name}** with Bilder/, Tegninger/, Rapporter/, "
            f"Notater/ and SJEKKLISTE.txt ({n} items from the template: {preview}). "
            f"Drop in what you have — I index as files arrive. "
            f"Does the project have a document number, or shall I set Rev. A / Draft?"
        )
    return (
        f"Opprettet prosjektmappe **{name}** med Bilder/, Tegninger/, Rapporter/, "
        f"Notater/ og SJEKKLISTE.txt ({n} punkter fra malen: {preview}). "
        f"Legg inn det du har — jeg indekserer fortløpende. "
        f"Har prosjektet et dokumentnummer, eller setter jeg Rev. A / Draft?"
    )


def start_demo_plan(msg: str, caps: dict, history: list | None = None) -> dict | None:
    """WORKORDER_0.23 C — Lag demosak / Create demo case → execute."""
    q = _fold(msg)
    if not re.search(r"\b(lag demosak|create demo|spin up.*(demo|sample)|start demo)\b", q):
        # Confirm pending demo
        return None
    kind = "technical" if any(w in q for w in ("technical", "teknisk", "lifting", "lofte")) else "contract"
    lang = detect_lang(msg)
    name = "DEMO_Løfteverktøy" if kind == "technical" else "DEMO_Kontraktsak"
    tkey = "technical_doc_package" if kind == "technical" else "contract_review"
    return {
        "execute": {"tool": "create_demo_project", "kind": kind, "name": name,
                    "template_key": tkey},
        "kind": "execute_demo",
        "lang": lang,
        "project_name": name,
        "template_key": tkey,
        "model_called": False,
        "reply": None,
    }


def apply_manifest_validators(out: dict, caps: dict, lang: str) -> dict:
    """WORKORDER_0.23 A2/B + 0.25 C — money, legal, completion/progress receipts."""
    import manifest_claims as mc
    import agent_truth as atruth
    import hub_session as hses
    reply = out.get("reply") or ""
    ok_m, _, reason_m = mc.validate_money_claims(reply, caps)
    if not ok_m:
        out["reply"] = mc.money_fallback(caps, lang)
        out["validator"] = reason_m
        return out
    ok_l, _, reason_l = mc.validate_legal_phrasing(reply, caps)
    if not ok_l:
        if reason_l == "however_role_shape":
            out["reply"] = mc.legal_prospect_reply(caps, lang)["reply"]
        else:
            out["reply"] = mc.legal_fallback(caps, lang)
        out["validator"] = reason_l
        reply = out["reply"]
    tools = []
    if out.get("tool"):
        tools.append(out["tool"] if isinstance(out["tool"], dict) else {"tool": out["tool"], "ok": True})
    if out.get("tool_receipt"):
        tools.append(out["tool_receipt"])
    if out.get("execute") and out.get("kind") == "dispatch_pending":
        tools.append({"tool": "dispatch_pending", "ok": True})
    ok_c, reply_c, reason_c = atruth.validate_completion_claims(reply, tools, lang=lang)
    if not ok_c:
        out["reply"] = reply_c
        out["validator"] = reason_c
        return out
    ok_a, reply_a, reason_a = atruth.validate_chat_artifacts(
        out.get("reply") or "", user_msg="", lang=lang, enforce_prose_cap=False)
    if not ok_a:
        out["reply"] = reply_a
        out["validator"] = reason_a
        return out
    session = hses.load_session()
    if hses.proposal_reask_violation(reply, session):
        # Already asked — strip to short confirmation CTA only
        pending = session.get("pending_action") or {}
        label = pending.get("offer_label") or ("Opprett prosjekt →" if lang != "en" else "Create project →")
        out["reply"] = (
            f"Bekreft med **ja** eller trykk «{label}»."
            if lang != "en" else
            f"Confirm with **yes** or press «{label}»."
        )
        out["validator"] = "confirm_reask"
        out["actions"] = [{
            "id": "create_project",
            "label": label,
            "token": (pending.get("args") or {}).get("token"),
        }] if pending.get("tool") == "create_project_from_staged" else out.get("actions") or []
    return out


def start_project_plan(msg: str, caps: dict, history: list | None = None) -> dict | None:
    """If message is a start instruction, return execute plan (zero-token)."""
    if not is_start_instruction(msg):
        return None
    tmpl = resolve_start_template(msg, caps)
    if not tmpl:
        return None
    lang = detect_lang(msg)
    name = infer_project_name(history, tmpl, msg)
    return {
        "execute": {
            "tool": "create_project_with_skeleton",
            "name": name,
            "template_key": tmpl.get("key"),
        },
        "kind": "execute_create",
        "lang": lang,
        "template_key": tmpl.get("key"),
        "template": tmpl,
        "project_name": name,
        "model_called": False,
        "reply": None,  # filled after execute
    }


def suggest_hub_actions(msg: str, caps: dict, lang: str) -> tuple:
    """Soft CTAs for hub replies — no «tom mappe» / catalog pills (UI declutter)."""
    matched = match_templates(msg, caps, limit=1, min_score=2)
    if not matched:
        matched = match_templates(msg, caps, limit=1, min_score=1)
    tkey = matched[0][0].get("key") if matched else None
    actions = []
    if is_structure_ask(msg) or "struktur" in _fold(msg):
        actions.append({
            "id": "use_structure",
            "label": "Use this structure" if lang == "en" else "Bruk denne strukturen",
            "template_key": tkey or "contract_review",
        })
    return actions, tkey


def hub_chat_offline(message: str, caps: dict | None = None,
                     history: list | None = None) -> dict:
    """Deterministic reasoner — ONLY when no API key (tests / browse-only).

    Never used as a gate in front of the model when a key is present
    (WORKORDER_0.20 C2-BIS).
    """
    caps = caps or load_capabilities()
    msg = (message or "").strip()
    lang = detect_lang(msg)
    history = history or []
    if not msg:
        return {
            "reply": "What would you like to make?" if lang == "en" else "Hva vil du lage?",
            "kind": "empty", "lang": lang, "actions": [], "model_called": False,
        }

    if is_privacy_question(msg):
        return {"reply": privacy_reply(caps, lang), "kind": "privacy", "lang": lang,
                "actions": [], "model_called": False}

    import manifest_claims as mc
    if is_pricing_question(msg):
        return {"reply": mc.pricing_reply(caps, lang), "kind": "pricing", "lang": lang,
                "actions": [], "model_called": False}

    if is_demo_request(msg):
        out = mc.demo_offer_reply(lang, kind="contract")
        out["model_called"] = False
        return out

    if is_legal_prospect(msg):
        out = mc.legal_prospect_reply(caps, lang)
        out["model_called"] = False
        return out

    if is_catalog_question(msg):
        return {
            "reply": catalog_reply(caps, lang),
            "kind": "catalog", "lang": lang, "model_called": False,
            "actions": [],
        }

    # foldok_route 0.85 — before CAD cannot, or wiring asks get the wrong refusal
    routed = try_diagram_route(msg, lang)
    if routed:
        return routed

    cannot_hit = match_cannot(msg, caps)
    hard_oos = cannot_hit and any(w in _fold(msg) for w in (
        "tegne hus", "dwg", "step", "solidworks", "native cad",
        "draw my house", "3d model", "3d-modell", "verify calculations", "beregn for meg",
        "legal advice", "signer for meg", "sign for me",
        "draft a contract", "write a contract", "utform", "skriv en kontrakt",
        "chain of custody", "beviskjede",
    ))
    if hard_oos:
        out = cannot_reply(cannot_hit, caps, lang=lang)
        out["model_called"] = False
        return out

    if is_check_capability(msg):
        out = check_can_reply(caps, lang=lang, history=history)
        out["model_called"] = False
        return out

    matched = match_templates(msg, caps, limit=3, min_score=3)
    soft = match_templates(msg, caps, limit=3, min_score=2)
    qf = _fold(msg)
    dd_intent = any(w in qf for w in (
        "due diligence", "duediligence", "compliance matrix", "obligations register",
        "requirement vs evidence", "conflict detection", "data room", "dataroom",
        "virtual data room", "forsikring", "insurance", "endelig rapport", "final report",
    ))
    rov_intent = any(w in qf for w in (
        "rov", "subsea", "undervann", "mange foldere", "mange mapper", "stort team",
        "technical doc", "teknisk dokument",
    ))

    if is_structure_ask(msg):
        dd = soft if dd_intent else (soft or matched or match_templates(
            "contract review tender compliance", caps, limit=3, min_score=1))
        if dd_intent and not dd:
            dd = match_templates("due diligence", caps, limit=3, min_score=1)
        out = structure_reply(caps, lang=lang, msg=msg, matched=dd or matched)
        out["model_called"] = False
        return out

    if is_scale_question(msg) or (dd_intent and any(
            w in qf for w in ("folder", "file", "mappe", "fil", "thousand", "hundred",
                              "tusenvis", "hundrevis", "many", "large", "stor"))):
        dd = soft if dd_intent else (soft or matched)
        out = scale_reply(caps, lang=lang, matched=dd or matched)
        out["model_called"] = False
        return out

    if dd_intent:
        dd = soft or matched or match_templates(msg, caps, limit=3, min_score=1)
        if dd:
            if any(w in qf for w in ("rapport", "report", "forslag", "proposal", "struktur")):
                out = structure_reply(caps, lang=lang, msg=msg, matched=dd)
            else:
                out = due_diligence_reply(dd, caps, lang=lang)
            out["model_called"] = False
            return out

    if rov_intent:
        suite = match_templates(
            "technical documentation design basis spec coherence rov subsea",
            caps, limit=3, min_score=1)
        if suite:
            top, _ = suite[0]
            out = template_yes_reply(top, lang=lang, also=[t for t, _ in suite[1:]])
            out["model_called"] = False
            return out

    if matched:
        top, _ = matched[0]
        also = [t for t, _ in matched[1:]]
        keys = {t.get("key") for t, _ in matched}
        if len(keys & {"contract_review", "spec_coherence_review", "tender_compliance_matrix"}) >= 2:
            out = due_diligence_reply(matched, caps, lang=lang)
        else:
            out = template_yes_reply(top, lang=lang, also=also)
        out["model_called"] = False
        return out

    if soft and (is_can_you_make(msg) or is_documentation_domain(msg)):
        top, _ = soft[0]
        out = template_yes_reply(top, lang=lang, also=[t for t, _ in soft[1:]])
        out["model_called"] = False
        return out

    if is_can_you_make(msg) or is_documentation_domain(msg):
        out = rung3_reply(lang=lang, msg=msg, caps=caps, matched=soft or matched)
        out["model_called"] = False
        return out

    if cannot_hit:
        out = cannot_reply(cannot_hit, caps, lang=lang)
        out["model_called"] = False
        return out

    weakest = match_templates(msg, caps, limit=1, min_score=1)
    if weakest:
        out = template_yes_reply(weakest[0][0], lang=lang)
        out["model_called"] = False
        return out

    cat = catalog_reply(caps, lang)
    reply = cat + ("\n\nWhat should we build first?" if lang == "en"
                   else "\n\nHva skal vi bygge først?")
    return {
        "reply": reply, "kind": "catalog", "lang": lang, "model_called": False,
        "actions": [],
    }


def hub_chat(message: str, caps: dict | None = None, history: list | None = None,
             *, ask_fn=None, force_offline: bool = False) -> dict:
    """Cold-start entry — WORKORDER_0.20 C2-BIS + 0.21 act-don't-describe.

    Start/Lag/Opprett instructions execute create_project_with_skeleton
    (zero-token) — never an intake essay. Other messages go to the model
    with §C5 context; replies are length-budgeted.
    """
    caps = caps or load_capabilities()
    msg = (message or "").strip()
    lang = detect_lang(msg)
    history = history or []

    if not msg:
        return {
            "reply": "What would you like to make?" if lang == "en" else "Hva vil du lage?",
            "kind": "empty", "lang": lang, "actions": [], "model_called": False,
        }

    # WORKORDER_0.25 B — affirmative dispatches pending_action (no re-ask)
    import hub_session as hses
    import agent_truth as atruth
    session = hses.load_session()
    pending = session.get("pending_action")
    if pending and hses.is_affirmative(msg):
        hses.append_event(session, "user", msg)
        # Keep pending until server execute succeeds (need_base_dir may retry)
        hses.save_session(session)
        return {
            "execute": {
                "tool": pending.get("tool"),
                **(pending.get("args") or {}),
            },
            "kind": "dispatch_pending",
            "lang": lang,
            "model_called": False,
            "reply": None,
            "pending_dispatched": pending,
            "tool_receipt": {"tool": "dispatch_pending", "ok": True,
                             "dispatched": pending.get("tool")},
        }

    # WORKORDER_0.21 A — instruction → execute plan (server performs create)
    plan = start_project_plan(msg, caps, history)
    if plan:
        return plan

    # WORKORDER_0.23 C — Lag demosak / Create demo case
    demo_plan = start_demo_plan(msg, caps, history)
    if demo_plan:
        return demo_plan

    # Ground next replies in staged extractions (D1)
    if session.get("staged") and re.search(
            r"hjelpe|help|denne|this|filen|file|hva kan", _fold(msg)):
        staged = session["staged"][-1]
        lang_s = lang
        keys = ", ".join(staged.get("fact_keys") or []) or "—"
        if lang_s == "en":
            reply = (
                f"Indeksert som: {staged.get('caption') or staged.get('name')}. "
                f"Found keys: {keys}. I can open a project around "
                f"**{staged.get('name')}** and run a matching review."
            )
        else:
            reply = (
                f"Indeksert som: {staged.get('caption') or staged.get('name')}. "
                f"Funnet: {keys}. Jeg kan opprette et prosjekt rundt "
                f"**{staged.get('name')}** og kjøre en passende gjennomgang."
            )
        if not session.get("pending_action"):
            pend = hses.set_pending(
                session, "create_project_from_staged",
                {"token": staged.get("token"), "name": Path(staged.get("name") or "Prosjekt").stem},
                offer_label="Opprett prosjekt →" if lang_s != "en" else "Create project →")
            hses.mark_action_asked(session, pend["fingerprint"])
            hses.save_session(session)
            actions = [{"id": "create_project", "label": pend["offer_label"],
                        "token": staged.get("token")}]
        else:
            pend = session["pending_action"]
            actions = [{"id": "create_project",
                        "label": pend.get("offer_label") or "Opprett prosjekt →",
                        "token": (pend.get("args") or {}).get("token")}]
        hses.append_event(session, "user", msg)
        hses.append_event(session, "bot", reply)
        hses.save_session(session)
        return apply_manifest_validators({
            "reply": reply, "kind": "staged_grounded", "lang": lang_s,
            "actions": actions, "model_called": False,
            "pending_action": session.get("pending_action"),
        }, caps, lang_s)

    import manifest_claims as mc

    # Zero-token lookup: approved privacy sentences from the manifest
    if is_privacy_question(msg):
        return {
            "reply": privacy_reply(caps, lang), "kind": "privacy", "lang": lang,
            "actions": [], "model_called": False,
        }

    if is_pricing_question(msg):
        return {
            "reply": mc.pricing_reply(caps, lang), "kind": "pricing", "lang": lang,
            "actions": [], "model_called": False,
        }

    if is_demo_request(msg):
        out = mc.demo_offer_reply(lang, kind="contract")
        out["model_called"] = False
        return out

    if is_legal_prospect(msg):
        out = mc.legal_prospect_reply(caps, lang)
        out["model_called"] = False
        return out

    # foldok_route 0.85 — before CAD cannot
    routed = try_diagram_route(msg, lang)
    if routed:
        return apply_manifest_validators(routed, caps, lang)

    # Zero-token lookup: unambiguous cannot-list boundary
    cannot_hit = match_cannot(msg, caps)
    hard_oos = cannot_hit and any(w in _fold(msg) for w in (
        "tegne hus", "dwg", "step", "solidworks", "native cad",
        "draw my house", "3d model", "3d-modell", "verify calculations", "beregn for meg",
        "legal advice", "signer for meg", "sign for me",
        "draft a contract", "write a contract", "skriv en kontrakt",
        "chain of custody", "beviskjede",
    ))
    if hard_oos or (cannot_hit and is_draft_legal_request(msg)):
        out = cannot_reply(cannot_hit or "utforme juridisk tekst", caps, lang=lang)
        out["model_called"] = False
        out["reply"] = enforce_reply_budget(out.get("reply") or "")
        return out

    allow_long = bool(re.search(r"\b(forklar|overview|oversikt|list|katalog|detalj)\b",
                                _fold(msg)))

    if force_offline:
        out = hub_chat_offline(msg, caps, history)
        out["reply"] = enforce_reply_budget(out.get("reply") or "", allow_long=allow_long)
        return apply_manifest_validators(out, caps, lang)

    if ask_fn is None:
        try:
            import os
            import foldok_compile as fc
            if len(os.environ.get("ANTHROPIC_API_KEY", "")) > 30:
                ask_fn = fc.ask
        except Exception:
            ask_fn = None

    if ask_fn is None:
        out = hub_chat_offline(msg, caps, history)
        out["reply"] = enforce_reply_budget(out.get("reply") or "", allow_long=allow_long)
        return apply_manifest_validators(out, caps, lang)

    ctx = build_cold_start_context(caps, history)
    prompt = (
        f"{ctx}\n\n"
        f"USER LANGUAGE: {'English' if lang == 'en' else 'Norwegian'}\n"
        f"USER: {msg}\n\n"
        f"Reply in ≤120 words. Name matching templates (one line each). "
        f"Offer next step. Never tell the user to create a folder or drag files in. "
        f"Never end with «Klar til å starte?». "
        f"€ amounts only from pricing_json. No evidence-handling claims."
    )
    try:
        raw = ask_fn(
            "hub_chat",
            getattr(__import__("foldok_compile", fromlist=["HAIKU"]), "HAIKU",
                    "claude-haiku-4-5-20251001"),
            [{"role": "user", "content": prompt}],
            system=HUB_POLICY,
            max_tokens=500,
        )
        reply = scrub_hub_reply((raw or "").strip(), allow_long=allow_long)
        if FORBIDDEN_HUB.search(reply or "") or BANNED_CLOSERS.search(reply or "") or not reply:
            raw2 = ask_fn(
                "hub_chat",
                getattr(__import__("foldok_compile", fromlist=["HAIKU"]), "HAIKU",
                        "claude-haiku-4-5-20251001"),
                [{"role": "user", "content": prompt +
                  "\n\nPREVIOUS REPLY VIOLATED POLICY (too long / shrug / told user to "
                  "create folder). Rewrite ≤120 words: name templates, one offer, ≤1 question."}],
                system=HUB_POLICY,
                max_tokens=400,
            )
            reply = scrub_hub_reply((raw2 or "").strip(), allow_long=allow_long)
        # Money / legal validators — one retry then fallback
        ok_m, _, reason_m = mc.validate_money_claims(reply or "", caps)
        ok_l, _, reason_l = mc.validate_legal_phrasing(reply or "", caps)
        if not ok_m or not ok_l:
            reason = reason_m or reason_l
            try:
                raw3 = ask_fn(
                    "hub_chat",
                    getattr(__import__("foldok_compile", fromlist=["HAIKU"]), "HAIKU",
                            "claude-haiku-4-5-20251001"),
                    [{"role": "user", "content": prompt +
                      f"\n\nPREVIOUS REPLY VIOLATED MANIFEST ({reason}). "
                      f"Rewrite using only pricing_json amounts and legal_framing. "
                      f"No forbidden legal phrases. No invented € totals."}],
                    system=HUB_POLICY,
                    max_tokens=400,
                )
                reply = scrub_hub_reply((raw3 or "").strip(), allow_long=allow_long)
            except Exception:
                pass
        if not reply:
            out = hub_chat_offline(msg, caps, history)
            out["reply"] = enforce_reply_budget(out.get("reply") or "", allow_long=allow_long)
            out["model_called"] = True
            out["kind"] = "model_empty_fallback"
            return apply_manifest_validators(out, caps, lang)
        actions, tkey = suggest_hub_actions(msg, caps, lang)
        cost = 0.0
        try:
            import foldok_compile as fc
            if fc.LEDGER:
                cost = round(fc.LEDGER[-1]["eur"], 4)
        except Exception:
            pass
        out = {
            "reply": reply,
            "kind": "model",
            "lang": lang,
            "template_key": tkey,
            "offer_folder": True,
            "actions": actions,
            "model_called": True,
            "cost_eur": cost,
        }
        return apply_manifest_validators(out, caps, lang)
    except Exception as e:
        print(f"[hub/chat] model error → offline reasoner: {e}", flush=True)
        out = hub_chat_offline(msg, caps, history)
        out["reply"] = enforce_reply_budget(out.get("reply") or "", allow_long=allow_long)
        out["model_error"] = str(e)
        return apply_manifest_validators(out, caps, lang)


def write_checklist(folder: Path, caps_entry: dict | None = None):
    lines = [
        "SJEKKLISTE — ta med / legg i mappen",
        "=" * 40,
        "",
    ]
    if caps_entry and caps_entry.get("checklist"):
        lines.extend(caps_entry["checklist"])
    else:
        lines.append("□ Prosjektfiler (PDF, bilder, notater)")
    lines.extend(["", "Mapper: Bilder/  Tegninger/  Rapporter/  Notater/", ""])
    (folder / "SJEKKLISTE.txt").write_text("\n".join(lines), encoding="utf-8")


def create_skeleton_folder(base_dir: Path, name: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', "_", (name or "Prosjekt").strip()) or "Prosjekt"
    folder = Path(base_dir) / safe
    n = 2
    while folder.exists():
        folder = Path(base_dir) / f"{safe} ({n})"
        n += 1
    folder.mkdir(parents=True, exist_ok=False)
    for sub in SKELETON_DIRS:
        (folder / sub).mkdir(exist_ok=True)
    return folder
