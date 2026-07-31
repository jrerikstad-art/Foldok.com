"""Lead Generator — first beat of the narrative arc (Innledning).

Dedicated retrieve → ground → author run for corpus framing + thesis + roadmap.
Higher word budget than a normal section; hard ban on abstract-paste and
file-count-as-story.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .model import RetrievalHit
from .plan import CorpusSketch, OutlineSection, corpus_sketch
from .retrieve import index_to_chunks, retrieve

LeadDepth = Literal["short", "standard", "rich"]

WORD_BUDGET = {
    "short": (90, 140),
    "standard": (150, 280),
    "rich": (240, 380),
}

# Filename / heading → material character (themes, not a file list)
_DOC_TYPE_HINTS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"(?i)\b(mil[-\s]?std|ieee\s*299|astm\s*e?\d|shielding\s*effect)\b"),
     "produkt-EMC-tester", "product EMC tests"),
    (re.compile(r"(?i)\b(york\s*emc|attenuation|shield(?:ing)?)\b"),
     "skjermingsmålinger", "shielding measurements"),
    (re.compile(r"(?i)\b(en\s*50174|bs\s*en\s*50174|iec\s*61537|en\s*61537|nek\s*702)\b"),
     "installasjons- og tray-standarder", "installation and tray standards"),
    (re.compile(r"(?i)\b(bod|board\s*of\s*decision|hypothes)\b"),
     "plattform-/beslutningsnotater", "platform / decision notes"),
    (re.compile(r"(?i)\b(cable\s*tray|wire\s*tray|stige|wibe|chalfant|marco|beama)\b"),
     "kabelforingsprodukter og veiledninger", "cable-management products and guides"),
    (re.compile(r"(?i)\b(emc|electromagnetic|faraday|emi)\b"),
     "EMC-praksis", "EMC practice"),
    (re.compile(r"(?i)\b(install|handling|storage|maintenance|guide)\b"),
     "installasjonsveiledninger", "installation guides"),
]

_OVERVIEW_QUERY = (
    "overview purpose scope introduction abstract executive summary "
    "EMC requirements electromagnetic compatibility cable tray shielding "
    "problem installation bonding segregation why"
)

_OVERVIEW_SIGNAL = re.compile(
    r"(?i)\b(overview|purpose|scope|introduction|abstract|executive|"
    r"requirement|emc|electromagnetic|compatibility|shield(?:ing)?|"
    r"cable\s*(?:tray|class)|installat|bonding|segregat|zone|"
    r"problem|design\s*constraint|faraday)\b"
)
_SKU_NOISE = re.compile(
    r"(?i)\b(sku|part\s*no|article\s*no|bestillingsnr|catalog\s*number|"
    r"order\s*code|ean\b|gtin)\b"
)
_ABSTRACT_PASTE = re.compile(
    r"(?i)\b(comprehensive technical (documentation|handbook|presentation)|"
    r"this (document|guide|presentation) (provides|covers)|"
    r"independently verified by|"
    r"covers (emc|safety|mandatory)\b)"
)
_EN_WORDY = re.compile(
    r"\b(the|and|with|from|that|this|shall|must|required|attenuation|"
    r"shielding|installation|standard|tested|measured)\b",
    re.I,
)
_NUM_CLAIM = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:dB|mm|cm|m|kHz|MHz|GHz|V/m|%)\b",
    re.I,
)


@dataclass
class LeadControls:
    lead_depth: LeadDepth = "standard"
    max_claims: int = 12
    prefer_paraphrase: bool = True
    allow_thesis: bool = True


@dataclass
class LeadGround:
    """Short grounded span for the lead — never a full PDF abstract."""
    text: str
    file_id: str
    kind: str = "span"  # span | claim | theme
    score: float = 0.0


@dataclass
class LeadResult:
    prose: str
    hits: list[RetrievalHit] = field(default_factory=list)
    grounds: list[LeadGround] = field(default_factory=list)
    thin_overview: bool = False
    word_count: int = 0
    depth: LeadDepth = "standard"

    def to_dict(self) -> dict:
        return {
            "prose": self.prose,
            "word_count": self.word_count,
            "thin_overview": self.thin_overview,
            "depth": self.depth,
            "grounds": [
                {"text": g.text[:120], "file_id": g.file_id, "kind": g.kind}
                for g in self.grounds
            ],
        }


def corpus_character(sketch: CorpusSketch, index=None, *, lang: str = "no") -> list[str]:
    """Themes of what the pile *is* — product tests, standards, guides — not filenames."""
    no = (lang or "no").startswith("no")
    blob_parts = [
        " ".join(sketch.themes),
        " ".join(sketch.sample_captions[:12]),
        sketch.theme_blob,
    ]
    for e in (index or [])[:80]:
        blob_parts.append(Path(e.get("file") or "").name)
        blob_parts.append(e.get("caption") or "")
    blob = " ".join(blob_parts)
    seen: set[str] = set()
    out: list[str] = []
    for rx, label_no, label_en in _DOC_TYPE_HINTS:
        if rx.search(blob):
            label = label_no if no else label_en
            if label not in seen:
                seen.add(label)
                out.append(label)
    if not out and sketch.themes:
        out = list(sketch.themes[:3])
    return out[:5]


def _overview_score(chunk: dict) -> float:
    text = chunk.get("text") or ""
    fname = (chunk.get("file_id") or "").lower()
    kind = chunk.get("kind") or ""
    if _SKU_NOISE.search(text) or _SKU_NOISE.search(fname):
        return 0.0
    if _ABSTRACT_PASTE.search(text) and len(text) > 160:
        return 0.05
    score = 0.0
    if _OVERVIEW_SIGNAL.search(text):
        score += 0.35
    if _OVERVIEW_SIGNAL.search(fname):
        score += 0.20
    if kind in ("caption", "detail"):
        score += 0.12
    if kind == "claim":
        score += 0.18
        if chunk.get("claim_binding"):
            score += 0.06
    if re.search(r"(?i)\b(bod|summary|exec|intro|overview|hypothesis)\b", fname):
        score += 0.15
    if 40 <= len(text) <= 220:
        score += 0.08
    elif len(text) > 400:
        score -= 0.10
    return score


def retrieve_overview(
    index,
    sketch: CorpusSketch,
    *,
    k: int = 14,
    intent_query: str = "",
) -> list[RetrievalHit]:
    """Retrieve passages that describe the collection / problem space."""
    q = f"{sketch.title} {' '.join(sketch.themes[:4])} {_OVERVIEW_QUERY}"
    if intent_query:
        q = f"{intent_query} {q}"
    hits = retrieve(q, index, k=max(k * 2, 16), min_score=0.16)
    if not hits:
        chunks = index_to_chunks(index)
        scored = []
        for ch in chunks:
            s = _overview_score(ch)
            if s >= 0.25:
                scored.append((s, ch))
        scored.sort(key=lambda x: -x[0])
        out = []
        seen: set[str] = set()
        for s, ch in scored[:k]:
            fid = ch.get("file_id") or ""
            if fid in seen:
                continue
            seen.add(fid)
            out.append(RetrievalHit(
                file_id=fid,
                text=ch.get("text") or "",
                score=s,
                pages=ch.get("pages") or "",
                chunk_id=ch.get("chunk_id") or "",
            ))
        return out

    enriched = []
    for h in hits:
        bonus = _overview_score({
            "text": h.text,
            "file_id": h.file_id,
            "kind": getattr(h, "kind", "") or "caption",
        })
        enriched.append((h.score * 0.55 + bonus, h))
    enriched.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for score, h in enriched:
        if h.file_id in seen:
            continue
        seen.add(h.file_id)
        h.score = score
        out.append(h)
        if len(out) >= k:
            break
    return out


def _shorten_span(text: str, *, max_len: int = 140) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if _ABSTRACT_PASTE.search(t):
        return ""
    if re.match(r"(?i)^[a-z0-9_ ]{3,40}:\s+\S", t):
        t = t.split(":", 1)[1].strip()
    if len(t) > max_len:
        cut = t[: max_len - 1]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        t = cut.rstrip(".,;:") + "…"
    return t


def _paraphrase_for_lead(text: str, *, lang: str, prefer_paraphrase: bool) -> str:
    """English blurbs → short paraphrase; never paste abstracts."""
    t = _shorten_span(text, max_len=130)
    if not t:
        return ""
    no = (lang or "no").startswith("no")
    if not prefer_paraphrase or not no:
        return t[0].lower() + t[1:] if t and t[0].isupper() and not t[:3].isupper() else t
    t2 = t
    t2 = re.sub(r"(?i)\bshall be used\b", "skal brukes", t2)
    t2 = re.sub(r"(?i)\bshall\b", "skal", t2)
    t2 = re.sub(r"(?i)\bmust\b", "må", t2)
    t2 = re.sub(r"(?i)\bis required\b", "er påkrevd", t2)
    t2 = re.sub(r"(?i)\bshielded cable\b", "skjermet kabel", t2)
    t2 = re.sub(r"(?i)\bshielding\b", "skjerming", t2)
    t2 = re.sub(r"(?i)\battenuation\b", "demping", t2)
    t2 = re.sub(r"(?i)\bcable tray\b", "kabelbane", t2)
    t2 = re.sub(r"(?i)\binstallation\b", "installasjon", t2)
    t2 = re.sub(r"(?i)\bzone transitions\b", "soneskiller", t2)
    en_hits = len(_EN_WORDY.findall(t2))
    if en_hits >= 5 and len(t2) > 80:
        m = re.search(
            r"(?i)(.{0,40}(skjerm|shield|demping|attenuat|klasse|class|sone|zone|"
            r"bonding|jord|50174|emc).{0,60})",
            t2,
        )
        if m:
            t2 = m.group(1).strip(" .,;")
        else:
            return ""
    # Lead embeds as "at {span}" — prefer sentence-case continuation
    if t2 and t2[0].isupper() and not t2[:4].isupper():
        t2 = t2[0].lower() + t2[1:]
    return t2.strip()


def ground_lead(
    hits: list[RetrievalHit],
    *,
    max_claims: int = 12,
    lang: str = "no",
    prefer_paraphrase: bool = True,
) -> list[LeadGround]:
    grounds: list[LeadGround] = []
    seen_text: set[str] = set()
    for h in hits:
        span = _paraphrase_for_lead(h.text, lang=lang, prefer_paraphrase=prefer_paraphrase)
        if not span or len(span) < 24:
            continue
        key = span[:60].lower()
        if key in seen_text:
            continue
        if _NUM_CLAIM.search(span) and not re.search(
            r"(?i)(dB|mm|skjerm|attenuat|demping|klasse|class|50174|mil)", span
        ):
            continue
        seen_text.add(key)
        grounds.append(LeadGround(
            text=span, file_id=h.file_id, kind="span", score=h.score,
        ))
        if len(grounds) >= max_claims:
            break
    return grounds


def _join_character(chars: list[str], *, no: bool) -> str:
    if not chars:
        return "fagkilder" if no else "technical sources"
    if len(chars) == 1:
        return chars[0]
    if len(chars) == 2:
        return f"{chars[0]} og {chars[1]}" if no else f"{chars[0]} and {chars[1]}"
    conj = "og" if no else "and"
    return f"{', '.join(chars[:-1])} {conj} {chars[-1]}"


def _roadmap_line(section_headings: list[str], *, no: bool) -> str:
    body = [
        h for h in section_headings
        if h and h.lower() not in (
            "innledning", "introduction", "kilder", "sources",
            "åpne punkter", "open points", "appendix",
        )
    ]
    body = body[:4]
    if not body:
        return (
            "Notatet utvikler deretter begreper, regler og standardlandskapet."
            if no else
            "The note then develops concepts, rules, and the standards landscape."
        )
    if no:
        listed = ", ".join(body[:-1]) + (f" og {body[-1]}" if len(body) > 1 else body[0])
        return f"Dette notatet rammer den tråden, og utvikler deretter {listed}."
    listed = ", ".join(body[:-1]) + (f", and {body[-1]}" if len(body) > 1 else body[0])
    return f"This note frames that thread, then develops {listed}."


def _limits_line(sketch: CorpusSketch, grounds: list[LeadGround], *, no: bool, thin: bool) -> str:
    blob = (sketch.theme_blob or "").lower()
    has_test_pdf = bool(re.search(r"(?i)mil[-\s]?std|york|attenuation|test", blob))
    has_method = bool(re.search(r"(?i)\b(method|methodology|test\s*plan|lab\s*report)\b", blob))
    if thin:
        return (
            "Overblikket i kildene er tynt — innledningen bygger derfor mest på "
            "filnavn/temaer, ikke på rike sammendrag."
            if no else
            "Overview text in the sources is thin — this lead therefore rests mainly on "
            "filename themes, not rich summaries."
        )
    if has_test_pdf and not has_method:
        return (
            "Prosjekteide testmetoder og primære datatabeller finnes ikke i indeksen og står åpne."
            if no else
            "Project-owned test methods and primary data tables are not present in the index "
            "and remain open."
        )
    if len(grounds) < 2:
        return (
            "Underlaget støtter en arbeidstese bare delvis — enkelte punkter forblir åpne."
            if no else
            "The material only partly supports a working thesis — some points remain open."
        )
    return (
        "Notatet er en kildeorientert fagpakke, ikke en fullført laboratoriekampanje."
        if no else
        "This note is a source-oriented technical package, not a completed laboratory campaign."
    )


def _context_opener(sketch: CorpusSketch, chars: list[str], *, no: bool) -> str:
    title = sketch.title or ("Prosjektet" if no else "The project")
    themes = sketch.themes[:3]
    char_s = _join_character(chars, no=no)
    if any(t in (sketch.theme_blob or "") for t in ("emc", "shield", "cable", "tray", "hvdc")):
        if no:
            return (
                f"Offshore- og industrirelaterte miljøer med tett kabelføring og kraftelektronikk "
                f"setter uvanlig press på elektromagnetisk kompatibilitet: kraftelektronikk, "
                f"tett routing og sensitiv styring deler ofte de samme konstruksjonene. "
                f"Materialet rundt {title} er et **kildebibliotek** om {char_s} — "
                f"ikke en ferdig laboratoriekampanje."
            )
        return (
            f"Offshore and industrial environments with dense routing and power electronics "
            f"put unusual pressure on electromagnetic compatibility: power electronics, "
            f"dense routing, and sensitive control often share the same structures. "
            f"The material around {title} is a **source library** on {char_s} — "
            f"not a completed laboratory campaign."
        )
    theme_s = ", ".join(themes) if themes else title
    if no:
        return (
            f"Materialet i {title} samler kilder om {theme_s}, med vekt på {char_s}. "
            f"Målet er å orientere leseren før detaljene — ikke å late som om alt er verifisert."
        )
    return (
        f"The {title} material gathers sources on {theme_s}, emphasising {char_s}. "
        f"The aim is to orient the reader before the details — not to pretend everything is verified."
    )


def write_lead_prose(
    *,
    sketch: CorpusSketch,
    thesis: str,
    grounds: list[LeadGround],
    cites,
    section_headings: list[str],
    lang: str = "no",
    controls: LeadControls | None = None,
    index=None,
    thin_overview: bool = False,
    allow_thesis: bool = True,
) -> str:
    controls = controls or LeadControls()
    no = (lang or "no").startswith("no")
    chars = corpus_character(sketch, index, lang=lang)
    paras: list[str] = []

    paras.append(_context_opener(sketch, chars, no=no))

    supports = [g for g in grounds if g.file_id][:3]
    thesis_ok = allow_thesis and bool((thesis or "").strip()) and (
        len(supports) >= 2 or (controls.lead_depth == "short" and len(supports) >= 1)
    )
    if thesis_ok:
        t = thesis.strip().rstrip(".")
        if no:
            body = [
                f"På tvers av kildene går en gjennomgående tråd: **{t}**."
            ]
            if supports:
                g0 = supports[0]
                body.append(
                    f"Et konkret underlag er at {g0.text} {cites.mark(g0.file_id)}."
                )
                if len(supports) > 1 and cites.unused(supports[1].file_id):
                    g1 = supports[1]
                    body.append(
                        f"Samme lesning understøttes av at {g1.text} {cites.mark(g1.file_id)}."
                    )
            paras.append(" ".join(body))
        else:
            body = [
                f"Across those sources a consistent thread appears: **{t}**."
            ]
            if supports:
                g0 = supports[0]
                body.append(
                    f"Concrete support includes that {g0.text} {cites.mark(g0.file_id)}."
                )
                if len(supports) > 1 and cites.unused(supports[1].file_id):
                    g1 = supports[1]
                    body.append(
                        f"The same reading is supported by {g1.text} {cites.mark(g1.file_id)}."
                    )
            paras.append(" ".join(body))
    elif supports:
        g0 = supports[0]
        if no:
            paras.append(
                f"Et konkret underlag i materialet er at {g0.text} {cites.mark(g0.file_id)}. "
                f"En samlet tese holdes foreløpig tilbake til dekning er tydeligere."
            )
        else:
            paras.append(
                f"Concrete support in the material includes that {g0.text} {cites.mark(g0.file_id)}. "
                f"A firm thesis is withheld until coverage is clearer."
            )

    if controls.lead_depth != "short":
        paras.append(_roadmap_line(section_headings, no=no))

    lim = _limits_line(sketch, grounds, no=no, thin=thin_overview)
    if controls.lead_depth == "short" and paras:
        paras.append(lim)
    else:
        paras.append(f"**{lim}**")

    if no:
        foot = f"*({sketch.file_count} filer indeksert.)*"
    else:
        foot = f"*({sketch.file_count} files indexed.)*"

    prose = "\n\n".join(p.strip() for p in paras if p and p.strip())
    prose = _verify_lead(prose)
    return prose + "\n\n" + foot


def _verify_lead(prose: str) -> str:
    """No abstract paste; strip banned voice per paragraph; keep paragraph breaks."""
    from .author_doc import BANNED_VOICE_RX

    kept_paras = []
    for para in (prose or "").split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if _ABSTRACT_PASTE.search(para) and len(para) > 200:
            continue
        kept_sents = []
        for sent in re.split(r"(?<=[.!?])\s+", para):
            if BANNED_VOICE_RX.search(sent):
                continue
            if len(sent) > 160 and re.search(
                r"(?i)\b(comprehensive|documentation on|covers )\b", sent
            ):
                continue
            kept_sents.append(sent)
        if kept_sents:
            kept_paras.append(" ".join(kept_sents))
    out = "\n\n".join(kept_paras).strip() or (prose or "").strip()
    first = (out.split("\n")[0] if out else "").strip()
    if re.match(r"(?i)^.{0,40}\d+\s+(indekserte\s+)?filer", first):
        parts = out.split("\n\n")
        out = "\n\n".join(parts[1:]) if len(parts) > 1 else out
    return out.strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def generate_lead(
    index,
    *,
    sketch: CorpusSketch | None = None,
    artifact=None,
    thesis: str = "",
    intent=None,
    section_headings: list[str] | None = None,
    cites=None,
    lang: str = "no",
    controls: LeadControls | None = None,
) -> LeadResult:
    """Full Lead Generator pipeline for Innledning / executive framing."""
    from .author_doc import CiteRegistry

    controls = controls or LeadControls()
    sk = sketch or corpus_sketch(index, artifact=artifact)
    cites = cites or CiteRegistry()
    intent_q = ""
    if intent is not None:
        intent_q = " ".join(filter(None, [
            getattr(intent, "main_question", "") or "",
            getattr(intent, "desired_outcome", "") or "",
            getattr(intent, "purpose", "") or "",
        ]))

    hits = retrieve_overview(index, sk, k=14, intent_query=intent_q)
    thin = len(hits) < 3
    grounds = ground_lead(
        hits,
        max_claims=controls.max_claims,
        lang=lang,
        prefer_paraphrase=controls.prefer_paraphrase,
    )
    allow = controls.allow_thesis and (len(grounds) >= 2 or not thin)
    headings = section_headings or []
    prose = write_lead_prose(
        sketch=sk,
        thesis=thesis,
        grounds=grounds,
        cites=cites,
        section_headings=headings,
        lang=lang,
        controls=controls,
        index=index,
        thin_overview=thin,
        allow_thesis=allow,
    )
    wc = _word_count(prose)
    lo, hi = WORD_BUDGET[controls.lead_depth]
    if controls.lead_depth == "short" and wc > hi:
        paras = [p for p in prose.split("\n\n") if p.strip()]
        keep = paras[:2]
        if paras and paras[-1].startswith("*("):
            keep.append(paras[-1])
        prose = "\n\n".join(keep)
        wc = _word_count(prose)

    return LeadResult(
        prose=prose.strip(),
        hits=hits,
        grounds=grounds,
        thin_overview=thin,
        word_count=wc,
        depth=controls.lead_depth,
    )


def author_lead_section(
    section: OutlineSection,
    index,
    *,
    narrative=None,
    artifact=None,
    sketch=None,
    cites,
    lang: str = "no",
    controls: LeadControls | None = None,
):
    """Author entrypoint — replaces thin write_framing for framing sections."""
    from .author_doc import SectionDraft

    sk = (
        (narrative.sketch if narrative else None)
        or sketch
        or corpus_sketch(index, artifact=artifact)
    )
    thesis = (narrative.thesis if narrative else "") or ""
    headings = []
    if narrative is not None:
        headings = [s.heading for s in narrative.sections]
    intent = narrative.intent if narrative else None
    result = generate_lead(
        index,
        sketch=sk,
        artifact=artifact,
        thesis=thesis,
        intent=intent,
        section_headings=headings,
        cites=cites,
        lang=lang,
        controls=controls,
    )
    return SectionDraft(
        heading=section.heading,
        purpose=section.purpose,
        kind="framing",
        prose=result.prose,
        hits=result.hits,
        author_intent="frame",
        arc_beat="problem",
    )
