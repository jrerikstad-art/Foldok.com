"""Installation manual — corpus-aware compile (not generic fact dump).

Contract:
  1. ``system_under_install`` is locked before plan/generate.
  2. Facts come only from an install allowlist (or named focus sources).
  3. Strategy PDFs + standards lists → stay thin (permission to be empty).
  4. User names any install source («bruk …» / «utvid med …») — no vendor list.
  5. Kilderegister = cited files only; unused high-value PDFs offered.

No project- or vendor-specific names are hard-coded. Focus needles are whatever
the user types; they match indexed paths/captions by substring.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

# Canonical values persisted on artifact["system_under_install"]
SYSTEM_VALUES = (
    "cable_tray",
    "sensor",
    "machine",
    "enclosure",
    "other",
)

SYSTEM_ALIASES: list[tuple[str, re.Pattern[str]]] = [
    ("cable_tray", re.compile(
        r"(?i)\b(cable\s*tray|kabelrenne|wire\s*tray|cable\s*ladder|"
        r"renne|tray\s*system|kabelbro)\b")),
    ("sensor", re.compile(
        r"(?i)\b(sensor|encoder|transmitter|probe|måler|giver|"
        r"laser\s*scanner|safety\s*camera|photoelectric|lidar)\b")),
    ("machine", re.compile(
        r"(?i)\b(machine|maskin|equipment|anlegg|unit|apparat|motor)\b")),
    ("enclosure", re.compile(
        r"(?i)\b(enclosure|skap|kabinett|cabinet|panel\s*board)\b")),
    ("other", re.compile(r"(?i)\b(other|annet|øvrig|misc)\b")),
]

# Generic install vocabulary — not a project corpus.
# Includes technical-info / background docs that carry mounting & wiring tips
# even when the filename has no "install"/"manual" token.
INSTALL_LEXICON = re.compile(
    r"(?i)\b("
    r"install|installation|installasjon|monter|montage|mount|mounting|"
    r"commission|idrift|wiring|tilkobling|connection|torque|moment|"
    r"clearance|avstand|fasten|feste|bolt|screw|bracket|brakett|"
    r"procedure|prosedyre|step|trinn|sekvens|sequence|"
    r"hazard|fare|safety|sikkerhet|ppe|earthing|jording|"
    r"datasheet|manual|bruksanvisning|operating\s*instructions|"
    r"technical\s*information|background\s*knowledge|application\s*note|"
    r"guideline|guidelines|tip|tips|best\s*practice|"
    r"shield|shielding|equipotential|ground\s*loop|cable\s*routing|"
    r"mains\s*filter|functional\s*earth|"
    r"laser|scanner|camera|sensor|tray|renne"
    r")\b"
)

MARKET_BOD_RX = re.compile(
    r"(?i)\b("
    r"bod|board\s*of\s*directors|styre|"
    r"persona|personas|buyer\s*persona|brukerpersona|"
    r"hypothesis|hypotese|hypotes|"
    r"market\s*(size|analysis|segment)|markedsanalyse|markedsandel|"
    r"competitive|konkurrent|go[\s-]?to[\s-]?market|gtm|"
    r"pitch|investor|business\s*case|opportunity|"
    r"swot|pestel|roadmap\s*slide|workshop\s*notes"
    r")\b"
)

MARKET_BOD_PATH_RX = re.compile(
    r"(?i)(bod|persona|market|hypothes|investor|pitch|swot|"
    r"business[\s_-]?case|competitive|workshop)"
)

# Engineering identity only — not marketing/org facts
IDENTITY_ALLOW = {
    "project_name", "project_title", "address", "site_address", "anleggsadresse",
    "system_type", "system_under_install", "manufacturer", "supplier", "leverandør",
    "product_name", "part_number", "model", "type_designation", "capacity",
    "serial_number", "tag", "drawing_number", "revision", "site", "location",
    "voltage", "power", "weight", "dimensions", "ip_rating", "protection_class",
}
IDENTITY_ALLOW_PREFIX = (
    "project_", "system_", "product_", "part_", "model_", "type_",
    "manufacturer", "supplier", "capacity", "rated_", "nominal_",
)
IDENTITY_DENY = {
    "persona", "personas", "hypothesis", "hypotese", "market_size",
    "market_segment", "competitive", "buyer", "stakeholder", "owner",
    "ceo", "cfo", "board", "investor", "opportunity", "swot",
    "email", "phone", "website", "linkedin", "slogan", "tagline",
    "author_name", "scope_statement",
}
IDENTITY_DENY_RX = re.compile(
    r"(?i)\b(persona|hypotese|hypothesis|marked|market\s*size|"
    r"konkurrent|investor|styre|board\s*of)\b"
)

PROCEDURE_SECTION_KEYS = frozenset({
    "sequence", "safety", "verification", "prerequisites",
})

PROCEDURE_SIGNAL_RX = re.compile(
    r"(?i)\b("
    r"install|installation|installasjon|monter|montage|mount|"
    r"procedure|prosedyre|step\s*\d|trinn\s*\d|"
    r"torque|moment|wiring|tilkobling|commission|"
    r"hazard|fare|warning|advarsel|ppe|"
    r"clearance|fasten|bolt|bracket|"
    r"shield|shielding|earthing|jording|ground\s*strap|"
    r"cable\s*routing|mains\s*filter|equipotential|"
    r"technical\s*information|guideline|tip"
    r")\b"
)

# Fact keys / values that read as install tips (not market sludge)
TIP_FACT_RX = re.compile(
    r"(?i)("
    r"install|mount|wire|wiring|shield|earth|ground|torque|clearance|"
    r"filter|connection|routing|fasten|bolt|brace|hazard|warning|ppe|"
    r"cable|bond|strap|prepare|avoid|prefer|must|shall|always|never|"
    r"selv|protection_class|fault|off.?state|connector|coverage"
    r")"
)

SECTION_TIP_RX: dict[str, re.Pattern[str]] = {
    "safety": re.compile(
        r"(?i)(hazard|warning|safety|ppe|protection|selv|fault|off.?state|danger|class)"
    ),
    "prerequisites": re.compile(
        r"(?i)(prerequisite|prepare|material|cable|connector|shield_type|"
        r"coverage|class|voltage|selv|rating|insulation)"
    ),
    "sequence": re.compile(
        r"(?i)(install|mount|connect|filter|ground|earth|routing|strap|"
        r"bond|fasten|torque|wiring|shield|cabinet|entry)"
    ),
    "verification": re.compile(
        r"(?i)(verify|check|test|measure|confirm|inspection|coverage|limit)"
    ),
}

# Single-assignment claim buckets (install compile plan)
CLAIM_BUCKETS = (
    "identity",
    "overview",
    "prerequisites",
    "safety",
    "checks",
    "sequence",
    "supplier_only",
)
# Tie-break when scores equal — prefer actionable install content
CLAIM_BUCKET_TIEBREAK = (
    "sequence", "safety", "prerequisites", "checks", "overview", "identity", "supplier_only",
)
BUCKET_SECTION = {
    "identity": "identification",
    "overview": "system_overview",
    "prerequisites": "prerequisites",
    "safety": "safety",
    "checks": "verification",
    "sequence": "sequence",
}
SECTION_BUCKET = {v: k for k, v in BUCKET_SECTION.items()}

SEQUENCE_PHASE_RX: list[tuple[int, re.Pattern[str]]] = [
    (0, re.compile(r"(?i)\b(prepar|prerequisite|before\s+install|material|tool)\b")),
    (1, re.compile(r"(?i)\b(mount|monter|fasten|fix|bolt|bracket|fix)\b")),
    (2, re.compile(r"(?i)\b(route|routing|cable\s*tray|gland|drag\s*chain|kabel)\b")),
    (3, re.compile(r"(?i)\b(connect|wire|wiring|tilkobling|terminal|plug)\b")),
    (4, re.compile(r"(?i)\b(earth|ground|bond|shield|equipotential|strap|jording|fe\b|pe\b)\b")),
    (5, re.compile(r"(?i)\b(filter|cabinet|skap|entry|mains|power|selv|pelv)\b")),
    (6, re.compile(r"(?i)\b(verify|check|test|measure|confirm|inspect|commission)\b")),
]
SEQUENCE_VERB_RX = re.compile(
    r"(?i)\b(mount|monter|connect|wire|route|install|fasten|"
    r"bond|earth|ground|shield|prepare|avoid|ensure|use|place|fit)\b"
)

BUCKET_SCORE_RX: dict[str, re.Pattern[str]] = {
    "identity": re.compile(
        r"(?i)(manufacturer|supplier|product_type|model|part_number|system_type|"
        r"applicable_products|document_part|revision)"
    ),
    "overview": re.compile(
        r"(?i)(overview|scope|system|product_type|applicable|emc_coupling|"
        r"background|principle)"
    ),
    "prerequisites": re.compile(
        r"(?i)(prerequisite|prepare|material|tool|cable_type|connector|coverage|"
        r"shield_type|rating|insulation|before|required)"
    ),
    "safety": re.compile(
        r"(?i)(hazard|warning|danger|ppe|fault|off.?state|protection_class|"
        r"selv|pelv|safety|limit)"
    ),
    "checks": re.compile(
        r"(?i)(verify|check|test|measure|confirm|inspection|commission|"
        r"acceptance|coverage_check)"
    ),
    "sequence": re.compile(
        r"(?i)(install|mount|connect|wire|route|filter|ground|earth|strap|"
        r"bond|fasten|torque|cabinet|entry|shield_connection|mains_filter)"
    ),
    "supplier_only": re.compile(
        r"(?i)(datasheet_only|catalogue|catalog|price|sku|order_code|"
        r"marketing|persona|hypothesis)"
    ),
}

# Pure standards catalogues — loud but not install procedures
STANDARDS_LIST_RX = re.compile(
    r"(?i)\b(iec\s*\d|iso\s*\d|en\s*\d|nor[sm]ok|standard\s*list|"
    r"standards?\s+register|normsamling|kravliste)\b"
)

# Minimum score to count as an install-shaped source
INSTALL_MIN_SCORE = 8.0

# System lock: facts/files that strongly belong to another system are excluded
SYSTEM_SIGNAL: dict[str, re.Pattern[str]] = {
    "cable_tray": re.compile(
        r"(?i)\b(cable\s*trays?|kabelrenne|wire\s*trays?|kabelbro|tray\s*system|"
        r"ladder\s*trays?|trays?)\b"
    ),
    "sensor": re.compile(
        r"(?i)\b(sensors?|encoders?|transmitters?|probes?|måler|giver|"
        r"laser\s*scanners?|safety\s*cameras?|photoelectric|lidars?|scanners?|"
        r"cameras?)\b"
    ),
    "machine": re.compile(r"(?i)\b(machines?|maskin|motors?|skid|equipment)\b"),
    "enclosure": re.compile(r"(?i)\b(enclosures?|skap|kabinett|cabinets?)\b"),
}

# «bruk X» / «utvid med X» — capture whatever the user named (no vendor list)
FOCUS_VERB_RX = re.compile(
    r"(?i)\b(?:bruk|use|pull|ta\s*inn|utvid\s*med|expand\s*with|include|hent|"
    r"focus\s*on|kilde)\s+"
    r"[`\"']?([A-Za-z0-9ÆØÅæøå][\w.\-ÆØÅæøå ]{0,48}?)[`\"']?"
    r"(?=\s*[,.!?;:]|\s*$|\s+og\b|\s+and\b|\s+i\b|\s+in\b|\s+for\b|\s+til\b)"
)
FOCUS_FILENAME_RX = re.compile(
    r"(?i)\b([\w.\-ÆØÅæøå]+\.(?:pdf|docx?|xlsx?|pptx?))\b"
)
FOCUS_STOP = {
    "en", "et", "ei", "den", "det", "de", "the", "a", "an", "this", "that",
    "kilde", "kilden", "source", "sources", "fil", "file", "pdf", "manual",
    "install", "installation", "installasjonsmanual", "dokument", "document",
    "denne", "dette", "her", "now", "ja", "ok", "please", "vennligst",
}


def is_installation_manual_template(template: dict | None = None, template_file: str = "") -> bool:
    key = str((template or {}).get("template_key") or "").strip().lower()
    name = Path(str(template_file or (template or {}).get("_file") or "")).name.lower()
    return key == "installation_manual" or name == "installation_manual.json"


def system_under_install(artifact: dict | None) -> str:
    raw = str((artifact or {}).get("system_under_install") or "").strip().lower()
    if raw in SYSTEM_VALUES:
        return raw
    return ""


def needs_system_under_install(artifact: dict | None) -> bool:
    return not bool(system_under_install(artifact))


def parse_system_under_install(text: str) -> str | None:
    """Parse tray/sensor/machine/… from user chat."""
    t = (text or "").strip()
    if not t:
        return None
    # Exact token answers
    low = t.lower().replace("-", "_").replace(" ", "_")
    for v in SYSTEM_VALUES:
        if low == v or low == v.replace("_", ""):
            return v
    for value, rx in SYSTEM_ALIASES:
        if rx.search(t):
            return value
    # Norwegian short answers
    if re.search(r"(?i)^\s*(kabelrenne|renne|trays?)\s*$", t):
        return "cable_tray"
    if re.search(r"(?i)^\s*(sensor)\s*$", t):
        return "sensor"
    if re.search(r"(?i)^\s*(maskin|machine)\s*$", t):
        return "machine"
    if re.search(r"(?i)^\s*(skap|enclosure)\s*$", t):
        return "enclosure"
    if re.search(r"(?i)^\s*(annet|other)\s*$", t):
        return "other"
    return None


def ask_system_under_install_reply(lang: str = "no") -> str:
    if lang == "en":
        return (
            "Before I plan the installation manual: **what is being installed?**\n"
            "Reply with one of: `cable_tray` · `sensor` · `machine` · `enclosure` · `other`\n"
            "(Name the equipment type — not a vendor. You can lock a source file next.)"
        )
    return (
        "Før jeg planlegger installasjonsmanualen: **hva skal installeres?**\n"
        "Svar med én av: `cable_tray` (kabelrenne) · `sensor` · `machine` (maskin) · "
        "`enclosure` (skap) · `other` (annet)\n"
        "(Oppgi anleggstype — ikke leverandør. Du kan låse en kildefil etterpå.)"
    )


def _blob(entry: dict) -> str:
    parts = [
        entry.get("file") or "",
        entry.get("caption") or "",
        entry.get("detail_summary") or "",
        " ".join(str(t) for t in (entry.get("content_tags") or [])),
        " ".join(str(r) for r in (entry.get("doc_role_hints") or [])),
    ]
    for f in (entry.get("facts") or [])[:40]:
        parts.append(str(f.get("key") or ""))
        parts.append(str(f.get("value") or "")[:80])
    return "\n".join(parts)


def dedupe_index_by_file(index: list[dict] | None) -> list[dict]:
    """One entry per file path — prefer richer / more tip-shaped fact sets.

    Duplicate folder roots (project + Documents/) can index the same PDF twice with
    the same id namespace but divergent fact rows; last-wins then breaks citations.
    """
    def _quality(e: dict) -> tuple:
        facts = e.get("facts") or []
        tip_hits = 0
        for f in facts:
            blob = f"{f.get('key') or ''} {f.get('value') or ''}"
            if TIP_FACT_RX.search(blob):
                tip_hits += 1
        return (len(facts), tip_hits, len(e.get("detail_summary") or ""))

    best: dict[str, dict] = {}
    order: list[str] = []
    for e in index or []:
        fn = e.get("file") or ""
        if not fn:
            continue
        if fn not in best:
            best[fn] = e
            order.append(fn)
            continue
        if _quality(e) > _quality(best[fn]):
            best[fn] = e
    return [best[fn] for fn in order]


def _system_blob(entry: dict) -> str:
    """Path/caption/roles only — fact values often mention cabinets, trays, etc."""
    return "\n".join([
        entry.get("file") or "",
        entry.get("caption") or "",
        entry.get("detail_summary") or "",
        " ".join(str(t) for t in (entry.get("content_tags") or [])),
        " ".join(str(r) for r in (entry.get("doc_role_hints") or [])),
    ])


def is_market_bod_entry(entry: dict) -> bool:
    path = str(entry.get("file") or "")
    if MARKET_BOD_PATH_RX.search(path):
        return True
    blob = _blob(entry)
    hits = len(MARKET_BOD_RX.findall(blob))
    install_hits = len(INSTALL_LEXICON.findall(blob))
    # Strong market/BoD signal and weak install signal → downrank/exclude
    return hits >= 2 and install_hits <= 1


def install_file_score(entry: dict, system: str = "") -> float:
    """Higher = more useful for an installation manual."""
    if not entry.get("file"):
        return -99.0
    if str(entry.get("file") or "").startswith("("):
        return -99.0
    blob = _blob(entry)
    score = 0.0
    score += 2.0 * len(INSTALL_LEXICON.findall(blob))
    if is_market_bod_entry(entry):
        score -= 25.0
    roles = set(entry.get("doc_role_hints") or [])
    if roles & {"datasheet", "manual", "technical_data", "drawing", "schematic", "spec"}:
        score += 8.0
    if roles & {"catalogue", "brochure", "marketing"}:
        score -= 6.0
    path = str(entry.get("file") or "").lower()
    if path.endswith(".pdf"):
        score += 3.0
    if "manual" in path or "install" in path or "montage" in path:
        score += 10.0
    # Filenames often omit "install" but still carry mounting/EMC tips
    if re.search(
        r"(?i)(technical[_\s-]?information|background[_\s-]?knowledge|"
        r"application[_\s-]?note|guideline|install.?tip)",
        path,
    ):
        score += 10.0
    if system == "sensor" and re.search(
        r"(?i)sensor|encoder|transmitter|probe|laser|scanner|camera|lidar", blob
    ):
        score += 12.0
    if system == "cable_tray" and re.search(r"(?i)tray|renne|cable\s*ladder|kabelbro", blob):
        score += 12.0
    if system == "machine" and re.search(r"(?i)machine|maskin|motor", blob):
        score += 8.0
    if system == "enclosure" and re.search(r"(?i)enclosure|skap|cabinet|kabinett", blob):
        score += 8.0
    # Procedure-grade text
    if PROCEDURE_SIGNAL_RX.search(blob):
        score += 6.0
    return score


def focus_needles(artifact: dict | None) -> list[str]:
    raw = (artifact or {}).get("install_focus_sources") or []
    out = []
    for n in raw:
        s = str(n or "").strip().lower()
        if s and s not in out:
            out.append(s)
    return out


def parse_focus_sources(text: str) -> list[str]:
    """Extract named install sources from chat — any token the user points at.

    No vendor allowlist. Matches «bruk X», «utvid med X», and bare filenames.
    """
    t = text or ""
    found: list[str] = []

    def _add(raw: str) -> None:
        needle = re.sub(r"\s+", " ", (raw or "").strip().lower()).strip(".,;:!?\"'`")
        if not needle or needle in FOCUS_STOP:
            return
        # Drop trailing stop words ("acme manual" ok; "the file" no)
        parts = [p for p in needle.split() if p not in FOCUS_STOP]
        needle = " ".join(parts).strip()
        if len(needle) < 2:
            return
        if needle not in found:
            found.append(needle)

    for m in FOCUS_VERB_RX.finditer(t):
        _add(m.group(1) or "")
    for m in FOCUS_FILENAME_RX.finditer(t):
        _add(m.group(1) or "")
    return found


def is_focus_ask(text: str) -> bool:
    if not parse_focus_sources(text):
        return False
    # Require an explicit pull verb or a filename — avoid random nouns
    return bool(
        FOCUS_VERB_RX.search(text or "")
        or FOCUS_FILENAME_RX.search(text or "")
    )


def match_focus_files(index: list[dict], needles: Iterable[str]) -> list[str]:
    needles = [str(n).strip().lower() for n in (needles or []) if str(n).strip()]
    if not needles:
        return []
    hits = []
    seen = set()
    for e in index or []:
        fn = e.get("file") or ""
        if not fn or fn in seen:
            continue
        blob = f"{fn}\n{_blob(e)}".lower()
        if any(n in blob for n in needles):
            seen.add(fn)
            hits.append(fn)
    return hits


def is_standards_list_entry(entry: dict) -> bool:
    blob = _blob(entry)
    std = len(STANDARDS_LIST_RX.findall(blob))
    proc = len(PROCEDURE_SIGNAL_RX.findall(blob))
    return std >= 3 and proc <= 1


def entry_fits_system(entry: dict, system: str) -> bool:
    """False when the file clearly belongs to a *different* locked system.

    Strict lock: foreign-system hits on path/caption win over score.
    Fact values are ignored here (they often mention cabinets, PE, trays…).
    """
    if not system or system == "other":
        return True
    blob = _system_blob(entry)
    counts: dict[str, int] = {}
    for key, rx in SYSTEM_SIGNAL.items():
        counts[key] = len(rx.findall(blob))
    own = counts.get(system, 0)
    other_max = max((c for k, c in counts.items() if k != system), default=0)
    if other_max > 0 and own == 0:
        return False
    if other_max >= 2 and other_max > own * 2:
        return False
    return True


def corpus_shape(index: list[dict], artifact: dict | None = None) -> str:
    """install_rich | strategy_standards | mixed | empty"""
    system = system_under_install(artifact)
    install_n = strategy_n = standards_n = 0
    for e in index or []:
        if not e.get("file"):
            continue
        if is_market_bod_entry(e):
            strategy_n += 1
        elif is_standards_list_entry(e):
            standards_n += 1
        elif install_file_score(e, system) >= INSTALL_MIN_SCORE and entry_fits_system(e, system):
            install_n += 1
    if install_n >= 2:
        return "install_rich"
    if install_n == 0 and (strategy_n + standards_n) >= 2:
        return "strategy_standards"
    if install_n == 0 and strategy_n + standards_n == 0:
        return "empty"
    return "mixed"


def should_stay_thin(index: list[dict], artifact: dict | None = None) -> bool:
    """Permission to stay thin: strategy/standards corpus and no named focus hit."""
    focus = match_focus_files(index, focus_needles(artifact))
    if focus:
        return False
    return corpus_shape(index, artifact) in ("strategy_standards", "empty")


def allowed_install_files(index: list[dict], artifact: dict | None = None) -> set[str]:
    """Hard allowlist for facts/files — never the whole loud project corpus."""
    index = dedupe_index_by_file(index)
    system = system_under_install(artifact)
    needles = focus_needles(artifact)
    focus_hits = match_focus_files(index, needles)
    if needles:
        # Named job: ONLY focus hits (even if empty — stay thin, don't fall back to BoD)
        return set(focus_hits)

    allowed: set[str] = set()
    for e in index or []:
        fn = e.get("file") or ""
        if not fn:
            continue
        if is_market_bod_entry(e) or is_standards_list_entry(e):
            continue
        if not entry_fits_system(e, system):
            continue
        sc = install_file_score(e, system)
        if sc < INSTALL_MIN_SCORE:
            continue
        # Weak scores need procedure signal or engineering role — keep out annual
        # reports / ambient PDFs that only share a few lexicon hits.
        if sc < 22.0:
            roles = set(e.get("doc_role_hints") or [])
            if not PROCEDURE_SIGNAL_RX.search(_blob(e)) and not (
                roles & {"manual", "datasheet", "technical_data", "drawing", "schematic", "spec"}
            ):
                continue
        allowed.add(fn)
    return allowed


def filter_index_for_install(index: list[dict], artifact: dict | None = None) -> list[dict]:
    index = dedupe_index_by_file(index)
    allowed = allowed_install_files(index, artifact)
    if not allowed:
        return []
    return [e for e in (index or []) if (e.get("file") or "") in allowed]


def lock_system_on_artifact(artifact: dict | None, system: str) -> dict:
    art = dict(artifact or {})
    art["system_under_install"] = system
    art["install_system_locked"] = True
    return art


def merge_focus_sources(artifact: dict | None, needles: Iterable[str]) -> dict:
    art = dict(artifact or {})
    cur = list(art.get("install_focus_sources") or [])
    for n in needles:
        s = re.sub(r"\s+", " ", str(n or "").strip().lower())
        if s and s not in cur:
            cur.append(s)
    art["install_focus_sources"] = cur
    return art


def _candidate_names_bit(candidates: list[str] | None, lang: str) -> str:
    names = [Path(c).name for c in (candidates or []) if c][:5]
    if not names:
        return ""
    listed = ", ".join(f"`{n}`" for n in names)
    if lang == "en":
        return f"\n\nIndexed candidates worth naming: {listed}."
    return f"\n\nIndekserte kandidater verdt å navngi: {listed}."


def candidate_install_filenames(
    index: list[dict],
    artifact: dict | None = None,
    *,
    limit: int = 6,
) -> list[str]:
    """High-scoring install-shaped PDFs for gap offers (respects system lock)."""
    system = system_under_install(artifact)
    ranked = []
    for e in index or []:
        fn = e.get("file") or ""
        if not fn or not str(fn).lower().endswith(".pdf"):
            continue
        if is_market_bod_entry(e) or is_standards_list_entry(e):
            continue
        if not entry_fits_system(e, system):
            continue
        sc = install_file_score(e, system)
        if sc < INSTALL_MIN_SCORE:
            continue
        ranked.append((sc, fn))
    ranked.sort(key=lambda t: -t[0])
    return [fn for _sc, fn in ranked[:limit]]


def thin_identity_md(
    artifact: dict | None,
    lang: str = "no",
    candidates: list[str] | None = None,
) -> str:
    system = system_under_install(artifact) or "—"
    name = str((artifact or {}).get("name") or "—")
    focus = ", ".join(focus_needles(artifact)) or "—"
    cand_bit = _candidate_names_bit(candidates, lang)
    if lang == "en":
        return (
            "| Parameter | Value | Unit | Source |\n"
            "|-----------|-------|------|--------|\n"
            f"| project | {name} | — | artefact |\n"
            f"| system_under_install | {system} | — | locked |\n"
            f"| manufacturer / product | [GAP: manufacturer] | — | — |\n"
            f"| focus sources | {focus} | — | chat |\n\n"
            "*Corpus is strategy/standards — identity stays thin until an install "
            "source from *your* index is named («bruk …» / «utvid med …») or indexed.*"
            f"{cand_bit}"
        )
    return (
        "| Parameter | Verdi | Enhet | Kilde |\n"
        "|-----------|-------|-------|-------|\n"
        f"| prosjekt | {name} | — | artefakt |\n"
        f"| system_under_install | {system} | — | låst |\n"
        f"| produsent / produkt | [MANGLER: manufacturer] | — | — |\n"
        f"| fokuskilder | {focus} | — | chat |\n\n"
        "*Korpuset er strategi/standardlister — identifikasjon holdes tynn til en "
        "installasjonskilde fra *din* indeks er navngitt («bruk …» / «utvid med …») "
        "eller indeksert.*"
        f"{cand_bit}"
    )


def thin_overview_md(
    artifact: dict | None,
    lang: str = "no",
    candidates: list[str] | None = None,
) -> str:
    system = system_under_install(artifact) or "—"
    cand_bit = _candidate_names_bit(candidates, lang)
    if lang == "en":
        return (
            f"Locked system: **{system}**. No install-shaped sources in the active "
            "allowlist yet (strategy PDFs and standards lists do not fill this section). "
            "Say «bruk …» or «utvid med filename.pdf» naming a file from *your* index."
            f"{cand_bit}"
        )
    return (
        f"Låst system: **{system}**. Ingen installasjonsformede kilder i tillatt "
        "sett ennå (strategi-PDF-er og standardlister fyller ikke denne seksjonen). "
        "Si «bruk …» eller «utvid med filnavn.pdf» med et navn fra *din* indeks."
        f"{cand_bit}"
    )


def procedure_gap_md(
    lang: str = "no",
    *,
    system: str = "",
    section_key: str = "",
    stay_thin: bool = False,
    focus: list[str] | None = None,
    candidates: list[str] | None = None,
) -> str:
    sys_bit = f" ({system})" if system else ""
    focus = focus or []
    cand_bit = _candidate_names_bit(candidates, lang)
    if stay_thin:
        hint = (
            "Corpus looks like strategy PDFs + standards lists. "
            "Name an install source from your index — e.g. «bruk …» / «utvid med fil.pdf»."
            if lang == "en" else
            "Korpuset ser ut som strategi-PDF-er + standardlister. "
            "Navngi en installasjonskilde fra indeksen — f.eks. «bruk …» / «utvid med fil.pdf»."
        )
        if focus:
            hint += (
                f" Focus set to {', '.join(focus)} but no matching indexed files yet."
                if lang == "en" else
                f" Fokus satt til {', '.join(focus)}, men ingen treff i indeksen ennå."
            )
        if lang == "en":
            return (
                f"**[GAP: installation procedure missing]{sys_bit}**\n\n"
                f"{hint} Staying thin on purpose — not padding from loud project facts."
                f"{cand_bit}"
            )
        return (
            f"**[MANGLER: installasjonsprosedyre]{sys_bit}**\n\n"
            f"{hint} Holdes bevisst tynn — ikke fyllt med høytalende prosjektfakta."
            f"{cand_bit}"
        )
    if lang == "en":
        return (
            f"**[GAP: installation procedure missing]{sys_bit}**\n\n"
            "No mounting/install/commissioning chunks were found for this system. "
            "Do not treat empty section shells as a complete procedure. "
            "Add the manufacturer's installation manual, or say «bruk …» / "
            "«utvid med fil.pdf» naming a file from your index, then regenerate."
            f"{cand_bit}"
        )
    return (
        f"**[MANGLER: installasjonsprosedyre]{sys_bit}**\n\n"
        "Ingen monterings-/installasjons-/idriftsettelses-kilder funnet for dette systemet. "
        "Tomme seksjonsskall er ikke en komplett struktur. "
        "Last opp leverandørens installasjonsmanual, eller si «bruk …» / "
        "«utvid med fil.pdf» med et navn fra indeksen, og generer på nytt."
        f"{cand_bit}"
    )


def map_install_files(
    index: list[dict],
    template: dict,
    artifact: dict | None = None,
) -> dict[str, list[str]]:
    """Deterministic section→file map — only allowlisted install/focus files."""
    system = system_under_install(artifact)
    allowed = allowed_install_files(index, artifact)
    filtered = [e for e in (index or []) if (e.get("file") or "") in allowed]
    ranked = sorted(
        filtered,
        key=lambda e: install_file_score(e, system),
        reverse=True,
    )
    # Focus needles force those files first
    focus_hits = match_focus_files(index, focus_needles(artifact))
    install_files = list(dict.fromkeys(focus_hits + [e["file"] for e in ranked]))[:16]
    thin = should_stay_thin(index, artifact)

    if thin and not focus_hits:
        # Stay thin: map almost nothing — sections render gaps / thin shells
        empty_map = {s.get("section_key"): [] for s in (template.get("sections") or [])}
        empty_map["identification"] = []
        empty_map["source_register"] = []
        return empty_map

    identity_files = [
        e["file"] for e in ranked
        if install_file_score(e, system) >= INSTALL_MIN_SCORE
    ][:8] or install_files[:6]
    procedure_files = [
        e["file"] for e in ranked
        if PROCEDURE_SIGNAL_RX.search(_blob(e))
    ][:10] or install_files[:8]
    drawing_files = [
        e["file"] for e in ranked
        if any(r in (e.get("doc_role_hints") or []) for r in (
            "drawing", "schematic", "site_plan", "overview"
        )) or str(e.get("file") or "").lower().endswith((".png", ".jpg", ".jpeg", ".pdf"))
    ][:8]

    file_map: dict[str, list[str]] = {}
    for s in (template.get("sections") or []):
        sk = s.get("section_key") or ""
        if sk == "identification":
            file_map[sk] = identity_files
        elif sk == "system_overview":
            file_map[sk] = drawing_files or install_files[:8]
        elif sk in ("prerequisites", "safety", "sequence", "verification"):
            file_map[sk] = procedure_files
        elif sk == "supplier_manual_gaps":
            file_map[sk] = []
        elif sk == "source_register":
            file_map[sk] = install_files
        elif sk == "declaration":
            file_map[sk] = []
        else:
            file_map[sk] = install_files[:6]
    return file_map


def filter_identity_fact_ids(ids: list[str], by_id: dict) -> list[str]:
    kept = []
    for fid in ids:
        f = by_id.get(fid) or {}
        key = str(f.get("key") or "").strip().lower()
        val = str(f.get("value") or "")
        if key in IDENTITY_DENY or IDENTITY_DENY_RX.search(key) or IDENTITY_DENY_RX.search(val):
            continue
        if key in IDENTITY_ALLOW or any(key.startswith(p) for p in IDENTITY_ALLOW_PREFIX):
            kept.append(fid)
    return kept


def procedure_evidence_files(index: list[dict], mapped_files: Iterable[str] | None = None,
                             artifact: dict | None = None) -> list[str]:
    want = set(mapped_files or [])
    allowed = allowed_install_files(index, artifact) if artifact is not None else None
    out = []
    for e in index or []:
        fn = e.get("file") or ""
        if not fn:
            continue
        if want and fn not in want:
            continue
        if allowed is not None and fn not in allowed:
            continue
        if is_market_bod_entry(e) or is_standards_list_entry(e):
            continue
        system = system_under_install(artifact)
        if PROCEDURE_SIGNAL_RX.search(_blob(e)) and install_file_score(e, system) >= INSTALL_MIN_SCORE:
            out.append(fn)
    return out


def has_procedure_evidence(index: list[dict], mapped_files: Iterable[str] | None = None,
                           artifact: dict | None = None) -> bool:
    return bool(procedure_evidence_files(index, mapped_files, artifact=artifact))


def _is_tip_fact(fact: dict) -> bool:
    key = str(fact.get("key") or "")
    val = str(fact.get("value") or "")
    if not key and not val:
        return False
    if IDENTITY_DENY_RX.search(key) or IDENTITY_DENY_RX.search(val):
        return False
    blob = f"{key} {val}"
    return bool(TIP_FACT_RX.search(blob))


def _tip_section_affinity(fact: dict, section_key: str) -> int:
    """Higher = better fit for this procedure section."""
    key = str(fact.get("key") or "")
    val = str(fact.get("value") or "")
    blob = f"{key} {val}"
    rx = SECTION_TIP_RX.get(section_key)
    score = 0
    if rx and rx.search(blob):
        score += 3
    if _is_tip_fact(fact):
        score += 1
    # Prefer instructive values in sequence
    if section_key == "sequence" and re.search(
        r"(?i)\b(must|shall|always|never|mount|connect|install|avoid|prefer)\b", val
    ):
        score += 2
    return score


def collect_install_tip_facts(
    index: list[dict],
    artifact: dict | None = None,
    *,
    mapped_files: Iterable[str] | None = None,
    section_key: str = "sequence",
    limit: int = 14,
) -> list[dict]:
    """Tip-shaped facts from allowlisted procedure sources (generic, cited).

    When the user locked focus sources, pull *all* engineering facts from those
    files (higher limit) — not only the tip-regex subset.
    """
    index = dedupe_index_by_file(index)
    allowed = allowed_install_files(index, artifact)
    focus_hits = set(match_focus_files(index, focus_needles(artifact)))
    want = set(mapped_files or []) or None
    evidence = set(procedure_evidence_files(index, mapped_files, artifact=artifact))
    focus_mode = bool(focus_hits)
    if focus_mode:
        limit = max(limit, 36)

    scored: list[tuple[int, str, dict]] = []
    for e in index or []:
        fn = e.get("file") or ""
        if not fn or fn not in allowed:
            continue
        if focus_hits and fn not in focus_hits:
            continue
        if not focus_hits:
            if want is not None and fn not in want and fn not in evidence:
                continue
        if is_market_bod_entry(e) or is_standards_list_entry(e):
            continue
        for f in e.get("facts") or []:
            if f.get("provenance") == "reference":
                continue
            fid = f.get("id") or ""
            if not fid:
                continue
            key = str(f.get("key") or "").strip().lower()
            # Skip pure identity rows in procedure sections
            if key in ("manufacturer", "supplier", "project_name", "project_title",
                       "document_part_number", "document_revision_date", "revision"):
                continue
            if key in IDENTITY_ALLOW or any(key.startswith(p) for p in IDENTITY_ALLOW_PREFIX):
                if key not in (
                    "voltage", "protection_class", "ip_rating", "capacity",
                    "rated_voltage", "nominal_voltage",
                ) and not key.startswith("protection_class") and not key.startswith("selv_"):
                    if not focus_mode:
                        continue
                    # Focus mode: keep product/type facts that describe the install
                    if not key.startswith(("product", "type", "model", "part", "system")):
                        continue
            aff = _tip_section_affinity(f, section_key)
            if focus_mode:
                # Prefer section affinity, but keep every engineering fact
                aff = max(aff, 1 if _is_tip_fact(f) else 0)
                if aff <= 0:
                    aff = 1  # still include from focused technical PDF
            else:
                if aff <= 0 and not _is_tip_fact(f):
                    continue
                if aff <= 0:
                    continue
            scored.append((aff, fid, {"id": fid, **{k: v for k, v in f.items() if k != "id"}}))
    scored.sort(key=lambda t: (-t[0], t[1]))
    out = []
    seen = set()
    for _aff, fid, fact in scored:
        if fid in seen:
            continue
        seen.add(fid)
        out.append(fact)
        if len(out) >= limit:
            break
    return out


def _claim_blob(claim: dict) -> str:
    return f"{claim.get('key') or ''} {claim.get('value') or ''}"


def score_claim_buckets(claim: dict) -> dict[str, int]:
    """Score a claim against each bucket — used for exclusive assignment."""
    blob = _claim_blob(claim)
    key = str(claim.get("key") or "").lower()
    scores = {b: 0 for b in CLAIM_BUCKETS}
    for bucket, rx in BUCKET_SCORE_RX.items():
        if rx.search(blob) or rx.search(key):
            scores[bucket] += 3
    if _is_tip_fact(claim):
        scores["sequence"] += 1
        scores["prerequisites"] += 1
    if SEQUENCE_VERB_RX.search(blob):
        scores["sequence"] += 4
    if SECTION_TIP_RX["safety"].search(blob):
        scores["safety"] += 2
    if SECTION_TIP_RX["verification"].search(blob):
        scores["checks"] += 5
        scores["sequence"] = max(0, scores["sequence"] - 2)
    if SECTION_TIP_RX["prerequisites"].search(blob):
        scores["prerequisites"] += 2
    if key in IDENTITY_ALLOW or any(key.startswith(p) for p in IDENTITY_ALLOW_PREFIX):
        scores["identity"] += 4
        if key.startswith(("protection_class", "selv_", "voltage", "ip_")):
            scores["safety"] += 3
            scores["identity"] -= 1
    if key in (
        "product_scope", "applicable_products", "product_type", "system_type",
        "manufacturer", "supplier", "model",
    ):
        scores["identity"] += 6
        scores["safety"] = 0
        scores["sequence"] = max(0, scores["sequence"] - 2)
        scores["checks"] = 0
    if re.search(r"(?i)\b(liability|excludes\s+liability|does not guarantee|disclaimer|"
                 r"no\s+warranty|without\s+warranty)\b", blob):
        scores["supplier_only"] += 8
        scores["checks"] = 0
        scores["sequence"] = 0
        scores["safety"] = 0
    if claim.get("_page_cite"):
        # Page harvest: prefer sequence/prerequisites over identity
        scores["sequence"] += 2
        scores["prerequisites"] += 1
        scores["identity"] = 0
    if scores["supplier_only"] and scores["sequence"] >= 3:
        scores["supplier_only"] = 0
    return scores


def assign_claim_bucket(claim: dict) -> str:
    scores = score_claim_buckets(claim)
    best = max(scores.values())
    if best <= 0:
        return "supplier_only" if not _is_tip_fact(claim) else "overview"
    candidates = [b for b, s in scores.items() if s == best]
    for b in CLAIM_BUCKET_TIEBREAK:
        if b in candidates:
            return b
    return candidates[0]


def sequence_phase(claim: dict) -> int:
    blob = _claim_blob(claim)
    for phase, rx in SEQUENCE_PHASE_RX:
        if rx.search(blob):
            return phase
    return 3  # default mid-install (connect-ish)


def order_sequence_steps(claims: list[dict]) -> list[dict]:
    """Stable order: install phase → verb presence → key."""
    ranked = []
    for c in claims:
        blob = _claim_blob(c)
        verb = 0 if SEQUENCE_VERB_RX.search(blob) else 1
        ranked.append((sequence_phase(c), verb, str(c.get("key") or ""), c))
    ranked.sort(key=lambda t: (t[0], t[1], t[2]))
    return [t[3] for t in ranked]


def extract_install_claims(
    index: list[dict],
    artifact: dict | None = None,
    *,
    mapped_files: Iterable[str] | None = None,
    include_page_spans: bool = True,
) -> list[dict]:
    """One claim set from allowlisted/focus sources (+ optional page spans)."""
    index = dedupe_index_by_file(index)
    allowed = allowed_install_files(index, artifact)
    focus_hits = set(match_focus_files(index, focus_needles(artifact)))
    want = set(mapped_files or []) or None
    evidence = set(procedure_evidence_files(index, mapped_files, artifact=artifact))
    folders = (artifact or {}).get("_folders") or []

    claims: list[dict] = []
    seen: set[str] = set()
    for e in index or []:
        fn = e.get("file") or ""
        if not fn or fn not in allowed:
            continue
        if focus_hits and fn not in focus_hits:
            continue
        if not focus_hits:
            if want is not None and fn not in want and fn not in evidence:
                continue
        if is_market_bod_entry(e) or is_standards_list_entry(e):
            continue
        for f in e.get("facts") or []:
            if f.get("provenance") == "reference":
                continue
            fid = str(f.get("id") or "")
            if not fid or fid in seen:
                continue
            seen.add(fid)
            claims.append({
                "id": fid,
                "key": f.get("key"),
                "value": f.get("value"),
                "unit": f.get("unit"),
                "source_location": f.get("source_location"),
                "_file": fn,
                "_kind": "fact",
            })
        if include_page_spans and focus_hits and fn in focus_hits:
            for row in harvest_page_guidance(e, folders, limit=16):
                val = str(row.get("value") or "").strip()
                if len(val) < 40:
                    continue
                pid = "page:" + re.sub(
                    r"[^a-zA-Z0-9]+", "_",
                    f"{Path(fn).stem}_{row.get('source_location')}_{val[:40]}",
                )[:72]
                if pid in seen:
                    continue
                seen.add(pid)
                claims.append({
                    "id": pid,
                    "key": row.get("key") or "page_guidance",
                    "value": val,
                    "unit": None,
                    "source_location": row.get("source_location"),
                    "_file": fn,
                    "_page_cite": row.get("_page_cite"),
                    "_kind": "page",
                })
    return claims


def partition_install_claims(claims: list[dict]) -> dict[str, list[dict]]:
    """Assign each claim_id to exactly one bucket."""
    buckets: dict[str, list[dict]] = {b: [] for b in CLAIM_BUCKETS}
    for c in claims:
        buckets[assign_claim_bucket(c)].append(c)
    return buckets


def build_install_claim_plan(
    index: list[dict],
    artifact: dict | None = None,
    *,
    mapped_files: Iterable[str] | None = None,
) -> dict:
    """Extract once → partition → order sequence. Cached on artifact."""
    art = artifact if isinstance(artifact, dict) else {}
    cached = art.get("_install_claim_plan")
    if isinstance(cached, dict) and cached.get("buckets"):
        return cached

    claims = extract_install_claims(index, art, mapped_files=mapped_files)
    buckets = partition_install_claims(claims)
    steps = order_sequence_steps(list(buckets.get("sequence") or []))
    # Page claims not used as sequence verbs → appendix once
    appendix = [
        c for c in claims
        if c.get("_kind") == "page"
        and assign_claim_bucket(c) not in ("sequence", "safety", "prerequisites", "checks")
    ]
    # Prefer unused page rows that landed in sequence but are weak verbs as appendix? No —
    # single assignment already placed them. Appendix = page claims assigned supplier_only/overview.
    appendix = [
        c for c in (buckets.get("overview") or []) + (buckets.get("supplier_only") or [])
        if c.get("_kind") == "page"
    ][:12]

    plan = {
        "claims": claims,
        "buckets": buckets,
        "sequence_steps": steps,
        "appendix": appendix,
        "claim_ids": {str(c.get("id")) for c in claims if c.get("id")},
        "by_id": {str(c["id"]): c for c in claims if c.get("id")},
    }
    art["_install_claim_plan"] = plan
    return plan


def get_install_claim_plan(
    index: list[dict],
    artifact: dict | None = None,
    *,
    mapped_files: Iterable[str] | None = None,
) -> dict:
    return build_install_claim_plan(index, artifact, mapped_files=mapped_files)


def _cite_claim(claim: dict) -> str:
    if claim.get("_kind") == "page":
        return str(claim.get("_page_cite") or claim.get("source_location") or "—")
    fid = claim.get("id")
    return f"{{{{fact:{fid}}}}}" if fid else "—"


def _claim_value(claim: dict) -> str:
    val = str(claim.get("value") or "").strip().replace("|", "/")
    unit = str(claim.get("unit") or "").strip()
    if unit and unit not in val:
        val = f"{val} {unit}".strip()
    return val or "—"


def compile_sequence_from_plan(plan: dict, *, lang: str = "no") -> str:
    """Numbered install steps from the sequence bucket — one claim each."""
    no = lang != "en"
    steps = list(plan.get("sequence_steps") or [])
    # Prefer verb-bearing steps for the ordered list
    verb_steps = [
        c for c in steps
        if SEQUENCE_VERB_RX.search(_claim_blob(c)) or c.get("_kind") == "page"
    ]
    use = verb_steps if len(verb_steps) >= 3 else steps

    if len(use) < 3:
        gap = (
            "[MANGLER: sekvens ikke utledet — se leverandørens installasjonskapittel "
            "for monteringsrekkefølge.]"
            if no else
            "[GAP: sequence not derived — see the supplier installation chapter "
            "for mounting order.]"
        )
        lines = [
            "*" + (
                "Installasjonssekvens — for få handlingssteg i kildene."
                if no else
                "Installation sequence — too few actionable steps in sources."
            ) + "*",
            "",
            gap,
        ]
        if use:
            lines.append("")
            lines.append("### " + ("Utdrag" if no else "Extracts"))
            for i, c in enumerate(use, 1):
                lines.append(f"{i}. {_claim_value(c)} ({_cite_claim(c)})")
        return "\n".join(lines)

    lines = [
        "*" + (
            "Installasjonssekvens — ordnede steg fra siterte kilder (ett krav per steg)."
            if no else
            "Installation sequence — ordered steps from cited sources (one claim per step)."
        ) + "*",
        "",
    ]
    for i, c in enumerate(use[:18], 1):
        key = str(c.get("key") or "").replace("_", " ")
        val = _claim_value(c)
        cite = _cite_claim(c)
        if key and key not in ("page guidance", "page_guidance"):
            lines.append(f"{i}. **{key}:** {val} ({cite})")
        else:
            lines.append(f"{i}. {val} ({cite})")
    return "\n".join(lines)


def compile_prerequisites_from_plan(plan: dict, *, lang: str = "no") -> str:
    no = lang != "en"
    rows = list(plan.get("buckets", {}).get("prerequisites") or [])
    if not rows:
        return (
            "[MANGLER: forutsetninger] — ingen krav plassert i denne bøtten."
            if no else
            "[GAP: prerequisites] — no claims assigned to this bucket."
        )
    lines = [
        "*" + (
            "Forutsetninger — kort oversikt og kompakt tabell (krav brukes ikke på nytt i andre seksjoner)."
            if no else
            "Prerequisites — short overview and compact table (claims are not reused in other sections)."
        ) + "*",
        "",
    ]
    # Short prose from first two
    for c in rows[:2]:
        lines.append(f"- {_claim_value(c)} ({_cite_claim(c)})")
    lines.append("")
    if no:
        lines += ["| Krav | Verdi | Kilde |", "|------|-------|-------|"]
    else:
        lines += ["| Requirement | Value | Source |", "|-------------|-------|--------|"]
    for c in rows[:16]:
        key = str(c.get("key") or "—").replace("_", " ").replace("|", "/")
        lines.append(f"| {key} | {_claim_value(c)} | {_cite_claim(c)} |")
    return "\n".join(lines)


def compile_safety_from_plan(plan: dict, *, lang: str = "no") -> str:
    no = lang != "en"
    rows = list(plan.get("buckets", {}).get("safety") or [])
    if not rows:
        return (
            "[MANGLER: sikkerhet] — ingen fare-/grensekrav plassert her."
            if no else
            "[GAP: safety] — no hazard/limit claims assigned here."
        )
    lines = [
        "*" + (
            "Sikkerhet — farer og grenser (kun safety-bøtten)."
            if no else
            "Safety — hazards and limits (safety bucket only)."
        ) + "*",
        "",
    ]
    if no:
        lines += ["| Fare / grense | Verdi | Kilde |", "|---------------|-------|-------|"]
    else:
        lines += ["| Hazard / limit | Value | Source |", "|----------------|-------|--------|"]
    for c in rows[:16]:
        key = str(c.get("key") or "—").replace("_", " ").replace("|", "/")
        lines.append(f"| {key} | {_claim_value(c)} | {_cite_claim(c)} |")
    return "\n".join(lines)


def compile_checks_from_plan(plan: dict, *, lang: str = "no") -> str:
    no = lang != "en"
    rows = list(plan.get("buckets", {}).get("checks") or [])
    if not rows:
        return (
            "[MANGLER: kontroll] — ingen verifikasjonskrav plassert her."
            if no else
            "[GAP: checks] — no verification claims assigned here."
        )
    lines = [
        "*" + (
            "Kontroll og idriftsettelse — sjekkliste fra kilder."
            if no else
            "Verification — checklist from sources."
        ) + "*",
        "",
    ]
    for i, c in enumerate(rows[:16], 1):
        lines.append(f"{i}. [ ] {_claim_value(c)} ({_cite_claim(c)})")
    return "\n".join(lines)


def compile_appendix_from_plan(plan: dict, *, lang: str = "no") -> str:
    """At most one appendix block (page spans not used as body steps)."""
    rows = list(plan.get("appendix") or [])
    if not rows:
        return ""
    no = lang != "en"
    lines = [
        "",
        "### " + ("Tillegg fra sider" if no else "Appendix from pages"),
        "",
        "*" + (
            "Utdrag som ikke passet som egne sekvens-/sikkerhetssteg — vist én gang."
            if no else
            "Extracts that did not fit sequence/safety steps — shown once."
        ) + "*",
        "",
    ]
    for i, c in enumerate(rows[:10], 1):
        lines.append(f"{i}. {_claim_value(c)} ({_cite_claim(c)})")
    return "\n".join(lines)


def compile_install_section_from_plan(
    section_key: str,
    index: list[dict],
    artifact: dict | None = None,
    *,
    mapped_files: Iterable[str] | None = None,
    lang: str = "no",
    include_diagrams: bool = False,
    include_appendix: bool = False,
) -> str | None:
    """Author one body section from the shared claim plan."""
    plan = get_install_claim_plan(index, artifact, mapped_files=mapped_files)
    sk = (section_key or "").strip().lower()
    if sk == "sequence":
        text = compile_sequence_from_plan(plan, lang=lang)
    elif sk == "prerequisites":
        text = compile_prerequisites_from_plan(plan, lang=lang)
    elif sk == "safety":
        text = compile_safety_from_plan(plan, lang=lang)
    elif sk == "verification":
        text = compile_checks_from_plan(plan, lang=lang)
    else:
        return None
    if include_diagrams:
        diagrams = compile_install_diagrams_md(
            "sequence" if sk == "sequence" else "system_overview",
            index, artifact, lang=lang, max_diagrams=3,
        )
        if diagrams:
            text = text.rstrip() + "\n\n" + diagrams
    if include_appendix:
        app = compile_appendix_from_plan(plan, lang=lang)
        if app:
            text = text.rstrip() + "\n" + app
    return text


def resolve_source_path(rel: str, folders: Iterable[str] | None) -> Path | None:
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if not rel:
        return None
    for folder in folders or []:
        base = Path(folder)
        cand = base / rel
        if cand.is_file():
            return cand
        # Project may include Documents/ as a root — strip first segment
        parts = Path(rel).parts
        if len(parts) > 1:
            cand2 = base / Path(*parts[1:])
            if cand2.is_file():
                return cand2
        by_name = list(base.rglob(Path(rel).name))
        for p in by_name[:3]:
            if p.is_file():
                return p
    return None


def select_install_figure_pages(entry: dict, *, section_key: str = "", limit: int = 6) -> list[int]:
    """0-based PDF pages to render — cover + fact pages + rich content pages."""
    stats = entry.get("extraction_stats") or {}
    page_count = int(stats.get("page_count") or 0)
    if page_count <= 0:
        return [0]
    chosen: set[int] = {0}
    for f in entry.get("facts") or []:
        m = re.search(r"page\s*(\d+)", str(f.get("source_location") or ""), re.I)
        if m:
            chosen.add(max(0, min(page_count - 1, int(m.group(1)) - 1)))
    cpp = stats.get("chars_per_page") or {}
    rich = sorted(
        ((int(p), int(c)) for p, c in cpp.items() if str(p).isdigit()),
        key=lambda t: -t[1],
    )
    # Prefer rich pages (diagrams + captions often sit on dense pages)
    for p1, chars in rich:
        if chars < 600:
            continue
        chosen.add(p1 - 1)
        if len(chosen) >= limit * 2:
            break
    # Spread across the document so late checklists (often un-facted) appear
    if page_count > 8:
        for frac in (0.25, 0.5, 0.75, 0.9):
            chosen.add(min(page_count - 1, max(0, int(page_count * frac))))
    ordered = sorted(p for p in chosen if 0 <= p < page_count)
    if len(ordered) <= limit:
        return ordered
    # Keep cover + evenly sample the rest
    rest = [p for p in ordered if p != 0]
    if not rest:
        return [0]
    out = [0]
    step = max(1, len(rest) / max(1, limit - 1))
    i = 0.0
    while len(out) < limit and int(i) < len(rest):
        p = rest[int(i)]
        if p not in out:
            out.append(p)
        i += step
    return sorted(out)[:limit]


def figure_markers_md(entry: dict, pages: list[int], *, heading: str = "") -> str:
    fn = entry.get("file") or ""
    if not fn or not pages:
        return ""
    stem = Path(fn).name
    lines = []
    if heading:
        lines.append(heading)
        lines.append("")
    for p in pages:
        lines.append(f"{{{{figure:{fn}:{p}|{stem} — side {p + 1}}}}}")
    return "\n\n".join(lines)


def focus_source_entries(index: list[dict], artifact: dict | None = None) -> list[dict]:
    index = dedupe_index_by_file(index)
    focus = set(match_focus_files(index, focus_needles(artifact)))
    allowed = allowed_install_files(index, artifact)
    want = focus or allowed
    out = []
    for e in index:
        fn = e.get("file") or ""
        if fn in want and str(fn).lower().endswith(".pdf"):
            out.append(e)
    # Prefer focus hits first
    if focus:
        out.sort(key=lambda e: (0 if e.get("file") in focus else 1, e.get("file") or ""))
    return out


_PAGE_GUIDANCE_RX = re.compile(
    r"(?is)([^.!?\n]{15,200}?\b(?:must|shall|always|never|required|mount|connect|"
    r"install|avoid|ensure|prefer|use|do not|should)\b[^.!?\n]{5,180}[.!?])"
)


def harvest_page_guidance(
    entry: dict,
    folders: Iterable[str] | None,
    *,
    limit: int = 16,
) -> list[dict]:
    """Pull install sentences from PDF pages that have little/no indexed facts.

    No LLM — regex on extracted page text. Cites as plain page references
    (not {{fact:}}) so duplicate-id issues cannot scramble them.
    """
    rel = entry.get("file") or ""
    path = resolve_source_path(rel, folders)
    if not path:
        return []
    try:
        from foldok_compile import extract_pdf_pages
    except Exception:
        return []
    pages = extract_pdf_pages(path)
    if not pages:
        return []
    fact_pages: set[int] = set()
    for f in entry.get("facts") or []:
        m = re.search(r"page\s*(\d+)", str(f.get("source_location") or ""), re.I)
        if m:
            fact_pages.add(int(m.group(1)))
    # Also skip pages that already contributed ≥2 facts
    fpp = (entry.get("extraction_stats") or {}).get("facts_per_page") or {}
    for p, n in fpp.items():
        try:
            if int(n) >= 2:
                fact_pages.add(int(p))
        except (TypeError, ValueError):
            pass

    out: list[dict] = []
    seen_val: set[str] = set()
    # Prefer unfacted rich pages, then thinly facted
    ordered = sorted(
        pages,
        key=lambda p: (0 if p["page"] not in fact_pages else 1, -p["chars"]),
    )
    for p in ordered:
        if p["chars"] < 400:
            continue
        text = p.get("text") or ""
        for m in _PAGE_GUIDANCE_RX.finditer(text):
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            if len(val) < 40:
                continue
            key = val.lower()[:80]
            if key in seen_val:
                continue
            seen_val.add(key)
            out.append({
                "id": "",  # plain row — no fact cite
                "key": f"page_{p['page']}_guidance",
                "value": val,
                "unit": None,
                "source_location": f"page {p['page']}",
                "_page_cite": f"{Path(rel).name} p.{p['page']}",
            })
            if len(out) >= limit:
                return out
    return out


def compile_install_overview_md(
    index: list[dict],
    artifact: dict | None = None,
    *,
    lang: str = "no",
) -> str:
    """Authored system overview — overview-bucket claims only + diagrams once."""
    entries = focus_source_entries(index, artifact)
    if not entries:
        allowed = allowed_install_files(index, artifact)
        entries = [
            e for e in dedupe_index_by_file(index)
            if (e.get("file") or "") in allowed and str(e.get("file") or "").lower().endswith(".pdf")
        ][:3]
    if not entries:
        return thin_overview_md(artifact, lang)

    no = lang != "en"
    system = system_under_install(artifact) or "—"
    name = str((artifact or {}).get("name") or "—")
    plan = get_install_claim_plan(index, artifact)
    overview_claims = list(plan.get("buckets", {}).get("overview") or [])

    parts: list[str] = []
    if no:
        parts.append(
            f"Denne installasjonsmanualen gjelder **{name}** for anleggstype "
            f"**`{system}`**. Oversikten bruker kun krav plassert i overview-bøtten."
        )
    else:
        parts.append(
            f"This installation manual covers **{name}** for system type "
            f"**`{system}`**. Overview uses only claims assigned to the overview bucket."
        )

    products = []
    for c in overview_claims:
        key = str(c.get("key") or "").lower()
        if key in ("applicable_products", "product_type", "system_type") or "product" in key:
            products.append(f"- {_cite_claim(c)}")
    if not products:
        # identity-adjacent product lines may sit in identity bucket — show type only
        for c in (plan.get("buckets", {}).get("identity") or [])[:4]:
            key = str(c.get("key") or "").lower()
            if key in ("applicable_products", "product_type", "system_type"):
                products.append(f"- {_cite_claim(c)}")

    if products:
        parts.append("### " + ("Anlegg / produkter" if no else "System / products"))
        parts.extend(products[:6])

    # Diagrams once — only in overview
    diagrams = compile_install_diagrams_md(
        "system_overview", index, artifact, lang=lang, max_diagrams=3,
    )
    if diagrams:
        parts.append(diagrams)

    bits = []
    for c in overview_claims[:8]:
        key = str(c.get("key") or "").replace("_", " ")
        if key in ("applicable products", "product type", "system type"):
            continue
        bits.append(f"- **{key}:** {_cite_claim(c)}")
    if bits:
        parts.append("### " + ("Nøkkelpunkter" if no else "Key points"))
        parts.extend(bits)

    parts.append(
        "*" + (
            "Detaljerte råd står i Forutsetninger, Sikkerhet og Installasjonssekvens. "
            "Illustrasjonene over er Foldok koblingsskjema. "
            "Leverandørens originale manual erstattes ikke — se Erklæring."
            if no else
            "Detailed guidance is in Prerequisites, Safety, and Installation Sequence. "
            "Illustrations above are Foldok wiring diagrams. "
            "This does not replace the supplier's original manual — see Declaration."
        ) + "*"
    )
    return "\n\n".join(parts).strip()


def append_install_figures(
    md: str,
    index: list[dict],
    artifact: dict | None,
    *,
    section_key: str,
    limit: int = 4,
    lang: str = "no",
) -> str:
    """Strip OEM PDF page copies only — keep engine-generated <svg> illustrations."""
    text = md or ""
    text = re.sub(r"\{\{figure:[^}]+\}\}", "", text)
    text = re.sub(r"\{\{fig:[^}]+\}\}", "", text)
    text = re.sub(r"(?m)^###\s*(Sider fra teknisk kilde|Pages from technical source|"
                  r"Illustrasjoner fra kilde|Source illustrations)\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + ("\n" if text.strip() else "")


def _tip_fact_blob(facts: list[dict]) -> str:
    parts = []
    for f in facts:
        parts.append(str(f.get("key") or ""))
        parts.append(str(f.get("value") or "")[:120])
    return "\n".join(parts)


def _port(pid: str, name: str, side: str, kind: str = "electrical") -> dict:
    return {"id": pid, "name": name, "side": side, "kind": kind}


def _wire(
    fr: str,
    to: str,
    designation: str,
    *,
    size: str | None = None,
    fact_id: str | None = None,
    medium: str = "wire",
) -> dict:
    w: dict[str, Any] = {
        "from": fr,
        "to": to,
        "designation": designation,
        "medium": medium,
    }
    if size:
        w["size"] = size
    if fact_id:
        w["fact_id"] = fact_id
    return w


def build_install_diagram_specs(
    index: list[dict],
    artifact: dict | None = None,
    *,
    section_key: str = "system_overview",
    lang: str = "no",
) -> list[dict]:
    """Build foldok_diagram wiring specs from install tip facts (no vendor names).

    Recipes fire only when matching facts exist. Specs are rendered by
    ``foldok_diagram_tool`` (foldok.diagram.v1) — same engine as water-heater
    interconnection SVGs — not the card-style block renderer.
    """
    tips = collect_install_tip_facts(
        index, artifact, section_key=section_key if section_key in PROCEDURE_SECTION_KEYS
        else "sequence",
        limit=40,
    )
    if not tips:
        tips = collect_install_tip_facts(
            index, artifact, section_key="sequence", limit=40,
        )
    blob = _tip_fact_blob(tips).lower()
    # Also scan focus-source captions / summaries (figures often lack tip keys)
    allowed = allowed_install_files(index, artifact)
    for e in index or []:
        fn = str(e.get("file") or "")
        if allowed and fn not in allowed:
            continue
        blob += "\n" + str(e.get("detail_summary") or "").lower()
        blob += "\n" + str(e.get("caption") or "").lower()
        blob += "\n" + fn.lower()
        for role in e.get("roles") or []:
            blob += "\n" + str(role).lower()
        for f in e.get("facts") or []:
            blob += "\n" + str(f.get("key") or "").lower()
            blob += "\n" + str(f.get("value") or "")[:200].lower()
        # Page text — tip harvest + keyword scan (figures often lack tip verbs)
        try:
            folders = (artifact or {}).get("_folders")
            for row in harvest_page_guidance(e, folders, limit=8):
                blob += "\n" + str(row.get("value") or "").lower()
            path = resolve_source_path(fn, folders)
            if path:
                try:
                    from foldok_compile import extract_pdf_pages
                    for p in extract_pdf_pages(path) or []:
                        t = (p.get("text") or "").lower()
                        if re.search(
                            r"cable\s*tray|kabelrenne|shielding effect|"
                            r"equipotential|protection class|selv",
                            t,
                        ):
                            blob += "\n" + t[:800]
                except Exception:
                    pass
        except Exception:
            pass
    by_key = {str(f.get("key") or "").lower(): f for f in tips}

    def _fid(*keys: str) -> str | None:
        for k in keys:
            f = by_key.get(k)
            if f and f.get("id"):
                return f["id"]
            for kk, ff in by_key.items():
                if k in kk and ff.get("id"):
                    return ff["id"]
        return None

    no = lang != "en"
    system = system_under_install(artifact) or ("feltutstyr" if no else "field device")
    device_label = {
        "sensor": ("Sikkerhetssensor" if no else "Safety sensor"),
        "cable_tray": ("Kabelrenne" if no else "Cable tray"),
        "machine": ("Maskin" if no else "Machine"),
        "enclosure": ("Skap" if no else "Enclosure"),
    }.get(system, ("Feltutstyr" if no else "Field equipment"))

    specs: list[dict] = []

    # ── Shielding + earthing (control / signal + PE bond) ──────────────
    if re.search(r"(?i)shield|earth|ground|jording|fe_|pe_|equipotential|bond|strap", blob):
        if section_key in ("system_overview", "sequence", "safety", "prerequisites"):
            comps = [
                {
                    "id": "DEV",
                    "label": device_label,
                    "tag": "-B1",
                    "type": "sensor",
                    "ports": [
                        _port("shield", "SHIELD", "right", "signal"),
                        _port("sig", "SIG", "right", "signal"),
                        _port("gnd", "0V", "right"),
                    ],
                },
                {
                    "id": "CAB",
                    "label": "Kontrollskap" if no else "Control cabinet",
                    "tag": "-A1",
                    "type": "distribution_board",
                    "ports": [
                        _port("fe", "FE", "left"),
                        _port("pe", "PE", "left"),
                        _port("sig", "SIG", "left", "signal"),
                    ],
                },
                {
                    "id": "PE1",
                    "label": "FE / PE" if no else "FE / PE",
                    "tag": "PE",
                    "type": "earth",
                    "ports": [_port("t", "PE", "top")],
                },
            ]
            conns = [
                _wire("DEV.shield", "CAB.fe", "SIG", size="0.5 mm2",
                      fact_id=_fid("shield_connection", "shielding_connection", "shield")),
                _wire("DEV.sig", "CAB.sig", "SIG", size="0.5 mm2",
                      fact_id=_fid("signal", "data_cable")),
                _wire("CAB.pe", "PE1.t", "GND", size="2.5 mm2",
                      fact_id=_fid("ground_strap", "ground_contact", "earth", "bond")),
            ]
            if re.search(r"(?i)double\s*shield|braided|foil|coverage", blob):
                comps.insert(1, {
                    "id": "CBL",
                    "label": "Skjermet datakabel" if no else "Shielded data cable",
                    "tag": "-W1",
                    "type": "cable_shielded",
                    "ports": [
                        _port("dev", "DEV", "left", "signal"),
                        _port("cab", "CAB", "right", "signal"),
                        _port("braid", "BRAID", "bottom", "signal"),
                    ],
                })
                conns = [
                    _wire("DEV.shield", "CBL.dev", "SIG", size="0.5 mm2",
                          fact_id=_fid("cable_shield", "data_cable", "shield_coverage")),
                    _wire("CBL.cab", "CAB.fe", "SIG", size="0.5 mm2",
                          fact_id=_fid("shield_connection", "shielding_connection")),
                    _wire("DEV.sig", "CAB.sig", "SIG", size="0.5 mm2"),
                    _wire("CAB.pe", "PE1.t", "GND", size="2.5 mm2",
                          fact_id=_fid("ground_strap", "earth", "bond")),
                ]
            specs.append({
                "id": "install_shield_earth",
                "recipe": "shield_earth",
                "title": ("Skjerming og jording" if no else "Shielding and earthing"),
                "subtitle": (
                    "Kobling · skjerm til FE/PE" if no
                    else "Interconnection · shield to FE/PE"
                ),
                "domain": "electrical",
                "profile": "wiring",
                "jurisdiction": "ELV_DC",
                "components": comps,
                "connections": conns,
            })

            # Reference: typical equipotential bonding connectors
            if re.search(
                r"(?i)equipotential|ground_strap|bond(?:ing)?|jordbånd|jordstropp|"
                r"braid(?:ed)?\s*strap|bonding\s*strap",
                blob,
            ):
                specs.append({
                    "id": "install_bond_connectors",
                    "recipe": "bond_connectors",
                    "title": (
                        "Ekvipotensialforbindelser" if no
                        else "Equipotential bonding connectors"
                    ),
                    "subtitle": (
                        "Stor flate / stort tverrsnitt · typiske forbindere"
                        if no else
                        "Large area / large cross-section · typical connectors"
                    ),
                    "domain": "electrical",
                    "profile": "wiring",
                    "jurisdiction": "ELV_DC",
                    "components": [
                        {
                            "id": "BS1",
                            "label": (
                                "Solid stropp / skinne"
                                if no else "Solid strap / busbar link"
                            ),
                            "tag": "1",
                            "type": "bond_strap",
                            "ports": [
                                _port("a", "A", "left"),
                                _port("b", "B", "right"),
                            ],
                        },
                        {
                            "id": "BS2",
                            "label": (
                                "Flettet bånd · firkantlugg"
                                if no else "Braided strap · square lugs"
                            ),
                            "tag": "2",
                            "type": "bond_braid_lug",
                            "ports": [
                                _port("a", "A", "left"),
                                _port("b", "B", "right"),
                            ],
                        },
                        {
                            "id": "BS3",
                            "label": (
                                "Flettet bånd · ringkabelsko"
                                if no else "Braided strap · ring terminals"
                            ),
                            "tag": "3",
                            "type": "bond_braid_ring",
                            "ports": [
                                _port("a", "A", "left"),
                                _port("b", "B", "right"),
                            ],
                        },
                    ],
                    "connections": [],
                })

    # ── Cable tray shielding (deep U vs shallow) ───────────────────────
    if (
        system == "cable_tray"
        or re.search(
            r"(?i)cable\s*tray|kabelrenne|kabelbro|tray.*shield|shield.*tray|"
            r"u-?shaped\s*cable|side\s*walls?",
            blob,
        )
    ):
        if section_key in ("system_overview", "sequence", "prerequisites", "safety"):
            # Insert after shield (index 1) so max_diagrams keeps it
            tray_spec = {
                "id": "install_cable_tray_shield",
                "recipe": "cable_tray_shield",
                "title": (
                    "Skjermingseffekt i kabelrenne" if no
                    else "Shielding effect for cable trays"
                ),
                "subtitle": (
                    "Lukket / høy U-profil · kabler under toppkant"
                    if no else
                    "Closed / high U-profile · cables below top edge"
                ),
                "domain": "electrical",
                "profile": "wiring",
                "jurisdiction": "ELV_DC",
                "components": [
                    {
                        "id": "TD",
                        "label": (
                            "Høy U-renne (foretrukket)" if no
                            else "Deep U-tray (preferred)"
                        ),
                        "tag": "OK",
                        "type": "cable_tray_deep",
                        "ports": [_port("m", "—", "bottom")],
                    },
                    {
                        "id": "TS",
                        "label": (
                            "Lav / bred U-renne" if no
                            else "Shallow / wide U-tray"
                        ),
                        "tag": "—",
                        "type": "cable_tray_shallow",
                        "ports": [_port("m", "—", "bottom")],
                    },
                    {
                        "id": "TDO",
                        "label": (
                            "Kabler godt under kant" if no
                            else "Cables well below rim"
                        ),
                        "tag": "OK",
                        "type": "cable_tray_deep_ok",
                        "ports": [_port("m", "—", "bottom")],
                    },
                    {
                        "id": "TSB",
                        "label": (
                            "Kabler nær lav kant" if no
                            else "Cables near low rim"
                        ),
                        "tag": "NEI" if no else "NO",
                        "type": "cable_tray_shallow_bad",
                        "ports": [_port("m", "—", "bottom")],
                    },
                ],
                "connections": [],
            }
            insert_at = 1 if specs and specs[0].get("recipe") == "shield_earth" else 0
            specs.insert(insert_at, tray_spec)

    # ── Mains filter at cabinet entry ──────────────────────────────────
    if re.search(r"(?i)mains\s*filter|filter.*cabinet|cabinet.*entry|skap.*inngang", blob):
        if section_key in ("system_overview", "sequence", "prerequisites"):
            specs.append({
                "id": "install_mains_filter",
                "recipe": "mains_filter",
                "title": (
                    "Nettfilter ved skapinngang" if no else "Mains filter at cabinet entry"
                ),
                "subtitle": (
                    "Kobling · TN 230/400 V" if no else "Interconnection · TN 230/400 V"
                ),
                "domain": "electrical",
                "profile": "wiring",
                "jurisdiction": "NO_TN_230_400",
                "components": [
                    {
                        "id": "NET",
                        "label": "Nett / supply" if no else "Mains / supply",
                        "tag": "-G1",
                        "type": "distribution_board",
                        "ports": [
                            _port("l1", "L1", "right"),
                            _port("n", "N", "right"),
                            _port("pe", "PE", "right"),
                        ],
                    },
                    {
                        "id": "FIL",
                        "label": "Nettfilter" if no else "Mains filter",
                        "tag": "-Z1",
                        "type": "mains_filter",
                        "ports": [
                            _port("line_l", "LINE L", "left"),
                            _port("line_n", "LINE N", "left"),
                            _port("load_l", "LOAD L", "right"),
                            _port("load_n", "LOAD N", "right"),
                            _port("pe", "PE", "bottom"),
                        ],
                    },
                    {
                        "id": "CAB",
                        "label": "Kontrollskap" if no else "Control cabinet",
                        "tag": "-A1",
                        "type": "distribution_board",
                        "ports": [
                            _port("l1", "L1", "left"),
                            _port("n", "N", "left"),
                            _port("pe", "PE", "left"),
                        ],
                    },
                    {
                        "id": "DEV",
                        "label": device_label,
                        "tag": "-B1",
                        "type": "sensor",
                        "ports": [
                            _port("pwr", "PWR", "left"),
                            _port("pe", "PE", "left"),
                        ],
                    },
                ],
                "connections": [
                    _wire("NET.l1", "FIL.line_l", "L1", size="2.5 mm2",
                          fact_id=_fid("mains_filter", "filter")),
                    _wire("NET.n", "FIL.line_n", "N", size="2.5 mm2",
                          fact_id=_fid("mains_filter", "filter")),
                    _wire("NET.pe", "FIL.pe", "PE", size="2.5 mm2",
                          fact_id=_fid("mains_filter", "ground")),
                    _wire("FIL.load_l", "CAB.l1", "L1", size="2.5 mm2",
                          fact_id=_fid("mains_filter_installation",
                                       "mains_filter_placement", "mains_filter")),
                    _wire("FIL.load_n", "CAB.n", "N", size="2.5 mm2",
                          fact_id=_fid("mains_filter_installation", "mains_filter")),
                    _wire("FIL.pe", "CAB.pe", "PE", size="2.5 mm2",
                          fact_id=_fid("mains_filter", "ground")),
                    _wire("CAB.l1", "DEV.pwr", "L1", size="1.5 mm2"),
                    _wire("CAB.pe", "DEV.pe", "PE", size="1.5 mm2"),
                ],
            })

    # ── SELV / protection class ────────────────────────────────────────
    if re.search(r"(?i)selv|pelv|protection_class|extra.?low|sikkerhetslavspent", blob):
        if section_key in ("system_overview", "safety", "prerequisites"):
            specs.append({
                "id": "install_selv",
                "recipe": "selv_supply",
                "title": (
                    "SELV/PELV — sikkerhetslavspent"
                    if no else "SELV/PELV — safety extra-low voltage"
                ),
                "subtitle": (
                    "Kobling · isolert lavspent · klasse III"
                    if no else
                    "Interconnection · isolated ELV · class III"
                ),
                "domain": "electrical",
                "profile": "wiring",
                "jurisdiction": "ELV_DC",
                "components": [
                    {
                        "id": "NET",
                        "label": (
                            "Nett (ikke direkte)" if no else "Mains (not direct)"
                        ),
                        "tag": "-G1",
                        "type": "distribution_board",
                        "ports": [
                            _port("l1", "L1", "right"),
                            _port("n", "N", "right"),
                        ],
                    },
                    {
                        "id": "ISO",
                        "label": (
                            "Sikkerhetsisolert PSU" if no
                            else "Safety-isolated PSU"
                        ),
                        "tag": "-T1",
                        "type": "power_supply",
                        "ports": [
                            _port("pri_l", "PRI L", "left"),
                            _port("pri_n", "PRI N", "left"),
                            _port("sec_p", "SEC+", "right"),
                            _port("sec_n", "SEC 0V", "right"),
                            _port("pe", "PE", "bottom"),
                        ],
                    },
                    {
                        "id": "DEV",
                        "label": device_label,
                        "tag": "-B1",
                        "type": "sensor",
                        "ports": [
                            _port("vplus", "+", "left"),
                            _port("gnd", "0V", "left"),
                            _port("mark", "III", "right", "signal"),
                        ],
                    },
                    {
                        "id": "PC3",
                        "label": (
                            "Beskyttelsesklasse III" if no
                            else "Protection class III"
                        ),
                        "tag": "III",
                        "type": "protection_class_iii",
                        "ports": [_port("m", "SELV", "left", "signal")],
                    },
                ],
                "connections": [
                    _wire("NET.l1", "ISO.pri_l", "VIN", size="0.75 mm2",
                          fact_id=_fid("selv_generation", "selv")),
                    _wire("NET.n", "ISO.pri_n", "GND", size="0.75 mm2",
                          fact_id=_fid("selv_generation", "selv")),
                    _wire("ISO.sec_p", "DEV.vplus", "24V", size="0.5 mm2",
                          fact_id=_fid("selv_extra_low", "selv_dc",
                                       "protection_class", "protection_class_iii")),
                    _wire("ISO.sec_n", "DEV.gnd", "GND", size="0.5 mm2",
                          fact_id=_fid("selv_isolation", "selv")),
                    _wire("DEV.mark", "PC3.m", "signal", size="0.5 mm2",
                          fact_id=_fid("protection_class_iii", "protection_class",
                                       "selv")),
                ],
            })

            # Reference strip — IEC marks I / II / III (from cited class facts)
            if re.search(r"(?i)protection_class|klasse\s*[i1]|class\s*[i1]|double\s*insul", blob):
                specs.append({
                    "id": "install_protection_classes",
                    "recipe": "protection_classes",
                    "title": (
                        "Beskyttelsesklasser (IEC)" if no
                        else "Protection classes (IEC)"
                    ),
                    "subtitle": (
                        "Navneskilt-symboler · klasse I / II / III"
                        if no else
                        "Nameplate marks · class I / II / III"
                    ),
                    "domain": "electrical",
                    "profile": "wiring",
                    "jurisdiction": "ELV_DC",
                    "components": [
                        {
                            "id": "PC1",
                            "label": (
                                "Klasse I — PE-tilkobling"
                                if no else "Class I — protective earth"
                            ),
                            "tag": "I",
                            "type": "protection_class_i",
                            "ports": [_port("m", "PE", "bottom")],
                        },
                        {
                            "id": "PC2",
                            "label": (
                                "Klasse II — dobbel isolasjon"
                                if no else "Class II — double insulation"
                            ),
                            "tag": "II",
                            "type": "protection_class_ii",
                            "ports": [_port("m", "—", "bottom")],
                        },
                        {
                            "id": "PC3",
                            "label": (
                                "Klasse III — SELV"
                                if no else "Class III — SELV"
                            ),
                            "tag": "III",
                            "type": "protection_class_iii",
                            "ports": [_port("m", "SELV", "bottom")],
                        },
                    ],
                    # No wires — these are nameplate marks, not a circuit.
                    "connections": [],
                })

    return specs


def render_install_wiring_svg(spec: dict) -> str:
    """Render one install recipe via foldok_diagram_tool (foldok.diagram.v1).

    Reference strips (no wires) stay at native mark size — stretching them to
    the full wiring figure width made bonding / tray / class marks look huge.
    """
    from foldok_diagram_tool import run as diagram_tool_run

    recipe = str(spec.get("recipe") or "")
    conns = spec.get("connections") or []
    n = len(spec.get("components") or [])
    if not conns or recipe in (
        "bond_connectors", "cable_tray_shield", "protection_classes",
    ):
        # Horizontal strip: ~column_gap per mark, keep under ~280 pt wide
        width = float(min(280.0, max(140.0, 70.0 * max(n, 1))))
    else:
        width = 520.0
    result = diagram_tool_run(spec, target_width_pt=width)
    return result.svg or ""


def compile_install_diagrams_md(
    section_key: str,
    index: list[dict],
    artifact: dict | None = None,
    *,
    lang: str = "no",
    max_diagrams: int = 3,
) -> str:
    """Render Foldok wiring SVGs for a section — original figures, not OEM pages."""
    specs = build_install_diagram_specs(
        index, artifact, section_key=section_key, lang=lang,
    )
    if not specs:
        return ""
    no = lang != "en"
    parts = [
        "### " + ("Genererte illustrasjoner" if no else "Generated illustrations"),
        "",
        "*" + (
            "Foldok koblingsskjema fra siterte installasjonsfakta. "
            "Verifiser mot datablad før utførelse."
            if no else
            "Foldok interconnection diagrams from cited install facts. "
            "Verify against the datasheet before work."
        ) + "*",
    ]
    for spec in specs[:max_diagrams]:
        title = spec.get("title") or "Install diagram"
        try:
            svg = render_install_wiring_svg(spec)
        except Exception as e:
            parts.append(f"\n*({title}: diagram render failed — {e})*")
            continue
        if not svg or "<svg" not in svg.lower():
            continue
        if "foldok.diagram.v1" not in svg and 'data-style="' not in svg:
            # Still usable, but flag quality path missed
            pass
        parts.append(f"\n### {title}\n\n{svg.strip()}")
    if len(parts) <= 3:
        return ""
    return "\n\n".join(parts).strip()


def compile_install_identity_md(
    index: list[dict],
    artifact: dict | None = None,
    *,
    lang: str = "no",
) -> str:
    """Engineering identity from allowlisted sources + locked system — no market sludge."""
    system = system_under_install(artifact) or "—"
    name = str((artifact or {}).get("name") or "—")
    allowed = allowed_install_files(index, artifact)
    by_key: dict[str, dict] = {}
    for e in index or []:
        fn = e.get("file") or ""
        if fn not in allowed:
            continue
        for f in e.get("facts") or []:
            key = str(f.get("key") or "").strip().lower()
            if not key or not f.get("id"):
                continue
            if key in IDENTITY_DENY or IDENTITY_DENY_RX.search(key):
                continue
            if key in IDENTITY_ALLOW or any(key.startswith(p) for p in IDENTITY_ALLOW_PREFIX):
                # Prefer first strong hit; manufacturer over manufacturer_name later
                if key not in by_key:
                    by_key[key] = f
            if key in ("applicable_products", "product_type", "equipment_type"):
                by_key.setdefault("system_type", f)

    def _row(label: str, fact: dict | None, fallback: str) -> str:
        if fact and fact.get("id"):
            val = str(fact.get("value") or "").replace("|", "/")
            return f"| {label} | {val} | — | {{{{fact:{fact['id']}}}}} |"
        return f"| {label} | {fallback} | — | — |"

    mfr = by_key.get("manufacturer") or by_key.get("manufacturer_name") or by_key.get("supplier")
    stype = by_key.get("system_type") or by_key.get("applicable_products")
    part = by_key.get("part_number") or by_key.get("document_part_number") or by_key.get("model")
    no = lang != "en"
    lines = [
        "| Parameter | Verdi | Enhet | Kilde |" if no else "| Parameter | Value | Unit | Source |",
        "|-----------|-------|-------|-------|",
        f"| {'prosjekt' if no else 'project'} | {name} | — | artefakt |",
        f"| system_under_install | {system} | — | låst |",
        _row("manufacturer", mfr, "[MANGLER: manufacturer]" if no else "[GAP: manufacturer]"),
        _row(
            "system_type",
            stype,
            system if system and system != "—" else (
                "[MANGLER: system_type]" if no else "[GAP: system_type]"
            ),
        ),
    ]
    if part:
        lines.append(_row("part / model", part, "—"))
    focus = focus_needles(artifact)
    if focus:
        lines.append(
            f"| {'fokuskilder' if no else 'focus sources'} | {', '.join(focus)} | — | chat |"
        )
    return "\n".join(lines)


def compile_install_tips_md(
    section_key: str,
    index: list[dict],
    artifact: dict | None = None,
    *,
    mapped_files: Iterable[str] | None = None,
    lang: str = "no",
) -> str | None:
    """Deterministic tip table from technical-info / install facts — no model.

    Returns None when there are no tip facts (caller may fall back to gap).
    When focus sources are locked, also harvest guidance from PDF pages that
    were never fact-extracted, and caller attaches page figures.
    """
    tips = collect_install_tip_facts(
        index, artifact, mapped_files=mapped_files, section_key=section_key,
        limit=36 if focus_needles(artifact) else 14,
    )
    # Harvest from unindexed pages of focused PDFs (sequence + prerequisites)
    page_rows: list[dict] = []
    if section_key in ("sequence", "prerequisites", "safety") and focus_needles(artifact):
        folders = (artifact or {}).get("_folders") or []
        for e in focus_source_entries(index, artifact)[:2]:
            page_rows.extend(harvest_page_guidance(e, folders, limit=12))
    if not tips and not page_rows:
        if section_key != "sequence":
            return None
        tips = collect_install_tip_facts(
            index, artifact, mapped_files=mapped_files, section_key="sequence", limit=16,
        )
        if not tips:
            allowed = allowed_install_files(index, artifact)
            evidence = set(procedure_evidence_files(index, mapped_files, artifact=artifact))
            for e in index or []:
                fn = e.get("file") or ""
                if fn not in allowed or fn not in evidence:
                    continue
                for f in e.get("facts") or []:
                    if f.get("id") and _is_tip_fact(f):
                        tips.append({"id": f["id"], **{k: v for k, v in f.items() if k != "id"}})
                if len(tips) >= 14:
                    break
    if not tips and not page_rows:
        return None

    no = lang != "en"
    title = {
        "safety": ("Sikkerhetstips fra kilder", "Safety tips from sources"),
        "prerequisites": ("Forutsetninger / forberedelse", "Prerequisites / preparation"),
        "sequence": ("Installasjons- og monteringsråd", "Installation and mounting guidance"),
        "verification": ("Kontrollpunkter", "Verification checks"),
    }.get(section_key, ("Installasjonstips", "Installation tips"))
    heading = title[0] if no else title[1]
    n_pages = int(
        ((focus_source_entries(index, artifact) or [{}])[0].get("extraction_stats") or {})
        .get("page_count") or 0
    )
    depth_note = ""
    if n_pages and focus_needles(artifact):
        depth_note = (
            f" Kilden har {n_pages} sider; Foldok gjengir siterte fakta — "
            f"ikke leverandørens originalsideoppsett."
            if no else
            f" Source has {n_pages} pages; Foldok renders cited facts — "
            f"not the supplier's original page layout."
        )
    lines = [
        f"*{heading} — sitert fra tillatte tekniske kilder; ikke en komplett leverandørprosedyre."
        f"{depth_note}*"
        if no else
        f"*{heading} — cited from allowlisted technical sources; not a complete OEM procedure."
        f"{depth_note}*",
        "",
    ]
    if no:
        lines += ["| Nr | Råd / krav | Verdi | Kilde |", "|----|------------|-------|-------|"]
    else:
        lines += ["| No | Tip / requirement | Value | Source |", "|----|-------------------|-------|--------|"]
    n = 0
    for f in tips:
        n += 1
        key = str(f.get("key") or "").replace("_", " ")
        val = str(f.get("value") or "").strip().replace("|", "/")
        unit = str(f.get("unit") or "").strip()
        if unit and unit not in val:
            val = f"{val} {unit}".strip()
        label = (key or "—").replace("|", "/")
        fid = f.get("id")
        cite = f"{{{{fact:{fid}}}}}" if fid else "—"
        lines.append(f"| {n} | {label} | {val or '—'} | {cite} |")
    if page_rows:
        lines.append("")
        lines.append(
            f"*Tillegg fra sider uten indekserte fakta ({len(page_rows)} utdrag):*"
            if no else
            f"*Extra from pages without indexed facts ({len(page_rows)} extracts):*"
        )
        lines.append("")
        if no:
            lines += ["| Nr | Råd (fra sidetekst) | Side |", "|----|---------------------|------|"]
        else:
            lines += ["| No | Tip (from page text) | Page |", "|----|---------------------|------|"]
        for f in page_rows:
            n += 1
            val = str(f.get("value") or "").replace("|", "/")
            cite = str(f.get("_page_cite") or f.get("source_location") or "—")
            lines.append(f"| {n} | {val} | {cite} |")
    return "\n".join(lines)


def cited_files_from_sections(
    sections_data: list[tuple],
    index: list[dict],
) -> list[str]:
    """Files actually used (cited facts or non-empty section mapping with content)."""
    index = dedupe_index_by_file(index)
    by_id = {f["id"]: (e.get("file") or "") for e in (index or []) for f in (e.get("facts") or []) if f.get("id")}
    used: list[str] = []
    seen = set()
    for row in sections_data or []:
        if len(row) < 3:
            continue
        sk, text, cited = row[0], row[1], row[2]
        if sk in ("declaration", "supplier_manual_gaps"):
            continue
        body = (text or "").strip()
        if not body or body.startswith("**[MANGLER:") or body.startswith("**[GAP:"):
            # Still count explicit cites if any
            pass
        for fid in cited or []:
            fn = by_id.get(fid) or ""
            if fn and fn not in seen:
                seen.add(fn)
                used.append(fn)
        # Also count files that appear in figure markers
        for m in re.finditer(r"\{\{figure:([^:}]+)", body):
            fn = m.group(1).strip()
            if fn and fn not in seen:
                seen.add(fn)
                used.append(fn)
    return used


def high_value_unused_pdfs(
    index: list[dict],
    cited: Iterable[str],
    *,
    system: str = "",
    limit: int = 6,
) -> list[dict[str, Any]]:
    cited_set = set(cited or [])
    ranked = []
    for e in index or []:
        fn = e.get("file") or ""
        if not fn or fn in cited_set:
            continue
        if not str(fn).lower().endswith(".pdf"):
            continue
        if is_market_bod_entry(e) or is_standards_list_entry(e):
            continue
        sc = install_file_score(e, system)
        if sc < INSTALL_MIN_SCORE:
            continue
        ranked.append({
            "file": fn,
            "score": round(sc, 1),
            "caption": (e.get("caption") or "")[:120],
            "why": (
                "install/manual signal" if INSTALL_LEXICON.search(_blob(e)) else
                "high-value PDF"
            ),
        })
    ranked.sort(key=lambda r: -r["score"])
    return ranked[:limit]


def compile_install_source_register(
    cited_files: list[str],
    index: list[dict],
    *,
    unused: list[dict] | None = None,
    lang: str = "no",
) -> str:
    no = lang != "en"
    by_file = {e.get("file"): e for e in (index or []) if e.get("file")}
    lines = []
    if no:
        lines.append("| # | Fil | Brukt til |")
        lines.append("|---|-----|-----------|")
    else:
        lines.append("| # | File | Used for |")
        lines.append("|---|------|----------|")
    if not cited_files:
        gap = (
            "Ingen siterte kilder i dokumentet ennå."
            if no else "No cited sources in the document yet."
        )
        lines.append(f"| — | {gap} | — |")
    else:
        for i, fn in enumerate(cited_files, 1):
            e = by_file.get(fn) or {}
            name = Path(fn).name
            use = (e.get("caption") or "")[:80] or ("Sitert i brødtekst" if no else "Cited in body")
            lines.append(f"| {i} | {name} | {use} |")

    unused = unused or []
    if unused:
        lines.append("")
        lines.append(
            "**Valgfritt — høyt verdifulle PDF-er ikke brukt** (si «utvid med …» for å ta inn):"
            if no else
            "**Optional — high-value PDFs not used** (say “expand with …” to include):"
        )
        for u in unused:
            lines.append(f"- `{Path(u['file']).name}` — {u.get('why') or 'PDF'} "
                         f"({u.get('caption') or ''})".rstrip())
    return "\n".join(lines)


def expand_offer_reply(unused: list[dict], lang: str = "no") -> str:
    if not unused:
        return (
            "\n\nSi «bruk …» eller «utvid med filnavn.pdf» med et navn fra indeksen "
            "for å låse installasjonskilden og regenerere."
            if lang != "en" else
            "\n\nSay «bruk …» or «expand with filename.pdf» naming a file from the index "
            "to lock the install source and regenerate."
        )
    if lang == "en":
        names = ", ".join(f"`{Path(u['file']).name}`" for u in unused[:5])
        return (
            f"\n\nHigh-value PDFs not cited: {names}. "
            "Say e.g. «expand with …» using one of those names."
        )
    names = ", ".join(f"`{Path(u['file']).name}`" for u in unused[:5])
    return (
        f"\n\nHøyt verdifulle PDF-er ikke sitert: {names}. "
        "Si f.eks. «utvid med …» med ett av disse navnene."
    )
