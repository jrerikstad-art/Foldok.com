"""State model v2 — per-section drafts, user facts, versions (WORKORDER 0.14)."""
import re
from datetime import datetime, timezone

MANGLER_RE = re.compile(r"`?\[MANGLER:\s*([\w_]+)\]`?")


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def default_state():
    return {
        "artifact": None,
        "confirmed": False,
        "user_facts": [],
        "dismissed": [],
        "dismissed_suggestions": [],
        "excluded_figures": [],
        "versions": [],
        "doc": None,
        "gaps": [],
        "template": None,
        "documents": [],
        "active_template": None,
        "violations": [],
        "conversation": [],
        "chat_pending": None,
        "assist_hint_shown": False,
        # Phase 1 compliance context — frameworks suggested, user confirms
        "compliance": {
            "regions": [],
            "domains": [],
            "frameworks": [],
            "suggested_frameworks": [],
            "internal_rules": [],
            "confirmed": False,
            "confirmed_requirements": [],
        },
    }


def migrate_state(state, template=None):
    """Upgrade legacy single-draft state to v2 doc.sections."""
    state.setdefault("user_facts", [])
    state.setdefault("dismissed", [])
    state.setdefault("dismissed_suggestions", [])
    state.setdefault("excluded_figures", [])
    state.setdefault("versions", [])
    state.setdefault("conversation", [])
    state.setdefault("chat_pending", None)
    state.setdefault("assist_hint_shown", False)
    if "compliance" not in state or not isinstance(state.get("compliance"), dict):
        state["compliance"] = {
            "regions": [],
            "domains": [],
            "frameworks": [],
            "suggested_frameworks": [],
            "internal_rules": [],
            "confirmed": False,
            "confirmed_requirements": [],
        }
    else:
        c = state["compliance"]
        c.setdefault("regions", [])
        c.setdefault("domains", [])
        c.setdefault("frameworks", [])
        c.setdefault("suggested_frameworks", [])
        c.setdefault("internal_rules", [])
        c.setdefault("confirmed", False)
        c.setdefault("confirmed_requirements", [])
    if state.get("doc") and isinstance(state["doc"], dict) and state["doc"].get("sections"):
        return state
    template_file = state.get("active_template") or state.get("template")
    sections = {}
    raw = state.pop("_legacy_draft_md", None)
    if raw and template:
        sections = split_draft_to_sections(raw, template)
    if sections or template_file:
        state["doc"] = {
            "template_file": template_file,
            "sections": sections,
            "generated_at": iso_now(),
        }
    return state


def _title_map(template):
    m = {}
    for s in template.get("sections", []):
        for t in (s.get("title_no"), s.get("title"), s.get("section_key")):
            if t:
                m[t.strip().lower()] = s["section_key"]
    return m


def split_draft_to_sections(md, template):
    """Split markdown on ## headings into section_key → {md, cited, gaps, updated}."""
    title_map = _title_map(template)
    sections = {}
    now = iso_now()
    parts = re.split(r"\n(?=## )", md)
    if parts and not parts[0].startswith("##"):
        parts = parts[1:]
    for part in parts:
        lines = part.split("\n", 1)
        heading = lines[0].lstrip("#").strip()
        body = lines[1] if len(lines) > 1 else ""
        key = title_map.get(heading.lower(), _slug(heading))
        sections[key] = {
            "md": body.strip(),
            "cited": [],
            "gaps": gaps_from_md(body, key),
            "updated": now,
        }
    if not sections and md.strip():
        key = template["sections"][0]["section_key"] if template.get("sections") else "body"
        sections[key] = {"md": md.strip(), "cited": [], "gaps": gaps_from_md(md, key), "updated": now}
    return sections


def _slug(text):
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_") or "section"


def gaps_from_md(md, section_key, severity_by_key=None):
    gaps = []
    for m in MANGLER_RE.finditer(md or ""):
        key = m.group(1)
        sev = (severity_by_key or {}).get(key) or "blocking"
        gaps.append({
            "section": section_key,
            "type": "missing_fact",
            "key": key,
            "label": key.replace("_", " "),
            "severity": sev,
        })
    return gaps


def assemble_draft(state, template, artifact=None, full_index=None):
    """Join sections in editorial order → full markdown with furniture (0.49)."""
    import form_model as fm
    if fm.is_form_fill(template):
        return fm.assemble_form_markdown(state, template, artifact)
    import source_citations as sc
    import editorial_layer as ed
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    title = artifact.get("name") if artifact else "Utkast"
    try:
        import doc_structure as dstruct
        section_defs = dstruct.effective_sections(state, template)
    except Exception:
        section_defs = sorted(template.get("sections", []), key=lambda x: x.get("position", 99))
    section_defs = ed.sort_sections_editorial(list(section_defs))
    body_parts = []
    for s in section_defs:
        sk = s["section_key"]
        sec = sections.get(sk, {})
        md = sec.get("md", "")
        if full_index and sec.get("stale_citations"):
            md = sc.section_md_for_display(sec, full_index, artifact)
        stitle = s.get("title_no") or s.get("title") or sk
        body_parts.append(f"\n## {stitle}\n\n{md}\n")
        files = sec.get("files")
        if files:
            body_parts.append("*Kilder: " + ", ".join(files) + "*\n")
    body = "".join(body_parts)
    cover = (state.get("cover_image") or {}).get("file")
    index = full_index if full_index is not None else (state.get("index_cache") or [])
    return ed.apply_editorial_furniture(
        body,
        artifact=artifact or {"name": title},
        template=template or {},
        section_defs=section_defs,
        index=index,
        lang="no",
        cover_figure=cover,
        doc_meta={
            "document_no": (template or {}).get("document_no")
            or (template or {}).get("template_key")
            or "",
            "revision": (state.get("revision") or "A"),
            "company": (artifact or {}).get("manufacturer") or "",
        },
    )


def next_user_fact_id(state):
    return f"user-{len(state.get('user_facts') or []) + 1:04d}"


def format_cited_value(fact):
    unit = f" {fact['unit']}" if fact.get("unit") else ""
    return f"**{fact['value']}{unit}**"


def format_verified_value(fact):
    unit = f" {fact['unit']}" if fact.get("unit") else ""
    return f"**{fact['value']}{unit} ✓**"


def format_reference_value(fact):
    """Amber AI reference — not verified against project sources."""
    unit = f" {fact['unit']}" if fact.get("unit") else ""
    return f"**{fact['value']}{unit} ~**"


def reference_facts(state):
    return [f for f in (state.get("user_facts") or []) if f.get("provenance") == "reference"]


def mark_ubekreftet_gaps(gaps, state):
    """Reference accepts leave an ubekreftet gap — never 'closed'."""
    ref_keys = {f["key"] for f in reference_facts(state)}
    if not ref_keys:
        return gaps
    out = []
    for g in gaps:
        if g.get("key") in ref_keys:
            g = {**g, "severity": "ubekreftet", "status": "unconfirmed"}
        out.append(g)
    # Ensure every accepted reference key appears as ubekreftet even if
    # template_gaps somehow omitted it (e.g. after MD substitution).
    have = {g["key"] for g in out if g.get("severity") == "ubekreftet"}
    for f in reference_facts(state):
        if f["key"] in have:
            continue
        out.append({
            "section": f.get("section") or "",
            "type": "unconfirmed_reference",
            "key": f["key"],
            "label": f.get("label") or f["key"].replace("_", " "),
            "severity": "ubekreftet",
            "status": "unconfirmed",
        })
    return out


def dismissed_keys(state):
    return {(d["key"], d.get("section")) for d in state.get("dismissed", [])}


def filter_dismissed_gaps(gaps, state):
    dk = dismissed_keys(state)
    return [g for g in gaps if (g.get("key"), g.get("section")) not in dk
            and g.get("key") not in {d["key"] for d in state.get("dismissed", [])}]


def _sync_table_mangler(sec, key, rendered):
    """Keep structured table cells in step with md MANGLER substitution."""
    table = sec.get("table")
    if not table:
        return False
    value = re.sub(r"^\*\*|\*\*$", "", rendered.strip())
    verified = value.endswith(" ✓")
    reference = value.endswith(" ~")
    if verified:
        value = value[:-2].strip()
    elif reference:
        value = value[:-2].strip()
    changed = False
    for row in table.get("rows", []):
        for cell in (row.get("cells") or {}).values():
            if cell.get("mangler") == key:
                cell.pop("mangler", None)
                cell["v"] = value
                if verified:
                    cell["verified"] = True
                    cell.pop("reference", None)
                elif reference:
                    cell["reference"] = True
                    cell.pop("verified", None)
                else:
                    cell["cited"] = True
                changed = True
    return changed


def apply_fact_to_sections(state, key, rendered, who, summary):
    doc = state.setdefault("doc", {"sections": {}, "template_file": state.get("template")})
    sections = doc.setdefault("sections", {})
    updated = []
    for sk, sec in sections.items():
        prev = sec.get("md", "")
        new_md = substitute_mangler(prev, key, rendered)
        synced = _sync_table_mangler(sec, key, rendered)
        if new_md != prev or synced:
            add_version(state, who, "section", summary, section=sk, prev_md=prev)
            sec["md"] = new_md
            sec["updated"] = iso_now()
            updated.append(sk)
    return updated


def apply_cited_fact(state, key, fact, template, index, artifact, fc):
    rendered = format_cited_value(fact)
    updated = apply_fact_to_sections(state, key, rendered, "user",
                                     f"Siterte {key} fra {fact.get('source_location', 'kilde')}")
    state["gaps"] = gaps_for_document(state, template, index, artifact, fc, fast=True)
    return {"sections_updated": updated, "gaps": state["gaps"], "fact": fact}


def dismiss_mangler(state, key, section, reason, severity, template, index, artifact, fc):
    reason = (reason or "").strip() or "Ikke relevant for dette prosjektet"
    entry = {"key": key, "section": section, "reason": reason,
             "severity": severity or "warning", "t": iso_now()}
    dismissed = state.setdefault("dismissed", [])
    dismissed[:] = [d for d in dismissed if not (d["key"] == key and d.get("section") == section)]
    dismissed.append(entry)
    rendered = f"*(ikke relevant: {reason})*"
    apply_fact_to_sections(state, key, rendered, "user", f"Avviste {key}: {reason}")
    state["gaps"] = gaps_for_document(state, template, index, artifact, fc, fast=True)
    return {"dismissed": entry, "gaps": state["gaps"]}


def undismiss_mangler(state, key, section, template, index, artifact, fc):
    state["dismissed"] = [d for d in state.get("dismissed", [])
                          if not (d["key"] == key and d.get("section") == section)]
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    if section in sections:
        md = sections[section].get("md", "")
        md = re.sub(rf"\*\(ikke relevant:[^)]+\)\*", f"`[MANGLER: {key}]`", md, count=1)
        sections[section]["md"] = md
    state["gaps"] = gaps_for_document(state, template, index, artifact, fc, fast=True)
    return {"gaps": state["gaps"]}


def apply_multiple_cited(state, key_facts, template, index, artifact, fc):
    """key_facts: {gap_key: fact_dict}"""
    for key, fact in key_facts.items():
        apply_fact_to_sections(state, key, format_cited_value(fact), "user",
                               f"Siterte {key} fra {fact.get('source_location', 'ny fil')}")
    all_gaps = gaps_for_document(state, template, index, artifact, fc, fast=True)
    state["gaps"] = all_gaps
    return {"gaps": state["gaps"], "applied": list(key_facts.keys())}


def blocking_dismissed(state):
    return [d for d in state.get("dismissed", []) if d.get("severity") == "blocking"]


def figure_key(file, page=0):
    return f"{file}|{int(page)}"


def excluded_figure_keys(state):
    return {figure_key(e["file"], e.get("page", 0)) for e in state.get("excluded_figures", [])}


def is_figure_excluded(state, file, page=0):
    return figure_key(file, page) in excluded_figure_keys(state)


def remove_figure_mark(md, file, page=0):
    import foldok_compile as fc
    page = int(page)

    def repl(m):
        if m.group(1) == file and int(m.group(2)) == page:
            return ""
        return m.group(0)

    md2 = fc.FIGURE_MARK.sub(repl, md or "")
    if "### Illustrasjoner" in md2 and not fc.FIGURE_MARK.search(md2):
        md2 = fc.strip_illustration_block(md2)
    return md2.rstrip() + "\n"


def exclude_figure(state, section, file, page=0):
    """Remove one illustration from the document and remember the choice."""
    page = int(page)
    state.setdefault("excluded_figures", [])
    key = figure_key(file, page)
    if key not in excluded_figure_keys(state):
        state["excluded_figures"].append({
            "file": file, "page": page, "section": section, "at": iso_now(),
        })
    doc = state.get("doc") or {}
    sec = (doc.get("sections") or {}).get(section) or {}
    prev = sec.get("md", "")
    new_md = remove_figure_mark(prev, file, page)
    if new_md != prev:
        sec["md"] = new_md
        sec["updated"] = iso_now()
    files = list(sec.get("files") or [])
    if file in files and not any(
        m.group(1) == file for m in __import__("foldok_compile").FIGURE_MARK.finditer(sec.get("md", ""))
    ):
        sec["files"] = [f for f in files if f != file]
    return {"file": file, "page": page, "section": section}


def restore_figure(state, file, page=0):
    page = int(page)
    key = figure_key(file, page)
    state["excluded_figures"] = [
        e for e in state.get("excluded_figures", [])
        if figure_key(e["file"], e.get("page", 0)) != key
    ]
    return {"file": file, "page": page}


def excluded_source_files(state):
    return {e["file"] for e in state.get("excluded_sources", [])}


def toggle_source(state, file, on, full_index=None, artifact=None):
    """Include/exclude a source file for THIS document. Index untouched."""
    import source_citations as sc
    state.setdefault("excluded_sources", [])
    if on:
        state["excluded_sources"] = [e for e in state["excluded_sources"] if e["file"] != file]
        if full_index is not None:
            sc.clear_stale_for_file(state, file, full_index)
        sc.clear_warnings_for_file(state, file)
    elif file not in excluded_source_files(state):
        state["excluded_sources"].append({"file": file, "at": iso_now(), "by": "user"})
        if full_index is not None:
            sc.apply_excluded_source_to_document(state, file, full_index, artifact)
    if not on:
        doc = state.get("doc") or {}
        for sk, sec in (doc.get("sections") or {}).items():
            files = sec.get("files") or []
            if file in files:
                sec["files"] = [f for f in files if f != file]
            md = sec.get("md") or ""
            import foldok_compile as fc
            if fc.FIGURE_MARK.search(md):
                new_md = fc.FIGURE_MARK.sub(
                    lambda m: "" if m.group(1) == file else m.group(0), md)
                if new_md != md:
                    sec["md"] = new_md
                    sec["updated"] = iso_now()
    impacts = state.get("source_citation_warnings", [])
    return {"file": file, "on": on, "excluded_sources": state["excluded_sources"],
            "impacts": [w for w in impacts if w.get("file") == file] if not on else []}


def set_cell_override(state, section, row_key, column, value, fact_id=None, verified=False):
    """Sovereign per-cell edit — survives recompiles of code-built tables."""
    overrides = state.setdefault("cell_overrides", [])
    overrides[:] = [o for o in overrides
                    if not (o.get("section") == section and o.get("row_key") == row_key
                            and o.get("column") == column)]
    entry = {"section": section, "row_key": row_key, "column": column,
             "value": value, "at": iso_now()}
    if fact_id:
        entry["fact_id"] = fact_id
    if verified:
        entry["verified_by_user"] = True
    overrides.append(entry)
    return entry


def substitute_mangler(md, key, rendered):
    if not md:
        return md
    md = md.replace(f"`[MANGLER: {key}]`", rendered)
    md = md.replace(f"[MANGLER: {key}]", rendered)
    return md


def add_version(state, who, scope, summary, section=None, prev_md=None):
    entry = {"t": iso_now(), "who": who, "scope": scope, "summary": summary}
    if section:
        entry["section"] = section
    if prev_md is not None:
        entry["prev_md"] = prev_md
    versions = state.setdefault("versions", [])
    versions.insert(0, entry)
    state["versions"] = versions[:100]


def compute_section_gaps(sec_key, sec_md, map_gaps, severity_by_key=None):
    md_gaps = gaps_from_md(sec_md, sec_key, severity_by_key)
    md_keys = {g["key"] for g in md_gaps}
    merged = list(md_gaps)
    for g in map_gaps:
        if g.get("section") != sec_key:
            continue
        if g.get("key") in md_keys:
            continue
        if g.get("type") == "matched_by_type":
            continue
        merged.append(g)
    return merged


def _template_severity_map(template):
    m = {}
    for s in template.get("sections") or []:
        for rf in s.get("required_facts") or []:
            k = rf.get("key")
            if k:
                m[k] = rf.get("severity") or "warning"
    return m


def compute_all_gaps(state, template, index, artifact, fc, fast=False):
    import form_model as fm
    # WORKORDER 0.58 §0 — refuse foreign form docs (wrong template_file in state.doc)
    doc_tf = ((state.get("doc") or {}).get("template_file") or "").strip()
    tpl_file = (template or {}).get("file") or (template or {}).get("template_key") or ""
    if tpl_file and not str(tpl_file).endswith(".json"):
        tpl_file = f"{tpl_file}.json"
    if fm.is_form_fill(template):
        if doc_tf and tpl_file and doc_tf != tpl_file:
            return []
        gaps = fm.form_gaps(state, template)
        return filter_dismissed_gaps(gaps, state)
    index2 = fc.inject_user_facts(index, state.get("user_facts") or [])
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    sev_map = _template_severity_map(template or {})
    if fast:
        section_files = {sk: (sec.get("files") or []) for sk, sec in sections.items()}
        map_gaps = fc.template_gaps(template, index2, artifact, section_files)
    else:
        _, map_gaps = fc.map_sections(template, index2, artifact)
    all_gaps = []
    for s in template.get("sections", []):
        sk = s["section_key"]
        sec_md = sections.get(sk, {}).get("md", "")
        sec_gaps = compute_section_gaps(sk, sec_md, map_gaps, sev_map)
        if sk in sections:
            sections[sk]["gaps"] = sec_gaps
        all_gaps.extend(sec_gaps)
    all_gaps = filter_dismissed_gaps(all_gaps, state)
    all_gaps = mark_ubekreftet_gaps(all_gaps, state)
    # Phase 1 — framework evidence gaps (suggested/confirmed profiles only)
    try:
        import compliance_engine as ceng
        ceng.ensure_compliance(state)
        ev = ceng.project_evidence_gaps(state, index2)
        if ev:
            existing = {(g.get("type"), g.get("key"), g.get("framework_id")) for g in all_gaps}
            for g in ev:
                sig = (g.get("type"), g.get("key"), g.get("framework_id"))
                if sig not in existing:
                    all_gaps.append(g)
    except Exception:
        pass
    return all_gaps


def _template_section_keys(template):
    return {s.get("section_key") for s in (template or {}).get("sections") or [] if s.get("section_key")}


def _template_field_keys(template):
    keys = set()
    for s in (template or {}).get("sections") or []:
        for rf in s.get("required_facts") or []:
            if rf.get("key"):
                keys.add(rf["key"])
        for f in s.get("fields") or []:
            if f.get("key"):
                keys.add(f["key"])
    return keys


def filter_gaps_to_template(gaps, template):
    """Drop any gap that cannot belong to this template (cross-doc contamination)."""
    allowed_sec = _template_section_keys(template)
    allowed_keys = _template_field_keys(template)
    out = []
    for g in gaps or []:
        sk = g.get("section")
        if allowed_sec and sk and sk not in allowed_sec:
            continue
        if g.get("type") == "form_field" and allowed_keys and g.get("key") not in allowed_keys:
            continue
        out.append(g)
    return out


def enrich_gap_for_assist(gap, template, index, fc, documents=None):
    """Local metadata for WORKORDER 0.58 §B — zero tokens."""
    g = dict(gap or {})
    sk = g.get("section") or ""
    sec_def = next(
        (s for s in (template or {}).get("sections") or [] if s.get("section_key") == sk),
        {},
    )
    g["section_title"] = sec_def.get("title_no") or sec_def.get("title") or sk
    notes = (sec_def.get("notes") or sec_def.get("assistant_hint") or "").strip()
    g["section_notes"] = notes[:240]
    key = g.get("key") or ""
    for rf in sec_def.get("required_facts") or []:
        if rf.get("key") == key:
            g["label"] = rf.get("label_no") or rf.get("label") or g.get("label") or key
            g["severity"] = rf.get("severity") or g.get("severity") or "warning"
            break
    for fdef in sec_def.get("fields") or []:
        if fdef.get("key") == key:
            g["label"] = fdef.get("label_no") or fdef.get("label") or g.get("label") or key
            break
    guide = {}
    try:
        guide = fc.gap_guide(key, sk, index or [], None, documents or []) or {}
    except Exception:
        guide = {}
    cands = guide.get("candidates") or []
    if not cands and key:
        try:
            cands = fc.search_fact_candidates(index or [], key) or []
        except Exception:
            cands = []
    g["index_hits"] = len(cands)
    g["likely_sources"] = [c.get("file") for c in cands[:3] if c.get("file")]
    g["allows_suggest"] = bool(fc.allows_reference_suggest(key, g.get("severity")))
    sug = guide.get("suggested") if guide.get("action") == "apply_value" else None
    if not sug and cands:
        sug = cands[0]
    if sug:
        g["candidate"] = {
            "value": sug.get("value"),
            "unit": sug.get("unit"),
            "file": sug.get("file") or sug.get("source"),
            "fact_id": sug.get("fact_id"),
            "excerpt": (sug.get("excerpt") or "")[:80],
        }
    else:
        g["candidate"] = None
    return g


def gaps_for_document(state, template, index, artifact, fc, fast=True, documents=None):
    """WORKORDER 0.58 §0 — gaps ONLY from the active document's template + its own state.

    Never unions gaps across project documents or other templates. compute_all_gaps
    refuses a mismatched form_fill template_file; filter_gaps_to_template drops any
    foreign section/field keys that slip through.
    """
    gaps = compute_all_gaps(state, template, index, artifact, fc, fast=fast)
    gaps = filter_gaps_to_template(gaps, template)
    # WORKORDER 0.59 D2 — unlabelled sketch placeholders are blocking
    try:
        import sketch_recognize as sk
        gaps = list(gaps) + sk.export_blocking_placeholders(state)
    except Exception:
        pass
    docs = documents if documents is not None else (state.get("documents") or [])
    return [enrich_gap_for_assist(g, template, index, fc, docs) for g in gaps]


def gaps_summary(gaps):
    return {
        "total": len(gaps),
        "blocking": sum(1 for g in gaps if g.get("severity") == "blocking"),
        "warning": sum(1 for g in gaps if g.get("severity") == "warning"),
        "info": sum(1 for g in gaps if g.get("severity") == "info"),
        "ubekreftet": sum(1 for g in gaps if g.get("severity") == "ubekreftet"),
    }


def explain_gap_text(gap, index_file_count=0):
    """Assemble ≤60-word zero-token explanation (WORKORDER 0.58 §B1)."""
    label = (gap.get("label") or gap.get("key") or "Felt").strip()
    sev = gap.get("severity") or "warning"
    sev_no = {"blocking": "blokkerende", "warning": "advarsel", "info": "info"}.get(sev, sev)
    n = int(index_file_count or 0)
    hits = int(gap.get("index_hits") or 0)
    notes = (gap.get("section_notes") or "").strip()
    cand = gap.get("candidate") or {}
    parts = [f"**{label}** kreves av malen ({sev_no})."]
    if cand.get("value"):
        src = (cand.get("file") or "").split("/")[-1].split("\\")[-1] or "kilde"
        parts.append(f"Funn: «{cand['value']}» i {src}.")
    elif hits:
        parts.append(f"Funnet {hits} treff i indeksen — pek på kilden eller bruk kandidaten.")
    elif n:
        parts.append(f"Ikke funnet i de {n} indekserte filene.")
    else:
        parts.append("Ingen indekserte filer å søke i ennå.")
    if notes:
        # keep short
        hint = notes.split(".")[0].strip()
        if hint:
            parts.append(hint + ("." if not hint.endswith(".") else ""))
    elif gap.get("likely_sources"):
        files = ", ".join(
            (f or "").split("/")[-1].split("\\")[-1] for f in gap["likely_sources"][:2]
        )
        if files:
            parts.append(f"Sjekk typisk: {files}.")
    text = " ".join(parts)
    words = text.replace("**", "").split()
    if len(words) > 60:
        text = " ".join(words[:58]) + "…"
    return text


def resolve_mangler(state, key, value, unit, template, index, artifact, fc,
                    provenance="user", section=None):
    fact = {
        "id": next_user_fact_id(state),
        "key": key,
        "fact_type": "spec",
        "value": value,
        "unit": unit or None,
        "verified_by_user": provenance == "user",
        "provenance": provenance or "user",
        "source_location": ("AI-foreslått referanseverdi" if provenance == "reference"
                            else "oppgitt manuelt av bruker"),
        "created": iso_now(),
    }
    if section:
        fact["section"] = section
    state.setdefault("user_facts", []).append(fact)
    if provenance == "reference":
        rendered = format_reference_value(fact)
        summary = f"Referanse {key}: {value}{(' ' + unit) if unit else ''} (ubekreftet)"
    else:
        rendered = format_verified_value(fact)
        summary = f"Oppga {key}: {value}{(' ' + unit) if unit else ''}"
    doc = state.setdefault("doc", {"sections": {}, "template_file": state.get("template")})
    sections = doc.setdefault("sections", {})
    updated_keys = []
    for sk, sec in sections.items():
        prev = sec.get("md", "")
        new_md = substitute_mangler(prev, key, rendered)
        synced = _sync_table_mangler(sec, key, rendered)
        if new_md != prev or synced:
            add_version(state, "user", "section", summary, section=sk, prev_md=prev)
            sec["md"] = new_md
            sec["updated"] = iso_now()
            updated_keys.append(sk)
    all_gaps = gaps_for_document(state, template, index, artifact, fc, fast=True)
    state["gaps"] = all_gaps
    return {"sections_updated": updated_keys, "gaps": all_gaps, "fact": fact}


def build_doc_from_generation(template_file, sections_data):
    now = iso_now()
    sections = {}
    for sec_key, md, cited, violations, files in sections_data:
        sections[sec_key] = {
            "md": md,
            "cited": cited,
            "cited_fact_ids": cited,
            "gaps": gaps_from_md(md, sec_key),
            "violations": violations,
            "updated": now,
        }
        if files:
            sections[sec_key]["files"] = files
    return {"template_file": template_file, "sections": sections, "generated_at": now}
