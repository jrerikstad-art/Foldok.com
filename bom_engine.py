"""
bom_engine.py — BOM aggregation + project completeness suggestions.
Merge into foldok-engine root; imported by foldok_compile.py and server.py.

CONTRACT (inherited, non-negotiable):
  - Vision EXTRACTS element instances per drawing (with confidence).
    ALL arithmetic (sums, totals, counts) is CODE — the model never computes.
  - Every BOM cell cites contributing fact ids or renders [MANGLER: ...].
  - Confidence < 0.80 on any contributing fact → line marked "usikker,
    bekreft mot <drawing>" — shown, never hidden, never silently trusted.
  - Suggestions SUGGEST, never push: max 4, each with its evidence,
    dismissible, zero tokens (pure signal matching in code).

Self-test:  python bom_engine.py selftest
"""

# ── 1. INDEX-TIME ADDON ──────────────────────────────────────────────
# Append to INDEX_SYSTEM (after the existing drawings/title-block paragraph):
ELEMENT_PROMPT_ADDON = """
For drawings that SHOW structural/building elements (plans, sections, details):
also extract element instances into "facts" with fact_type="element":
  key   = element category: beam|joist|stud|column|rafter|plate|window|door|pipe|duct
  value = profile/size as written: "48x198", "IPE200", "36x148 c/c600"
  unit  = "mm" (dimension system) or null
  props = { "qty": int|null, "length_mm": int|null, "spacing_cc_mm": int|null,
            "material": "C24|S355|..."|null }
  source_location = where on the drawing: "snitt A-A", "plan 1. etg", "detalj 3"
Extract each DISTINCT occurrence (same profile in two views = one instance per
view; aggregation happens later in code). Only what is legibly written or
dimensioned. A prop not stated is null — NEVER estimated, NEVER counted by
guessing from the picture. Confidence reflects legibility of THAT instance.
"""

CONF_OK = 0.80

# ── 2. BOM AGGREGATION (pure code, zero tokens) ─────────────────────
def aggregate_bom(index):
    """Group element facts by (key, value) → lines with code-computed totals.

    Returns list of lines:
      { key, profile, unit, material,
        qty_total:int|None, qty_partial:(have,of)|None,
        length_total_mm:int|None, length_partial:(have,of)|None,
        instances:[{fact_id,file,loc,qty,length_mm,conf}],
        fact_ids:[...], min_conf:float,
        gaps:[{prop:'qty'|'length_mm', likely_sources:[file,...]}] }
    """
    groups = {}
    for e in index or []:
        for f in e.get("facts", []):
            if f.get("fact_type") != "element":
                continue
            gkey = (f.get("key", "?"), str(f.get("value", "?")).replace(" ", ""))
            g = groups.setdefault(gkey, {"key": gkey[0], "profile": f.get("value"),
                                         "unit": f.get("unit"), "materials": set(),
                                         "instances": []})
            p = f.get("props") or {}
            if p.get("material"):
                g["materials"].add(str(p["material"]))
            g["instances"].append({
                "fact_id": f.get("id"), "file": e.get("file"),
                "loc": f.get("source_location") or "",
                "qty": p.get("qty"), "length_mm": p.get("length_mm"),
                "spacing_cc_mm": p.get("spacing_cc_mm"),
                "conf": float(f.get("confidence") or 0.0)})

    drawings = [e.get("file") for e in index or []
                if any(r in (e.get("doc_role_hints") or [])
                       for r in ("drawing", "site_plan", "schematic", "sketch"))]

    lines = []
    for g in groups.values():
        inst = g["instances"]
        qtys = [i["qty"] for i in inst if isinstance(i.get("qty"), (int, float))]
        lens = [i["length_mm"] for i in inst if isinstance(i.get("length_mm"), (int, float))]
        line = {
            "key": g["key"], "profile": g["profile"], "unit": g["unit"],
            "material": "/".join(sorted(g["materials"])) or None,
            "instances": inst,
            "fact_ids": [i["fact_id"] for i in inst if i.get("fact_id")],
            "min_conf": min((i["conf"] for i in inst), default=0.0),
            "qty_total": None, "qty_partial": None,
            "length_total_mm": None, "length_partial": None,
            "gaps": [],
        }
        # totals are CODE arithmetic over extracted instance values, nothing else
        if qtys and len(qtys) == len(inst):
            line["qty_total"] = int(sum(qtys))
        elif qtys:
            line["qty_partial"] = (len(qtys), len(inst))
        if lens and len(lens) == len(inst):
            line["length_total_mm"] = int(sum(lens))
        elif lens:
            line["length_partial"] = (len(lens), len(inst))
        # gap guidance: likely sources = drawings not yet contributing that prop
        contributing = {i["file"] for i in inst}
        candidates = ([f for f in drawings if f not in contributing] or list(contributing))[:3]
        if line["qty_total"] is None:
            line["gaps"].append({"prop": "qty", "likely_sources": candidates})
        if line["length_total_mm"] is None and (lens or line["length_partial"]):
            line["gaps"].append({"prop": "length_mm", "likely_sources": candidates})
        lines.append(line)

    lines.sort(key=lambda l: (l["key"], str(l["profile"])))
    return lines


def render_bom_markdown(lines, lang="no"):
    """Code-rendered BOM table. Cells cite {{fact:id}} (postprocess resolves &
    registers cited_fact_ids) or carry [MANGLER: ...] + likely-source hint."""
    if not lines:
        return ("_Ingen elementer funnet i tegningene — BOM krever tegninger "
                "med målsatte elementer._" if lang == "no"
                else "_No elements found in drawings._")
    H = (["Element", "Profil", "Materiale", "Antall", "Total lengde", "Kilder", "Status"]
         if lang == "no" else
         ["Element", "Profile", "Material", "Qty", "Total length", "Sources", "Status"])
    out = ["| " + " | ".join(H) + " |", "|" + "---|" * len(H)]
    NO = {"beam": "Bjelke", "joist": "Bjelkelag", "stud": "Stender", "column": "Søyle",
          "rafter": "Sperre", "plate": "Svill", "window": "Vindu", "door": "Dør",
          "pipe": "Rør", "duct": "Kanal"}
    for l in lines:
        name = NO.get(l["key"], l["key"].title()) if lang == "no" else l["key"].title()
        cite = " ".join("{{fact:%s}}" % i for i in l["fact_ids"][:1])  # 1 cite anchors the row
        srcs = ", ".join(sorted({f"{i['file'].split('/')[-1]}" for i in l["instances"]}))

        def cell(total, partial, prop, fmt=lambda v: str(v)):
            if total is not None:
                return fmt(total)
            hint = next((g for g in l["gaps"] if g["prop"] == prop), None)
            likely = (" — sjekk: " + ", ".join(s.split("/")[-1] for s in hint["likely_sources"])) if hint and hint["likely_sources"] else ""
            if partial:
                return f"[MANGLER: {partial[0]} av {partial[1]} instanser målsatt{likely}]"
            return f"[MANGLER: ikke angitt{likely}]"

        qty = cell(l["qty_total"], l["qty_partial"], "qty", lambda v: f"{v} stk")
        ln = cell(l["length_total_mm"], l["length_partial"], "length_mm",
                  lambda v: f"{v/1000:.2f} m (beregnet)")
        status = ("OK" if l["min_conf"] >= CONF_OK
                  else f"⚠ usikker ({int(l['min_conf']*100)}%) — bekreft mot {l['instances'][0]['file'].split('/')[-1]}")
        out.append(f"| {name} {cite} | {l['profile'] or ''} | {l['material'] or '—'} | "
                   f"{qty} | {ln} | {srcs} | {status} |")
    note = ("\n*Totaler er beregnet i kode ved summering av målsatte instanser fra "
            "tegningene — aldri estimert. Rader merket ⚠ må bekreftes av bruker.*")
    return "\n".join(out) + note


def render_component_bom_markdown(components, lang="no"):
    """WO 0.22 C3 — photo-derived BOM rows with image reference (document state)."""
    if not components:
        return ""
    H = (["Komponent", "Del-ID", "Bilde", "Konf.", "Status"]
         if lang == "no" else
         ["Component", "Part ID", "Image", "Conf.", "Status"])
    out = ["", "### " + ("Komponenter fra bilder" if lang == "no" else "Components from photos"),
           "", "| " + " | ".join(H) + " |", "|" + "---|" * len(H)]
    for c in components:
        pn = c.get("part_no") or "—"
        img = (c.get("file") or "").split("/")[-1]
        conf = float(c.get("confidence") or 0)
        status = c.get("status") or ("ok" if conf >= CONF_OK else "uncertain")
        if c.get("verified_by_user"):
            st = "bekreftet" if lang == "no" else "verified"
        elif status == "ok":
            st = "OK"
        elif status == "uncertain":
            st = f"⚠ usikker ({int(conf*100)}%)" if lang == "no" else f"⚠ uncertain ({int(conf*100)}%)"
        else:
            st = "uten ID" if lang == "no" else "no ID"
        cite = f" {{{{fact:{c['fact_id']}}}}}" if c.get("fact_id") else ""
        out.append(f"| komponent{cite} | {pn} | {img} | {int(conf*100)}% | {st} |")
    return "\n".join(out)


def merge_bom_markdown(element_md: str, components: list | None, lang="no") -> str:
    comp = render_component_bom_markdown(components or [], lang=lang)
    if not comp:
        return element_md or ""
    base = (element_md or "").rstrip()
    if base and "Ingen elementer" not in base and "No elements" not in base:
        return base + "\n" + comp
    return comp.lstrip() + ("\n\n" + base if base else "")


# ── 3. COMPLETENESS SUGGESTIONS (pure code, zero tokens) ────────────
SUGGESTION_RULES = [
    # (rule_id, strong signal terms in tags/captions, suggests[(name_no, template_key|None)], reason_no)
    ("spec_library", [
        "emc", "electromagnetic", "shielding", "cable_tray", "cable tray",
        "cable_management", "earthing", "grounding", "mil std", "mil-std",
        "ieee", "specification", "datasheet",
    ],
     [("Temabrief (sitert fagpakke)", "topic_brief"),
      ("Spesifikasjonsgjennomgang (konflikter)", "spec_coherence_review")],
     "Kildene ser ut som spesifikasjons-/EMC-bibliotek — ikke et labforsøk"),
    ("research", [
        "phd", "ph.d", "thesis", "avhandling", "preregistration", "qualitative_research",
        "thematic_analysis", "systematic_review", "research_design", "research_protocol",
        "selficon", "selficom", "survey", "intervju", "forsknings", "work_package",
    ],
     [("Forskningsprosjektrapport", "research_project_report"),
      ("Prosjektplan", "project_plan"),
      ("PhD materials draft", "phd_materials_draft")],
     "Kildene ser ut som forskning (protokoll, survey, metode, WP)"),
    ("wetroom", ["bad", "våtrom", "dusj", "wc", "bathroom", "membran"],
     [("Våtromsdokumentasjon (membran/tetting)", None),
      ("Rørleggerdokumentasjon", None)],
     "Prosjektet ser ut til å inneholde bad/våtrom"),
    ("floorheat", ["gulvvarme", "varmekabel", "floor heating"],
     [("Gulvvarme-dokumentasjon (samsvar varmekabel)", None)],
     "Gulvvarme/varmekabel nevnt i kildene"),
    ("electrical", ["sikringsskap", "kurs ", "kabel", "wiring", "el-anlegg", "stikkontakt"],
     [("Samsvarserklæring elektro", "samsvarserklaering_el")],
     "Elektrisk arbeid funnet i kildene"),
    ("lifting", ["løft", "swl", "wll", "sakkyndig", "lifting"],
     [("Kontrollrapport løfteutstyr", None),
      ("Teknisk dokumentasjonspakke", "technical_doc_package")],
     "Løfteutstyr/last funnet"),
    ("structure", ["__ELEMENTS__"],
     [("Konstruksjonsrapport", "structural_design_report"),
      ("Designgrunnlag", "design_basis"),
      ("Prosjektplan", "project_plan")],
     "Bærende elementer funnet i tegningene (BOM)"),
    ("plan", ["søknad", "tilbygg", "fasade", "utførelse", "ferdigattest", "byggesak"],
     [("Prosjektplan", "project_plan")],
     "Byggesak/utførelse — en fasert prosjektplan kan hjelpe"),
    ("standards", ["__MULTI_STD__"],
     [("Spesifikasjonsgjennomgang (konflikter)", "spec_coherence_review"),
      ("Temabrief (sitert fagpakke)", "topic_brief")],
     "Flere standarder påberopt på tvers av dokumenter"),
]


def detect_suggestions(index, artifact, current_template_key=None, max_out=4):
    """Strong-signal document suggestions. Suggests, never pushes:
    returns evidence per suggestion; caller renders as dismissible cards.
    ONE_AGENT_SPEC B2: structure rule needs element facts from drawing-role
    files; collapse to one card per RULE (top template + extras count)."""
    DRAWING_ROLES = {"drawing", "site_plan", "schematic", "sketch"}
    hay = " ".join(
        (" ".join(e.get("content_tags", [])) + " " + (e.get("caption") or "")
         + " " + (e.get("file") or "")).lower()
        for e in index or [])
    art_blob = " ".join([
        str((artifact or {}).get("name") or ""),
        str((artifact or {}).get("purpose") or ""),
        str((artifact or {}).get("artifact_type") or ""),
    ]).lower()
    hay_all = hay + " " + art_blob
    researchish = any(t in hay_all for t in (
        "phd", "thesis", "preregistration", "qualitative", "selficon", "selficom",
        "research_project", "forsknings", "thematic_analysis", "avhandling",
    )) and not any(t in hay_all for t in (
        "emc", "cable tray", "shielding", "electromagnetic", "mil-std", "mil std",
    ))
    spec_library = any(t in hay_all for t in (
        "emc", "cable tray", "shielding", "electromagnetic", "earthing", "grounding",
        "mil-std", "mil std", "cable_management",
    ))
    has_drawing_elements = any(
        f.get("fact_type") == "element"
        and set(e.get("doc_role_hints") or []) & DRAWING_ROLES
        for e in index or [] for f in e.get("facts", []))
    std_docs = {e.get("file") for e in index or [] for f in e.get("facts", [])
                if f.get("fact_type") == "standard_ref"}
    out, seen_rules = [], set()
    for rule_id, terms, suggests, reason in SUGGESTION_RULES:
        # Spec libraries: prefer topic_brief / coherence; suppress research + construction
        if spec_library and rule_id in ("research", "structure", "wetroom", "floorheat", "plan", "lifting"):
            continue
        # Don't push construction templates onto research corpora
        if researchish and rule_id in ("structure", "wetroom", "floorheat", "plan", "lifting", "standards", "spec_library"):
            continue
        hit = None
        for t in terms:
            if t == "__ELEMENTS__":
                if has_drawing_elements:
                    hit = "elementer i tegninger"
            elif t == "__MULTI_STD__" and len(std_docs) >= 2:
                hit = f"standarder i {len(std_docs)} dokumenter"
            elif t not in ("__ELEMENTS__", "__MULTI_STD__") and t in hay_all:
                hit = t.strip()
            if hit:
                break
        if not hit:
            continue
        if rule_id in seen_rules:
            continue
        # Pick top remaining template for this rule; note extras
        candidates = [(n, k) for n, k in suggests
                      if not (k and k == current_template_key)]
        if not candidates:
            continue
        name, tkey = candidates[0]
        extra = len(candidates) - 1
        seen_rules.add(rule_id)
        card = {"rule": rule_id, "name": name, "template_key": tkey,
                "reason": reason, "evidence": hit}
        if extra > 0:
            card["also"] = extra
            card["label"] = f"{name} · og {extra} til"
        out.append(card)
        if len(out) >= min(2, max_out):  # max 2 rule-cards visible
            break
    return out


# ── selftest ────────────────────────────────────────────────────────
if __name__ == "__main__":
    idx = [
        {"file": "Tegninger/K-01.pdf", "doc_role_hints": ["drawing"],
         "content_tags": ["bad", "gulvvarme"], "caption": "Plan 1. etg med bad",
         "facts": [
             {"id": "a1", "fact_type": "element", "key": "beam", "value": "48x198",
              "confidence": 0.92, "source_location": "snitt A-A",
              "props": {"qty": 8, "length_mm": 4200, "material": "C24"}},
             {"id": "a2", "fact_type": "element", "key": "beam", "value": "48x198",
              "confidence": 0.85, "source_location": "plan 1.etg",
              "props": {"qty": 4, "length_mm": 3600, "material": "C24"}},
             {"id": "a3", "fact_type": "element", "key": "stud", "value": "36x148",
              "confidence": 0.55, "source_location": "detalj 2",
              "props": {"qty": None, "length_mm": 2400}},
         ]},
        {"file": "Tegninger/K-02.pdf", "doc_role_hints": ["drawing"], "content_tags": [],
         "caption": "Snitt", "facts": []},
    ]
    lines = aggregate_bom(idx)
    beam = next(l for l in lines if l["key"] == "beam")
    assert beam["qty_total"] == 12 and beam["length_total_mm"] == 7800  # CODE math
    stud = next(l for l in lines if l["key"] == "stud")
    assert stud["qty_total"] is None and stud["gaps"][0]["prop"] == "qty"
    assert stud["min_conf"] < CONF_OK  # → ⚠ usikker in render
    md = render_bom_markdown(lines)
    assert "12 stk" in md and "7.80 m (beregnet)" in md and "MANGLER" in md and "⚠" in md
    sugg = detect_suggestions(idx, {}, current_template_key="technical_doc_package")
    names = [s["name"] for s in sugg]
    assert any("Våtrom" in n for n in names) and any("Gulvvarme" in n for n in names)
    assert len(sugg) <= 2
    # structure only when element facts come from drawing-role files
    draw_only = [{"file": "Tegninger/K-01.pdf", "doc_role_hints": ["drawing"],
                  "content_tags": [], "caption": "Snitt", "facts": [
                      {"fact_type": "element", "key": "beam", "value": "48x198"}]}]
    assert any(s["rule"] == "structure" for s in detect_suggestions(draw_only, {}))
    text_only = [{"file": "manual.txt", "doc_role_hints": ["manual"], "content_tags": [],
                  "caption": "Manual", "facts": [
                      {"fact_type": "element", "key": "beam", "value": "x"}]}]
    assert not any(s["rule"] == "structure" for s in detect_suggestions(text_only, {}))
    print("bom_engine selftest OK —", len(lines), "BOM lines,", len(sugg), "suggestions")
