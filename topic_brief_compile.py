"""Topic brief compiler — cited facet packs (Phase B).

Index → retrieve by facet → allowlisted facts → AuthoringEngine → verify.
Never joins facts as key:value walls. MANGLER only where the facet is silent.
"""
from __future__ import annotations

import re
from pathlib import Path

CONTACT_RX = re.compile(
    r"(?i)([\w.+-]+@[\w-]+\.[\w.-]+|https?://\S+|www\.\S|"
    r"\+?\d[\d\s().-]{7,}\d|"
    r"\b(phone|telefon|email|e-post|fax|linkedin|address|adresse)\b)"
)

STD_ID_RX = re.compile(
    r"(?i)\b((?:EN|IEC|ISO|NEK|HD)\s*\d[\d\-:/]*|"
    r"MIL[-\s]?STD[-\s]?\d[\w\-]*|"
    r"IEEE\s*(?:Std\s*)?\d[\w\-]*|"
    r"ASTM\s*[A-Z]?\d[\w\-]*|"
    r"UL\s*\d[\w\-]*|"
    r"NEMA\s*[A-Z]?\d?[\w\-]*)\b"
)

# Facet → (key allowlist, key prefixes, caption/value needles)
FACETS: dict[str, dict] = {
    "emc_zones": {
        "keys": {
            "emc_zone", "zone", "shielding_zone", "attenuation", "test_standard",
            "navy_project_test_result", "measurement_equipment_capability",
        },
        "prefixes": ("attenuation", "h_field", "e_field", "plane_wave", "shield", "zone_"),
        "needles": (
            "zone", "sone", "shield", "skjerm", "attenuation", "faraday",
            "emc zone", "zoning", "segregation",
        ),
    },
    "cable_classes": {
        "keys": {
            "cable_class", "cable_category", "separation_distance", "class_1",
            "class_2", "class_3", "class_4", "class_5", "class_6",
        },
        "prefixes": ("cable_class", "class_", "separation", "tray_", "nec_ground"),
        "needles": (
            "cable class", "kabelklasse", "class 1", "class 2", "class 3",
            "class 4", "class 5", "class 6", "300 mm", "90°", "90 deg",
            "fibre", "fiber", "separation", "separa",
        ),
    },
    "earthing": {
        "keys": {
            "earthing", "grounding", "bonding", "earth_bar", "pe_conductor",
            "equipotential", "ground_resistance",
        },
        "prefixes": ("earth", "ground", "bond", "pe_", "equipotential"),
        "needles": (
            "earth", "jord", "ground", "bonding", "equipotential",
            "earthing", "pe conductor", "earth bar",
        ),
    },
    "separation": {
        "keys": {"separation_distance", "min_distance", "clearance", "crossing_angle"},
        "prefixes": ("separation", "clearance", "crossing"),
        "needles": (
            "300 mm", "separation", "separa", "crossing", "90°", "90 deg",
            "parallel run", "avstand",
        ),
    },
    "standards": {
        "keys": {
            "test_standard", "material_standard", "governing_standard",
            "building_code", "standard_ref",
        },
        "prefixes": ("en_", "iec_", "mil_", "nek_", "ieee_", "astm_", "ul_", "hd_", "nema_"),
        "needles": ("mil-std", "ieee", "iec", "en ", "astm", "nek", "norsok"),
    },
}


def _usable(index):
    return [e for e in (index or []) if e.get("kind") != "skipped" and e.get("file")]


def _md_table(headers, rows):
    if not rows:
        return ""
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _mangler(keys, lang="no"):
    if (lang or "no").lower().startswith("no"):
        return "\n".join(f"MANGLER: {k} - ikke i korpus" for k in keys)
    return "\n".join(f"MISSING: {k} - not in corpus" for k in keys)


def retrieve_facet(index, facet: str, *, limit: int = 16) -> list[dict]:
    """Return allowlisted fact dicts with citation for one facet."""
    spec = FACETS.get(facet) or {}
    keys = {k.lower() for k in (spec.get("keys") or ())}
    prefixes = tuple(p.lower() for p in (spec.get("prefixes") or ()))
    needles = tuple(n.lower() for n in (spec.get("needles") or ()))
    out, seen = [], set()
    for e in _usable(index):
        src = Path(e.get("file") or "").name
        caption = (e.get("caption") or "").strip()
        cap_l = caption.lower()
        for f in e.get("facts") or []:
            key = str(f.get("key") or "").strip().lower()
            val = str(f.get("value") or "").strip()
            if not key or not val or CONTACT_RX.search(val) or CONTACT_RX.search(key):
                continue
            if key in ("manufacturer", "manufacturer_name", "phone", "email", "website", "address"):
                continue
            hit = (
                key in keys
                or any(key.startswith(p) for p in prefixes)
                or any(n in key or n in val.lower() for n in needles)
            )
            if not hit:
                continue
            unit = f.get("unit") or ""
            shown = f"{val} {unit}".strip() if unit else val
            sig = (key, shown.lower(), src)
            if sig in seen:
                continue
            seen.add(sig)
            out.append({
                "id": f.get("id") or f"{key}:{src}",
                "key": key,
                "value": val,
                "unit": unit,
                "label": key.replace("_", " "),
                "citation": src,
                "shown": shown,
            })
            if len(out) >= limit:
                return out
        # Caption-only hit when no structured facts matched this file for facet
        if needles and any(n in cap_l for n in needles) and caption and not CONTACT_RX.search(caption):
            sig = ("caption", caption[:80].lower(), src)
            if sig not in seen:
                seen.add(sig)
                out.append({
                    "id": f"cap:{src}",
                    "key": f"{facet}_note",
                    "value": caption[:180],
                    "unit": "",
                    "label": "Fra kildetittel" if facet else "Note",
                    "citation": src,
                    "shown": caption[:180],
                })
                if len(out) >= limit:
                    return out
    return out


def _author_prose(facts: list[dict], *, intent: str, title: str, lang: str) -> str:
    """AuthoringEngine plan → compose → verify. Deterministic (no model)."""
    if not facts:
        return ""
    try:
        from foldok_author import AuthoringEngine, Fact
    except Exception:
        # Fallback: one short cited sentence, never key:value wall
        bits = []
        for f in facts[:4]:
            bits.append(f"{f['shown']} ({f['citation']})")
        return (title + ": " if title else "") + "; ".join(bits) + "."

    engine = AuthoringEngine(lang=lang or "no")
    afacts = [
        Fact(
            id=str(f["id"]),
            key=f["key"],
            value=f["value"],
            unit=f.get("unit") or "",
            label=f.get("label") or "",
            citation=f.get("citation") or "",
        )
        for f in facts[:10]
    ]
    try:
        result = engine.author(intent, afacts, title=title)
        text = (result.prose or "").strip()
        # Strip accidental key:value / phone lines
        lines = [
            ln for ln in text.splitlines()
            if ln.strip() and not CONTACT_RX.search(ln)
            and not re.match(r"(?i)^\s*[a-z0-9_ æøå.-]{2,40}:\s+\S+", ln)
        ]
        return "\n".join(lines).strip()
    except Exception:
        bits = [f"{f['shown']} [{f['citation']}]" for f in facts[:5]]
        return "; ".join(bits) + "."


def _theme_bits(index, artifact=None):
    art = artifact or {}
    hay = " ".join(
        [str(art.get("name") or ""), str(art.get("purpose") or "")]
        + [str(e.get("caption") or "") for e in _usable(index)[:40]]
        + [" ".join(e.get("content_tags") or []) for e in _usable(index)[:40]]
    ).lower()
    themes = []
    for needle, label in (
        ("emc", "elektromagnetisk kompatibilitet (EMC)"),
        ("cable tray", "cable tray / cable management"),
        ("cable management", "cable tray / cable management"),
        ("shield", "skjerming"),
        ("earthing", "jording"),
        ("grounding", "jording"),
    ):
        if needle in hay and label not in themes:
            themes.append(label)
    return themes or ["teknisk kildesamling"]


def compile_topic_brief_section(sec_key, mapping, index, artifact, lang="no"):
    """Deterministic topic_brief bodies — cited tables + short authored prose."""
    sk = (sec_key or "").strip().lower()
    art = artifact or {}
    no = (lang or "no").lower().startswith("no")
    usable = _usable(index)
    n = len(usable)
    themes = _theme_bits(index, art)
    theme_txt = ", ".join(themes[:3])

    if sk == "overview":
        title = art.get("name") or (Path(usable[0]["file"]).stem if usable else "Prosjekt")
        facts = []
        for e in usable[:8]:
            cap = (e.get("caption") or "").strip()
            if cap and not CONTACT_RX.search(cap):
                facts.append({
                    "id": e.get("file") or cap[:20],
                    "key": "source_note",
                    "value": cap[:120],
                    "unit": "",
                    "label": "kilde",
                    "citation": Path(e.get("file") or "").name,
                    "shown": cap[:120],
                })
        lead = (
            f"**{title}** er en kildesamling ({n} filer) om {theme_txt}. "
            f"Denne briefen trekker ut temaer med sitering — ikke et laboratorieforsøk."
            if no else
            f"**{title}** is a source collection ({n} files) on {theme_txt}. "
            f"This brief extracts cited topics — not a laboratory study."
        )
        prose = _author_prose(
            facts[:6], intent="summarize_system",
            title=title, lang=lang,
        )
        parts = [lead]
        if prose and prose.lower() not in lead.lower():
            parts.append(prose)
        return "\n\n".join(parts)

    if sk == "emc_zones":
        rows_f = retrieve_facet(index, "emc_zones", limit=12)
        if not rows_f:
            return _mangler(["emc_zones"], lang=lang) + (
                "\n\n*Ingen sone-/skjermingsdata funnet i korpus.*"
                if no else
                "\n\n*No zone/shielding data found in corpus.*"
            )
        headers = ["Tema", "Verdi", "Kilde"] if no else ["Topic", "Value", "Source"]
        rows = [[f["label"], f["shown"], f["citation"]] for f in rows_f[:10]]
        prose = _author_prose(
            rows_f[:6], intent="specify_parameters",
            title="EMC-soner og skjerming" if no else "EMC zones and shielding",
            lang=lang,
        )
        parts = []
        if prose:
            parts.append(prose)
        parts.append("**Sone / skjerming (utvalg)**" if no else "**Zone / shielding (selection)**")
        parts.append(_md_table(headers, rows))
        return "\n\n".join(parts)

    if sk == "cable_classes":
        class_f = retrieve_facet(index, "cable_classes", limit=12)
        sep_f = retrieve_facet(index, "separation", limit=8)
        merged = class_f + [f for f in sep_f if f["id"] not in {x["id"] for x in class_f}]
        if not merged:
            return _mangler(["cable_classes", "separation"], lang=lang) + (
                "\n\n*Ingen kabelklasse- eller separasjonsregler funnet.*"
                if no else
                "\n\n*No cable class or separation rules found.*"
            )
        headers = ["Regel", "Verdi", "Kilde"] if no else ["Rule", "Value", "Source"]
        rows = [[f["label"], f["shown"], f["citation"]] for f in merged[:12]]
        prose = _author_prose(
            merged[:6], intent="specify_parameters",
            title="Kabelklasser og separasjon" if no else "Cable classes and separation",
            lang=lang,
        )
        parts = []
        if prose:
            parts.append(prose)
        parts.append("**Kabelklasse / avstand**" if no else "**Cable class / distance**")
        parts.append(_md_table(headers, rows))
        # Highlight common rules if present in values
        highlight = []
        blob = " ".join(f["shown"].lower() for f in merged)
        if "300" in blob and "mm" in blob:
            highlight.append("300 mm" + (" separasjon nevnt i kilder." if no else " separation mentioned in sources."))
        if "90" in blob:
            highlight.append("90°" + (" kryssing nevnt i kilder." if no else " crossing mentioned in sources."))
        if "fibre" in blob or "fiber" in blob:
            highlight.append("Fiber" + (" nevnt som klasse/unntak." if no else " mentioned as class/exception."))
        if highlight:
            parts.append("- " + "\n- ".join(highlight))
        return "\n\n".join(parts)

    if sk == "earthing":
        rows_f = retrieve_facet(index, "earthing", limit=12)
        if not rows_f:
            return _mangler(["earthing"], lang=lang) + (
                "\n\n*Ingen jording-/bondingdata funnet i korpus.*"
                if no else
                "\n\n*No earthing/bonding data found in corpus.*"
            )
        headers = ["Parameter", "Verdi", "Kilde"] if no else ["Parameter", "Value", "Source"]
        rows = [[f["label"], f["shown"], f["citation"]] for f in rows_f[:10]]
        prose = _author_prose(
            rows_f[:6], intent="specify_parameters",
            title="Jording og bonding" if no else "Earthing and bonding",
            lang=lang,
        )
        parts = []
        if prose:
            parts.append(prose)
        parts.append("**Jording (utvalg)**" if no else "**Earthing (selection)**")
        parts.append(_md_table(headers, rows))
        return "\n\n".join(parts)

    if sk == "standards_register":
        rows_f = retrieve_facet(index, "standards", limit=20)
        rows, seen = [], set()
        for f in rows_f:
            m = STD_ID_RX.search(f["shown"]) or STD_ID_RX.search(f["label"])
            if not m:
                continue
            shown = m.group(1).strip()
            sig = shown.lower()
            if sig in seen:
                continue
            seen.add(sig)
            rows.append([shown, f["citation"]])
        if not rows:
            return _mangler(["standards"], lang=lang)
        headers = ["Standard", "Kilde"] if no else ["Standard", "Source"]
        return _md_table(headers, rows[:15])

    if sk == "gaps":
        silent = []
        for facet, label in (
            ("emc_zones", "EMC-soner / skjerming"),
            ("cable_classes", "Kabelklasser"),
            ("separation", "Separasjonsavstand"),
            ("earthing", "Jording / bonding"),
            ("standards", "Standarder"),
        ):
            if not retrieve_facet(index, facet, limit=1):
                silent.append(label)
        rows = []
        for label in silent:
            rows.append([
                label,
                "MANGLER i korpus — ikke funnet som strukturert fakta eller tydelig caption",
            ])
        # Simple conflict: same key, different values across files
        by_key: dict[str, list] = {}
        for e in usable:
            src = Path(e.get("file") or "").name
            for f in e.get("facts") or []:
                key = str(f.get("key") or "").strip().lower()
                val = str(f.get("value") or "").strip()
                if not key or not val or CONTACT_RX.search(val):
                    continue
                if key in ("test_standard", "attenuation", "separation_distance", "cable_class"):
                    by_key.setdefault(key, []).append((val, src))
        for key, pairs in by_key.items():
            vals = {p[0].lower(): p for p in pairs}
            if len(vals) >= 2:
                a, b = list(vals.values())[:2]
                rows.append([
                    f"Konflikt-kandidat: {key}",
                    f"{a[0]} ({a[1]}) vs {b[0]} ({b[1]})",
                ])
        if not rows:
            return (
                "Ingen synlige temahull eller verdikonflikter i de skannede nøklene."
                if no else
                "No visible topic gaps or value conflicts in scanned keys."
            )
        headers = ["Gap / konflikt", "Merknad"] if no else ["Gap / conflict", "Note"]
        return _md_table(headers, rows)

    if sk == "source_register":
        rows = []
        for e in usable[:40]:
            name = Path(e.get("file") or "").name
            if not name or name.startswith("("):
                continue
            use = (e.get("caption") or "")[:70] or ("Bakgrunn" if no else "Background")
            if CONTACT_RX.search(use):
                use = "—"
            rows.append([name, use])
        if n > 40:
            rows.append([
                f"Øvrige {n - 40} filer" if no else f"Remaining {n - 40} files",
                "Bakgrunn" if no else "Background",
            ])
        headers = ["Dokument", "Bruk"] if no else ["Document", "Use"]
        return _md_table(headers, rows) if rows else (
            "Ingen kilder i indeksen." if no else "No sources in index."
        )

    return None
