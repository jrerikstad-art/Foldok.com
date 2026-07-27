"""Structural evidence profiles — not legal compliance.

Foldok helps build and check a *documentation package* against structural
profiles (evidence kinds + document shapes). It never holds full NEK/ISO/NEC
text and never asserts that a project is legally compliant.

Human (compliance manager / competent person) decides legal conformity.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("PyYAML required — pip install pyyaml") from e

ROOT = Path(__file__).resolve().parent.parent
FRAMEWORKS_DIR = ROOT / "registry" / "frameworks"

# Shown on every compliance API response and UI surface.
DISCLAIMER = (
    "Structural profile only — not a legal compliance determination. "
    "Foldok does not certify NEK, ISO, NEC, CE marking, or any regulation. "
    "You (or your compliance manager) review evidence and sign off."
)

SAFE_STATUS_LABELS = {
    "ready_for_review": "Ready for review",
    "not_ready": "Not ready for export — blocking gaps",
    "in_progress": "Evidence coverage in progress",
    "empty": "No structural profile selected",
}

EVIDENCE_TYPES = (
    "drawing",
    "calculation",
    "test_record",
    "inspection_record",
    "risk_assessment",
    "photo",
    "declaration",
    "procedure",
    "material_certificate",
)

REGIONS = ("eu", "eea", "uk", "no", "us", "ca", "au", "international")
DOMAINS = (
    "electrical", "machinery", "pressure", "construction",
    "process", "marine", "general",
)
OBLIGATION_TYPES = (
    "design", "installation", "inspection", "operation", "maintenance", "handover",
)


def default_compliance() -> dict:
    return {
        "regions": [],
        "domains": [],
        "frameworks": [],          # user-confirmable structural profile ids
        "suggested_frameworks": [],
        "internal_rules": [],      # Phase 4
        "confirmed": False,        # user confirmed applicable set
        "kind": "structural_profiles",
        "disclaimer": DISCLAIMER,
    }


def ensure_compliance(state: dict | None) -> dict:
    state = state or {}
    comp = state.setdefault("compliance", default_compliance())
    for k, v in default_compliance().items():
        comp.setdefault(k, v if not isinstance(v, list) else list(v))
    return comp


@lru_cache(maxsize=1)
def _load_frameworks() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not FRAMEWORKS_DIR.is_dir():
        return out
    for path in sorted(FRAMEWORKS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        fid = data.get("id") or path.stem
        data["id"] = fid
        data["_path"] = str(path.relative_to(ROOT).as_posix())
        if isinstance(data.get("regions"), list):
            data["regions"] = ["no" if x is False else x for x in data["regions"]]
        out[fid] = data
    return out


def reload_frameworks() -> None:
    _load_frameworks.cache_clear()


def list_frameworks(
    region: str | None = None,
    domain: str | None = None,
) -> list[dict]:
    rows = []
    for fid, d in _load_frameworks().items():
        regions = [str(x).lower() for x in (d.get("regions") or [])]
        domains = [str(x).lower() for x in (d.get("domains") or [])]
        if region and region.lower() not in regions and "international" not in regions:
            continue
        if domain and domain.lower() not in domains and "general" not in domains:
            continue
        rows.append({
            "id": fid,
            "label": d.get("label") or fid,
            "kind": "structural_profile",
            "regions": list(d.get("regions") or []),
            "domains": list(d.get("domains") or []),
            "description": (d.get("description") or "").strip(),
            "requirement_count": len(d.get("evidence_requirements") or []),
            "disclaimer": DISCLAIMER,
        })
    return rows


def get_framework(framework_id: str) -> dict | None:
    if not framework_id:
        return None
    all_fw = _load_frameworks()
    key = str(framework_id).strip().lower().replace(" ", "_").replace("-", "_")
    raw = None
    if key in all_fw:
        raw = dict(all_fw[key])
    else:
        for fid, d in all_fw.items():
            if fid.replace("-", "_") == key:
                raw = dict(d)
                break
    if not raw:
        return None
    raw["kind"] = "structural_profile"
    raw["disclaimer"] = DISCLAIMER
    return raw


def suggest_frameworks(regions: list[str] | None, domains: list[str] | None) -> list[str]:
    """Suggest structural profile ids from region/domain tags (not legal truth)."""
    regs = {str(r).lower() for r in (regions or []) if r}
    doms = {str(d).lower() for d in (domains or []) if d}
    scored: list[tuple[int, str]] = []
    for fid, d in _load_frameworks().items():
        fr = {str(x).lower() for x in (d.get("regions") or [])}
        fd = {str(x).lower() for x in (d.get("domains") or [])}
        score = 0
        if regs and (regs & fr):
            score += 2
        if doms and (doms & fd):
            score += 2
        if not regs and not doms:
            continue
        if score:
            scored.append((score, fid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [fid for _, fid in scored]


def _index_fact_keys(index: list[dict] | None) -> set[str]:
    keys: set[str] = set()
    for f in index or []:
        if not isinstance(f, dict):
            continue
        for k in (f.get("key"), f.get("fact_key"), f.get("id")):
            if k:
                keys.add(str(k).lower())
        ft = f.get("fact_type")
        if ft:
            keys.add(str(ft).lower())
    return keys


def _media_roles(index: list[dict] | None, media: list[dict] | None) -> set[str]:
    roles: set[str] = set()
    for m in media or []:
        if isinstance(m, dict):
            for k in (m.get("role"), m.get("preferred_role"), m.get("kind")):
                if k:
                    roles.add(str(k).lower())
    for f in index or []:
        if not isinstance(f, dict):
            continue
        if str(f.get("kind") or "").lower() in ("photo", "image", "drawing"):
            roles.add(str(f.get("kind")).lower())
        for r in f.get("roles") or []:
            roles.add(str(r).lower())
    return roles


def _section_keys(state: dict | None, template: dict | None) -> set[str]:
    keys: set[str] = set()
    doc = (state or {}).get("doc") or {}
    sections = doc.get("sections") or {}
    if isinstance(sections, dict):
        for sk, sec in sections.items():
            if not sk:
                continue
            md = ""
            if isinstance(sec, dict):
                md = sec.get("md") or ""
            # count as present if non-empty content
            if md and md.strip() and "MANGLER" not in md[:80]:
                keys.add(str(sk).lower())
            else:
                # still register key if section shell exists with any body
                if md and md.strip():
                    keys.add(str(sk).lower())
    for s in (template or {}).get("sections") or []:
        if isinstance(s, dict) and s.get("section_key"):
            # template alone does not satisfy — only filled sections do
            pass
    return keys


def _requirement_satisfied(
    req: dict,
    *,
    fact_keys: set[str],
    media_roles: set[str],
    section_keys: set[str],
    user_confirmed: set[str],
) -> tuple[bool, str]:
    rid = str(req.get("id") or "")
    if rid and rid in user_confirmed:
        return True, "user_confirmed"
    sat = req.get("satisfied_by") or {}
    for k in sat.get("fact_keys") or []:
        if str(k).lower() in fact_keys:
            return True, f"fact:{k}"
    for s in sat.get("document_sections") or []:
        if str(s).lower() in section_keys:
            return True, f"section:{s}"
    for r in sat.get("media_roles") or []:
        if str(r).lower() in media_roles:
            return True, f"media:{r}"
    return False, ""


def evidence_gaps(
    *,
    framework_ids: list[str],
    index: list[dict] | None = None,
    media: list[dict] | None = None,
    state: dict | None = None,
    template: dict | None = None,
    user_confirmed_requirements: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic *evidence* gaps for selected structural profiles.

    Never asserts legal compliance. Output is missing evidence kinds only:
      type=evidence, evidence_type, framework_ref, severity, description
    """
    fact_keys = _index_fact_keys(index)
    # also fold user_facts
    for uf in (state or {}).get("user_facts") or []:
        if isinstance(uf, dict) and uf.get("key"):
            fact_keys.add(str(uf["key"]).lower())
        elif isinstance(uf, str):
            fact_keys.add(uf.lower())
    media_roles = _media_roles(index, media)
    section_keys = _section_keys(state, template)
    confirmed = {str(x) for x in (user_confirmed_requirements or [])}

    gaps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fid in framework_ids or []:
        fw = get_framework(fid)
        if not fw:
            continue
        for req in fw.get("evidence_requirements") or []:
            ok, how = _requirement_satisfied(
                req,
                fact_keys=fact_keys,
                media_roles=media_roles,
                section_keys=section_keys,
                user_confirmed=confirmed,
            )
            if ok:
                continue
            gid = f"ev:{fid}:{req.get('id')}"
            if gid in seen:
                continue
            seen.add(gid)
            gaps.append({
                "id": gid,
                "type": "evidence",
                "key": req.get("id"),
                "evidence_type": req.get("evidence_type"),
                "framework_ref": req.get("framework_ref") or fid,
                "clause_family": req.get("clause_family"),
                "framework_id": fid,
                "severity": req.get("severity") or "warning",
                "description": req.get("description") or req.get("id"),
                "status": "open",
                # Explicit: this is a package gap, not a legal finding
                "legal_claim": False,
            })
    severity_rank = {"blocking": 0, "warning": 1, "info": 2}
    gaps.sort(key=lambda g: (severity_rank.get(g.get("severity"), 9), g.get("id") or ""))
    return gaps


def package_status(
    *,
    framework_ids: list[str],
    index: list[dict] | None = None,
    media: list[dict] | None = None,
    state: dict | None = None,
    template: dict | None = None,
    user_confirmed_requirements: list[str] | None = None,
) -> dict[str, Any]:
    """Evidence coverage for selected structural profiles — never 'compliant'.

    Returns coverage %, missing evidence labels, and a review-oriented status.
    """
    gaps = evidence_gaps(
        framework_ids=framework_ids,
        index=index,
        media=media,
        state=state,
        template=template,
        user_confirmed_requirements=user_confirmed_requirements,
    )
    total = 0
    for fid in framework_ids or []:
        fw = get_framework(fid)
        if fw:
            total += len(fw.get("evidence_requirements") or [])
    open_n = len(gaps)
    covered = max(0, total - open_n)
    pct = int(round(100.0 * covered / total)) if total else 0
    blocking = [g for g in gaps if g.get("severity") == "blocking"]
    missing = [g.get("description") or g.get("key") for g in gaps]

    if not framework_ids:
        status = "empty"
    elif blocking:
        status = "not_ready"
    elif open_n:
        status = "in_progress"
    else:
        status = "ready_for_review"

    return {
        "kind": "structural_profile_coverage",
        "disclaimer": DISCLAIMER,
        "legal_compliance_claimed": False,
        "framework_ids": list(framework_ids or []),
        "requirements_total": total,
        "requirements_covered": covered,
        "coverage_percent": pct,
        "gaps_open": open_n,
        "blocking_gaps": len(blocking),
        "missing": missing,
        "gaps": gaps,
        "status": status,
        "status_label": SAFE_STATUS_LABELS[status],
        # Forbidden phrases must never appear as product conclusions:
        "forbidden_claims": [
            "NEK compliant", "ISO satisfied", "CE OK", "legally compliant",
            "approved by the standard",
        ],
    }


def project_package_status(state: dict, index: list[dict] | None = None) -> dict:
    comp = ensure_compliance(state)
    frameworks = list(comp.get("frameworks") or [])
    if not frameworks:
        frameworks = list(comp.get("suggested_frameworks") or [])
    if not frameworks:
        frameworks = suggest_frameworks(comp.get("regions"), comp.get("domains"))
        comp["suggested_frameworks"] = frameworks
    return package_status(
        framework_ids=frameworks,
        index=index,
        state=state,
        user_confirmed_requirements=comp.get("confirmed_requirements") or [],
    )


def project_evidence_gaps(state: dict, index: list[dict] | None = None) -> list[dict]:
    """Read project.compliance frameworks (confirmed or suggested) and emit gaps."""
    return project_package_status(state, index).get("gaps") or []

