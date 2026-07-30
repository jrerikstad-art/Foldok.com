"""WORKORDER_0.22 — Agent truthfulness: perception, receipts, source immutability."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

CONF_OK = 0.80

PART_KEYS = (
    "part_no", "part_number", "model", "model_no", "sku", "mpn",
    "manufacturer_part", "component_id", "type_no", "article_no",
)

COMPLETION_VERBS = re.compile(
    r"\b(oppdatert|oppdaterte|lagt\s+(til|inn|i)|markert|opprettet|satt|generert|lagret|"
    r"skrevet|endre[td]|fylt\s+inn|registrert|"
    r"updated|added|created|saved|marked|generated|wrote|modified)\b",
    re.I,
)

# WORKORDER_0.25 C + 0.22 B — progress/start claims need a job-start receipt
# in the same turn. Phrases: starter, kjører, skriver nå, klar om.
# Capability prose («Indeksering kjører med…») and conditional offers
# («si ifra så starter jeg») are stripped before the check.
PROGRESS_VERBS = re.compile(
    r"(?:"
    r"\bjeg\s+(starter|kj[øo]rer|analyserer|genererer|indekserer)\b|"
    r"\b(starter|kj[øo]rer)\b|"
    r"\b(jeg\s+)?skriver\s+n[åa]\b|"
    r"\b(i('m|\s+am)\s+)?(starting|running|writing\s+now|analysing|analyzing|generating)\b|"
    r"\bklar\s+om\b|\bom\s+noen\s+minutter\b|\bstarter\s+straks\b|"
    r"\bready\s+in\b|\bin\s+a\s+few\s+minutes\b"
    r")",
    re.I,
)

CAPABILITY_OR_CONDITIONAL = re.compile(
    r"(?:"
    r"(indeksering|indexing)\s+(kj[øo]rer|runs)\b|"
    r"kj[øo]rer\s+bedre\s+som\b|"
    r"(så|then)\s+starter\s+(jeg|i)\b|"
    r"si\s+ifra\s+så\s+starter\b|"
    r"når\s+du\s+.{0,40}\s+starter\b"
    r")",
    re.I,
)

# Claims that touch forbidden write targets (templates / user sources)
FORBIDDEN_WRITE_CLAIMS = re.compile(
    r"(templates[/\\][\w.-]+\.json|"
    r"TECHNICAL_SPEC|PRE_HARDWARE_CHECKLIST|"
    r"oppdatert\s+(malen|templaten|template)|"
    r"updated\s+the\s+template|"
    r"skrevet\s+til\s+(din|kilde)|"
    r"modified\s+your\s+(source|file))",
    re.I,
)

TRIAGE_QUESTIONS = re.compile(
    r"hvilke\s+bilder|which\s+photos|prioriter|prioritiz|hvilket\s+format|"
    r"which\s+format|what\s+format",
    re.I,
)

# WORKORDER_0.26 A — artifacts belong in documents, never in chat replies
MARKUP_DUMP = re.compile(r"<\s*(svg|html|table)\b", re.I)
MD_TABLE_SEP = re.compile(r"(?m)^\s*\|?\s*:?-{3,}")
MD_TABLE_ROW = re.compile(r"(?m)^\s*\|.+\|\s*$")
FENCED_CODE = re.compile(r"```")
NUMBERED_ITEM = re.compile(r"(?m)^\s*\d+[\.\)]\s+\S+")
CODE_ASK = re.compile(
    r"\b(vis\s+meg\s+(python|kode|kommando)|hvilken\s+kommando|"
    r"show\s+me\s+(the\s+)?(code|python|command)|paste\s+the\s+code)\b",
    re.I,
)
PROSE_DUMP_MARK = re.compile(
    r"her\s+er\s+(din|seksjonen|dokumentet|utkastet)|"
    r"here\s+is\s+(your|the)\s+(section|document|draft)|"
    r"^#{1,3}\s+\S+",
    re.I | re.M,
)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def validate_chat_artifacts(reply: str, *, user_msg: str = "",
                            lang: str = "no",
                            enforce_prose_cap: bool = True) -> tuple:
    """0.26 §A — reject SVG/HTML/tables/long lists/code dumps in chat.

    Returns (ok, reply_or_fallback, reason|None).
    """
    text = reply or ""
    if MARKUP_DUMP.search(text):
        return False, honest_fallback(lang), "artifact_markup_in_chat"
    if MD_TABLE_SEP.search(text) or (
        len(MD_TABLE_ROW.findall(text)) >= 2 and "|" in text
    ):
        return False, honest_fallback(lang), "markdown_table_in_chat"
    if FENCED_CODE.search(text) and not CODE_ASK.search(user_msg or ""):
        return False, honest_fallback(lang), "fenced_code_in_chat"
    if len(NUMBERED_ITEM.findall(text)) > 5:
        return False, honest_fallback(lang), "intake_list_too_long"
    if enforce_prose_cap and word_count(text) > 120 and PROSE_DUMP_MARK.search(text):
        return False, honest_fallback(lang), "document_prose_dump"
    return True, text, None


def checklist_created_reply(path: str, *, n_items: int = 0,
                            lang: str = "no") -> str:
    """0.26 §C/E25 — reference the file; never paste the list."""
    name = Path(path).name if path else "SJEKKLISTE.txt"
    if lang == "en":
        return (
            f"Wrote **{name}** in the project folder"
            + (f" ({n_items} items from the template)." if n_items else ".")
            + " Open the file in the folder — I won't paste the list here."
        )
    return (
        f"Skrev **{name}** i prosjektmappen"
        + (f" ({n_items} punkter fra malen)." if n_items else ".")
        + " Åpne filen i mappen — jeg limer ikke inn listen her."
    )


def honest_fallback(lang: str = "no") -> str:
    if lang == "en":
        return (
            "I couldn't finish that as claimed — here is what I CAN do: draw a "
            "wiring / interconnection diagram into the document (tell me what "
            "connects to what), quote «Indexed as: …» from the index, add a BOM "
            "row with an image reference after a confirmed part ID, or scan "
            "Bilder/ for components (~€). I don't have tools that silently rewrite "
            "source files or templates."
        )
    return (
        "Jeg fikk ikke fullført det slik det ble sagt — her er hva jeg KAN gjøre: "
        "tegne koblingsskjema inn i dokumentet (si hva som kobles til hva), "
        "sitere «Indeksert som: …» fra indeksen, legge en BOM-rad med "
        "bildereferanse etter bekreftet del-ID, eller skanne Bilder/ for "
        "komponenter (~€). Jeg har ikke verktøy som stille omskriver kilder eller maler."
    )


def tools_receipt_ids(tools_run: list | None) -> set:
    out = set()
    for t in tools_run or []:
        if not isinstance(t, dict):
            continue
        if t.get("ok") is False:
            continue
        name = t.get("tool") or t.get("id") or ""
        if name:
            out.add(name)
    return out


def has_progress_claim(text: str) -> bool:
    """True when the reply asserts work is starting/running (needs job receipt)."""
    if not text or not PROGRESS_VERBS.search(text):
        return False
    cleaned = CAPABILITY_OR_CONDITIONAL.sub(" ", text)
    return bool(PROGRESS_VERBS.search(cleaned))


def job_start_receipt(tools_run: list | None) -> bool:
    """0.25 C1 — progress claims need a real job id in the same turn."""
    for t in tools_run or []:
        if not isinstance(t, dict) or t.get("ok") is False:
            continue
        if t.get("job_id") or t.get("job"):
            return True
    return False


def validate_completion_claims(reply: str, tools_run: list | None = None,
                               *, lang: str = "no") -> tuple:
    """WORKORDER_0.22 B2 + 0.25 C — completion/progress verbs require tool receipts.

    Progress language (starter / kjører / skriver nå / klar om) requires a
    job-start receipt with job_id in the same turn — else the reply is rejected.

    Returns (ok: bool, reply_or_fallback: str, reason: str|None).
    """
    text = reply or ""
    receipts = tools_receipt_ids(tools_run)
    progress = has_progress_claim(text)

    if FORBIDDEN_WRITE_CLAIMS.search(text):
        return False, honest_fallback(lang), "forbidden_write_claim"

    if TRIAGE_QUESTIONS.search(text):
        return False, honest_fallback(lang), "triage_question_forbidden"

    needs_receipt = bool(COMPLETION_VERBS.search(text) or progress)
    if not needs_receipt:
        return True, text, None

    if progress:
        if not job_start_receipt(tools_run):
            reason = ("progress_without_job" if receipts
                      else "progress_without_receipt")
            return False, honest_fallback(lang), reason
        return True, text, None

    if not receipts:
        return False, honest_fallback(lang), "completion_without_receipt"

    return True, text, None


def is_checklist_ask(msg: str) -> bool:
    return bool(re.search(
        r"\b(sjekkliste|checklist|lag\s+en\s+sjekkliste|"
        r"hva\s+jeg\s+trenger|what\s+i\s+need)\b",
        msg or "", re.I,
    ))


def part_facts_from_entry(entry: dict | None) -> list:
    """Identifier-like facts that could be a part number (from index only)."""
    out = []
    for f in (entry or {}).get("facts") or []:
        key = (f.get("key") or "").lower()
        ft = (f.get("fact_type") or "").lower()
        if key in PART_KEYS or (ft in ("identifier", "spec") and key in PART_KEYS):
            out.append(f)
        elif key in PART_KEYS or (
            ft == "identifier" and re.search(r"part|model|sku|mpn|article", key)
        ):
            out.append(f)
    # Also accept identifier facts with part-like values if key is generic
    for f in (entry or {}).get("facts") or []:
        if f in out:
            continue
        key = (f.get("key") or "").lower()
        val = str(f.get("value") or "")
        if key in PART_KEYS:
            out.append(f)
        elif (f.get("fact_type") == "identifier"
              and re.match(r"^[A-Za-z]{1,8}[\w./-]{2,30}$", val)
              and any(c.isdigit() for c in val)):
            # Cautious: only if looks like a PN and key suggests it
            if re.search(r"part|model|sku|type|article|mpn", key):
                out.append(f)
    return out


def known_part_values(entry: dict | None) -> set:
    vals = set()
    for f in part_facts_from_entry(entry):
        v = str(f.get("value") or "").strip()
        if v:
            vals.add(v.lower())
            vals.add(re.sub(r"\s+", "", v.lower()))
    return vals


def extract_asserted_part_numbers(reply: str) -> list:
    """Heuristic: token patterns that look like manufacturer part numbers."""
    found = []
    for m in re.finditer(
        r"\b([A-Z]{1,6}\d{1,4}[A-Z]{0,4}\d{0,4}[A-Z]?\d{0,2})\b",
        reply or "",
    ):
        tok = m.group(1)
        if len(tok) >= 5:
            found.append(tok)
    return found


def validate_perception(reply: str, entries: list | None = None,
                        *, lang: str = "no") -> tuple:
    """A1/A2 — no part numbers asserted that are absent from extractions."""
    text = reply or ""
    known = set()
    for e in entries or []:
        known |= known_part_values(e)
    # Also allow values explicitly marked as hypothesis questions
    if re.search(r"\ber det\b.+\?|\bis it\b.+\?", text, re.I):
        # Hypothesis form — strip the questioned token from hard fails
        pass
    asserted = extract_asserted_part_numbers(text)
    # If reply quotes Indeksert som / Indexed as, still block PNs not in facts
    bad = []
    for pn in asserted:
        if pn.lower() not in known and re.sub(r"\s+", "", pn.lower()) not in known:
            # Allow if only appears inside a question hypothesising from BOM
            window = _window_around(text, pn, 40)
            if re.search(r"\ber det\b|\bis it\b|fra BOM|from the BOM|bekrefte",
                         window, re.I):
                continue
            bad.append(pn)
    if bad and not known:
        # Invented ID with no extraction support
        return False, _perception_fallback(lang), "invented_part_no"
    if bad:
        return False, _perception_fallback(lang), f"part_no_not_in_index:{','.join(bad)}"
    return True, text, None


def _window_around(text: str, needle: str, radius: int) -> str:
    i = (text or "").find(needle)
    if i < 0:
        return text or ""
    return text[max(0, i - radius): i + len(needle) + radius]


def _perception_fallback(lang: str) -> str:
    if lang == "en":
        return (
            "I can only describe what the index extracted. "
            "Indeksert caption and facts are the source — I won't invent a part number."
        )
    return (
        "Jeg kan bare beskrive det indeksen har trukket ut. "
        "«Indeksert som: …» og fakta derfra er kilden — jeg finner ikke på delnummer."
    )


def format_indexed_as(entry: dict | None, lang: str = "no") -> str:
    cap = ((entry or {}).get("caption") or Path((entry or {}).get("file") or "").name
           or "(uten bildetekst)")
    if lang == "en":
        return f"Indexed as: {cap}"
    return f"Indeksert som: {cap}"


def ground_photo_reply(entry: dict | None, *, bom_hypotheses: list | None = None,
                       lang: str = "no") -> dict:
    """A1–A3 grounded photo reply — no free-form vision. Returns reply + optional execute."""
    entry = entry or {}
    cap_line = format_indexed_as(entry, lang)
    parts = part_facts_from_entry(entry)
    best = None
    if parts:
        best = max(parts, key=lambda f: float(f.get("confidence") or 0))
    conf = float((best or {}).get("confidence") or 0)
    val = str((best or {}).get("value") or "").strip()

    if best and conf >= CONF_OK and val:
        if lang == "en":
            reply = (f"{cap_line}. Readable ID: **{val}** "
                     f"(conf {int(conf*100)}%). Adding BOM row with image reference.")
        else:
            reply = (f"{cap_line}. Lesbar ID: **{val}** "
                     f"(konf. {int(conf*100)} %). Legger BOM-rad med bildereferanse.")
        return {
            "reply": reply,
            "execute": {
                "tool": "add_bom_component",
                "part_no": val,
                "file": entry.get("file"),
                "caption": entry.get("caption"),
                "confidence": conf,
                "fact_id": best.get("id"),
                "status": "ok",
            },
            "kind": "ground_photo",
        }

    if best and val and conf < CONF_OK:
        if lang == "en":
            reply = (f"{cap_line}. Uncertain reading ({int(conf*100)}%): **{val}** — confirm?")
        else:
            reply = (f"{cap_line}. Usikker lesning ({int(conf*100)} %): **{val}** — bekreft?")
        return {
            "reply": reply,
            "kind": "ground_photo_uncertain",
            "set_pending": {
                "action": "confirm_part",
                "part_no": val,
                "file": entry.get("file"),
                "caption": entry.get("caption"),
                "confidence": conf,
                "fact_id": best.get("id"),
            },
            "actions": [
                {"id": "confirm_part_yes", "label": "Ja, bekreft" if lang == "no" else "Yes, confirm"},
                {"id": "confirm_part_no", "label": "Nei" if lang == "no" else "No"},
            ],
        }

    # No legible ID — hypothesis only
    hypo = (bom_hypotheses or [None])[0]
    if lang == "en":
        reply = f"{cap_line}. Cannot confirm model from the photo."
        if hypo:
            reply += f" Looks like a power component — is it {hypo} from the BOM?"
        else:
            reply += " No part number in the extraction."
    else:
        reply = f"{cap_line}. Kan ikke bekrefte modell fra bildet."
        if hypo:
            reply += f" Ligner en buck-konverter — er det {hypo} fra BOM-en?"
        else:
            reply += " Ingen delnummer i ekstraksjonen."
    out = {"reply": reply, "kind": "ground_photo_no_id"}
    if hypo:
        out["set_pending"] = {
            "action": "confirm_part",
            "part_no": hypo,
            "file": entry.get("file"),
            "caption": entry.get("caption"),
            "confidence": 0.0,
            "hypothesis": True,
        }
        out["actions"] = [
            {"id": "confirm_part_yes", "label": "Ja, bekreft" if lang == "no" else "Yes, confirm"},
            {"id": "confirm_part_no", "label": "Nei" if lang == "no" else "No"},
        ]
    return out


def photo_entries(index: list | None) -> list:
    PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".tif", ".tiff", ".bmp"}
    out = []
    for e in index or []:
        if e.get("kind") == "skipped":
            continue
        rel = e.get("file") or ""
        if e.get("kind") == "photo" or Path(rel).suffix.lower() in PHOTO_EXT:
            out.append(e)
    return out


def needs_component_scan(entry: dict) -> bool:
    if entry.get("component_scanned"):
        return False
    return not bool(part_facts_from_entry(entry))


def scan_offer_reply(index: list | None, *, eur_per_photo: float = 0.008,
                     lang: str = "no",
                     index_lo: float = 0.001, index_hi: float = 0.01) -> dict:
    """WORKORDER_0.22 D — bulk offer; € quotes manifest index range (0.23 A2)."""
    photos = photo_entries(index)
    pending = [e for e in photos if needs_component_scan(e)]
    n_all, n_pend = len(photos), len(pending)
    cost = round(n_pend * eur_per_photo, 2)
    lo, hi = index_lo, index_hi
    if lang == "en":
        if n_pend == 0:
            reply = (f"{n_all} photos in the project — all already have component "
                     f"extractions. I can refresh the BOM from indexed facts.")
            return {"reply": reply, "kind": "scan_offer", "pending": 0,
                    "execute": {"tool": "refresh_bom_from_components"}}
        reply = (f"{n_all} photos — {n_pend} not component-scanned yet. "
                 f"Scan all for part IDs and specs: ~€{lo}–{hi} per file × {n_pend}.")
    else:
        if n_pend == 0:
            reply = (f"{n_all} bilder i prosjektet — alle har allerede "
                     f"komponent-ekstraksjon. Jeg kan oppdatere BOM fra indeksen.")
            return {"reply": reply, "kind": "scan_offer", "pending": 0,
                    "execute": {"tool": "refresh_bom_from_components"}}
        reply = (f"{n_all} bilder — {n_pend} er ikke komponent-skannet ennå. "
                 f"Skanner alle for del-ID og spesifikasjoner: ~€{lo}–{hi} per fil × {n_pend}.")
    return {
        "reply": reply,
        "kind": "scan_offer",
        "pending": n_pend,
        "estimate_eur": cost,
        "set_pending": {"action": "scan_components", "count": n_pend, "estimate_eur": cost},
        "actions": [{"id": "scan_components", "label": "Skann" if lang == "no" else "Scan"}],
        "offer_scan": True,
    }


def scan_complete_reply(results: dict, lang: str = "no") -> str:
    ok = results.get("ok", 0)
    uncertain = results.get("uncertain", 0)
    no_id = results.get("no_id", 0)
    if lang == "en":
        return (f"Found {ok} components with readable ID (added to BOM with image ref), "
                f"{uncertain} uncertain (⚠ marked — confirm), {no_id} without ID.")
    return (f"Fant {ok} komponenter med lesbar ID (lagt i BOM med bildereferanse), "
            f"{uncertain} usikre (⚠ merket — bekreft), {no_id} uten ID.")


def is_scan_bom_intent(msg: str) -> bool:
    q = (msg or "").lower()
    return bool(re.search(
        r"legg.*bom|bom.*bild|scanne?.*komponent|komponent.*scan|"
        r"se p[åa] komponent|scan.*photos?|photos?.*bom|"
        r"bilder.*bom|bom.*bilder",
        q, re.I,
    ))


def is_photo_mark_intent(msg: str) -> bool:
    q = (msg or "").lower()
    return bool(re.search(
        r"scanne?\s+denn|merke?\s+den|i dokumentasjonen|"
        r"scan\s+this|mark\s+(it|this)|identify\s+(this|the)\s+(photo|image|part)",
        q, re.I,
    ))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def templates_hashes(templates_dir: Path) -> dict:
    out = {}
    for p in sorted(Path(templates_dir).glob("*.json")):
        out[p.name] = file_sha256(p)
    return out


def additive_dest(path: Path) -> Path:
    """Never overwrite an existing source — WO 0.22 C1."""
    if not path.exists():
        return path
    stem, suf = path.stem, path.suffix
    n = 2
    while True:
        cand = path.with_name(f"{stem}_{n}{suf}")
        if not cand.exists():
            return cand
        n += 1


def assert_not_template_write(path: Path, engine_root: Path) -> None:
    """Raise if a write would touch templates/*.json."""
    try:
        rel = path.resolve().relative_to(Path(engine_root).resolve())
    except ValueError:
        return
    parts = rel.parts
    if parts and parts[0] == "templates" and path.suffix.lower() == ".json":
        raise PermissionError("WO 0.22 C2: tools cannot modify templates/*.json")
