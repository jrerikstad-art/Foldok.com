"""Engineering Author — writes the story Narrative decided.

Consumes short grounded *claims*, paraphrases into the document language.
Never dumps file abstracts / catalog blurbs into paragraphs.
One body cite per file (unless safety-critical). Section purpose gate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .model import RetrievalHit
from .plan import OutlineSection
from .retrieve import retrieve
from .claims_bridge import (
    claims_for_section,
    coherence_gap_lines,
    corpus_claims,
    format_claim_sentence,
    has_type_coverage,
    section_needs_types,
)

if TYPE_CHECKING:
    from .narrative import NarrativePlan
    from foldok_claims import ClaimSet
    from foldok_claims.coherence import CoherenceReport

CONTACT_RX = re.compile(
    r"(?i)([\w.+-]+@[\w-]+\.[\w.-]+|\+?\d[\d\s().-]{7,}\d)"
)
STD_ID_RX = re.compile(
    r"(?i)\b((?:EN|IEC|ISO|NEK|HD)\s*\d[\d\-:/]*|"
    r"MIL[-\s]?STD[-\s]?\d[\w\-]*|"
    r"IEEE\s*(?:Std\s*)?\d[\w\-]*|"
    r"ASTM\s*[A-Z]?\d[\w\-]*|"
    r"UL\s*\d[\w\-]*|"
    r"NEMA\s*(?:VE\s*)?[A-Z]?\d?[\w\-]*)\b"
)
NUM_RX = re.compile(r"\b\d+(?:[.,]\d+)?\b")

ABSTRACT_RX = re.compile(
    r"(?i)\b(comprehensive technical (documentation|handbook|presentation)|"
    r"covers (emc|safety|mandatory)|this (document|guide|presentation) (provides|covers)|"
    r"independently verified by|"
    r"technical documentation on)\b"
)
CLASS_RX = re.compile(
    r"(?i)\b(class\s*[1-6]|kabelklasse\s*[1-6]|kabelklasser?|cable\s*class(?:es)?|"
    r"category\s*[1-6]|segregation|separation\s+between|klassevalg)\b"
)
ZONE_RX = re.compile(
    r"(?i)\b(zones?|soner?|zoning|faraday|bonding|earthing|equipotential|"
    r"shield\s+grounding|emc\s+zone|jordovergang)\b"
)
SHIELD_RX = re.compile(
    r"(?i)\b(shield(?:ing)?|attenuation|skjerm|emi|emc|mil[-\s]?std|"
    r"50174|york\s+emc)\b"
)

# Known clean roles — prefer these over truncated context snippets
_STD_ROLES = {
    "EN50174": ("kabling / installasjon (EMC-avstand)", "cabling / installation (EMC spacing)"),
    "EN501741": ("kabling — generelle krav", "cabling — general requirements"),
    "EN501742": ("kabling — installasjonspraksis / avstand", "cabling — installation practice / spacing"),
    "BSEN50174": ("kabling / installasjon (EMC-avstand)", "cabling / installation (EMC spacing)"),
    "BSEN501742": ("skjermingsavstand / installasjonspraksis", "shielding spacing / installation practice"),
    "IEC61537": ("cable tray / kabelstige", "cable tray / ladder systems"),
    "EN61537": ("cable tray / kabelstige", "cable tray / ladder systems"),
    "IEC61914": ("kabelklemmer / feste", "cable cleats / fastening"),
    "EN50310": ("jording og potentialutjevning", "earthing and bonding"),
    "IEEE299": ("måling av skjermingseffektivitet", "shielding effectiveness measurement"),
    "ASTME1851": ("skjermingseffektivitet (test)", "shielding effectiveness (test)"),
    "ASTMD4935": ("skjermingseffektivitet (planmateriale)", "shielding effectiveness (planar materials)"),
    "MILSTD285": ("skjermingseffektivitet / EMI-test", "shielding effectiveness / EMI test"),
    "MILSTD188125": ("HEMP / skjermingseffektivitet", "HEMP / shielding effectiveness"),
    "NEMAVE1": ("cable tray-konstruksjon", "cable tray construction"),
    "NEMAVE": ("cable tray-konstruksjon", "cable tray construction"),
}

# Drop from standards register — not EMC-argumentative roles
_STD_DROP = re.compile(
    r"(?i)^(ISO\s*9|ISO\s*14|ISO\s*14001|ISO\s*9001|ISO\s*14025|"
    r"UL\s*870|REACH|RoHS|CE\b)"
)

BANNED_VOICE_RX = re.compile(
    r"(?i)\b("
    r"the following findings|according to the documents|"
    r"the corpus contains|kildene beskriver også|kildematerialet|"
    r"denne briefen samler|sources also note that|"
    r"comprehensive technical|"
    r"covers emc fundamentals"
    r")\b"
)


@dataclass
class CiteRegistry:
    """Maps file_id → [n]. Tracks body uses so one file ≈ one narrative cite."""
    _order: list[str] = field(default_factory=list)
    _body_used: set[str] = field(default_factory=set)
    _claim_texts: set[str] = field(default_factory=set)

    def number_for(self, file_id: str) -> int:
        fid = (file_id or "").strip()
        if not fid:
            return 0
        if fid not in self._order:
            self._order.append(fid)
        return self._order.index(fid) + 1

    def mark(self, file_id: str, *, body: bool = True) -> str:
        fid = (file_id or "").strip()
        if not fid:
            return ""
        n = self.number_for(fid)
        if body:
            self._body_used.add(fid)
        return f"[{n}]" if n else ""

    def unused(self, file_id: str) -> bool:
        return (file_id or "") not in self._body_used

    def claim_fresh(self, text: str) -> bool:
        key = re.sub(r"\s+", " ", (text or "").lower())[:90]
        if not key or key in self._claim_texts:
            return False
        self._claim_texts.add(key)
        return True

    def appendix_lines(self, *, lang: str = "no") -> list[str]:
        if not self._order:
            return ["Ingen siterte kilder." if (lang or "no").startswith("no") else "No cited sources."]
        return [f"[{i}] {fid}" for i, fid in enumerate(self._order, 1)]

    @property
    def files(self) -> list[str]:
        return list(self._order)


@dataclass
class Claim:
    """One short, usable fact — not a PDF abstract."""
    text_no: str
    text_en: str
    file_id: str
    kind: str = "fact"  # fact | measure | standard_ref | principle
    signals: set[str] = field(default_factory=set)


@dataclass
class SectionDraft:
    heading: str
    purpose: str
    kind: str
    prose: str = ""
    gap: str = ""
    omitted: bool = False
    hits: list[RetrievalHit] = field(default_factory=list)
    author_intent: str = ""
    arc_beat: str = ""
    fidelity_ok: bool = True


def _usable(index):
    return [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]


def _looks_like_abstract(text: str) -> bool:
    t = text or ""
    if len(t) > 180 and ABSTRACT_RX.search(t):
        return True
    if t.lower().startswith("comprehensive "):
        return True
    if re.match(r"(?i)^(this|the)\s+(document|guide|handbook|presentation)\b", t):
        return True
    return False


def _claim_from_fact_line(text: str, file_id: str) -> Claim | None:
    """Parse 'key: value — excerpt' into a short claim."""
    raw = (text or "").strip()
    if not raw or CONTACT_RX.search(raw):
        return None
    key, val = "", raw
    if ":" in raw:
        key, val = raw.split(":", 1)
        key, val = key.strip(), val.strip()
    if " — " in val:
        val = val.split(" — ", 1)[0].strip()
    val = re.sub(r"\s+", " ", val)[:120]
    key_l = key.lower().replace("_", " ")
    signals: set[str] = set()
    blob = f"{key_l} {val}".lower()
    if CLASS_RX.search(blob):
        signals.add("class")
    if ZONE_RX.search(blob):
        signals.add("zone")
    if SHIELD_RX.search(blob):
        signals.add("shield")

    # Norwegian paraphrases for common keys
    if "attenuation" in key_l or "attenuat" in key_l:
        unit = ""
        return Claim(
            text_no=f"målt skjermingsdemping oppgis til {val}",
            text_en=f"measured shielding attenuation is given as {val}",
            file_id=file_id, kind="measure", signals=signals | {"shield"},
        )
    if "cable class" in key_l or "kabelklasse" in key_l or re.search(r"(?i)^class\s*[1-6]", val):
        return Claim(
            text_no=f"kabelklasse angis som {val}",
            text_en=f"cable class is given as {val}",
            file_id=file_id, kind="fact", signals=signals | {"class"},
        )
    if "separat" in key_l or "segregat" in key_l or "spacing" in key_l:
        return Claim(
            text_no=f"separasjons-/avstandskrav: {val}",
            text_en=f"separation/spacing requirement: {val}",
            file_id=file_id, kind="fact", signals=signals | {"class"},
        )
    if "test standard" in key_l or "governing standard" in key_l:
        return Claim(
            text_no=f"relevant referanse er {val}",
            text_en=f"relevant reference is {val}",
            file_id=file_id, kind="standard_ref", signals=signals,
        )
    if "standard" in key_l and ("list" in key_l or "reference" in key_l):
        # Spreadsheet row labels — not narrative claims
        return None
    if "installation distance" in key_l and "ceiling" in key_l:
        # Install clearance — weak for class/EMC story unless asked
        return None
    if key and val and len(val) < 80 and not _looks_like_abstract(val):
        if re.search(r"(?i)(conversion failed|missing docx|historical\s*=\s*\d{4})", val):
            return None
        # Skip encyclopedia trivia
        if re.search(r"(?i)\b(miesbach|munich|1882)\b", val):
            return None
        # Skip English catalogue enumerations
        if re.search(r"(?i)^(cabling|covers|requirements for)\b", val):
            return None
        nice = key_l or "verdi"
        return Claim(
            text_no=f"{nice} = {val}",
            text_en=f"{nice} = {val}",
            file_id=file_id, kind="fact", signals=signals,
        )
    return None


def _claim_from_caption(text: str, file_id: str) -> Claim | None:
    """Pull one concrete claim from caption — never the whole abstract."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return None
    if re.search(r"(?i)(conversion failed|missing docx|error reading|failed to parse|reference list)", t):
        return None

    # York / BS EN 50174-2
    if re.search(r"(?i)york\s+emc", t) and re.search(r"(?i)(BS\s*EN\s*50174-?2|EN\s*50174-?2)", t):
        return Claim(
            text_no=(
                "York EMC-tester viser skjermingsytelse bedre enn BS EN 50174-2-kravet "
                "ved typisk 200 mm avstandskonfigurasjon"
            ),
            text_en=(
                "York EMC tests show shielding performance better than BS EN 50174-2 "
                "at a typical 200 mm spacing configuration"
            ),
            file_id=file_id, kind="measure", signals={"shield", "class"},
        )
    m = re.search(r"(?i)(BS\s*EN\s*50174-?2|EN\s*50174-?2).{0,40}?(200\s*mm)", t)
    if m:
        return Claim(
            text_no="BS EN 50174-2 knytter skjermings-/avstandskrav til 200 mm-konfigurasjon",
            text_en="BS EN 50174-2 ties shielding/spacing practice to a 200 mm configuration",
            file_id=file_id, kind="principle", signals={"shield", "class"},
        )

    m = re.search(r"(?i)(MIL[-\s]?STD[-\s]?\d+[\w\-]*).{0,40}?(\d+\s*(?:to\s*)?\d+\s*dB|\d+\s*dB)", t)
    if m:
        return Claim(
            text_no=f"skjermingstest mot {m.group(1).upper().replace(' ', '-')} med demping {m.group(2)}",
            text_en=f"shielding test to {m.group(1)} with attenuation {m.group(2)}",
            file_id=file_id, kind="measure", signals={"shield"},
        )

    if re.search(r"(?i)cable\s*classes?\s*1\s*[–\-to]+\s*6|classes?\s*1\s*[–\-]?\s*6", t):
        return Claim(
            text_no="kabelklasser 1–6 brukes for å skille kraft- og signalkretser",
            text_en="cable classes 1–6 are used to separate power and signal circuits",
            file_id=file_id, kind="principle", signals={"class"},
        )
    if CLASS_RX.search(t) and re.search(r"(?i)segregat|separat|power.+signal|signal.+power", t):
        return Claim(
            text_no="klasse-/separasjonspraksis skiller kraft- og signalkretser",
            text_en="class/segregation practice separates power and signal circuits",
            file_id=file_id, kind="principle", signals={"class"},
        )

    # Zone: require explicit zone word (not any shield hit)
    if re.search(r"(?i)\b(zone|zones|sone|soner|zoning)\b", t) and (
        SHIELD_RX.search(t) or re.search(r"(?i)\b(earth|jord|bond)", t)
    ):
        return Claim(
            text_no="EMC-soner og skjerm-/jordoverganger spesifiseres som del av installasjonspraksis",
            text_en="EMC zones and shield/earth transitions are specified as installation practice",
            file_id=file_id, kind="principle", signals={"zone", "shield"},
        )

    if len(t) <= 120 and not _looks_like_abstract(t):
        signals: set[str] = set()
        if CLASS_RX.search(t):
            signals.add("class")
        if ZONE_RX.search(t):
            signals.add("zone")
        if SHIELD_RX.search(t):
            signals.add("shield")
        if not signals:
            return None
        short = t.rstrip(".")
        return Claim(
            text_no=short if _mostly_norwegian(short) else _en_claim_to_no(short, signals),
            text_en=short,
            file_id=file_id, kind="principle", signals=signals,
        )
    return None


def _mostly_norwegian(s: str) -> bool:
    return bool(re.search(r"[æøåÆØÅ]", s)) or bool(
        re.search(r"(?i)\b(og|til|for|med|er|som|ikke|ved|fra)\b", s)
    )


def _en_claim_to_no(short: str, signals: set[str]) -> str:
    """Minimal deterministic paraphrase for short English claims."""
    s = short
    s = re.sub(r"(?i)\bEMI/RFI shielded cable tray\b", "EMI/RFI-skjermet kabelbane", s)
    s = re.sub(r"(?i)\bshielding attenuation\b", "skjermingsdemping", s)
    s = re.sub(r"(?i)\belectromagnetic compatibility\b", "elektromagnetisk kompatibilitet", s)
    s = re.sub(r"(?i)\bcable tray\b", "kabelbane", s)
    if signals == {"shield"} or "shield" in signals:
        return f"underlaget beskriver {s[0].lower()}{s[1:]}" if s else s
    return s


def extract_claims(hits: list[RetrievalHit], *, limit: int = 6) -> list[Claim]:
    """Prefer fact rows; from captions extract patterns — never full abstracts."""
    claims: list[Claim] = []
    seen = set()

    def _add(c: Claim | None):
        if not c or not c.text_no:
            return
        key = (c.file_id, c.text_no[:80].lower())
        if key in seen:
            return
        seen.add(key)
        claims.append(c)

    # Pass 1: fact-shaped hits
    for h in hits:
        t = h.text or ""
        if re.match(r"(?i)^[a-z0-9_ ]+:\s+", t) or " — " in t:
            _add(_claim_from_fact_line(t, h.file_id))
        if len(claims) >= limit:
            return claims

    # Pass 2: pattern extraction from any text
    for h in hits:
        _add(_claim_from_caption(h.text or "", h.file_id))
        if len(claims) >= limit:
            break
    return claims


def _purpose_needs(purpose: str, heading: str, retrieve_query: str) -> set[str]:
    blob = f"{purpose} {heading} {retrieve_query}".lower()
    need: set[str] = set()
    if any(w in blob for w in ("kabelklasse", "cable class", "separa", "segregat", "klasse")):
        need.add("class")
    if any(w in blob for w in ("sone", "zone", "jord", "earth", "bonding")):
        need.add("zone")
    if any(w in blob for w in ("emc", "skjerm", "shield")) and "designbegrens" in blob:
        need.add("shield")
    return need


def _claims_satisfy(claims: list[Claim], need: set[str]) -> bool:
    if not need:
        return bool(claims)
    have = set()
    for c in claims:
        have |= c.signals
    return bool(need & have)


def _pick_claims(claims: list[Claim], cites: CiteRegistry, *, n: int = 2,
                 prefer: set[str] | None = None) -> list[Claim]:
    """Prefer unused files, fresh claim text, and matching signals."""
    prefer = prefer or set()
    ranked = sorted(
        claims,
        key=lambda c: (
            0 if cites.unused(c.file_id) else 1,
            0 if (prefer & c.signals) else 1,
            0 if c.kind in ("measure", "principle") else 1,
            0 if "york" in c.text_no.lower() or "50174" in c.text_no else 1,
        ),
    )
    out: list[Claim] = []
    files: set[str] = set()
    for c in ranked:
        if c.file_id in files:
            continue
        if not cites.claim_fresh(c.text_no):
            continue
        out.append(c)
        files.add(c.file_id)
        if len(out) >= n:
            break
    return out


def _sentence_for(claim: Claim, *, no: bool, cites: CiteRegistry, wrapper: str) -> str:
    body = claim.text_no if no else claim.text_en
    mark = cites.mark(claim.file_id, body=True)
    return wrapper.format(claim=body.rstrip("."), mark=mark)


def _foldok_to_local(fc_claim, *, lang: str = "no") -> Claim:
    """Adapt foldok_claims.Claim → Author Claim (short sentence + signals)."""
    text = format_claim_sentence(fc_claim, lang=lang)
    signals: set[str] = set()
    t = (fc_claim.type or "").lower()
    blob = (fc_claim.text or "").lower()
    if t == "classification" or getattr(fc_claim.scope, "cable_class", ""):
        signals.add("class")
    if t in ("rule", "practice", "constraint") and any(
        w in blob for w in ("zone", "sone", "jord", "earth", "bond")
    ):
        signals.add("zone")
    if t in ("quantity", "rule", "distinction", "definition", "risk") or any(
        w in blob for w in ("emc", "shield", "skjerm", "attenuat", "dB")
    ):
        signals.add("shield")
    if "class" in blob or "klasse" in blob:
        signals.add("class")
    kind = "measure" if t == "quantity" else ("principle" if t in ("classification", "definition", "distinction") else "fact")
    return Claim(
        text_no=text,
        text_en=text,
        file_id=fc_claim.source or "",
        kind=kind,
        signals=signals or {"shield"},
    )


def _pick_foldok_claims(
    claimset,
    cites: CiteRegistry,
    *,
    purpose: str,
    heading: str,
    retrieve_query: str,
    used_claim_ids: set[str],
    lang: str,
    n: int = 2,
    prefer: set[str] | None = None,
) -> list[Claim]:
    raw = claims_for_section(
        claimset,
        purpose=purpose,
        heading=heading,
        retrieve_query=retrieve_query,
        used_ids=used_claim_ids,
        limit=n + 2,
    )
    out: list[Claim] = []
    for fc in raw:
        local = _foldok_to_local(fc, lang=lang)
        if prefer and not (prefer & local.signals):
            # still allow if type matched purpose via claims_for_section
            pass
        if not cites.claim_fresh(local.text_no):
            continue
        if not cites.unused(local.file_id) and out:
            continue
        used_claim_ids.add(fc.id)
        out.append(local)
        if len(out) >= n:
            break
    return out


def write_framing(
    section: OutlineSection,
    index,
    *,
    narrative: "NarrativePlan | None" = None,
    artifact=None,
    sketch=None,
    cites: CiteRegistry,
    lang: str = "no",
    claimset=None,
    used_claim_ids: set[str] | None = None,
    lead_depth: str = "standard",
) -> SectionDraft:
    """Innledning via Lead Generator (½-page corpus framing + thesis + roadmap)."""
    from .lead import LeadControls, author_lead_section

    depth = lead_depth if lead_depth in ("short", "standard", "rich") else "standard"
    return author_lead_section(
        section, index,
        narrative=narrative, artifact=artifact, sketch=sketch,
        cites=cites, lang=lang,
        controls=LeadControls(lead_depth=depth),  # type: ignore[arg-type]
    )


def section_summary(prose: str, *, max_sents: int = 2) -> str:
    """2–3 sentence previous-section summary for continuity bridges."""
    text = re.sub(r"\s+", " ", (prose or "").strip())
    text = re.sub(r"\*?\(\d+\s+filer[^*]*\*?", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    keep = [p.strip() for p in parts if len(p.strip()) > 20][:max_sents]
    return " ".join(keep)


def bridge_opening(
    *,
    prev_summary: str,
    prev_beat: str,
    next_beat: str,
    next_purpose: str,
    lang: str = "no",
) -> str:
    """Hard continuity input — not hope. Ban findings-voice openers."""
    no = (lang or "no").startswith("no")
    key = (prev_beat or "", next_beat or "")
    canned = {
        ("frame", "context"): (
            "Med tesen lagt, følger begrunnelsen for hvorfor det betyr noe."
            if no else
            "With the thesis in place, the case for why it matters follows."
        ),
        ("frame", "concepts"): (
            "Med tesen lagt, trengs felles begreper før designregler."
            if no else
            "With the thesis stated, shared concepts come before design rules."
        ),
        ("context", "concepts"): (
            "Når begrensningen er klar, trengs felles språk for klasser og soner."
            if no else
            "Once the constraint is clear, shared language for classes and zones is needed."
        ),
        ("concepts", "rules"): (
            "Når begrepene er på plass, følger designimplikasjonene."
            if no else
            "Having established the concepts, the design implications follow."
        ),
        ("concepts", "evidence"): (
            "Samme logikk dukker opp i produkt-EMC-tester og målte påstander."
            if no else
            "The same logic appears in the product EMC tests and measured claims."
        ),
        ("evidence", "rules"): (
            "Fra de målte påstandene følger praktiske designregler."
            if no else
            "From the measured claims follow practical design rules."
        ),
        ("rules", "standards"): (
            "Reglene forankres i navngitte standarder med en rolle i argumentet."
            if no else
            "The rules are anchored in named standards that play a role in the argument."
        ),
        ("standards", "close"): (
            "Mot slutten: hva leseren skal sitte igjen med."
            if no else
            "Toward the close: what the reader should leave with."
        ),
        ("standards", "conclusion"): (
            "Mot slutten: hva leseren skal sitte igjen med."
            if no else
            "Toward the close: what the reader should leave with."
        ),
        ("rules", "close"): (
            "Oppsummert følger anbefalingen av samme tråd."
            if no else
            "In closing, the recommendation follows the same thread."
        ),
        ("rules", "conclusion"): (
            "Oppsummert følger anbefalingen av samme tråd."
            if no else
            "In closing, the recommendation follows the same thread."
        ),
    }
    # Map problem→frame for lookup
    pb = "frame" if prev_beat in ("problem", "frame") else prev_beat
    nb = "close" if next_beat in ("conclusion", "close") else next_beat
    line = canned.get((pb, nb)) or canned.get((prev_beat, next_beat))
    if line:
        return line
    if prev_summary:
        short = prev_summary.split(".")[0].strip()
        if len(short) > 20:
            if no:
                return f"Etter dette — {short[:110].rstrip('.')} — følger neste ledd i argumentet."
            return f"Having established that — {short[:110].rstrip('.')} — the next step in the argument follows."
    if next_purpose and no:
        return "Neste ledd i argumentet bygger direkte på det foregående."
    if next_purpose:
        return "The next step in the argument builds directly on what precedes it."
    return ""


def write_teach(
    section: OutlineSection,
    index,
    *,
    cites: CiteRegistry,
    lang: str = "no",
    author_intent: str = "explain",
    arc_beat: str = "concepts",
    thesis: str = "",
    purpose: str = "",
    claimset=None,
    used_claim_ids: set[str] | None = None,
    previous_summary: str = "",
    previous_beat: str = "",
    next_purpose: str = "",
    main_argument: str = "",
) -> SectionDraft:
    no = (lang or "no").startswith("no")
    purpose = purpose or section.purpose
    optional = getattr(section, "optional", True)
    need = _purpose_needs(purpose, section.heading, section.retrieve_query)
    used = used_claim_ids if used_claim_ids is not None else set()

    hits = retrieve(section.retrieve_query, index, k=10, min_score=0.26)

    # Primary: foldok_claims
    picked: list[Claim] = []
    if claimset is not None and len(claimset) > 0:
        need_types = section_needs_types(purpose, section.heading, section.retrieve_query)
        if need_types and not has_type_coverage(claimset, need_types):
            gap = _fidelity_gap(section.heading, need, no=no) if need else (
                f"MANGLER: «{section.heading}» — ingen treffende claims i korpus"
                if no else
                f"MISSING: “{section.heading}” — no matching claims in corpus"
            )
            return SectionDraft(
                heading=section.heading, purpose=purpose, kind=section.kind,
                gap=gap, prose="", fidelity_ok=False,
                author_intent=author_intent, arc_beat=arc_beat, hits=hits,
            )
        prefer = need or {"class", "zone", "shield"}
        if author_intent == "conclude":
            prefer = {"shield"}
        picked = _pick_foldok_claims(
            claimset, cites,
            purpose=purpose, heading=section.heading,
            retrieve_query=section.retrieve_query,
            used_claim_ids=used, lang=lang, n=2 if author_intent != "conclude" else 1,
            prefer=prefer,
        )
    else:
        claims = extract_claims(hits, limit=10)
        if need and not _claims_satisfy(claims, need):
            gap = _fidelity_gap(section.heading, need, no=no)
            return SectionDraft(
                heading=section.heading, purpose=purpose, kind=section.kind,
                gap=gap, prose="", fidelity_ok=False,
                author_intent=author_intent, arc_beat=arc_beat, hits=hits,
            )
        if not claims and author_intent != "conclude":
            if optional:
                return SectionDraft(
                    heading=section.heading, purpose=purpose, kind=section.kind,
                    omitted=True, author_intent=author_intent, arc_beat=arc_beat,
                )
            return SectionDraft(
                heading=section.heading, purpose=purpose, kind=section.kind,
                gap=("MANGLER: for tynt treffgrunnlag" if no else "MISSING: too thin to ground"),
                fidelity_ok=False, author_intent=author_intent, arc_beat=arc_beat,
            )
        if author_intent == "conclude":
            picked = _pick_claims(claims, cites, n=1, prefer=need or {"shield"})
        else:
            picked = _pick_claims(claims, cites, n=2, prefer=need or {"class", "zone", "shield"})

    bridge = bridge_opening(
        prev_summary=previous_summary,
        prev_beat=previous_beat,
        next_beat=arc_beat,
        next_purpose=next_purpose or purpose,
        lang=lang,
    )

    if author_intent == "conclude":
        prose = _write_conclusion(
            picked, cites, thesis=thesis or main_argument, lang=lang,
            leave_with="",
        )
    elif not picked:
        gap = (
            f"MANGLER: «{section.heading}» — relevante claims er allerede brukt tidligere; "
            f"ingen nye konkrete krav her."
            if no else
            f"MISSING: “{section.heading}” — matching claims already used; no fresh requirements here."
        )
        return SectionDraft(
            heading=section.heading, purpose=purpose, kind=section.kind,
            gap=gap, prose="", fidelity_ok=False,
            author_intent=author_intent, arc_beat=arc_beat, hits=hits,
        )
    elif author_intent == "recommend":
        prose = _write_recommend(section.heading, picked, cites, lang=lang)
    elif author_intent == "argue":
        prose = _write_argue(section.heading, picked, cites, lang=lang)
    else:
        prose = _write_explain(section.heading, picked, cites, lang=lang)

    if bridge and prose and not prose.lower().startswith(bridge[:18].lower()):
        prose = f"{bridge} {prose}"

    prose = validate_prose(prose, hits) or prose
    prose = _strip_banned(prose)
    return SectionDraft(
        heading=section.heading, purpose=purpose, kind=section.kind,
        prose=prose, hits=hits, author_intent=author_intent, arc_beat=arc_beat,
        fidelity_ok=True,
    )


def _fidelity_gap(heading: str, need: set[str], *, no: bool) -> str:
    labels = {
        "class": ("kabelklasser 1–6 / separasjon" if no else "cable classes 1–6 / segregation"),
        "zone": ("soner / jording / bonding" if no else "zones / earthing / bonding"),
        "shield": ("skjerming / demping" if no else "shielding / attenuation"),
    }
    missing = ", ".join(labels[n] for n in need if n in labels)
    if no:
        return (
            f"MANGLER: «{heading}» lovet innhold om {missing}, "
            f"men treffene var produkt-/katalogtekst uten klasse-/sone-språk."
        )
    return (
        f"MISSING: “{heading}” required {missing}, "
        f"but hits were product blurbs without class/zone language."
    )


def _purpose_lead(heading: str, *, no: bool, author_intent: str) -> str:
    h = (heading or "").lower()
    if author_intent == "argue":
        if "emc" in h or "skjerm" in h:
            return (
                "EMC er ikke et tilleggskrav — det er en primær designbegrensning."
                if no else
                "EMC is not an add-on — it is a primary design constraint."
            )
        return (
            "Temaet er ikke periferisk — det styrer designvalg."
            if no else
            "The topic is not peripheral — it drives design choices."
        )
    if author_intent == "recommend":
        return (
            "Fra begrepene følger praktiske designhensyn."
            if no else
            "From the concepts follow practical design considerations."
        )
    if "kabel" in h or "class" in h:
        return (
            "Kabelklasser finnes for å styre separasjon mellom kraft og signal — ikke som produktkatalog."
            if no else
            "Cable classes exist to manage power/signal separation — not as a product catalogue."
        )
    if "sone" in h or "zone" in h or "jord" in h:
        return (
            "Soner og jording begrenser støyveier i anlegget."
            if no else
            "Zones and earthing limit noise paths in the installation."
        )
    return (
        f"{heading} må leses som del av samme argument."
        if no else
        f"{heading} must be read as part of the same argument."
    )


def _write_explain(heading, claims: list[Claim], cites, *, lang) -> str:
    no = lang.startswith("no")
    lead = _purpose_lead(heading, no=no, author_intent="explain")
    if not claims:
        return lead
    parts = [lead]
    c0 = claims[0]
    if no:
        parts.append(f"Konkret: {c0.text_no} {cites.mark(c0.file_id)}.")
    else:
        parts.append(f"Specifically: {c0.text_en} {cites.mark(c0.file_id)}.")
    if len(claims) > 1:
        c1 = claims[1]
        if no:
            parts.append(f"Videre gjelder at {c1.text_no} {cites.mark(c1.file_id)}.")
        else:
            parts.append(f"Further, {c1.text_en} {cites.mark(c1.file_id)}.")
    return " ".join(parts)


def _write_argue(heading, claims: list[Claim], cites, *, lang) -> str:
    no = lang.startswith("no")
    lead = _purpose_lead(heading, no=no, author_intent="argue")
    if not claims:
        return lead
    c0 = claims[0]
    if no:
        body = f"{lead} Når {c0.text_no} {cites.mark(c0.file_id)}, er det ikke et periferikrav."
    else:
        body = f"{lead} When {c0.text_en} {cites.mark(c0.file_id)}, it is not peripheral."
    if len(claims) > 1 and cites.unused(claims[1].file_id):
        c1 = claims[1]
        if no:
            body += f" Det underbygges også av at {c1.text_no} {cites.mark(c1.file_id)}."
        else:
            body += f" It is also supported by {c1.text_en} {cites.mark(c1.file_id)}."
    return body


def _write_recommend(heading, claims: list[Claim], cites, *, lang) -> str:
    no = lang.startswith("no")
    lead = _purpose_lead(heading, no=no, author_intent="recommend")
    if not claims:
        return lead
    c0 = claims[0]
    if no:
        parts = [lead, f"En praktisk retning er at {c0.text_no} {cites.mark(c0.file_id)}."]
    else:
        parts = [lead, f"A practical direction is that {c0.text_en} {cites.mark(c0.file_id)}."]
    if len(claims) > 1 and cites.unused(claims[1].file_id):
        c1 = claims[1]
        if no:
            parts.append(f"Ved detaljering bør man også ta hensyn til at {c1.text_no} {cites.mark(c1.file_id)}.")
        else:
            parts.append(f"In detailing, also account for {c1.text_en} {cites.mark(c1.file_id)}.")
    return " ".join(parts)


def _write_conclusion(
    claims: list[Claim], cites, *, thesis: str, lang: str, leave_with: str = "",
) -> str:
    no = lang.startswith("no")
    parts = []
    if thesis:
        short = thesis.split(".")[0].strip() + "."
        parts.append(short)
    else:
        parts.append("Oppsummert er retningen i underlaget klar." if no else "In summary the direction is clear.")
    fresh = [c for c in claims if cites.unused(c.file_id)]
    if fresh:
        c0 = fresh[0]
        if no:
            parts.append(f"Blant det som er etablert: {c0.text_no} {cites.mark(c0.file_id)}.")
        else:
            parts.append(f"Among what is established: {c0.text_en} {cites.mark(c0.file_id)}.")
    if leave_with:
        parts.append(leave_with if leave_with.endswith(".") else leave_with + ".")
    elif no:
        parts.append(
            "Anbefalingen er å lese klassevalg, soner, installasjon og standarder som én sammenheng "
            "— og å lukke åpne punkter før beslutning."
        )
    else:
        parts.append(
            "The recommendation is to read class selection, zones, installation, and standards "
            "as one argument — and to close open points before deciding."
        )
    return " ".join(parts)


def write_standards(
    section: OutlineSection,
    index,
    *,
    cites: CiteRegistry,
    lang: str = "no",
    claimset=None,
) -> SectionDraft:
    no = (lang or "no").startswith("no")
    hits = retrieve(
        section.retrieve_query or "standard IEC IEEE EN MIL shielding cable",
        index, k=20, min_score=0.18,
    )

    # Prefer claim-based register (what the standard requires, not name windows)
    if claimset is not None and len(claimset) > 0:
        from .claims_bridge import standards_markdown
        prose = standards_markdown(claimset, lang=lang)
        if prose.strip():
            # Register sources for appendix
            from foldok_claims import standards_register
            for entry in standards_register(claimset):
                for src in entry.get("sources") or []:
                    cites.mark(src, body=False)
            return SectionDraft(
                heading=section.heading, purpose=section.purpose, kind="standards",
                prose=prose, hits=hits, author_intent="list", arc_beat="standards",
            )

    def _std_key(sid: str) -> str:
        return re.sub(r"[-\s]+", "", sid.upper())

    entries: dict[str, tuple[str, str, str]] = {}
    for h in hits:
        text = h.text or ""
        if _looks_like_abstract(text) and not STD_ID_RX.search(text):
            continue
        for m in STD_ID_RX.finditer(text):
            sid = re.sub(r"\s+", " ", m.group(1).strip())
            if _STD_DROP.match(sid):
                continue
            key = _std_key(sid)
            if key in entries:
                continue
            role = _role_for_standard(sid, text, no=no)
            if not role or role.startswith("(") or len(role) < 4:
                continue
            if role.endswith(("cov", "the", "and", "for", "with", "of", "i", "a")) and len(role) < 40:
                continue
            if re.search(r"[;,]{2,}|\(\s*;", role):
                continue
            entries[key] = (sid, role, h.file_id)

    if len(entries) < 3:
        for e in _usable(index)[:80]:
            fid = Path(e.get("file") or "").name
            for f in (e.get("facts") or [])[:12]:
                blob = f"{f.get('key') or ''} {f.get('value') or ''}"
                for m in STD_ID_RX.finditer(blob):
                    sid = re.sub(r"\s+", " ", m.group(1).strip())
                    if _STD_DROP.match(sid):
                        continue
                    key = _std_key(sid)
                    if key in entries:
                        continue
                    role = _role_for_standard(sid, blob, no=no)
                    if role:
                        entries[key] = (sid, role, fid)
            if len(entries) >= 12:
                break

    if not entries:
        return SectionDraft(
            heading=section.heading, purpose=section.purpose, kind="standards",
            gap=("MANGLER: ingen rene standardreferanser identifisert"
                 if no else "MISSING: no clean standard references identified"),
            arc_beat="standards", author_intent="list", fidelity_ok=False,
        )

    lines = []
    for sid, role, fid in list(entries.values())[:12]:
        mark = cites.mark(fid, body=False)
        lines.append(f"- **{sid}** — {role} {mark}".rstrip())

    intro = (
        "Disse referansene underbygger argumentet:"
        if no else
        "These references underpin the argument:"
    )
    return SectionDraft(
        heading=section.heading, purpose=section.purpose, kind="standards",
        prose=intro + "\n\n" + "\n".join(lines),
        hits=hits, author_intent="list", arc_beat="standards",
    )


def _role_for_standard(sid: str, context: str, *, no: bool) -> str:
    key = re.sub(r"[-\s]+", "", sid.upper())
    # Longest prefix match in table
    for k, (role_no, role_en) in sorted(_STD_ROLES.items(), key=lambda x: -len(x[0])):
        if key.startswith(k) or k.startswith(key[: max(6, len(k))]):
            return role_no if no else role_en
    ctx = (context or "").lower()
    sid_l = sid.lower()
    if "mil" in sid_l:
        return "skjermingseffektivitet / EMI-test" if no else "shielding effectiveness / EMI test"
    if "ieee" in sid_l and "299" in sid_l:
        return "måling av skjermingseffektivitet" if no else "shielding effectiveness measurement"
    if "50174" in sid_l:
        return "kabling / installasjon (EMC)" if no else "cabling / installation (EMC)"
    if "61537" in sid_l or "nema" in sid_l:
        return "cable tray / kabelstige" if no else "cable tray / ladder systems"
    if "50310" in sid_l:
        return "jording og bonding" if no else "earthing and bonding"
    if "astm" in sid_l:
        return "skjermingstest / materiale" if no else "shielding test / material"
    if "en" in sid_l or "iec" in sid_l:
        if "shield" in ctx or "emc" in ctx or "attenuat" in ctx:
            return "EMC / skjermingskrav" if no else "EMC / shielding requirement"
        return "teknisk krav i underlaget" if no else "technical requirement in sources"
    return "referanse i underlaget" if no else "reference in sources"


def validate_prose(prose: str, hits: list[RetrievalHit]) -> str:
    if not prose:
        return ""
    ground = " ".join(h.text for h in hits).lower()
    # Also allow numbers that appear in our paraphrased claims (200, 1-6, etc.)
    kept = []
    for sent in re.split(r"(?<=[.!?])\s+", prose):
        if CONTACT_RX.search(sent):
            continue
        if BANNED_VOICE_RX.search(sent):
            continue
        body = re.sub(r"\[\d+\]", "", sent)
        nums = NUM_RX.findall(body)
        # Soft: only drop if number looks like a measurement orphan not in ground
        orphan = False
        for n in nums:
            if n in ("1", "2", "3", "4", "5", "6"):  # class numbers ok
                continue
            if n not in ground and len(n) >= 3:
                orphan = True
                break
        if orphan:
            continue
        kept.append(sent)
    return " ".join(kept).strip()


def _strip_banned(prose: str) -> str:
    if not prose:
        return prose
    kept = []
    for sent in re.split(r"(?<=[.!?])\s+", prose):
        if BANNED_VOICE_RX.search(sent):
            continue
        # Drop leftover long English abstract fragments
        if len(sent) > 160 and re.search(r"(?i)\b(comprehensive|documentation on|covers )\b", sent):
            continue
        kept.append(sent)
    return " ".join(kept).strip() or prose


def write_gaps(
    section: OutlineSection,
    drafts: list[SectionDraft],
    *,
    lang: str = "no",
    thesis: str = "",
    coherence=None,
) -> SectionDraft:
    no = (lang or "no").startswith("no")
    lines = []
    for d in drafts:
        if d.gap:
            lines.append(f"- {d.heading}: {d.gap}")
        elif d.omitted and d.kind == "teach":
            lines.append(
                f"- {d.heading}: "
                + ("ingen dekning i treff" if no else "no coverage in retrieval")
            )

    th = (thesis or "").lower()
    body = " ".join((d.prose or "") + (d.gap or "") for d in drafts).lower()
    if any(w in th for w in ("sone", "zone")) and not ZONE_RX.search(body):
        lines.append(
            "- Soner: "
            + ("tesen nevner soner, men brødteksten fikk ikke sone-/jordingstreff."
               if no else
               "thesis mentions zones, but the body lacked zone/earthing hits.")
        )
    concept = " ".join(d.prose for d in drafts if d.arc_beat == "concepts")
    if any(w in th for w in ("klasse", "class")) and not CLASS_RX.search(concept):
        lines.append(
            "- Kabelklasser: "
            + ("tesen lover klassevalg, men seksjonen mangler klasse 1–6 / separasjonsspråk."
               if no else
               "thesis promises class selection, but the section lacks class 1–6 / segregation language.")
        )

    # Coherence findings (what a summary cannot do)
    if coherence is not None:
        lines.extend(coherence_gap_lines(coherence, lang=lang, limit=6))

    if not lines:
        prose = (
            "Ingen kritiske dekningshull i den planlagte fortellingen."
            if no else
            "No critical coverage gaps in the planned narrative."
        )
    else:
        head = ("Punkter som ikke var godt dekket:" if no else "Points not well covered:")
        prose = head + "\n\n" + "\n".join(lines[:14])
    return SectionDraft(
        heading=section.heading, purpose=section.purpose, kind="gaps",
        prose=prose, arc_beat="open", author_intent="list",
    )


def write_appendix(section: OutlineSection, cites: CiteRegistry, *, lang: str = "no") -> SectionDraft:
    no = (lang or "no").startswith("no")
    intro = ("Henvisninger i teksten:" if no else "In-text references:")
    return SectionDraft(
        heading=section.heading, purpose=section.purpose, kind="appendix",
        prose=intro + "\n\n" + "\n".join(cites.appendix_lines(lang=lang)),
        arc_beat="appendix", author_intent="list",
    )


def author_document(
    outline: list[OutlineSection] | None = None,
    index=None,
    *,
    narrative: "NarrativePlan | None" = None,
    artifact=None,
    lang: str = "no",
) -> tuple[list[SectionDraft], CiteRegistry]:
    from .plan import corpus_sketch

    cites = CiteRegistry()
    sketch = (narrative.sketch if narrative else None) or corpus_sketch(index, artifact=artifact)
    thesis = narrative.thesis if narrative else ""
    blueprint = narrative.as_blueprint() if narrative is not None else None
    main_argument = (
        (blueprint.main_argument if blueprint else "")
        or (narrative.intent.main_argument if narrative else "")
        or thesis
    )
    leave_with = blueprint.reader_should_leave_with if blueprint else ""
    drafts: list[SectionDraft] = []
    work = list(narrative.sections if narrative is not None else (outline or []))

    claimset, coherence = corpus_claims(index)
    used_claim_ids: set[str] = set()
    prev_summary = ""
    prev_beat = ""

    def _next_purpose(i: int) -> str:
        for j in range(i + 1, len(work)):
            nxt = work[j]
            kind = getattr(nxt, "kind", None) or getattr(nxt, "kind", "")
            if kind in ("appendix", "gaps"):
                continue
            return getattr(nxt, "purpose", "") or ""
        return ""

    for i, sec in enumerate(work):
        if hasattr(sec, "to_outline"):
            outline_sec = sec.to_outline()
            intent = sec.author_intent
            beat = sec.arc_beat
            purpose = sec.purpose
        else:
            outline_sec = sec
            intent, beat, purpose = "explain", "concepts", sec.purpose
            if sec.kind == "framing":
                intent, beat = "frame", "frame"
            elif sec.kind == "standards":
                intent, beat = "list", "standards"
            elif sec.kind == "gaps":
                intent, beat = "list", "open"
            elif sec.kind == "appendix":
                intent, beat = "list", "appendix"

        next_purp = _next_purpose(i)

        if outline_sec.kind == "framing":
            d = write_framing(
                outline_sec, index, narrative=narrative, artifact=artifact,
                sketch=sketch, cites=cites, lang=lang,
                claimset=claimset, used_claim_ids=used_claim_ids,
            )
            drafts.append(d)
            if d.prose:
                prev_summary = section_summary(d.prose)
                prev_beat = beat or "frame"
        elif outline_sec.kind == "teach":
            d = write_teach(
                outline_sec, index, cites=cites, lang=lang,
                author_intent=intent, arc_beat=beat, thesis=thesis, purpose=purpose,
                claimset=claimset, used_claim_ids=used_claim_ids,
                previous_summary=prev_summary, previous_beat=prev_beat,
                next_purpose=next_purp, main_argument=main_argument,
            )
            # Inject leave-with into conclusion
            if not d.omitted and intent == "conclude" and leave_with and d.prose:
                if leave_with.rstrip(".") not in d.prose:
                    d.prose = d.prose.rstrip() + " " + (
                        leave_with if leave_with.endswith(".") else leave_with + "."
                    )
            if not d.omitted:
                drafts.append(d)
                if d.prose:
                    prev_summary = section_summary(d.prose)
                    prev_beat = beat
        elif outline_sec.kind == "standards":
            d = write_standards(outline_sec, index, cites=cites, lang=lang, claimset=claimset)
            if not d.omitted:
                # Light bridge into standards
                br = bridge_opening(
                    prev_summary=prev_summary, prev_beat=prev_beat,
                    next_beat="standards", next_purpose=purpose, lang=lang,
                )
                if br and d.prose and not d.prose.startswith(br[:12]):
                    d.prose = f"{br}\n\n{d.prose}"
                drafts.append(d)
                if d.prose:
                    prev_summary = section_summary(d.prose)
                    prev_beat = "standards"
        elif outline_sec.kind == "gaps":
            drafts.append(write_gaps(
                outline_sec, drafts, lang=lang, thesis=thesis, coherence=coherence,
            ))
        elif outline_sec.kind == "appendix":
            drafts.append(write_appendix(outline_sec, cites, lang=lang))
        else:
            d = write_teach(
                outline_sec, index, cites=cites, lang=lang,
                author_intent=intent, arc_beat=beat, thesis=thesis, purpose=purpose,
                claimset=claimset, used_claim_ids=used_claim_ids,
                previous_summary=prev_summary, previous_beat=prev_beat,
                next_purpose=next_purp, main_argument=main_argument,
            )
            if not d.omitted:
                drafts.append(d)
                if d.prose:
                    prev_summary = section_summary(d.prose)
                    prev_beat = beat

    return drafts, cites
