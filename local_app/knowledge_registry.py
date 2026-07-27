"""Registry knowledge packs — vendor-neutral structural profiles.

Schema: registry/knowledge/_knowledge_schema.yaml

Claim boundary: vocabulary and selection structure only — not code certification,
not manufacturer recommendations, not automatic pass/fail.
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
KNOWLEDGE_DIR = ROOT / "registry" / "knowledge"

DISCLAIMER = (
    "Knowledge packs provide structural guidance and vocabulary only. "
    "Feltdok does not substitute applicable standards, project specifications, "
    "or competent material selection. Final choices remain with the user."
)

_GAP_DESCRIPTIONS: dict[str, str] = {
    "missing_exposure_class": "Corrosivity class not set or user-confirmed",
    "missing_material_family": "Material family not selected",
    "galvanic_pair_unreviewed": (
        "Dissimilar metals present but galvanic review not recorded"
    ),
    "chemical_or_splash_exposure_without_note": (
        "Splash or chemical exposure declared without exposure notes"
    ),
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping in {path}")
    return data


def _pack_dir(pack_id: str) -> Path | None:
    for sub in KNOWLEDGE_DIR.iterdir() if KNOWLEDGE_DIR.is_dir() else []:
        if not sub.is_dir():
            continue
        pack_path = sub / "pack.yaml"
        if not pack_path.is_file():
            continue
        meta = _load_yaml(pack_path)
        if meta.get("id") == pack_id or sub.name == pack_id:
            return sub
    return None


@lru_cache(maxsize=16)
def _load_pack_cached(pack_id: str) -> dict[str, Any] | None:
    pack_root = _pack_dir(pack_id)
    if pack_root is None:
        return None
    meta = _load_yaml(pack_root / "pack.yaml")
    fragments: dict[str, Any] = {}
    for name in meta.get("includes") or []:
        frag_path = pack_root / name
        if frag_path.is_file():
            fragments[name] = _load_yaml(frag_path)
    return {
        "id": meta.get("id", pack_id),
        "meta": meta,
        "fragments": fragments,
        "path": str(pack_root.relative_to(ROOT)).replace("\\", "/"),
    }


def reload_knowledge() -> None:
    _load_pack_cached.cache_clear()


def list_packs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not KNOWLEDGE_DIR.is_dir():
        return out
    for sub in sorted(KNOWLEDGE_DIR.iterdir()):
        pack_path = sub / "pack.yaml"
        if not pack_path.is_file():
            continue
        meta = _load_yaml(pack_path)
        out.append({
            "id": meta.get("id", sub.name),
            "title": meta.get("title", sub.name),
            "version": meta.get("version"),
            "status": meta.get("status"),
            "domains": meta.get("domains", []),
        })
    return out


def get_pack(pack_id: str) -> dict[str, Any] | None:
    return _load_pack_cached(pack_id)


def blocking_gaps(pack_id: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return open blocking gaps for a pack given project context facts."""
    pack = get_pack(pack_id)
    if not pack:
        return []
    ctx = context or {}
    fragments = pack.get("fragments") or {}
    checklist = fragments.get("selection_checklist.yaml") or {}
    evidence = fragments.get("evidence.yaml") or {}
    raw_gaps = checklist.get("blocking_gaps") or evidence.get("gaps") or []
    defined: dict[str, str] = {}
    for g in raw_gaps:
        if isinstance(g, str):
            defined[g] = _GAP_DESCRIPTIONS.get(g, g.replace("_", " "))
        elif isinstance(g, dict) and g.get("id"):
            defined[g["id"]] = g.get("description") or _GAP_DESCRIPTIONS.get(
                g["id"], g["id"].replace("_", " ")
            )
    open_ids: list[str] = []

    if pack_id == "corrosion_materials":
        if not ctx.get("corrosivity_class") or not ctx.get("corrosivity_class_confirmed"):
            open_ids.append("missing_exposure_class")
        if not ctx.get("material_family"):
            open_ids.append("missing_material_family")
        if ctx.get("dissimilar_metals") and ctx.get("galvanic_review") not in (
            "reviewed",
            "not_applicable",
        ):
            open_ids.append("galvanic_pair_unreviewed")
        if (ctx.get("splash") or ctx.get("chemical_media")) and not (
            ctx.get("exposure_notes") or ""
        ).strip():
            open_ids.append("chemical_or_splash_exposure_without_note")

    if pack_id == "cable_management_wiring":
        if not ctx.get("tray_classification_complete"):
            open_ids.append("tray_class_missing")
        if not ctx.get("swl_span_basis_documented"):
            open_ids.append("swl_span_missing")
        if not ctx.get("support_spacing_documented"):
            open_ids.append("support_spacing_missing")
        if not ctx.get("external_influences_reviewed"):
            open_ids.append("external_influences_missing")
        if not ctx.get("grouping_or_ccc_referenced"):
            open_ids.append("grouping_or_ccc_missing")
        if not ctx.get("penetration_sealing_recorded"):
            open_ids.append("penetration_seal_missing")
        if ctx.get("metallic_system") and not ctx.get("pe_continuity_noted"):
            open_ids.append("pe_continuity_missing")

    return [
        {
            "id": gid,
            "description": defined.get(gid, gid.replace("_", " ")),
        }
        for gid in open_ids
        if gid in defined
    ]


def render_report_block(pack_id: str, note: dict[str, Any]) -> str:
    """Render CorrosionProtectionNote text from field values."""
    pack = get_pack(pack_id)
    if not pack:
        return ""
    status = note.get("status") or "draft"
    if pack_id == "cable_management_wiring":
        block_type = note.get("type") or note.get("block_type") or "CableSupportSystemNote"
        if block_type == "WiringSystemSelectionNote":
            lines = [f"Wiring system selection ({status})"]
            types_used = note.get("wiring_types_used") or []
            if types_used:
                lines.append(f"  Wiring types: {', '.join(types_used)}")
            ext = note.get("external_influences") or []
            if ext:
                lines.append(f"  External influences: {', '.join(ext)}")
            methods = note.get("installation_methods") or []
            if methods:
                lines.append(f"  Installation methods: {', '.join(methods)}")
            if note.get("ccc_basis"):
                lines.append(f"  CCC basis: {note['ccc_basis']}")
            lines.append(
                "  Voltage drop reviewed: "
                + ("yes" if note.get("voltage_drop_reviewed") else "no")
            )
            lines.append(
                "  Fire sealing reviewed: "
                + ("yes" if note.get("fire_sealing_reviewed") else "no")
            )
            return "\n".join(lines)

        lines = [f"Cable support system ({status})"]
        if note.get("system_type"):
            lines.append(f"  System type: {note['system_type']}")
        if note.get("material_class"):
            lines.append(f"  Material class: {note['material_class']}")
        if note.get("corrosion_link"):
            lines.append(f"  Corrosion link: {note['corrosion_link']}")
        if note.get("swl_span_summary"):
            lines.append(f"  SWL/span: {note['swl_span_summary']}")
        if note.get("support_summary"):
            lines.append(f"  Support summary: {note['support_summary']}")
        return "\n".join(lines)

    lines = [f"Corrosion protection ({status})"]
    env = note.get("environment_class")
    if env:
        suffix = " (user-confirmed)" if note.get("corrosivity_class_confirmed") else ""
        notes = (note.get("exposure_notes") or "").strip()
        line = f"  Environment: {env}{suffix}"
        if notes:
            line += f" — {notes}"
        lines.append(line)
    if note.get("material_family"):
        mat = note["material_family"]
        prot = (note.get("protection_system") or "").strip()
        lines.append(
            f"  Material: {mat}"
            + (f" — {prot}" if prot else " (project choice)")
        )
    ss = note.get("stainless_class")
    if ss:
        lines.append(f"  Stainless class: {ss}")
    gr = note.get("galvanic_review")
    if gr:
        lines.append(f"  Galvanic: {gr}")
    assumptions = note.get("assumptions") or []
    if assumptions:
        lines.append("  Assumptions:")
        for a in assumptions:
            lines.append(f"    - {a}")
    sources = note.get("sources") or []
    if sources:
        lines.append(f"  Sources: [{', '.join(sources)}]")
    if note.get("confirmed_by"):
        lines.append(f"  Confirmed by: {note['confirmed_by']}")
    return "\n".join(lines)
