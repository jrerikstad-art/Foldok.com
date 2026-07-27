"""WORKORDER_0.23 — Manifest-grounded money + legal claim validators."""
from __future__ import annotations

import re
from typing import Iterable

CURRENCY_AMOUNT = re.compile(
    r"(?:€\s*([\d]+(?:[.,]\d+)?)|([\d]+(?:[.,]\d+)?)\s*€)",
    re.I,
)
# Also catch the right side of €a–b / €a-b ranges
CURRENCY_RANGE_TAIL = re.compile(
    r"€\s*[\d]+(?:[.,]\d+)?\s*[–\-]\s*([\d]+(?:[.,]\d+)?)",
    re.I,
)

HOWEVER_ROLE = re.compile(
    r"\bi can\b.{0,80}?\.\s*however,?\s*my role\b|"
    r"\bjeg kan\b.{0,80}?\.\s*imidlertid\b.{0,40}?\brolle\b",
    re.I | re.S,
)

DEMO_BANNER = (
    "SYNTETISK DEMOMATERIALE — fiktive parter, ingen juridisk virkning"
)


def _parse_amount(raw: str) -> float:
    return float((raw or "").replace(",", "."))


def allowed_money_amounts(caps: dict | None) -> set:
    """Exact euro amounts the agent may state (from pricing + index range)."""
    allowed: set = set()
    pr = (caps or {}).get("pricing") or {}
    idx = pr.get("index_per_file_eur") or [0.001, 0.01]
    for v in idx:
        try:
            allowed.add(round(float(v), 6))
        except (TypeError, ValueError):
            pass
    tiers = pr.get("export_tiers_eur") or {}
    for v in tiers.values():
        try:
            allowed.add(round(float(v), 6))
        except (TypeError, ValueError):
            pass
    # Scale endpoints (must stay within index range)
    sc = (caps or {}).get("scale") or {}
    for k in ("index_cost_eur_per_file_min", "index_cost_eur_per_file_max",
              "typical_doc_eur", "typical_photo_eur"):
        if k in sc:
            try:
                allowed.add(round(float(sc[k]), 6))
            except (TypeError, ValueError):
                pass
    # Compat: also accept per_file_index_cost_eur list
    for v in sc.get("per_file_index_cost_eur") or []:
        try:
            allowed.add(round(float(v), 6))
        except (TypeError, ValueError):
            pass
    return allowed


def extract_currency_amounts(text: str) -> list:
    found = []
    for m in CURRENCY_AMOUNT.finditer(text or ""):
        raw = m.group(1) or m.group(2)
        try:
            found.append(_parse_amount(raw))
        except ValueError:
            continue
    for m in CURRENCY_RANGE_TAIL.finditer(text or ""):
        try:
            found.append(_parse_amount(m.group(1)))
        except ValueError:
            continue
    return found


def validate_money_claims(reply: str, caps: dict | None = None,
                          *, extra_allowed: Iterable[float] | None = None) -> tuple:
    """A2 — every € amount must be a manifest value (or tool-returned extra).

    Returns (ok, reply_or_same, reason|None).
    """
    text = reply or ""
    amounts = extract_currency_amounts(text)
    if not amounts:
        return True, text, None
    allowed = allowed_money_amounts(caps)
    for x in extra_allowed or []:
        try:
            allowed.add(round(float(x), 6))
        except (TypeError, ValueError):
            pass
    bad = []
    for a in amounts:
        # Exact match, or within listed index range endpoints already in set
        rounded = round(a, 6)
        if rounded in allowed:
            continue
        # Tolerate float noise: 0.0010 vs 0.001
        if any(abs(rounded - x) < 1e-9 for x in allowed):
            continue
        bad.append(a)
    if bad:
        return False, text, f"money_not_in_manifest:{bad}"
    return True, text, None


def pricing_reply(caps: dict | None = None, lang: str = "no") -> str:
    """A3 — canonical cost answer from the pricing block."""
    pr = (caps or {}).get("pricing") or {}
    idx = pr.get("index_per_file_eur") or [0.001, 0.01]
    lo, hi = idx[0], idx[-1]
    tiers = pr.get("export_tiers_eur") or {"basic": 9, "standard": 19, "complex": 49}
    b, s, c = tiers.get("basic", 9), tiers.get("standard", 19), tiers.get("complex", 49)
    if lang == "en":
        return (
            f"Free to try. Indexing your files costs cents (€{lo}–{hi} per file). "
            f"You pay per exported document: €{b} / €{s} / €{c} by complexity — "
            f"contract reviews are typically the €{c} tier. "
            f"Re-exports of paid documents are free."
        )
    return (
        f"Gratis å prøve. Indeksering koster øre (€{lo}–{hi} per fil). "
        f"Du betaler per eksportert dokument: €{b} / €{s} / €{c} etter kompleksitet — "
        f"kontraktsgjennomgang er typisk €{c}-nivået. "
        f"Re-eksport av betalte dokumenter er gratis."
    )


def forbidden_legal_hit(text: str, caps: dict | None = None) -> str | None:
    phrases = list((caps or {}).get("forbidden_legal_phrases") or [])
    if not phrases:
        phrases = [
            "evidence handling", "bevishåndtering", "admissible",
            "chain of custody", "beviskjede",
        ]
    low = (text or "").lower()
    for p in phrases:
        if p.lower() in low:
            return p
    # «legal advice» as an offering (not the disclaimer "not legal advice")
    if re.search(r"\b(offers?|provides?|gives?)\s+legal advice\b", low):
        return "legal advice (offering)"
    if re.search(r"\b(tilbyr|gir)\s+juridisk r[åa]d\b", low):
        return "gi juridisk råd (tilbud)"
    return None


def validate_legal_phrasing(reply: str, caps: dict | None = None) -> tuple:
    """B1/B4 — forbidden legal phrases + however-role shape."""
    text = reply or ""
    hit = forbidden_legal_hit(text, caps)
    if hit:
        return False, text, f"forbidden_legal:{hit}"
    if HOWEVER_ROLE.search(text):
        return False, text, "however_role_shape"
    return True, text, None


def legal_prospect_reply(caps: dict | None = None, lang: str = "no") -> dict:
    """B2 — lawyer/large-case cold start: framing + contract_review, ≤2 questions."""
    framing = ((caps or {}).get("legal_framing") or {}).get(lang) or ""
    if not framing:
        framing = ((caps or {}).get("legal_framing") or {}).get("en") or ""
    by_key = {t.get("key"): t for t in (caps or {}).get("templates") or []}
    cr = by_key.get("contract_review") or {}
    name = (cr.get("name") if lang == "en" else cr.get("name_no")) or "contract_review"
    if lang == "en":
        reply = (
            f"{framing} For a large case, **{name}** (`contract_review`) is the fit — "
            f"obligations and deadlines with clause citations. "
            f"Want a marked synthetic demo first, or shall I open a project folder?"
        )
    else:
        reply = (
            f"{framing} For en stor sak passer **{name}** (`contract_review`) — "
            f"forpliktelser og frister med klausulsitater. "
            f"Vil du ha en merket syntetisk demosak først, eller skal jeg åpne en prosjektmappe?"
        )
    return {
        "reply": reply,
        "kind": "legal_prospect",
        "lang": lang,
        "template_key": "contract_review",
        "actions": [
            {"id": "create_demo", "label": "Lag demosak" if lang == "no" else "Create demo case",
             "kind": "contract"},
        ],
    }


def demo_offer_reply(lang: str = "no", *, kind: str = "contract") -> dict:
    """C3 — draft boundary + offer marked demo (not unmarked contract text)."""
    if lang == "en":
        reply = (
            "I don't draft contracts — but I can spin up a marked demo case so you "
            "can see the extraction before using your real files."
        )
        label = "Create demo case"
    else:
        reply = (
            "Jeg utformer ikke juridisk tekst — men jeg kan spinne opp en merket "
            "demosak så du ser ekstraksjonen før du bruker egne filer."
        )
        label = "Lag demosak"
    return {
        "reply": reply,
        "kind": "demo_offer",
        "lang": lang,
        "execute": None,  # wait for button / confirm unless start intent
        "set_pending": {"action": "create_demo", "kind": kind},
        "actions": [{"id": "create_demo", "label": label, "kind": kind}],
        "template_key": "contract_review" if kind == "contract" else "technical_doc_package",
    }


def money_fallback(caps: dict | None, lang: str = "no") -> str:
    return pricing_reply(caps, lang)


def legal_fallback(caps: dict | None, lang: str = "no") -> str:
    return legal_prospect_reply(caps, lang).get("reply") or ""
