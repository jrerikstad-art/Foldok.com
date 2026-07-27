"""Source toggle ↔ AI prose citation traceability (SOURCE_INTERACTION rider 1)."""
from __future__ import annotations

EXCLUDED_CITATION_MARK = "`[MANGLER: kilde ekskludert]`"


def fact_ids_for_file(index, file):
    return {f["id"] for e in index or [] if e.get("file") == file
            for f in e.get("facts", []) if f.get("id")}


def facts_by_id(index, artifact=None):
    by_id = {}
    for e in index or []:
        for f in e.get("facts", []):
            if f.get("id"):
                by_id[f["id"]] = {**f, "source_file": e.get("file")}
    if artifact:
        if artifact.get("name"):
            by_id["artifact-name"] = {"id": "artifact-name", "key": "project_title",
                                      "value": artifact["name"], "unit": None}
        if artifact.get("purpose"):
            by_id["artifact-purpose"] = {"id": "artifact-purpose", "key": "scope_statement",
                                         "value": artifact["purpose"], "unit": None}
    return by_id


def section_cited_ids(sec):
    if not sec:
        return []
    return list(sec.get("cited_fact_ids") or sec.get("cited") or [])


def _rendered_patterns(fact):
    val = str(fact.get("value") or "")
    unit = fact.get("unit") or ""
    u = f" {unit}" if unit else ""
    return [
        f"**{val}{u} ✓**",
        f"**{val}{u}**",
    ]


def invalidate_facts_in_md(md, fact_ids, by_id):
    """Replace resolved citation values with MANGLER marker — zero tokens."""
    if not md or not fact_ids:
        return md, 0
    n = 0
    for fid in fact_ids:
        f = by_id.get(fid)
        if not f:
            continue
        for pat in _rendered_patterns(f):
            if pat in md:
                md = md.replace(pat, EXCLUDED_CITATION_MARK)
                n += 1
    return md, n


def section_md_for_display(sec, full_index, artifact=None):
    """Render section md with stale citations shown as MANGLER — md stored intact."""
    md = sec.get("md") or ""
    stale = sec.get("stale_citations") or []
    if not stale:
        return md
    by_id = facts_by_id(full_index, artifact)
    out, _ = invalidate_facts_in_md(md, stale, by_id)
    return out


def rebuild_citation_warnings(state):
    """Aggregate per-section stale_citations → source_citation_warnings."""
    warnings = []
    for sk, sec in ((state.get("doc") or {}).get("sections") or {}).items():
        stale = sec.get("stale_citations") or []
        if not stale:
            continue
        by_file = {}
        for fid in stale:
            # file attribution filled by apply_excluded when possible
            pass
        warnings.append({
            "section": sk,
            "count": len(stale),
            "fact_ids": list(stale),
        })
    # Merge file-level entries preserved from impacts
    existing = {w.get("section"): w for w in state.get("source_citation_warnings", [])
                if w.get("file")}
    for sk, sec in ((state.get("doc") or {}).get("sections") or {}).items():
        stale = sec.get("stale_citations") or []
        if not stale:
            continue
        prev = existing.get(sk)
        if prev:
            prev["count"] = len(stale)
            prev["fact_ids"] = list(stale)
            warnings.append(prev)
        elif stale:
            warnings.append({"section": sk, "count": len(stale), "fact_ids": list(stale)})
    # Dedupe by section+file
    seen = set()
    out = []
    for w in warnings:
        key = (w.get("section"), w.get("file"))
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    state["source_citation_warnings"] = out
    return out


def apply_excluded_source_to_document(state, file, full_index, artifact=None):
    """Toggle-off: intersect cited ids → stale_citations (md unchanged for restore)."""
    excluded_fids = fact_ids_for_file(full_index, file)
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    impacts = []
    for sk, sec in sections.items():
        if not sec:
            continue
        cited = section_cited_ids(sec)
        hit = [fid for fid in cited if fid in excluded_fids]
        if not hit:
            continue
        prev_stale = set(sec.get("stale_citations") or [])
        sec["stale_citations"] = sorted(prev_stale | set(hit))
        impacts.append({"section": sk, "file": file, "count": len(hit), "fact_ids": hit})
    warnings = [w for w in state.get("source_citation_warnings", []) if w.get("file") != file]
    warnings.extend(impacts)
    state["source_citation_warnings"] = warnings
    return impacts


def clear_stale_for_file(state, file, full_index):
    """Toggle-on: remove stale markers for facts belonging to this file."""
    excluded_fids = fact_ids_for_file(full_index, file)
    if not excluded_fids:
        return
    for sec in ((state.get("doc") or {}).get("sections") or {}).values():
        stale = sec.get("stale_citations") or []
        if stale:
            sec["stale_citations"] = [f for f in stale if f not in excluded_fids]


def clear_warnings_for_file(state, file):
    state["source_citation_warnings"] = [
        w for w in state.get("source_citation_warnings", [])
        if w.get("file") != file
    ]
