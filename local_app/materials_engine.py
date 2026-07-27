"""Materials knowledge — Quantity-based catalog (steel MVP + GFRP template).

Schema: registry/materials/_material_schema.yaml
        registry/sections/_section_schema.yaml
        registry/calculations/schema_core.yaml

Claim boundary: documentation groundwork only — no code certification.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("PyYAML required — pip install pyyaml") from e

ROOT = Path(__file__).resolve().parent.parent
MATERIALS_DIR = ROOT / "registry" / "materials"
SECTIONS_DIR = ROOT / "registry" / "sections"

DISCLAIMER = (
    "Material catalog for documentation groundwork only. "
    "Foldok does not claim Eurocode/code compliance or composite approval. "
    "Confirm properties, factors, and design method before formal report use."
)

# Property aliases (GFRP Xt ↔ ft1, etc.)
_PROP_ALIASES = {
    "ft1": "Xt",
    "fc1": "Xc",
    "Xt": "ft1",
    "Xc": "fc1",
}

# Stress/modulus families for Quantity conversion when binding
_UNIT_SCALE: dict[str, tuple[str, float]] = {
    "mpa": ("stress", 1.0),
    "n/mm2": ("stress", 1.0),
    "gpa": ("stress", 1000.0),  # → MPa
    "ksi": ("stress", 6.89476),
    "mm": ("length", 1.0),
    "m": ("length", 1000.0),
    "mm2": ("area", 1.0),
    "m2": ("area", 1e6),
    "mm3": ("smod", 1.0),
    "mm4": ("inertia", 1.0),
    "n": ("force", 1.0),
    "kn": ("force", 1000.0),
    "kg/m3": ("density", 1.0),
    "-": ("ratio", 1.0),
    "": ("ratio", 1.0),
}


def _norm_id(s: str) -> str:
    return (
        str(s or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("×", "x")
        .replace(".", "")
    )


def quantity(
    value: Any = None,
    unit: str | None = None,
    *,
    source: str | None = None,
    status: str | None = None,
    note: str | None = None,
) -> dict:
    """Build a Quantity dict (schema_core)."""
    st = status
    if st is None:
        if value is None:
            st = "missing"
        elif source in ("profile_default",):
            st = "assumed"
        elif source in ("user_entry",):
            st = "user_provided"
        else:
            st = "bound"
    return {
        "value": None if value is None else (
            float(value) if isinstance(value, (int, float)) else value
        ),
        "unit": unit,
        "source": source,
        "status": st,
        "note": note,
    }


def normalize_quantity(raw: Any, default_unit: str | None = None) -> dict:
    if isinstance(raw, dict) and ("value" in raw or "unit" in raw or "status" in raw):
        return quantity(
            raw.get("value"),
            raw.get("unit") or default_unit,
            source=raw.get("source"),
            status=raw.get("status"),
            note=raw.get("note"),
        )
    if isinstance(raw, (int, float)):
        return quantity(raw, default_unit, source="profile_default", status="assumed")
    return quantity(None, default_unit, status="missing")


def convert_quantity_value(value: float, from_unit: str | None, to_unit: str | None) -> float | None:
    if value is None:
        return None
    fu = (from_unit or "").strip().lower().replace("²", "2").replace("³", "3")
    tu = (to_unit or "").strip().lower().replace("²", "2").replace("³", "3")
    if not fu or not tu or fu == tu:
        return float(value)
    if fu not in _UNIT_SCALE or tu not in _UNIT_SCALE:
        return None
    fam_a, sa = _UNIT_SCALE[fu]
    fam_b, sb = _UNIT_SCALE[tu]
    if fam_a != fam_b:
        return None
    return float(value) * sa / sb


def _is_schema_file(path: Path) -> bool:
    name = path.name
    return name.startswith("_") or name.startswith("schema")


def _normalize_props(raw_props: dict | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for pk, pv in (raw_props or {}).items():
        out[str(pk)] = normalize_quantity(pv)
    return out


def _load_material_file(path: Path, data: dict) -> dict | None:
    # Skip pure schema docs
    if "Material:" in data and "id" not in data:
        return None
    if not data.get("id"):
        return None
    row = dict(data)
    row["designation"] = row.get("designation") or row.get("grade")
    row["grade"] = row.get("grade") or row.get("designation")
    row["disclaimer"] = DISCLAIMER
    row["_path"] = str(path.relative_to(ROOT).as_posix())
    row["properties"] = _normalize_props(row.get("properties"))
    # Sync GFRP aliases Xt ↔ ft1 when one is filled
    props = row["properties"]
    if props.get("Xt", {}).get("value") is not None and props.get("ft1", {}).get("value") is None:
        props["ft1"] = dict(props["Xt"])
    if props.get("ft1", {}).get("value") is not None and props.get("Xt", {}).get("value") is None:
        props["Xt"] = dict(props["ft1"])
    return row


def _load_section_file(path: Path, data: dict) -> dict | None:
    if "Section:" in data and "id" not in data:
        return None
    if not data.get("id"):
        return None
    row = dict(data)
    row["disclaimer"] = DISCLAIMER
    row["_path"] = str(path.relative_to(ROOT).as_posix())
    row["properties"] = _normalize_props(row.get("properties"))
    geom = {}
    for pk, pv in (row.get("geometry") or {}).items():
        geom[str(pk)] = normalize_quantity(pv)
    row["geometry"] = geom
    # series convenience from family
    if not row.get("series") and row.get("family"):
        row["series"] = str(row["family"]).upper()
    return row


@lru_cache(maxsize=1)
def _load_catalog() -> tuple[dict[str, dict], dict[str, dict]]:
    materials: dict[str, dict] = {}
    sections: dict[str, dict] = {}

    if MATERIALS_DIR.is_dir():
        for path in sorted(MATERIALS_DIR.rglob("*.yaml")):
            if _is_schema_file(path):
                # gfrp/_template.yaml is a real template — allow if it has id
                if path.name != "_template.yaml":
                    continue
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            # Legacy pack file: materials: [...]
            if isinstance(data.get("materials"), list):
                pack = data.get("pack")
                family = data.get("family")
                for m in data["materials"]:
                    if not isinstance(m, dict):
                        continue
                    m = dict(m)
                    m.setdefault("pack", pack)
                    m.setdefault("family", family)
                    row = _load_material_file(path, m)
                    if row:
                        materials[str(row["id"])] = row
                continue
            row = _load_material_file(path, data)
            if row:
                materials[str(row["id"])] = row
                # also index gfrp_datasheet alias for older tests
                if row["id"] == "gfrp_template":
                    materials["gfrp_datasheet"] = dict(row)
                    materials["gfrp_datasheet"]["id"] = "gfrp_datasheet"

    if SECTIONS_DIR.is_dir():
        for path in sorted(SECTIONS_DIR.rglob("*.yaml")):
            if _is_schema_file(path):
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data.get("sections"), list):
                pack = data.get("pack")
                family = data.get("family")
                for s in data["sections"]:
                    if not isinstance(s, dict):
                        continue
                    s = dict(s)
                    s.setdefault("pack", pack)
                    s.setdefault("family", family)
                    row = _load_section_file(path, s)
                    if row:
                        sections[str(row["id"])] = row
                continue
            row = _load_section_file(path, data)
            if row:
                sections[str(row["id"])] = row

    return materials, sections


def reload() -> None:
    _load_catalog.cache_clear()


def list_materials(
    *,
    family: str | None = None,
    pack: str | None = None,
    include_templates: bool = True,
) -> list[dict]:
    mats, _ = _load_catalog()
    rows = []
    seen = set()
    for mid, m in mats.items():
        # skip alias duplicates in list
        if m.get("id") in seen and mid != m.get("id"):
            continue
        real_id = str(m.get("id") or mid)
        if real_id in seen:
            continue
        seen.add(real_id)
        if family and str(m.get("family") or "").lower() != family.lower():
            continue
        if pack and str(m.get("pack") or "").lower() != pack.lower():
            continue
        if not include_templates and (m.get("template") or m.get("status") == "user_defined" and _props_incomplete(m.get("properties") or {})):
            if m.get("template"):
                continue
        props = m.get("properties") or {}
        rows.append({
            "id": real_id,
            "grade": m.get("grade") or m.get("designation"),
            "designation": m.get("designation") or m.get("grade"),
            "label": m.get("label") or m.get("designation") or real_id,
            "family": m.get("family"),
            "pack": m.get("pack"),
            "status": m.get("status") or "profile",
            "template": bool(m.get("template")),
            "property_keys": list(props.keys()),
            "complete": not _props_incomplete(props),
            "disclaimer": DISCLAIMER,
        })
    return rows


def _props_incomplete(props: dict) -> bool:
    if not props:
        return True
    if "fy" in props:
        return props["fy"].get("value") is None
    if "Xt" in props or "ft1" in props:
        xt = (props.get("Xt") or props.get("ft1") or {}).get("value")
        return xt is None
    # generic: incomplete if every numeric prop is null
    vals = [
        p.get("value") for p in props.values()
        if isinstance(p, dict) and not isinstance(p.get("value"), str)
    ]
    if not vals:
        return False
    return all(v is None for v in vals)


def get_material(material_id: str) -> dict | None:
    mats, _ = _load_catalog()
    key = _norm_id(material_id)
    # direct
    for mid, m in mats.items():
        if _norm_id(mid) == key or _norm_id(m.get("id") or "") == key:
            return dict(m)
    for mid, m in mats.items():
        if _norm_id(m.get("grade") or "") == key:
            return dict(m)
        if _norm_id(m.get("designation") or "") == key:
            return dict(m)
        if key in {_norm_id(x) for x in (m.get("fact_keys") or [])}:
            return dict(m)
    return None


def list_sections(
    *,
    pack: str | None = None,
    series: str | None = None,
    family: str | None = None,
) -> list[dict]:
    _, secs = _load_catalog()
    rows = []
    for sid, s in secs.items():
        if pack and str(s.get("pack") or "").lower() != pack.lower():
            continue
        if series and str(s.get("series") or s.get("family") or "").lower() != series.lower():
            continue
        if family and str(s.get("family") or "").lower() != family.lower():
            continue
        props = s.get("properties") or {}
        rows.append({
            "id": sid,
            "designation": s.get("designation") or sid,
            "family": s.get("family"),
            "series": s.get("series") or (str(s.get("family") or "").upper() or None),
            "pack": s.get("pack"),
            "property_keys": list(props.keys()),
            "disclaimer": DISCLAIMER,
        })
    return rows


def get_section(section_id: str) -> dict | None:
    _, secs = _load_catalog()
    key = _norm_id(section_id)
    if section_id in secs:
        return dict(secs[section_id])
    for sid, s in secs.items():
        if _norm_id(sid) == key:
            return dict(s)
        des = _norm_id(s.get("designation") or "")
        if des == key or des.replace("_", "") == key.replace("_", ""):
            return dict(s)
        # ipe_200 ↔ IPE200
        if _norm_id(sid).replace("_", "") == key.replace("_", ""):
            return dict(s)
    return None


def property_value(material_or_section: dict | None, key: str, *, unit: str | None = None) -> float | None:
    if not material_or_section:
        return None
    props = material_or_section.get("properties") or {}
    keys = [key]
    if key in _PROP_ALIASES:
        keys.append(_PROP_ALIASES[key])
    for k in keys:
        p = props.get(k)
        if not isinstance(p, dict):
            continue
        v = p.get("value")
        if not isinstance(v, (int, float)):
            continue
        if unit:
            converted = convert_quantity_value(float(v), p.get("unit"), unit)
            return converted if converted is not None else float(v)
        return float(v)
    return None


def suggest_material(
    index: list[dict] | None = None,
    state: dict | None = None,
    text: str | None = None,
) -> list[str]:
    blobs: list[str] = []
    if text:
        blobs.append(text.lower())
    for item in index or []:
        if isinstance(item, dict):
            blobs.append(str(item.get("key") or "").lower())
            blobs.append(str(item.get("value") or "").lower())
            for f in item.get("facts") or []:
                if isinstance(f, dict):
                    blobs.append(str(f.get("key") or "").lower())
                    blobs.append(str(f.get("value") or "").lower())
    for uf in (state or {}).get("user_facts") or []:
        blobs.append(
            str(uf).lower()
            if not isinstance(uf, dict)
            else str(uf.get("value") or uf.get("key") or "").lower()
        )
    hay = " ".join(blobs)
    scored: list[tuple[int, str]] = []
    mats, _ = _load_catalog()
    seen = set()
    for mid, m in mats.items():
        real = str(m.get("id") or mid)
        if real in seen:
            continue
        seen.add(real)
        score = 0
        grade = str(m.get("grade") or m.get("designation") or "")
        if grade and grade.lower() in hay:
            score += 5
        for fk in m.get("fact_keys") or []:
            if str(fk).lower() in hay:
                score += 4
        if m.get("family") == "steel" and re.search(r"\bsteel\b|\bstål\b", hay):
            score += 1
        if m.get("family") == "gfrp" and re.search(
            r"\bgfrp\b|\bfrp\b|\bcomposite\b|\bglass\s*fiber\b", hay
        ):
            score += 3
        if score:
            scored.append((score, real))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [mid for _, mid in scored]


def suggest_section(
    index: list[dict] | None = None,
    text: str | None = None,
) -> list[str]:
    blobs = [(text or "").lower()]
    for item in index or []:
        if isinstance(item, dict):
            blobs.append(str(item.get("value") or ""))
            blobs.append(str(item.get("key") or ""))
    hay = " ".join(blobs).lower().replace("×", "x")
    scored: list[tuple[int, str]] = []
    _, secs = _load_catalog()
    for sid, s in secs.items():
        des = str(s.get("designation") or "").lower().replace("×", "x")
        if des and des in hay:
            scored.append((5, sid))
        elif _norm_id(sid).replace("_", "") in hay.replace(" ", "").replace("_", ""):
            scored.append((4, sid))
        elif s.get("family") and str(s["family"]).lower() in hay:
            scored.append((1, sid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    seen, out = set(), []
    for _, sid in scored:
        if sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def apply_property_overrides(
    material: dict,
    overrides: dict[str, Any] | None,
    *,
    source: str = "user_entry",
) -> dict:
    m = dict(material)
    props = {
        k: dict(v) if isinstance(v, dict) else quantity(v)
        for k, v in (m.get("properties") or {}).items()
    }
    for k, v in (overrides or {}).items():
        if isinstance(v, dict):
            cur = normalize_quantity({**props.get(k, {}), **v})
            cur["source"] = v.get("source") or source
            if cur.get("value") is not None and cur.get("status") == "missing":
                cur["status"] = "bound" if source == "datasheet_ref" else "user_provided"
            props[k] = cur
        else:
            props[k] = quantity(v, (props.get(k) or {}).get("unit"), source=source, status="user_provided")
        # sync aliases
        alias = _PROP_ALIASES.get(k)
        if alias and props[k].get("value") is not None:
            props[alias] = dict(props[k])
    m["properties"] = props
    m["overrides_applied"] = True
    if any(p.get("source") == "datasheet_ref" for p in props.values() if isinstance(p, dict)):
        m["status"] = "from_datasheet"
    return m


def resolve_binds(
    profile: dict,
    *,
    material_id: str | None = None,
    section_id: str | None = None,
    material_overrides: dict | None = None,
) -> tuple[dict[str, Any], dict]:
    material = get_material(material_id) if material_id else None
    if material and material_overrides:
        material = apply_property_overrides(material, material_overrides)
    section = get_section(section_id) if section_id else None

    bound: dict[str, Any] = {}
    notes: list[str] = []
    for key, spec in (profile.get("binds") or {}).items():
        if not isinstance(spec, dict):
            continue
        src = str(spec.get("from") or "")
        want_unit = spec.get("unit")
        val = None
        cite = None
        qstatus = "missing"
        if src.startswith("material."):
            pk = src.split(".", 1)[1]
            if not material:
                notes.append(f"Material required for {key} ({src})")
            else:
                val = property_value(material, pk, unit=want_unit)
                q = (material.get("properties") or {}).get(pk) or {}
                if val is None and pk in _PROP_ALIASES:
                    val = property_value(material, _PROP_ALIASES[pk], unit=want_unit)
                    q = (material.get("properties") or {}).get(_PROP_ALIASES[pk]) or {}
                cite = f"material:{material.get('id')}"
                qstatus = q.get("status") or ("assumed" if val is not None else "missing")
                if val is None:
                    notes.append(
                        f"Missing material property {pk}"
                        + (" — fill from datasheet" if material.get("template") else "")
                    )
        elif src.startswith("section."):
            pk = src.split(".", 1)[1]
            if not section:
                notes.append(f"Section required for {key} ({src})")
            else:
                val = property_value(section, pk, unit=want_unit)
                cite = f"section:{section.get('id')}"
                q = (section.get("properties") or {}).get(pk) or {}
                qstatus = q.get("status") or ("bound" if val is not None else "missing")
                if val is None:
                    notes.append(f"Missing section property {pk}")
        if val is not None:
            bound[key] = {
                "value": val,
                "unit": want_unit,
                "source": cite or "catalog",
                "status": qstatus if qstatus != "missing" else "bound",
            }

    binding = {
        "kind": "material_section_binding",
        "disclaimer": DISCLAIMER,
        "code_compliance_claimed": False,
        "material": None,
        "section": None,
        "notes": notes,
    }
    if material:
        binding["material"] = {
            "id": material.get("id"),
            "grade": material.get("grade") or material.get("designation"),
            "designation": material.get("designation") or material.get("grade"),
            "label": material.get("label") or material.get("designation") or material.get("id"),
            "family": material.get("family"),
            "standard_family": material.get("standard_family"),
            "status": material.get("status"),
            "template": bool(material.get("template")),
            "properties": material.get("properties"),
            "design_notes": list(material.get("design_notes") or []),
            "sources": list(material.get("sources") or []),
            "limits": material.get("limits"),
            "complete": not _props_incomplete(material.get("properties") or {}),
        }
        if material.get("family") == "gfrp":
            notes.append("Composite — verify manufacturer design method")
            binding["notes"] = notes
    if section:
        binding["section"] = {
            "id": section.get("id"),
            "designation": section.get("designation"),
            "family": section.get("family"),
            "series": section.get("series"),
            "geometry": section.get("geometry"),
            "properties": section.get("properties"),
            "source": section.get("source"),
            "status": section.get("status"),
        }
    return bound, binding


def render_material_text(binding: dict) -> str:
    lines = []
    mat = binding.get("material") or {}
    sec = binding.get("section") or {}
    if mat:
        lines.append(f"Material: {mat.get('label') or mat.get('designation') or mat.get('id')}")
        if mat.get("standard_family"):
            lines.append(f"  standard_family: {mat['standard_family']}  [label only]")
        for pk, pv in (mat.get("properties") or {}).items():
            if not isinstance(pv, dict):
                continue
            if pk in ("ft1", "fc1") and "Xt" in (mat.get("properties") or {}):
                continue  # skip alias duplicates in text
            val = pv.get("value")
            unit = pv.get("unit") or ""
            src = pv.get("source") or "catalog"
            st = pv.get("status") or ""
            if val is None:
                lines.append(f"  {pk} = (missing)  [{st}]")
            else:
                lines.append(f"  {pk} = {val} {unit}  [{src} / {st}]")
        for n in mat.get("design_notes") or []:
            lines.append(f"  note: {n}")
    if sec:
        lines.append(f"Section: {sec.get('designation') or sec.get('id')}")
        for pk in ("A", "Wy", "Iy", "Iz", "Wz"):
            pv = (sec.get("properties") or {}).get(pk)
            if isinstance(pv, dict) and pv.get("value") is not None:
                lines.append(f"  {pk} = {pv['value']} {pv.get('unit') or ''}")
    for n in binding.get("notes") or []:
        lines.append(f"  ! {n}")
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def material_to_block(binding: dict) -> dict:
    return {
        "type": "material",
        "title": (binding.get("material") or {}).get("label")
        or (binding.get("section") or {}).get("designation")
        or "Material",
        "binding": binding,
        "text": render_material_text(binding),
        "disclaimer": DISCLAIMER,
        "code_compliance_claimed": False,
    }
