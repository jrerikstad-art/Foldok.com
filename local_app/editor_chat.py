"""ONE_AGENT_SPEC — editor intent routing (code-first, tools)."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Norwegian / informal synonyms → canonical gap keys
GAP_SYNONYMS = {
    "reg_no": [
        "registreringsnummer", "registrerings nummer", "regnr", "reg nr",
        "kjennemerke", "skiltnummer", "reg.nr", "reg no", "registrering",
    ],
    "vin": ["vin", "chassisnummer", "understellsnummer", "chassis"],
    "model_year": ["årsmodell", "arsmodell", "model year", "årgang", "argang"],
    "mileage": ["kilometerstand", "km-stand", "km stand", "mileage", "kilometer"],
    "owner": ["eier", "owner", "bileier"],
    "oil_type": ["oljetype", "olje type", "motorolje", "oil type", "0w-20", "5w-30"],
    "make": ["merke", "make", "fabrikat"],
    "model": ["modell", "model"],
    "serial_no": ["serienummer", "serie nr", "serial"],
    "address": ["adresse", "address"],
    "kommune": ["kommune"],
    "gnr_bnr": ["gnr", "bnr", "gnr/bnr", "gårdsnummer"],
}

# ONE_AGENT_SPEC §7 / WORKORDER_0.20 A2–A4 / 0.21 length+act
CHAT_AGENT_POLICY = """
VOICE (HARD): Warm but professional. Mirror the USER'S LANGUAGE (NO/EN).
No emoji. No exclamatory openers ("Kult!", "Supert!", "Flott!", "Nice!").
Write like a competent field engineer, not a chatbot.

LENGTH (HARD — WORKORDER_0.21):
- Default ≤120 words. Hard ceiling 200 unless user asks for list/overview/forklar.
- No markdown headings (##). Bold only the document name or one key term.
- Max ONE short list, ≤5 items (rest: «…og N til»).
- Shape: [what I did / what fits] → [one next step or € offer] → [≤1 question].
- No restating the user. No closing pleasantries.
- Banned closers when intent was explicit: «Klar til å starte?», «Skal vi gjøre det?»,
  «Si fra når du er klar».

ACT, DON'T DESCRIBE: Never tell the user to do what a tool can do
(create folder, drag files, pick template, set cover). EXECUTE then report.

PERCEPTION (HARD — WORKORDER_0.22): You have no eyes. Every image claim
must quote the index: «Indeksert som: <caption>». Never invent visual
details (housing colour, DIN-rail, dimensions) not in the extraction.
Part numbers only from extraction facts; otherwise offer a BOM hypothesis
as a question. Confidence <0.80 → say «usikker» explicitly.

CONNECTION DIAGRAMS (WORKORDER_0.24/0.26): Free-text schematic/wiring asks
trigger propose_connection_spec → confirm rows (plain text) → create_diagram
→ SVG in the DOCUMENT. Never paste <svg> or markdown tables into chat.
Mirror USER LANGUAGE.

ARTIFACTS IN DOCUMENTS (WORKORDER_0.26): Chat only REFERENCES tool
results (≤3 lines). Never dump SVG, HTML, code fences, or long intake
lists into the reply. Checklists → write_checklist → SJEKKLISTE.txt.

ACTION TRUTH (HARD): Never claim you updated/wrote/saved a file unless a
tool in THIS turn returned success. Never claim to modify templates/*.json
or the user's source .md/.txt files — those tools do not exist.

CONTEXT RULE (HARD): «Aldri spør om noe som finnes i konteksten eller kan
slås opp i indeksen. Søk først (0 tokens), spør etterpå.»

OPEN-ENDED ASKS — HARD:
1. Ground FIRST: name THIS project and what is in it.
2. Search before asking (ALREADY KNOWN / FACT KEY INVENTORY).
3. At most TWO questions, only for things sources cannot contain.
4. End with concrete document offer including €.

FORBIDDEN: "eller er det noe helt nytt"; "klar for innlevering"; feature menus;
emoji; "Kult!"; permission-seeking for free actions; instructing the user to
create folders or drag files; free-form vision; narrating fictional file writes.
""".strip()

# Message intent → keys to search zero-token before the model asks
INTENT_SEARCH_KEYS = [
    (r"phd|ph\.?d|forskning|research|thesis|avhandling|imitation\s*learning",
     ["institution", "university", "method", "hardware", "platform", "model",
      "supervisor", "research_field", "thesis_title", "author_name", "author",
      "framework", "dataset", "sensor", "controller"]),
    (r"samsvar|elektro|el-anlegg",
     ["voltage", "installation_type", "contractor", "standard_ref"]),
    (r"våtrom|bad|membran",
     ["floor_area", "room_type", "property_address"]),
    (r"bil|kjøretøy|rav4|service|vedlikehold",
     ["make", "model", "model_year", "vin", "reg_no", "mileage", "oil_type"]),
]

TAG_PHRASE_NO = {
    "code": "kode", "python": "kode", "script": "kode", "firmware": "kode",
    "log": "logger", "logs": "logger", "telemetry": "logger",
    "hardware": "hardware-notater", "pcb": "hardware-notater",
    "raspberry": "hardware-notater", "pi": "hardware-notater",
    "schematic": "skjemaer", "wiring": "koblingsskjema",
    "drawing": "tegninger", "photo": "bilder", "nameplate": "merkeskilt",
    "manual": "manualer", "spec": "spesifikasjoner", "datasheet": "datablad",
    "notebook": "notater", "readme": "notater",
}

EXT_PHRASE_NO = {
    ".py": "kode", ".js": "kode", ".ts": "kode", ".cpp": "kode", ".c": "kode",
    ".h": "kode", ".ipynb": "kode", ".rs": "kode", ".go": "kode",
    ".log": "logger", ".csv": "logger", ".json": "logger",
    ".md": "notater", ".txt": "notater",
    ".pdf": "dokumenter", ".docx": "dokumenter",
    ".jpg": "bilder", ".jpeg": "bilder", ".png": "bilder", ".webp": "bilder",
    ".sch": "hardware-notater", ".brd": "hardware-notater",
}

FORBIDDEN_REPLY = re.compile(
    r"eller er det noe helt nytt|kult\s*!|supert\s*!|flott\s*!|"
    r"klar for innlevering|skal vi gj[øo]re det\s*\?|"
    r"klar til [åa] starte\s*\?|si fra n[åa]r du er klar|"
    r"lag en ny mappe|dra inn (alle )?fil|"
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF]",
    re.I,
)

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".tif", ".tiff", ".bmp"}

IMPERATIVE_RE = re.compile(
    r"\b(bruk|sett|legg(\s+til)?|fjern|endre|oppdater|lag|generer|put|set|use|add|remove|update)\b",
    re.I,
)
COVER_RE = re.compile(
    r"\b(forsiden?|cover(\s*page)?|frontpage|front\s*page|title\s*page)\b",
    re.I,
)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def _iso():
    return datetime.now(timezone.utc).isoformat()


def append_turn(state, role, text, *, html=None, meta=None, project_id=None):
    """Append a chat turn. project_id stamps the turn (BUGFIX_0.19 §A extended)."""
    conv = state.setdefault("conversation", [])
    entry = {"role": role, "text": text or "", "t": _iso()}
    if html:
        entry["html"] = html
    if meta:
        entry["meta"] = meta
    # Isolation: every turn belongs to exactly one project
    pid = project_id or state.get("project_id")
    if pid:
        entry["project_id"] = pid
        state["project_id"] = pid
    conv.append(entry)
    # keep last 200 turns
    if len(conv) > 200:
        del conv[:-200]
    return entry


def conversation_for_project(state, project_id: str | None) -> list:
    """BUGFIX_0.19 §A extended — return only turns for this project_id.

    Turns without project_id are kept only when state.project_id matches
    (legacy states written before the stamp). Foreign project_id turns
    are never returned.
    """
    conv = (state or {}).get("conversation") or []
    if not project_id:
        return list(conv)
    own_state = (state or {}).get("project_id")
    out = []
    for t in conv:
        tid = t.get("project_id")
        if tid and tid != project_id:
            continue
        if not tid and own_state and own_state != project_id:
            continue
        out.append(t)
    return out


def corpus_brief(index, file_count: int) -> str:
    """Zero-token: '109 filer med kode, logger og hardware-notater'."""
    phrases = Counter()
    for e in index or []:
        if e.get("kind") == "skipped":
            continue
        blob = " ".join(
            list(e.get("content_tags") or []) + list(e.get("doc_role_hints") or [])
        ).lower()
        for tag, phrase in TAG_PHRASE_NO.items():
            if tag in blob:
                phrases[phrase] += 1
        ext = Path(e.get("file") or "").suffix.lower()
        if ext in EXT_PHRASE_NO:
            phrases[EXT_PHRASE_NO[ext]] += 1
        kind = e.get("kind")
        if kind == "photo":
            phrases["bilder"] += 1
        elif kind == "doc" and not phrases:
            phrases["dokumenter"] += 1
    # Prefer distinctive phrases by frequency
    top = [p for p, _ in phrases.most_common(4)]
    if not top:
        top = ["prosjektfiler"]
    if len(top) == 1:
        joined = top[0]
    elif len(top) == 2:
        joined = f"{top[0]} og {top[1]}"
    else:
        joined = f"{', '.join(top[:-1])} og {top[-1]}"
    n = file_count if file_count is not None else sum(
        1 for e in (index or []) if e.get("kind") != "skipped")
    return f"{n} filer med {joined}"


def keys_to_search_for_message(message: str) -> list:
    q = _fold(message)
    keys, seen = [], set()
    for pat, ks in INTENT_SEARCH_KEYS:
        if re.search(pat, q, re.I):
            for k in ks:
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
    # Always useful grounding keys when present
    for k in ("project_title", "product_name", "model", "make", "hardware", "platform"):
        if k not in seen:
            seen.add(k)
            keys.append(k)
    return keys[:16]


def known_from_index(message: str, index, artifact=None, search_fn=None) -> str:
    """Zero-token: state values already in the index for obvious keys."""
    lines = []
    art = artifact or {}
    if art.get("name"):
        lines.append(f"- artifact.name = {art['name']}")
    if art.get("purpose"):
        lines.append(f"- artifact.purpose = {str(art['purpose'])[:200]}")
    if art.get("confidence") is not None:
        lines.append(f"- artifact.confidence = {art['confidence']}")
    comps = art.get("main_components") or []
    if comps:
        names = ", ".join((c.get("name") if isinstance(c, dict) else str(c)) for c in comps[:6])
        lines.append(f"- artifact.main_components = {names}")

    keys = keys_to_search_for_message(message)
    found = {}
    if search_fn:
        for k in keys:
            for c in (search_fn(index, k) or [])[:1]:
                found[k] = c
    else:
        # inline match without importing compile
        by_key = {}
        for e in index or []:
            for f in e.get("facts") or []:
                fk = f.get("key")
                if fk and fk not in by_key:
                    by_key[fk] = (f, e.get("file"))
        for k in keys:
            hit = by_key.get(k)
            if hit:
                f, src = hit
                found[k] = {"key": k, "value": f.get("value"), "unit": f.get("unit"),
                            "file": src}

    for k, c in found.items():
        unit = c.get("unit") or ""
        val = c.get("value")
        src = c.get("file") or c.get("source") or ""
        lines.append(f"- {k} = {val}{(' ' + unit) if unit else ''} (fra {src})" if src
                     else f"- {k} = {val}{(' ' + unit) if unit else ''}")

    if not lines:
        return "(ingen treff i indeks for åpenbare nøkler)"
    return "\n".join(lines)


def is_open_ended_create(message: str) -> bool:
    q = _fold(message)
    return bool(re.search(
        r"\b(vil\s+lage|lag\s+(et|en|et)\s+|lage\s+(et|en)\s+|trenger\s+(et|en)\s+|"
        r"phd|forskningsprosjekt|dokumentasjon|prosjektplan|rapport)\b",
        q,
    ))


def scrub_chat_voice(text: str) -> str:
    """Strip emoji, banned closers, and soft-ban unserious openers."""
    if not text:
        return text
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+", "", text)
    text = re.sub(r"^(Kult|Supert|Flott|Nice|Awesome)\s*!+\s*", "", text, flags=re.I)
    text = re.sub(r"klar for innlevering", "klar for gjennomgang", text, flags=re.I)
    text = re.sub(
        r"klar til [åa] starte\s*\?|skal vi gj[øo]re det\s*\?|si fra n[åa]r du er klar",
        "", text, flags=re.I)
    text = re.sub(r"(?m)^#{1,6}\s+.*$", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    # Soft length cap (hard ceiling 200) — WO 0.21 B
    words = re.findall(r"\S+", text)
    if len(words) > 200:
        text = " ".join(words[:200]).rstrip(" ,;:")
    return text


def format_gaps_reply(gaps: list, scope=None, *, max_items: int = 5) -> str:
    """WORKORDER_0.21 C9 — ≤5 items, remainder as «…og N til»."""
    scoped = [g for g in (gaps or []) if not scope or g.get("section") == scope]
    if not scoped:
        return "✓ Ingen mangler i dette dokumentet."
    lines = [
        f"• **{g.get('section')}** · {g.get('label') or g.get('key')} (`{g.get('key')}`)"
        for g in scoped[:max_items]
    ]
    head = "Åpne mangler" + (f" i {scope}" if scope else "") + f" ({len(scoped)}):\n"
    body = "\n".join(lines)
    if len(scoped) > max_items:
        body += f"\n…og {len(scoped) - max_items} til."
    return head + body


def reply_violates_policy(text: str) -> bool:
    return bool(FORBIDDEN_REPLY.search(text or ""))


def count_questions(text: str) -> int:
    return (text or "").count("?")


def open_ended_grounded_reply(*, project_name: str, brief: str, artifact: dict | None,
                              known_block: str, estimate_eur: float = 0.22,
                              lang: str = "no") -> str:
    """WORKORDER_0.20 A — deterministic ground-first reply (no model required)."""
    art = artifact or {}
    name = art.get("name") or project_name or "prosjektet"
    purpose = (art.get("purpose") or "").strip()
    conf = art.get("confidence")
    conf_bit = ""
    if conf is not None:
        try:
            conf_bit = f" ({int(round(float(conf) * 100))} % bekreftet modell)" if lang == "no" \
                else f" ({int(round(float(conf) * 100))} % confirmed model)"
        except (TypeError, ValueError):
            conf_bit = ""
    # Pull a few known lines (already formatted)
    known_lines = []
    for line in (known_block or "").splitlines():
        line = line.strip()
        if line.startswith("- ") and "artifact." not in line:
            known_lines.append(line[2:])
        if len(known_lines) >= 4:
            break
    known_bit = ""
    if known_lines:
        if lang == "en":
            known_bit = " Already in the index: " + "; ".join(known_lines[:3]) + "."
        else:
            known_bit = " Allerede i indeksen: " + "; ".join(known_lines[:3]) + "."

    if lang == "en":
        head = f"Based on **{name}**{conf_bit}: {brief}."
        if purpose:
            head += f" Purpose on file: {purpose[:180]}."
        head += known_bit
        qs = ("Which institution should this be aimed at, and is this an "
              "RC-scale study or the full machine?")
        offer = (
            f"I can assemble a research project report from what is already here "
            f"(~€{estimate_eur:.2f}) — say the word and I start that document."
        )
        return f"{head}\n\n{qs}\n\n{offer}"

    head = f"Basert på **{name}**{conf_bit}: {brief}."
    if purpose:
        head += f" Formål i modellen: {purpose[:180]}."
    head += known_bit
    qs = ("Hvilken institusjon skal dette sikte mot, og er det RC-skala "
          "eller full maskin?")
    offer = (
        f"Jeg kan sette sammen en forskningsprosjektrapport fra det som allerede "
        f"ligger her (~€{estimate_eur:.2f}) — si ifra så starter jeg dokumentet."
    )
    return f"{head}\n\n{qs}\n\n{offer}"


def is_cover_imperative(message: str) -> bool:
    q = message or ""
    if not COVER_RE.search(q):
        return False
    # "bruk/sett … på forsiden" or English equivalents
    if IMPERATIVE_RE.search(q) or re.search(r"\bp[åa]\s+forsiden\b", q, re.I):
        return True
    if re.search(r"\b(as|on)\s+(the\s+)?cover\b", q, re.I):
        return True
    return False


def cover_section_key(template: dict | None) -> str | None:
    if not template:
        return None
    keys = {s["section_key"] for s in template.get("sections") or []}
    for sk in ("cover", "front_matter", "title", "identification", "summary"):
        if sk in keys:
            return sk
    secs = sorted(template.get("sections") or [], key=lambda x: x.get("position", 99))
    return secs[0]["section_key"] if secs else None


def pick_cover_image(state: dict, index: list | None, message: str = "") -> tuple:
    """Return (rel_path, caption) for 'dette bildet' — prefer last indexed media."""
    last = (state or {}).get("last_indexed_media") or {}
    if last.get("file"):
        return last["file"], last.get("caption") or Path(last["file"]).name
    # Named file in the utterance?
    q = message or ""
    photos = []
    for e in index or []:
        rel = e.get("file") or ""
        ext = Path(rel).suffix.lower()
        if e.get("kind") == "photo" or ext in PHOTO_EXT:
            photos.append(e)
            if rel and Path(rel).name.lower() in q.lower():
                return rel, e.get("caption") or Path(rel).name
    if len(photos) == 1:
        e = photos[0]
        return e.get("file"), e.get("caption") or Path(e.get("file") or "").name
    if photos:
        e = photos[-1]
        return e.get("file"), e.get("caption") or Path(e.get("file") or "").name
    return None, None


def format_cover_reply(*, doc_name: str, caption: str, rel: str,
                       other_docs: list | None = None, lang: str = "no") -> str:
    """B3/B4 — report what was done; optional one follow-up; cite index caption."""
    cap = (caption or Path(rel).name).strip()
    if lang == "en":
        text = (
            f"Set as cover on **{doc_name}** ✓ — Indexed as: {cap}. "
            f"Generating the PDF with this image on the cover."
        )
        if other_docs:
            text += f" Want it on {other_docs[0]} as well?"
        return text
    text = (
        f"Satt som forside på **{doc_name}** ✓ — Indeksert som: {cap}. "
        f"Genererer PDF med bildet på forsiden."
    )
    if other_docs:
        text += f" Vil du ha den på {other_docs[0]} også?"
    return text


def match_gap_from_text(text: str, gaps: list) -> list:
    """Return matching gap dicts for user utterance (fuzzy, code-only)."""
    q = _fold(text)
    if not q or not gaps:
        return []
    hits = []
    for g in gaps:
        key = (g.get("key") or "").lower()
        label = _fold(g.get("label") or "")
        score = 0
        if key and (key in q or key.replace("_", " ") in q):
            score += 5
        if label and label in q:
            score += 4
        for syn in GAP_SYNONYMS.get(key, []):
            if _fold(syn) in q:
                score += 6
                break
        # partial label tokens
        for tok in label.split():
            if len(tok) > 4 and tok in q:
                score += 2
        if score >= 4:
            hits.append((score, g))
    hits.sort(key=lambda x: -x[0])
    # unique by key
    seen, out = set(), []
    for _, g in hits:
        k = g.get("key")
        if k in seen:
            continue
        seen.add(k)
        out.append(g)
    return out


def looks_like_value(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) > 80:
        return False
    if re.search(r"\b(mangler|hva|hvordan|skriv|finn|hent|regener)\b", t, re.I):
        return False
    # plate-like / short identifiers / numbers
    if re.match(r"^[A-ZÆØÅ]{1,3}\s*\d{2,5}$", t, re.I):
        return True
    if re.match(r"^[\w.\-/]{2,40}$", t) and " " not in t.strip():
        return True
    if len(t.split()) <= 4 and not t.endswith("?"):
        return True
    return False


RECREATE_FORM_RE = re.compile(
    r"(?:"
    r"gjenskap|recreate|gjenopprett|"
    r"lag\s+(dette\s+)?(skjema|formen)|"
    r"make\s+(this\s+)?(form|template)|"
    r"bygg\s+(skjemaet|formen)|"
    r"(skjema|form).{0,40}(som\s+mal|as\s+(?:a\s+)?template)|"
    r"multipoint"
    r")",
    re.I,
)


def is_recreate_form_ask(text: str) -> bool:
    """«recreate this form» / gjenskap skjema — template + document, never .txt."""
    t = text or ""
    if re.search(r"sjekkliste\.txt|checklist\.txt|write_checklist", t, re.I):
        return False
    return bool(RECREATE_FORM_RE.search(t))


def dispatch_pending_action(pending: dict) -> dict | None:
    """WORKORDER_0.25 B2 — turn chat_pending into an execute plan."""
    if not pending or not isinstance(pending, dict):
        return None
    action = pending.get("action") or pending.get("tool")
    if not action:
        return None
    # Normalize hub-style {tool, args} and editor-style {action, ...}
    args = dict(pending.get("args") or {})
    for k in ("template_key", "template", "draft", "token", "file", "source",
              "part_no", "caption", "confidence", "fact_id", "status",
              "verified_by_user", "key", "value", "unit", "section",
              "confirm", "source_ids", "mode", "since_version", "document_id"):
        if pending.get(k) is not None and k not in args:
            args[k] = pending[k]

    tool = action
    if action == "run_generate":
        tool = "run_generate"
    elif action == "reindex":
        tool = "reindex"
        args["confirm"] = True
    elif action == "diff_index":
        tool = "diff_index"
    elif action == "update_document_from_sources":
        tool = "update_document_from_sources"
    elif action == "confirm_location_map":
        # Affirmative → report receipt; UI/doc insert is confirm path
        tool = "confirm_location_map"
        args["proposal"] = pending.get("proposal")
    elif action == "accept_drafted_template":
        tool = "accept_drafted_template"
    elif action == "save_as_template":
        tool = "save_as_template"
    elif action == "recreate_form":
        tool = "recreate_form"
    elif action == "create_document":
        tool = "create_document"
    elif action == "import_form":
        tool = "propose_form_template"
    elif action == "scan_components":
        tool = "scan_components_run"
    elif action == "confirm_part":
        tool = "add_bom_component"
    elif action == "confirm_connection_spec":
        return None  # handled by connection_diagram parser
    elif action == "accept_reference":
        return None  # handled earlier in server
    elif action == "resolve_mangler":
        return None  # needs a value, not bare ja
    elif action == "write_checklist":
        # Affirmative after a mistaken .txt offer — redirect to form recreate
        # when the pending was about a form; else write checklist.
        if pending.get("form") or pending.get("redirect_form"):
            tool = "recreate_form"
        else:
            tool = "write_checklist"

    execute = {"tool": tool, **args}
    return {
        "execute": execute,
        "kind": "dispatch_pending",
        "clear_pending": True,
    }


def explicitly_names_document(text: str, caps: dict | None = None) -> bool:
    """WORKORDER 0.56 §C5 — true when user clearly names a doc/template to create."""
    t = text or ""
    lower = _fold(t)
    # Verb + named type (compound nouns count: installasjonsveiledning, etc.)
    if re.search(
        r"\b(opprett|lag|create|new|generer|kj[øo]r|start)\b.{0,48}"
        r"\b(dokument|document|rapport|manual|mal|template|"
        r"samsvarserkl\w*|kontrakt\w*|datasheet|datablad|"
        r"brukermanual|user\s*manual|installasjons\w*|vedlikehold\w*|"
        r"kontraktsgjennomgang|contract\s*review|sjekkliste|checklist)\b",
        lower,
    ):
        return True
    if re.search(r"\b(template_key|dokumenttype|document\s*type)\b\s*[:=]?\s*[\w\-]+", lower):
        return True
    # Named doc type alone + create verb (order-independent)
    named = re.search(
        r"\b(brukermanual|installasjonsveiledning|kontraktsgjennomgang|contract\s*review|"
        r"samsvarserkl\w*|datasheet|datablad|vedlikeholdsmanual)\b",
        lower,
    )
    if named and re.search(r"\b(opprett|lag|create|new|generer|kj[øo]r|start)\b", lower):
        return True
    # Known template keys / capability names mentioned verbatim
    keys = []
    for row in (caps or {}).get("templates") or []:
        if isinstance(row, dict):
            keys.append(row.get("template_key") or row.get("file") or "")
            keys.append(row.get("name_no") or "")
            keys.append(row.get("name_en") or "")
        elif isinstance(row, str):
            keys.append(row)
    for k in keys:
        k = (k or "").strip()
        if len(k) >= 4 and k.lower() in lower:
            return True
    return False


def _would_create_document(text: str, lower: str) -> bool:
    """Heuristic: message looks like a create-document intent."""
    if re.search(
        r"\b(opprett|lag et|lag en|create|new document|nytt dokument|ny rapport|"
        r"generer dokument|start (en )?mal)\b",
        lower,
    ):
        return True
    if re.search(r"\b(contract\s*review|kontraktsgjennomgang|installasjonsveiledning|"
                 r"brukermanual|samsvarserkl)\b", lower) and re.search(
            r"\b(opprett|lag|kj[øo]r|generer|start|create|make)\b", lower):
        return True
    return False


def format_annotations_context(annotations: list | None) -> str:
    """Compact block for model / system — never geometry."""
    if not annotations:
        return ""
    lines = ["PENDING ANNOTATIONS (WORKORDER 0.56 §C5) — deictics refer HERE, not a new document:"]
    for i, a in enumerate(annotations, 1):
        chip = a.get("chip") or a.get("action") or a.get("kind")
        targets = ", ".join(a.get("targets") or []) or "—"
        note = (a.get("note") or "").strip()
        lines.append(
            f"{i}. {chip} · targets=[{targets}]"
            + (f" · note=«{note[:120]}»" if note else "")
        )
    lines.append(
        "If marks are pending you MUST NOT create a document unless the user "
        "explicitly names one. Resolve «denne/her/dette» to these marks."
    )
    return "\n".join(lines)


def route_editor_message(message: str, state: dict, gaps: list, scope_section=None,
                         template: dict | None = None, caps: dict | None = None,
                         annotations: list | None = None):
    """Code-first router. Returns dict: reply, actions[], pending?, tools_run[]."""
    text = (message or "").strip()
    lower = _fold(text)
    pending = state.get("chat_pending")
    annotations = annotations or []

    # WORKORDER 0.56 §C5 — pending marks block document creation unless named
    if annotations and _would_create_document(text, lower) and not explicitly_names_document(text, caps):
        labels = ", ".join(
            (a.get("chip") or a.get("action") or a.get("kind") or "?")
            for a in annotations[:4]
        )
        return {
            "reply": (
                f"Du har {len(annotations)} merke(r) som venter ({labels}). "
                "«Denne/her/dette» peker på merket — ikke et nytt dokument. "
                "Skriv hva merket skal gjøre, eller si eksplisitt hvilket dokument "
                "du vil opprette (f.eks. malnavn / dokumenttype)."
            ),
            "kind": "annot_blocks_create",
            "annotations": annotations,
        }

    # Continue pending resolve with a stated value
    if pending and pending.get("action") == "resolve_mangler" and looks_like_value(text):
        key = pending.get("key")
        return {
            "reply": None,  # filled after execute
            "execute": {"tool": "resolve_mangler", "key": key, "value": text.strip(), "unit": None},
            "clear_pending": True,
            "kind": "resolve_value",
        }

    # WORKORDER_0.25 B — ANY pending + affirmative → server dispatch (never re-ask / model)
    import hub_session as hses
    if pending and hses.is_affirmative(text):
        dispatched = dispatch_pending_action(pending)
        if dispatched:
            return dispatched

    # WORKORDER_0.25 B — pending generate / contract review confirm (legacy explicit)
    if pending and pending.get("action") == "run_generate" and re.search(
            r"\b(ja|yes|ok|kj[øo]r|gj[øo]r\s+det|go|confirm|bekreft)\b", lower):
        return {
            "execute": {
                "tool": "run_generate",
                "template_key": pending.get("template_key"),
                "template": pending.get("template"),
            },
            "kind": "dispatch_generate",
            "clear_pending": True,
        }

    # WORKORDER_0.27 — accept drafted rung-3 structure
    if pending and pending.get("action") == "accept_drafted_template" and re.search(
            r"\b(ja|yes|ok|bruk denne|use this|bekreft)\b", lower):
        return {
            "execute": {
                "tool": "accept_drafted_template",
                "draft": pending.get("draft"),
            },
            "kind": "accept_draft",
            "clear_pending": True,
        }

    if pending and pending.get("action") == "save_as_template" and re.search(
            r"\b(ja|yes|lagre|save|ok)\b", lower):
        return {
            "execute": {"tool": "save_as_template"},
            "kind": "save_as_template",
            "clear_pending": True,
        }

    # WORKORDER_0.30 — named file «… as a template» → import path (before recreate)
    import chat_attach as chattach
    if chattach.is_import_as_template_ask(text) and chattach.mentioned_filename(text):
        fname = chattach.mentioned_filename(text)
        return {
            "execute": {"tool": "propose_form_template", "file": fname},
            "kind": "propose_form_template",
        }

    # WORKORDER_0.29/0.30 + TEMPLATE_STANDARD — recreate form → flexible profile by default
    if is_recreate_form_ask(text):
        # sample_multipoint fixture only when explicitly named; otherwise inspection_checklist
        source = (
            "sample_multipoint"
            if re.search(r"\bsample[_\s-]?multipoint\b", text or "", re.I)
            else "inspection_checklist"
        )
        return {
            "execute": {"tool": "recreate_form", "source": source},
            "kind": "recreate_form",
        }

    # WORKORDER_0.27 — curated installation manual → create document (no pre-questions)
    import template_lifecycle as tl
    if tl.is_installation_manual_ask(text):
        return {
            "execute": {"tool": "create_document", "template_key": "installation_manual"},
            "kind": "create_document",
        }

    # WORKORDER_0.29 — inspection checklist form_fill
    if tl.is_inspection_checklist_ask(text):
        return {
            "execute": {"tool": "create_document", "template_key": "inspection_checklist"},
            "kind": "create_document",
        }

    # WORKORDER_0.30 — import without filename still goes through propose when asked
    if chattach.is_import_as_template_ask(text):
        return {
            "execute": {"tool": "propose_form_template", "file": None},
            "kind": "propose_form_template",
        }

    # WORKORDER_0.27 — rung-3 draft when commissioning type has no curated template
    if tl.is_commissioning_ask(text):
        return {
            "execute": {"tool": "draft_template_rung3", "story": text},
            "kind": "draft_rung3",
        }

    # WORKORDER_0.27 C — layout via chat (structural tools, zero tokens)
    if template and state.get("doc"):
        import doc_structure as dstruct
        layout = dstruct.parse_layout_intent(text, template, state)
        if layout:
            return {"execute": layout, "kind": "layout_edit"}

    # WORKORDER_0.20 B — cover/forside imperatives execute immediately
    if is_cover_imperative(text):
        return {"execute": {"tool": "set_cover"}, "kind": "set_cover"}

    # Explicit «kjør contract review» / generate without confirm when imperative
    # (not the agent's own «Skal jeg …?» confirm question)
    if (not re.search(r"\bskal\s+jeg\b|\bshall\s+i\b", lower)
            and re.search(
            r"\b(kj[øo]r|start|generer|run|generate)\b.*\b(contract\s*review|kontraktsgjennomgang|dokumentet|generate)\b|"
            r"\b(contract\s*review|kontraktsgjennomgang)\b.*\b(n[åa]|now|kj[øo]r)\b",
            lower)):
        return {
            "execute": {"tool": "run_generate", "template_key": "contract_review"},
            "kind": "run_generate",
        }
    # Soft ask → set pending (one confirm). Skip if already pending same action.
    if re.search(r"contract\s*review|kontraktsgjennomgang", lower) and re.search(
            r"\b(skal|shall|kan du|can you|vil du)\b", lower):
        if pending and pending.get("action") == "run_generate":
            return {
                "reply": ("Bekreft med **ja** — jeg spør ikke om det samme to ganger."
                          if re.search(r"[æøå]", text) or "skal" in lower
                          else "Confirm with **yes** — I won't ask the same thing twice."),
                "kind": "propose_generate_reask",
                "actions": [{"id": "confirm_generate", "label": "Ja — kjør"}],
            }
        return {
            "reply": ("Skal jeg kjøre Contract Review nå?"
                      if "skal" in lower or "kan" in lower or re.search(r"[æøå]", text)
                      else "Shall I run Contract Review now?"),
            "set_pending": {"action": "run_generate", "template_key": "contract_review"},
            "kind": "propose_generate",
            "actions": [{"id": "confirm_generate", "label": "Ja — kjør"}],
        }

    # WORKORDER_0.24 — connection spec / block diagram
    import sys
    from pathlib import Path as _P
    _eng = str(_P(__file__).resolve().parents[1])
    if _eng not in sys.path:
        sys.path.insert(0, _eng)
    import connection_diagram as cdiag
    if pending and pending.get("action") == "confirm_connection_spec":
        decision = cdiag.parse_confirm_message(text)
        if decision:
            return {
                "execute": {"tool": "confirm_connection_spec", **decision},
                "kind": "confirm_connection",
                "clear_pending": True,
            }
    if cdiag.is_connection_diagram_ask(text):
        return {"execute": {"tool": "propose_connection_spec"},
                "kind": "propose_connection"}

    # WORKORDER_0.26 B — checklist → SJEKKLISTE.txt on disk, not chat list
    # Never steal form-recreate asks into checklist
    import agent_truth as atruth
    if atruth.is_checklist_ask(text) and not is_recreate_form_ask(text):
        return {"execute": {"tool": "write_checklist"}, "kind": "write_checklist"}

    # WORKORDER_0.22 D — bulk component → BOM
    if atruth.is_scan_bom_intent(text):
        return {"execute": {"tool": "scan_components_offer"}, "kind": "scan_offer"}

    # Accept pending scan
    if pending and pending.get("action") == "scan_components" and re.search(
            r"\b(skann|scan|ja|ok|kj[øo]r)\b", lower):
        return {"execute": {"tool": "scan_components_run"}, "kind": "scan_run",
                "clear_pending": True}

    # Accept pending part confirm
    if pending and pending.get("action") == "confirm_part":
        if re.search(r"\b(ja|bekreft|yes|confirm|ok)\b", lower):
            return {
                "execute": {
                    "tool": "add_bom_component",
                    "part_no": pending.get("part_no"),
                    "file": pending.get("file"),
                    "caption": pending.get("caption"),
                    "confidence": pending.get("confidence") or 1.0,
                    "fact_id": pending.get("fact_id"),
                    "status": "ok",
                    "verified_by_user": True,
                },
                "kind": "confirm_part",
                "clear_pending": True,
            }
        if re.search(r"\b(nei|no)\b", lower):
            return {
                "reply": ("OK — ingen BOM-rad.") if re.search(r"\bnei\b", lower)
                else "OK — no BOM row.",
                "kind": "confirm_part_no",
                "clear_pending": True,
            }

    # WORKORDER_0.22 A — single photo mark/scan from index only
    if atruth.is_photo_mark_intent(text) or (
        state.get("last_indexed_media") and re.search(
            r"\b(bilde|photo|image|komponent|denne|this)\b", lower)
        and re.search(r"\b(scan|skann|merk|bom|dokument|identify|legg)\b", lower)
    ):
        return {"execute": {"tool": "ground_photo"}, "kind": "ground_photo"}

    if re.search(r"hva\s*mangler|what.?s\s*missing|vis\s*(mangler|gap|hull)|list\s*gaps", lower):
        return {"execute": {"tool": "list_gaps"}, "kind": "list_gaps"}

    # Document Type Registry — lookup before inventing structure
    if re.search(
            r"\b(list\s*document\s*types|hvilke\s*dokumenttyper|dokumenttyper\s*i\s*register|"
            r"available\s*document\s*types)\b",
            lower):
        return {"execute": {"tool": "list_document_types"}, "kind": "list_document_types"}

    if re.search(
            r"\b(materialis|materialise|materialize)\b.*\b(mal|template|brukermanual|datasheet|"
            r"installasjons|vedlikehold|samsvar|kontrollrapport)\b|"
            r"\bmaterialise_template\b",
            lower):
        matches = None
        try:
            import document_type_registry as _dtr
            matches = _dtr.match_document_types(text, limit=1)
        except Exception:
            matches = []
        tid = matches[0]["id"] if matches else None
        if tid:
            return {"execute": {"tool": "materialise_template", "type_id": tid},
                    "kind": "materialise_template"}
        return {"execute": {"tool": "list_document_types"}, "kind": "list_document_types"}

    if re.search(
            r"\b(brukermanual|user\s*manual|datasheet|datablad|installasjonsveiledning|"
            r"installation\s*(guide|manual)|vedlikeholdsmanual|service\s*manual|"
            r"samsvarserkl[æa]ring|declaration\s*of\s*conformity|kontrollrapport|"
            r"inspection\s*report|hvilken\s*dokumenttype|which\s*document\s*type|"
            r"lag\s*(en\s*)?(brukermanual|datasheet|installasjons|vedlikehold|samsvar|sjekkliste))\b",
            lower):
        return {"execute": {"tool": "match_document_type", "query": text},
                "kind": "match_document_type"}

    # Hybrid knowledge — project_findings.xlsx
    if re.search(
            r"\b(project_findings|hybrid.?knowledge|finn\s*funn|get_findings|"
            r"hva\s*vet\s*vi\s*om|what\s*do\s*we\s*know|knowledge_get_findings)\b",
            lower):
        return {
            "execute": {
                "tool": "knowledge_get_findings",
                "component": None,
                "property_name": None,
                "query": text,
            },
            "kind": "knowledge_get_findings",
        }

    if re.search(
            r"\b(semantic\s*search|s[øo]k\s*i\s*funn|knowledge_semantic_search|"
            r"finn\s*dimensjon|search\s*findings)\b",
            lower):
        return {
            "execute": {"tool": "knowledge_semantic_search", "query": text, "limit": 10},
            "kind": "knowledge_semantic_search",
        }

    if re.search(
            r"\b(importer?\s*(fakta|funn)|import\s*(index\s*)?facts|"
            r"knowledge_import|synk\s*funn\s*fra\s*indeks)\b",
            lower):
        return {"execute": {"tool": "knowledge_import_index_facts"},
                "kind": "knowledge_import_index_facts"}

    if re.search(
            r"\b(rebuild\s*(vector\s*)?index|knowledge_rebuild|"
            r"bygg\s*vector|oppdater\s*funnindeks)\b",
            lower):
        return {"execute": {"tool": "knowledge_rebuild_index"},
                "kind": "knowledge_rebuild_index"}

    # Location / site map
    if re.search(
            r"\b(sett\s*lokasjon|set_location|adresse\s*er|address\s*is|"
            r"lokasjonen\s*er|municipality|kommune\s*er)\b",
            lower) and re.search(
            r"\b(adresse|address|vei|gate|kommune|municipality|postnr|postal)\b",
            lower):
        # Light extract: leave full parse to model/fallback; store raw in address
        return {
            "execute": {
                "tool": "set_location",
                "address": text,
                "location_type": "project_site",
            },
            "kind": "set_location",
        }

    if re.search(
            r"\b(get_location|hva\s*er\s*adressen|where\s*is\s*the\s*site|"
            r"vis\s*lokasjon|project\s*location)\b",
            lower):
        return {"execute": {"tool": "get_location"}, "kind": "get_location"}

    if re.search(
            r"\b(situasjonskart|location\s*map|site\s*map|generer\s*kart|"
            r"propose_location_map|generate_location_map|lag\s*(et\s*)?kart)\b",
            lower):
        style = "technical" if re.search(r"technical|teknisk", lower) else (
            "satellite" if re.search(r"satellitt|satellite", lower) else (
                "minimal" if re.search(r"minimal|enkel", lower) else "default"))
        return {
            "execute": {"tool": "propose_location_map", "style": style},
            "kind": "propose_location_map",
        }

    # ENGINE_TOOLS — incremental index path (prefer over new documents)
    if re.search(
            r"\b(diff[_\s-]?index|hva\s*(er\s*)?(nytt|endret)|what.?s\s*new|"
            r"nye\s*filer|changed\s*files|index\s*diff)\b",
            lower):
        return {"execute": {"tool": "diff_index"}, "kind": "diff_index"}

    if re.search(
            r"\b(reindeks|re-?index|oppdater\s*indeks|scan\s*(for\s*)?(nye\s*)?filer|"
            r"indekser\s*(p[åa]\s*)?nytt|rescan)\b",
            lower):
        return {"execute": {"tool": "reindex", "confirm": False}, "kind": "reindex"}

    if re.search(
            r"\b(oppdater\s*(dokument|utkast|rapport)|update\s*(the\s*)?document|"
            r"merge\s*(nye\s*)?(kilder|sources)|flett\s*inn|"
            r"update_document_from_sources|fra\s*(nye\s*)?kilder)\b",
            lower):
        mode = "replace_sections" if re.search(
            r"replace|erstatte?\s*seksjon|overwrite", lower) else "merge"
        return {
            "execute": {"tool": "update_document_from_sources", "mode": mode},
            "kind": "update_from_sources",
        }

    if re.search(r"regener|skriv\s*om|forkort|utvid|strengere|omskriv|sammendrag", lower):
        sec = scope_section or (pending.get("section") if pending else None)
        if not sec:
            # Infer common section names from the utterance
            if re.search(r"sammendrag|summary|executive", lower):
                sec = "summary"
            elif re.search(r"identifikasjon|identification", lower):
                sec = "identification"
            elif re.search(r"omfang|scope", lower):
                sec = "scope"
        return {
            "execute": {"tool": "regenerate_section", "section": sec, "instruction": text},
            "kind": "regenerate",
            "need_section": not bool(sec),
        }

    # "den mangler X" / "mangler registreringsnummer"
    mangler_utterance = bool(re.search(
        r"\b(mangler|savner|finnes ikke|har ikke|uten)\b", lower
    )) or bool(re.search(r"registrerings?\s*nummer|reg\.?\s*nr", lower))

    matches = match_gap_from_text(text, gaps)
    if mangler_utterance and matches:
        g = matches[0]
        key = g.get("key")
        label = g.get("label") or key
        if len(matches) > 1:
            # ambiguous — ask one clarifying question
            opts = ", ".join(f"{m.get('label') or m.get('key')} (`{m.get('key')}`)"
                             for m in matches[:3])
            return {
                "reply": f"Jeg fant flere mulige mangler: {opts}. Hvilken mener du?",
                "kind": "clarify",
                "set_pending": None,
            }
        return {
            "reply": (
                f"Stemmer — {label} (`{key}`) er blant manglene. "
                f"Hva er det? (Eller si «det står i …» hvis du har filen, så henter jeg det derfra.)"
            ),
            "kind": "ask_value",
            "set_pending": {"action": "resolve_mangler", "key": key, "section": g.get("section")},
        }

    if matches and re.search(r"\b(fyll|finn|hent|løs|oppgi|sett)\b", lower):
        g = matches[0]
        return {
            "reply": (
                f"Jeg kan fylle inn **{g.get('label') or g.get('key')}**. "
                f"Oppgi verdien, eller si hvilken fil jeg skal hente den fra."
            ),
            "kind": "ask_value",
            "set_pending": {"action": "resolve_mangler", "key": g.get("key"),
                            "section": g.get("section")},
        }

    # Reference suggest intent
    if matches and re.search(r"\b(foreslå|typisk|referanse|vanlig)\b", lower):
        return {
            "execute": {"tool": "suggest_reference", "key": matches[0].get("key")},
            "kind": "reference",
        }

    # Pek på kilden
    if re.search(r"\b(står i|ligger i|fra fil|vognkort|håndbok|typeskilt)\b", lower) and (
        matches or (pending and pending.get("key"))
    ):
        key = (matches[0].get("key") if matches else pending.get("key"))
        return {
            "reply": (
                f"Si hvilken fil (eller åpne «Pek på kilden» på MANGLER-chipen for `{key}`), "
                f"så henter jeg verdien derfra."
            ),
            "kind": "extract_hint",
            "set_pending": {"action": "resolve_mangler", "key": key},
        }

    return {"kind": "fallback", "need_model": True}
