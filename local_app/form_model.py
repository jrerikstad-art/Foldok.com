"""WORKORDER_0.29/0.30 — form_fill document species + malimport helpers."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

FIELD_TYPES = ("rating3", "check", "measure", "text", "date", "signature", "photo")
RATING3_OPTIONS = ("ok", "attention", "immediate")
# Never AI-suggest or auto-fill these (technician judgment)
NO_AUTO_TYPES = frozenset({"rating3", "check", "signature"})

# Canonical key aliases for import / prefill
KEY_ALIASES = {
    "regnr": "reg_no", "reg_nr": "reg_no", "registreringsnummer": "reg_no",
    "kjennemerke": "reg_no", "number_plate": "reg_no",
    "vin": "vin", "chassisnummer": "vin", "understellsnummer": "vin",
    "km": "mileage", "kilometerstand": "mileage", "odometer": "mileage",
    "kunde": "customer_name", "customer": "customer_name", "kundenavn": "customer_name",
    "dato": "date", "date": "date",
    "arsmodell": "model_year", "årsmodell": "model_year", "model_year": "model_year",
    "merke": "make", "make": "make", "modell": "model", "model": "model",
    # Flexible inspection profile (TEMPLATE_STANDARD)
    "objekt": "subject_ref", "objekt_id": "subject_ref", "subject": "subject_ref",
    "anlegg": "subject_ref", "anleggsid": "subject_ref", "equipment_id": "subject_ref",
    "sted": "location", "lokasjon": "location", "location": "location",
    "driftsmal": "usage_counter", "driftsmål": "usage_counter", "timer": "usage_counter",
}

FORM_SHAPED_RE = re.compile(
    r"(utfylt\s+av|signatur|dato\s*:|navn\s*:|vin\s*:|reg\.?\s*nr|"
    r"\[\s*\]|_{3,}|☐|☑|□|ok\s*/\s*attention|immediate|"
    r"kunde\s*kopi|dealer\s*copy|item\s*#|multipoint|"
    r"bremsebelegg|dekkmønster|tread|kontrollskjema|egenkontroll|"
    r"sjekkliste|checklist|inspection\s+form)",
    re.I,
)

# Domain-locked vehicle fixtures — hide unless project tag includes "vehicle"
_VEHICLE_FIXTURE_KEYS = frozenset({
    "sample_multipoint", "toyota_multipoint",
})
_VEHICLE_LOCK_APPLIES = frozenset({
    "sample_fixture", "toyota_fixture", "vehicle_oem", "vehicle_fixture",
})
_VEHICLE_TAG_RE = re.compile(
    r"\b(vehicle|bil|kjøretøy|kjoretoy|verksted|servicebil|multipoint|"
    r"car|auto|suv|van)\b",
    re.I,
)


def is_domain_locked_vehicle_template(template: dict | None) -> bool:
    """True for OEM/fixture vehicle forms that must not pollute other domains."""
    if not template:
        return False
    key = (template.get("key") or template.get("template_key") or "").strip().lower()
    if key == "inspection_checklist":
        return False
    if template.get("system_default"):
        return False
    if key in _VEHICLE_FIXTURE_KEYS:
        return True
    fname = (template.get("file") or "").strip().lower()
    if fname in {f"{k}.json" for k in _VEHICLE_FIXTURE_KEYS}:
        return True
    applies = {str(a).lower() for a in (template.get("applies_to") or [])}
    if applies & _VEHICLE_LOCK_APPLIES:
        return True
    badge = (template.get("badge") or "").lower()
    name = f"{template.get('name') or ''} {template.get('name_no') or ''}".lower()
    if "domeneeksempel" in badge or "sample fixture" in name or "domain fixture" in name:
        return True
    # Imported/owned print-faithful vehicle sheets (VIN/Reg.nr OEM shape)
    origin = (template.get("origin") or "").lower()
    if origin in ("imported", "owned") and "vehicle" in applies:
        return True
    return False


def project_has_vehicle_tag(project: dict | None = None, *, tags=None) -> bool:
    """True when the project is tagged or clearly named as vehicle work."""
    bag = set()
    for t in tags or []:
        bag.add(str(t).lower())
    for t in (project or {}).get("tags") or []:
        bag.add(str(t).lower())
    art = (project or {}).get("artifact") or {}
    for t in art.get("tags") or []:
        bag.add(str(t).lower())
    if "vehicle" in bag:
        return True
    blob = " ".join([
        str((project or {}).get("name") or ""),
        str(art.get("name") or ""),
        str(art.get("artifact_type") or ""),
        " ".join(str(x) for x in bag),
    ]).lower()
    return bool(_VEHICLE_TAG_RE.search(blob))


def filter_templates_for_project(templates: list, project: dict | None = None,
                                 *, tags=None) -> list:
    """Drop domain-locked vehicle forms unless project tag = vehicle."""
    allow_vehicle = project_has_vehicle_tag(project, tags=tags)
    out = []
    for t in templates or []:
        if is_domain_locked_vehicle_template(t) and not allow_vehicle:
            continue
        out.append(t)
    return out

FILLED_VALUE_RE = re.compile(
    r"(tegning|rev\.?\s*\d|snitt|plan\s+\d|bom\b|spesifikasjon|"
    r"\b\d{4,}\s*km\b|\b[A-Z]{2}\s*\d{4,5}\b)",
    re.I,
)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def _iso():
    return datetime.now(timezone.utc).isoformat()


def is_form_fill(template: dict | None) -> bool:
    if not template:
        return False
    if template.get("document_species") == "form_fill":
        return True
    # Heuristic: majority of sections carry fields
    secs = template.get("sections") or []
    if not secs:
        return False
    with_fields = sum(1 for s in secs if s.get("fields") or s.get("block_type") == "form_section")
    return with_fields >= max(1, len(secs) // 2)


def canonicalize_key(raw: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "_", _fold(raw)).strip("_")[:48] or "field"
    return KEY_ALIASES.get(k, k)


def normalize_field(f: dict, *, section_key: str = "") -> dict | None:
    if not isinstance(f, dict):
        return None
    key = canonicalize_key(f.get("key") or f.get("label_no") or f.get("label") or "field")
    ftype = (f.get("type") or "text").lower().strip()
    if ftype not in FIELD_TYPES:
        ftype = "text"
    out = {
        "key": key,
        "label": f.get("label") or f.get("label_no") or key.replace("_", " "),
        "label_no": f.get("label_no") or f.get("label") or key.replace("_", " "),
        "type": ftype,
        "unit": f.get("unit"),
        "options": list(f.get("options") or (RATING3_OPTIONS if ftype == "rating3" else [])),
        "value": f.get("value"),
        "source": f.get("source"),
        "required": bool(f.get("required", False)),
        "severity": f.get("severity") or ("warning" if f.get("required") else "info"),
        "note": f.get("note") or "",
        "min": f.get("min"),
        "max": f.get("max"),
        "section": section_key or f.get("section") or "",
    }
    # Form Engine v2 overlay — preserve layout regions when present
    if f.get("bbox"):
        out["bbox"] = f["bbox"]
    if f.get("page") is not None:
        out["page"] = f.get("page")
    if f.get("cells") is not None:
        out["cells"] = f["cells"]
    return out


def validate_form_template(template: dict) -> dict:
    """Code-validate imported/drafted form templates. Mutates a copy."""
    t = deepcopy(template) if isinstance(template, dict) else {}
    sections = []
    field_count = 0
    capture_types = 0
    seen_keys: set[str] = set()
    for i, s in enumerate(t.get("sections") or []):
        if not isinstance(s, dict):
            continue
        s = dict(s)
        sk = s.get("section_key") or f"section_{i+1}"
        s["section_key"] = sk
        s.setdefault("title_no", s.get("title") or sk)
        s.setdefault("title", s["title_no"])
        s.setdefault("position", i + 1)
        fields = []
        for f in s.get("fields") or []:
            nf = normalize_field(f, section_key=sk)
            if not nf:
                continue
            # merge duplicate keys into first occurrence
            if nf["key"] in seen_keys:
                continue
            seen_keys.add(nf["key"])
            fields.append(nf)
            field_count += 1
            if nf["type"] in ("check", "rating3", "measure"):
                capture_types += 1
        # Promote required_facts without fields into text fields
        if not fields:
            for rf in s.get("required_facts") or []:
                if not isinstance(rf, dict) or not rf.get("key"):
                    continue
                nf = normalize_field({
                    "key": rf["key"],
                    "label_no": rf.get("label_no") or rf.get("label") or rf["key"],
                    "type": "text",
                    "required": rf.get("severity") == "blocking",
                    "severity": rf.get("severity") or "warning",
                }, section_key=sk)
                if nf and nf["key"] not in seen_keys:
                    seen_keys.add(nf["key"])
                    fields.append(nf)
                    field_count += 1
        if fields:
            s["fields"] = fields
            s["block_type"] = "form_section"
            s.setdefault("columns", 1)
        # Boilerplate stays non-AI
        if s.get("boilerplate") or s.get("boilerplate_no"):
            s["writing_rules"] = {"structure": "boilerplate"}
            s["ai_editable"] = False
        sections.append(s)
    t["sections"] = sections
    if field_count and (capture_types / max(field_count, 1)) > 0.60:
        t["document_species"] = "form_fill"
    elif field_count:
        t.setdefault("document_species", "form_fill")
    # Preserve Form Engine v2 overlay package (backgrounds + bboxes)
    if template.get("form_package"):
        t["form_package"] = template["form_package"]
    if template.get("layout_mode"):
        t["layout_mode"] = template["layout_mode"]
    return t


def init_section_shell(section_def: dict) -> dict:
    """Empty section shell for a form_section (or narrative md)."""
    fields = section_def.get("fields") or []
    if fields or section_def.get("block_type") == "form_section":
        values = {}
        for f in fields:
            nf = normalize_field(f, section_key=section_def.get("section_key", ""))
            if not nf:
                continue
            values[nf["key"]] = {
                "value": None,
                "source": None,
                "note": "",
                "type": nf["type"],
                "unit": nf.get("unit"),
                "label_no": nf.get("label_no"),
                "required": nf.get("required"),
                "severity": nf.get("severity"),
            }
        return {"md": "", "files": [], "block_type": "form_section",
                "fields": values, "columns": section_def.get("columns") or 1}
    return {"md": "", "files": []}


def fact_lookup(index: list | None, user_facts: list | None = None) -> dict:
    """key → {value, unit, fact_id, provenance} — first wins."""
    out = {}
    for f in user_facts or []:
        if not isinstance(f, dict) or not f.get("key"):
            continue
        k = canonicalize_key(f["key"])
        if k in out:
            continue
        out[k] = {
            "value": f.get("value"),
            "unit": f.get("unit"),
            "fact_id": f.get("id") or f"user-{k}",
            "provenance": f.get("provenance") or "user",
        }
    for e in index or []:
        for f in e.get("facts") or []:
            if not isinstance(f, dict) or not f.get("key"):
                continue
            k = canonicalize_key(f["key"])
            if k in out:
                continue
            out[k] = {
                "value": f.get("value"),
                "unit": f.get("unit"),
                "fact_id": f.get("id"),
                "provenance": "extracted",
            }
    return out


def prefill_form(state: dict, template: dict, index: list | None = None) -> dict:
    """C1 — fill fields whose key matches an index/user fact. Never ratings/checks."""
    facts = fact_lookup(index, state.get("user_facts"))
    doc = state.setdefault("doc", {"sections": {}})
    sections = doc.setdefault("sections", {})
    filled = 0
    for sdef in template.get("sections") or []:
        sk = sdef["section_key"]
        sec = sections.setdefault(sk, init_section_shell(sdef))
        if sec.get("block_type") != "form_section" and not (sdef.get("fields")):
            continue
        if "fields" not in sec:
            sec.update(init_section_shell(sdef))
        for fdef in sdef.get("fields") or []:
            nf = normalize_field(fdef, section_key=sk)
            if not nf:
                continue
            slot = sec["fields"].setdefault(nf["key"], {
                "value": None, "source": None, "note": "",
                "type": nf["type"], "unit": nf.get("unit"),
                "label_no": nf.get("label_no"),
                "required": nf.get("required"),
                "severity": nf.get("severity"),
            })
            if nf["type"] in NO_AUTO_TYPES:
                continue  # C3 — never auto-fill ratings
            if slot.get("value") not in (None, ""):
                continue
            hit = facts.get(nf["key"])
            if not hit or hit.get("value") in (None, ""):
                continue
            slot["value"] = hit["value"]
            if nf["type"] == "measure" and hit.get("unit") and not slot.get("unit"):
                slot["unit"] = hit["unit"]
            slot["source"] = hit.get("fact_id")
            slot["prefilled"] = True
            filled += 1
    return {"prefilled": filled}


def form_gaps(state: dict, template: dict) -> list:
    """Empty required fields → gaps (same pill UX as narrative)."""
    gaps = []
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    for sdef in template.get("sections") or []:
        sk = sdef["section_key"]
        sec = sections.get(sk) or {}
        field_vals = sec.get("fields") or {}
        for fdef in sdef.get("fields") or []:
            nf = normalize_field(fdef, section_key=sk)
            if not nf or not nf.get("required"):
                continue
            slot = field_vals.get(nf["key"]) or {}
            val = slot.get("value")
            empty = val is None or val == "" or (nf["type"] == "check" and val is False)
            if empty:
                gaps.append({
                    "section": sk,
                    "type": "form_field",
                    "key": nf["key"],
                    "label": nf.get("label_no") or nf["key"],
                    "severity": nf.get("severity") or sdef.get("gap_severity") or "warning",
                    "field_type": nf["type"],
                })
    return gaps


def set_field(state: dict, section_key: str, key: str, value, *,
              note: str | None = None, unit: str | None = None) -> dict:
    """Set a form field value. Returns the slot."""
    doc = state.setdefault("doc", {"sections": {}})
    sec = doc.setdefault("sections", {}).setdefault(section_key, {
        "md": "", "files": [], "block_type": "form_section", "fields": {},
    })
    fields = sec.setdefault("fields", {})
    slot = fields.setdefault(key, {"value": None, "source": None, "note": "", "type": "text"})
    slot["value"] = value
    if note is not None:
        slot["note"] = note
    if unit is not None:
        slot["unit"] = unit
    # User entry clears prefilled provenance unless they kept the same value
    if not slot.get("prefilled") or slot.get("source") is None:
        slot["source"] = None
        slot["prefilled"] = False
    slot["updated"] = _iso()
    return slot


def field_becomes_fact(state: dict, section_key: str, key: str, slot: dict,
                       *, template_field: dict | None = None) -> dict | None:
    """A3 — filled measure/text/date → user_facts for later narrative citation."""
    ftype = (slot.get("type") or (template_field or {}).get("type") or "text")
    if ftype in ("rating3", "check", "signature", "photo"):
        return None
    val = slot.get("value")
    if val is None or val == "":
        return None
    fact_type = "measurement" if ftype == "measure" else "spec"
    user_facts = state.setdefault("user_facts", [])
    # Update existing same key
    for f in user_facts:
        if f.get("key") == key and f.get("provenance") in ("user", "form"):
            f["value"] = val
            f["unit"] = slot.get("unit") or f.get("unit")
            f["provenance"] = "form" if not slot.get("prefilled") else (f.get("provenance") or "extracted")
            f["section"] = section_key
            return f
    fact = {
        "id": f"form-{len(user_facts)+1:04d}",
        "key": key,
        "value": val,
        "unit": slot.get("unit"),
        "fact_type": fact_type,
        "provenance": "form" if not slot.get("source") else "extracted",
        "section": section_key,
        "label": slot.get("label_no") or key,
        "confidence": 1.0 if not slot.get("prefilled") else 0.9,
    }
    if slot.get("source"):
        fact["source_fact_id"] = slot["source"]
        fact["provenance"] = "extracted"
    user_facts.append(fact)
    return fact


def assemble_form_markdown(state: dict, template: dict, artifact=None) -> str:
    """Print-oriented markdown for form_fill export (PDF later)."""
    title = (artifact or {}).get("name") if artifact else None
    title = title or template.get("name_no") or template.get("name") or "Skjema"
    out = [f"# {title}\n"]
    if template.get("badge"):
        out.append(f"*{template['badge']}*\n")
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    for sdef in sorted(template.get("sections") or [], key=lambda x: x.get("position", 99)):
        sk = sdef["section_key"]
        stitle = sdef.get("title_no") or sdef.get("title") or sk
        out.append(f"\n## {stitle}\n")
        if sdef.get("boilerplate_no") or sdef.get("boilerplate"):
            out.append((sdef.get("boilerplate_no") or sdef.get("boilerplate")) + "\n")
            continue
        if sdef.get("writing_rules", {}).get("structure") == "prose" and not sdef.get("fields"):
            md = (sections.get(sk) or {}).get("md") or ""
            out.append(md + "\n")
            continue
        fields = sdef.get("fields") or []
        vals = (sections.get(sk) or {}).get("fields") or {}
        cols = sdef.get("columns") or 1
        if cols == 2:
            out.append("| Felt | Verdi | Felt | Verdi |\n|---|---|---|---|\n")
            row = []
            for fdef in fields:
                nf = normalize_field(fdef, section_key=sk)
                if not nf:
                    continue
                slot = vals.get(nf["key"]) or {}
                cell = _format_export_value(nf, slot)
                row.append((nf.get("label_no") or nf["key"], cell))
                if len(row) == 2:
                    out.append(f"| {row[0][0]} | {row[0][1]} | {row[1][0]} | {row[1][1]} |\n")
                    row = []
            if row:
                out.append(f"| {row[0][0]} | {row[0][1]} |  |  |\n")
        else:
            out.append("| Felt | Verdi |\n|---|---|\n")
            for fdef in fields:
                nf = normalize_field(fdef, section_key=sk)
                if not nf:
                    continue
                slot = vals.get(nf["key"]) or {}
                out.append(f"| {nf.get('label_no') or nf['key']} | {_format_export_value(nf, slot)} |\n")
    return "".join(out)


def _format_export_value(nf: dict, slot: dict) -> str:
    val = slot.get("value")
    ftype = nf.get("type")
    if ftype == "rating3":
        colors = {"ok": "🟢 OK", "attention": "🟡 Attention", "immediate": "🔴 Immediate"}
        return colors.get(val, "☐") if val else "☐ ☐ ☐"
    if ftype == "check":
        return "☑" if val else "☐"
    if val is None or val == "":
        return "____________________"
    unit = slot.get("unit") or nf.get("unit") or ""
    cited = " ✓" if slot.get("source") else ""
    return f"{val}{(' ' + unit) if unit else ''}{cited}"


def form_summary_for_offer(template: dict, lang: str = "no") -> str:
    """One-line field summary for the import offer."""
    n_sec = 0
    n_fields = 0
    types = set()
    id_keys = []
    for s in template.get("sections") or []:
        fields = s.get("fields") or []
        if not fields and s.get("block_type") != "form_section":
            continue
        n_sec += 1
        for f in fields:
            n_fields += 1
            types.add(f.get("type") or "text")
            k = f.get("key") or ""
            if k in ("reg_no", "vin", "mileage", "customer_name", "date", "model_year"):
                id_keys.append(f.get("label_no") or k)
    type_bits = []
    if "rating3" in types:
        type_bits.append("trefarget vurdering" if lang != "en" else "tri-state ratings")
    if "measure" in types:
        type_bits.append("måleverdier" if lang != "en" else "measurements")
    if "check" in types:
        type_bits.append("avkryssing" if lang != "en" else "checks")
    id_bit = (", ".join(id_keys[:5]) if id_keys
              else ("identifikasjon" if lang != "en" else "identification"))
    if lang == "en":
        return (f"Found: {id_bit}; {n_sec} check groups, {n_fields} fields"
                + (f" ({', '.join(type_bits)})" if type_bits else "") + ".")
    return (f"Fant: {id_bit}; {n_sec} sjekkgrupper, {n_fields} felt"
            + (f" ({', '.join(type_bits)})" if type_bits else "") + ".")


def form_propose_reply(summary: str, *, filled: bool = False, lang: str = "no") -> dict:
    if lang == "en":
        if filled:
            reply = (
                f"This looks like a completed form. {summary} "
                f"I can turn the structure into a reusable template, "
                f"and/or read the values in as project facts."
            )
            actions = [
                {"id": "import_form", "label": "Make template from structure"},
                {"id": "extract_form_values", "label": "Read values as facts"},
            ]
        else:
            reply = (
                f"This is a form — I can make it a reusable template for every job. "
                f"{summary}"
            )
            actions = [
                {"id": "import_form", "label": "Make template"},
                {"id": "review_fields", "label": "Review fields"},
            ]
    else:
        if filled:
            reply = (
                f"Dette ser ut som et utfylt skjema. {summary} "
                f"Jeg kan lage mal av strukturen, og/eller lese inn verdiene som fakta."
            )
            actions = [
                {"id": "import_form", "label": "Lag mal av strukturen"},
                {"id": "extract_form_values", "label": "Les inn verdiene som fakta"},
            ]
        else:
            reply = (
                f"Dette er et skjema — jeg kan gjøre det til en mal du kan bruke på hver jobb. "
                f"{summary}"
            )
            actions = [
                {"id": "import_form", "label": "Lag mal"},
                {"id": "review_fields", "label": "Se gjennom feltene"},
            ]
    return {"reply": reply, "actions": actions, "filled": filled}


def detect_form_shaped(text: str, name: str = "") -> dict:
    """Zero-token form vs material; also blank vs filled."""
    blob = f"{name}\n{text or ''}"
    form_hits = len(FORM_SHAPED_RE.findall(blob))
    blankish = (text or "").count("_") + (text or "").count("[ ]") + (text or "").count("☐")
    blankish += (text or "").count("____")
    filled_hits = len(FILLED_VALUE_RE.findall(blob))
    # Heuristic value density: many colon-separated short filled tokens
    filled_slots = len(re.findall(r":\s*\S{2,}", text or ""))
    is_form = form_hits >= 2 or (form_hits >= 1 and blankish >= 3) or bool(
        re.search(r"multipoint|kontrollskjema|inspection\s+form|sjekkliste", name or "", re.I)
    )
    is_filled = is_form and filled_hits >= 2 and blankish < 3 and filled_slots >= 8
    return {
        "form_shaped": is_form,
        "filled": is_filled,
        "form_hits": form_hits,
        "blankish": blankish,
        "filled_hits": filled_hits,
    }


def offline_extract_form_structure(text: str, name: str = "", lang: str = "no") -> dict:
    """Regex/heuristic form extract — zero tokens (tests + no-API fallback)."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    sections = []
    cur = {
        "section_key": "identification",
        "title": "Identification",
        "title_no": "Identifikasjon",
        "position": 1,
        "block_type": "form_section",
        "columns": 1,
        "fields": [],
        "gap_severity": "warning",
        "required": True,
    }
    group_n = 1
    rating_words = re.compile(r"\b(ok|attention|immediate|bra|avvik|kritis?k)\b", re.I)
    measure_words = re.compile(r"\b(mm|bar|°c|celsius|32nds|km|mønster|belegg|trykk)\b", re.I)
    check_words = re.compile(r"☐|\[\s*\]|checkbox|avkryss", re.I)

    def flush():
        nonlocal group_n, cur
        if cur["fields"]:
            sections.append(cur)
            group_n += 1
            cur = {
                "section_key": f"group_{group_n}",
                "title": f"Inspection group {group_n}",
                "title_no": f"Sjekkgruppe {group_n}",
                "position": group_n,
                "block_type": "form_section",
                "columns": 1,
                "fields": [],
                "gap_severity": "warning",
                "required": True,
            }

    for ln in lines[:200]:
        # Section headers: ALL CAPS or numbered
        if re.match(r"^[A-ZÆØÅ0-9][A-ZÆØÅ0-9 /&-]{4,}$", ln) or re.match(r"^\d+[\.)]\s+\S+", ln):
            flush()
            title = re.sub(r"^\d+[\.)]\s+", "", ln).title()
            cur["title"] = title
            cur["title_no"] = title
            cur["section_key"] = canonicalize_key(title) or f"group_{group_n}"
            continue
        # Label:____ or Label .... patterns
        m = re.match(
            r"^([A-Za-zÆØÅæøå0-9][A-Za-zÆØÅæøå0-9 /_-]{1,50})\s*[:：]\s*(.*)$", ln)
        if not m:
            m2 = re.match(r"^([A-Za-zÆØÅæøå][^_]{2,40}?)\s_{3,}", ln)
            if m2:
                label = m2.group(1).strip()
                rest = ""
            else:
                continue
        else:
            label, rest = m.group(1).strip(), m.group(2).strip()
        key = canonicalize_key(label)
        if rating_words.search(ln) or "☐ ☐ ☐" in ln or "□ □ □" in ln:
            ftype = "rating3"
        elif measure_words.search(ln) or re.search(r"\d+\s*(mm|bar|km)", rest, re.I):
            ftype = "measure"
        elif check_words.search(ln) or rest in ("", "____", "___"):
            # Prefer text for id-like labels
            if key in KEY_ALIASES.values() or key in (
                    "reg_no", "vin", "mileage", "customer_name", "date", "make", "model"):
                ftype = "date" if key == "date" else "text"
            else:
                ftype = "check" if check_words.search(ln) else "text"
        else:
            ftype = "text"
        unit = None
        um = re.search(r"\((mm|bar|°C|km|32nds)\)", ln, re.I)
        if um:
            unit = um.group(1)
        elif ftype == "measure":
            unit = "mm"
        required = key in ("reg_no", "vin", "customer_name", "date") or cur["section_key"] == "identification"
        cur["fields"].append({
            "key": key,
            "label": label,
            "label_no": label,
            "type": ftype,
            "unit": unit,
            "options": list(RATING3_OPTIONS) if ftype == "rating3" else [],
            "required": required,
            "severity": "blocking" if required and key in ("reg_no", "vin") else (
                "warning" if required else "info"),
            "value": None,
            "source": None,
            "note": "",
        })
    flush()
    if not sections:
        sections = [{
            "section_key": "identification",
            "title": "Identification", "title_no": "Identifikasjon",
            "position": 1, "block_type": "form_section", "columns": 1,
            "fields": [
                {"key": "customer_name", "label_no": "Kundenavn", "type": "text", "required": True, "severity": "warning"},
                {"key": "reg_no", "label_no": "Reg.nr", "type": "text", "required": True, "severity": "blocking"},
                {"key": "vin", "label_no": "VIN", "type": "text", "required": False, "severity": "warning"},
                {"key": "mileage", "label_no": "Km-stand", "type": "measure", "unit": "km", "required": False, "severity": "warning"},
                {"key": "date", "label_no": "Dato", "type": "date", "required": True, "severity": "warning"},
            ],
        }, {
            "section_key": "inspection",
            "title": "Inspection", "title_no": "Kontroll",
            "position": 2, "block_type": "form_section", "columns": 1,
            "fields": [
                {"key": "item_1", "label_no": "Punkt 1", "type": "rating3", "options": list(RATING3_OPTIONS), "required": True, "severity": "warning"},
                {"key": "item_2", "label_no": "Punkt 2", "type": "rating3", "options": list(RATING3_OPTIONS), "required": True, "severity": "warning"},
                {"key": "item_3", "label_no": "Punkt 3", "type": "rating3", "options": list(RATING3_OPTIONS), "required": True, "severity": "warning"},
            ],
        }]
    # Always append comments + signature
    sections.append({
        "section_key": "comments",
        "title": "Comments", "title_no": "Kommentarer",
        "position": len(sections) + 1,
        "block_type": "form_section",
        "fields": [
            {"key": "comments", "label_no": "Kommentarer", "type": "text", "required": False, "severity": "info"},
        ],
        "gap_severity": "info",
    })
    sections.append({
        "section_key": "technician",
        "title": "Technician", "title_no": "Tekniker",
        "position": len(sections) + 1,
        "block_type": "form_section",
        "fields": [
            {"key": "technician_name", "label_no": "Tekniker", "type": "text", "required": True, "severity": "warning"},
            {"key": "technician_signature", "label_no": "Signatur", "type": "signature", "required": True, "severity": "warning"},
            {"key": "inspection_date", "label_no": "Dato", "type": "date", "required": True, "severity": "warning"},
        ],
    })
    stem = Path(name).stem if name else "imported_form"
    key = re.sub(r"[^a-z0-9_]+", "_", _fold(stem))[:40] or "imported_form"
    t = {
        "template_key": key,
        "name": stem.replace("_", " ").title(),
        "name_no": stem.replace("_", " "),
        "description": f"Importert skjema fra {name or 'fil'}",
        "document_species": "form_fill",
        "origin": "imported",
        "badge": "Egen mal",
        "import_status": "review",
        "version": 1,
        "language_default": lang,
        "export_price_tier": "basic",
        "source_file": name,
        "sections": sections,
    }
    return validate_form_template(t)


def extract_form_structure(text: str, name: str = "", lang: str = "no",
                           ask_fn=None, artifact: dict | None = None) -> dict:
    """B1 — one model call when ask_fn given; else offline. Cached by caller on sha."""
    if not ask_fn:
        return offline_extract_form_structure(text, name, lang)
    prompt = f"""Extract this blank/filled form into a Foldok form_fill template JSON.
Rules: every field needs key (snake_case) + type in {list(FIELD_TYPES)}.
Map obvious keys to: vin, mileage, reg_no, customer_name, date, make, model, model_year.
rating3 options must be ["ok","attention","immediate"].
Preserve Norwegian labels verbatim in label_no.
Boilerplate/legal text → section with boilerplate_no (verbatim, not AI-rewritten).
document_species = form_fill when most fields are check/rating3/measure.

FILE: {name}
CONTENT:
{(text or '')[:8000]}

Reply ONLY JSON:
{{"template_key":"...","name":"...","name_no":"...","document_species":"form_fill",
 "sections":[{{"section_key":"...","title_no":"...","position":1,"block_type":"form_section",
 "columns":1,"fields":[{{"key":"...","label_no":"...","type":"text|rating3|check|measure|date|signature|photo",
 "unit":null,"options":[],"required":true,"severity":"warning"}}]}}]}}"""
    try:
        raw = ask_fn("template_import", None, [{"role": "user", "content": prompt}], max_tokens=4000)
        if isinstance(raw, dict):
            data = raw
        else:
            data = json.loads(raw) if isinstance(raw, str) else {}
    except Exception:
        return offline_extract_form_structure(text, name, lang)
    data["origin"] = "imported"
    data["badge"] = "Egen mal"
    data["import_status"] = "review"
    data["source_file"] = name
    data.setdefault("language_default", lang)
    return validate_form_template(data)


def review_payload(template: dict) -> dict:
    """C1 — structure for the review screen."""
    sections = []
    for s in template.get("sections") or []:
        fields = []
        for f in s.get("fields") or []:
            nf = normalize_field(f, section_key=s.get("section_key", ""))
            if nf:
                fields.append(nf)
        sections.append({
            "section_key": s.get("section_key"),
            "title": s.get("title_no") or s.get("title"),
            "columns": s.get("columns") or 1,
            "boilerplate": s.get("boilerplate_no") or s.get("boilerplate"),
            "ai_editable": s.get("ai_editable", True),
            "fields": fields,
        })
    return {
        "template_key": template.get("template_key"),
        "name_no": template.get("name_no") or template.get("name"),
        "document_species": template.get("document_species"),
        "origin": template.get("origin"),
        "badge": template.get("badge"),
        "sections": sections,
        "summary": form_summary_for_offer(template),
    }
