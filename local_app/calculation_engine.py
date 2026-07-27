"""Calculation Engine — curated formulas, project facts, user confirm.

Same claim boundary as structural profiles:
  Engine prepares data and formulas.
  Auto-fills only when inputs are obvious and sourced.
  User confirms before a calculation enters the formal report.

HARD: LLM never invents numeric engineering results. It may only suggest
which library profile fits and map text → input keys. Arithmetic is code.
"""
from __future__ import annotations

import ast
import math
import re
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("PyYAML required — pip install pyyaml") from e

ROOT = Path(__file__).resolve().parent.parent
CALCULATIONS_DIR = ROOT / "registry" / "calculations"

DISCLAIMER = (
    "Library formula only — not a certified design calculation. "
    "Foldok does not replace engineering judgment or code checks. "
    "Confirm inputs and assumptions before use in a formal report."
)

STATUSES = ("draft", "needs_input", "ready_for_review", "confirmed")

STATUS_LABELS = {
    "draft": "Draft",
    "needs_input": "Needs input or verification",
    "ready_for_review": "Ready for review",
    "confirmed": "Confirmed for report",
}

# Unit families: convert to canonical base, then to target.
_UNIT_TO_BASE: dict[str, tuple[str, float]] = {
    "m": ("length", 1.0),
    "mm": ("length", 0.001),
    "cm": ("length", 0.01),
    "km": ("length", 1000.0),
    "m/s": ("speed", 1.0),
    "km/h": ("speed", 1.0 / 3.6),
    "mph": ("speed", 0.44704),
    "pa": ("pressure", 1.0),
    "kpa": ("pressure", 1000.0),
    "mpa": ("pressure", 1_000_000.0),
    "n": ("force", 1.0),
    "kn": ("force", 1000.0),
    "v": ("voltage", 1.0),
    "a": ("current", 1.0),
    "ohm": ("resistance", 1.0),
    "Ω": ("resistance", 1.0),
    "w": ("power", 1.0),
    "kw": ("power", 1000.0),
    "m2": ("area", 1.0),
    "m²": ("area", 1.0),
    "mm2": ("area", 1e-6),
    "mm3": ("smod", 1e-9),
    "mm4": ("inertia", 1e-12),
    "m3": ("volume", 1.0),
    "m³": ("volume", 1.0),
    "gpa": ("pressure", 1_000_000_000.0),
    "knm": ("moment", 1000.0),
    "nm": ("moment", 1.0),
    "percent": ("ratio", 1.0),
    "%": ("ratio", 1.0),
    "-": ("ratio", 1.0),
    "": ("ratio", 1.0),
}

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)
_ALLOWED_FUNCS = {"sqrt": math.sqrt, "abs": abs}
_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@lru_cache(maxsize=1)
def _load_profiles() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not CALCULATIONS_DIR.is_dir():
        return out
    for path in sorted(CALCULATIONS_DIR.rglob("*.yaml")):
        name = path.name
        if name.startswith("_") or name.startswith("schema"):
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict) or not data.get("id"):
            continue
        # Skip pure schema docs
        if "Calculation:" in data and "formula_code" not in data:
            continue
        pid = str(data.get("id") or path.stem).strip()
        data["id"] = pid
        data["profile"] = data.get("profile") or pid
        data["label"] = data.get("label") or data.get("name") or pid
        data["_path"] = str(path.relative_to(ROOT).as_posix())
        # Normalize inputs: support quantity: {} shape
        norms = []
        for inp in data.get("inputs") or []:
            if not isinstance(inp, dict):
                continue
            row = dict(inp)
            q = row.get("quantity") if isinstance(row.get("quantity"), dict) else {}
            if q:
                row.setdefault("unit", q.get("unit"))
                if row.get("default") is None and q.get("value") is not None:
                    row["default"] = q.get("value")
            norms.append(row)
        data["inputs"] = norms
        out[pid] = data
        for alias in data.get("aliases") or []:
            a = str(alias).strip()
            if a and a not in out:
                out[a] = data
    return out


def reload_profiles() -> None:
    _load_profiles.cache_clear()


def list_profiles(domain: str | None = None) -> list[dict]:
    rows = []
    for pid, d in _load_profiles().items():
        domains = [str(x).lower() for x in (d.get("domains") or [])]
        if domain and domain.lower() not in domains and "general" not in domains:
            continue
        rows.append({
            "id": pid,
            "label": d.get("label") or pid,
            "domains": list(d.get("domains") or []),
            "formula_latex": d.get("formula_latex") or "",
            "description": (d.get("description") or "").strip(),
            "safety_critical": bool(d.get("safety_critical")),
            "input_keys": [i.get("key") for i in (d.get("inputs") or [])],
            "output_keys": [o.get("key") for o in (d.get("outputs") or [])],
            "disclaimer": DISCLAIMER,
        })
    return rows


def get_profile(profile_id: str) -> dict | None:
    if not profile_id:
        return None
    key = str(profile_id).strip().lower().replace("-", "_").replace(" ", "_")
    all_p = _load_profiles()
    if key in all_p:
        raw = dict(all_p[key])
        raw["disclaimer"] = DISCLAIMER
        return raw
    for pid, d in all_p.items():
        if pid.replace("-", "_") == key:
            raw = dict(d)
            raw["disclaimer"] = DISCLAIMER
            return raw
    return None


def suggest_profiles(
    domains: list[str] | None = None,
    intent: str | None = None,
) -> list[str]:
    """Suggest profile ids from domains / free-text intent (no LLM required)."""
    doms = {str(d).lower() for d in (domains or []) if d}
    text = (intent or "").lower()
    scored: list[tuple[int, str]] = []
    keywords = {
        "rect_area": ("area", "rectangle", "flate", "areal"),
        "circle_area": ("circle", "radius", "sirkel"),
        "volume_rect": ("volume", "volum", "box"),
        "cable_length_simple": ("cable", "kabel", "slack", "route"),
        "ohms_law": ("ohm", "resistance", "voltage", "current", "motstand"),
        "power_dc": ("power", "watt", "effekt", "dc"),
        "wind_dynamic_pressure": ("wind", "vind", "pressure", "q =", "0.613"),
        "utilization": ("utilization", "utnyttelse", "capacity", "f_ed", "f_rd"),
        "steel_axial_tension": ("tension", "axial", "steel", "nrd", "ned", "strekk"),
        "steel_axial_tension_simple": ("tension", "axial", "steel", "nrd", "ned", "strekk"),
        "steel_bending_simple": ("bending", "moment", "steel", "mrd", "med", "bøying"),
        "gfrp_tension_simple": ("gfrp", "frp", "composite", "glass fiber"),
        "gfrp_axial_tension_simple": ("gfrp", "frp", "composite", "glass fiber", "xt"),
    }
    for pid, d in _load_profiles().items():
        score = 0
        pd = {str(x).lower() for x in (d.get("domains") or [])}
        if doms and (doms & pd or "general" in pd):
            score += 2
        for kw in keywords.get(pid, ()):
            if kw in text:
                score += 3
        label = (d.get("label") or "").lower()
        if text and any(w in label for w in text.split() if len(w) > 3):
            score += 1
        if score:
            scored.append((score, pid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [pid for _, pid in scored]


# ── Safe expression evaluation ───────────────────────────────────────

class FormulaError(ValueError):
    pass


def _validate_ast(node: ast.AST) -> None:
    if isinstance(node, ast.Expression):
        _validate_ast(node.body)
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return
    if isinstance(node, ast.Name):
        return
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        _validate_ast(node.left)
        _validate_ast(node.right)
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
        _validate_ast(node.operand)
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise FormulaError(f"Function not allowed: {ast.dump(node)}")
        for a in node.args:
            _validate_ast(a)
        if node.keywords:
            raise FormulaError("Keyword args not allowed")
        return
    raise FormulaError(f"Expression not allowed: {type(node).__name__}")


def evaluate_formula(formula_code: str, variables: dict[str, float]) -> float:
    """Evaluate a curated formula_code with bound numeric variables only.

    Supports a single expression, or multi-statement form:
      N_rd = A * fy / 1000; U = N_ed / N_rd
    Returns the value of the last statement (assignment RHS or expression).
    """
    expr = (formula_code or "").strip()
    if not expr:
        raise FormulaError("Empty formula")
    env: dict[str, float] = {k: float(v) for k, v in variables.items()}
    parts = [p.strip() for p in expr.split(";") if p.strip()]
    last = 0.0
    for part in parts:
        if "=" in part and not part.strip().startswith(("=", "==")):
            # assignment: name = expression (single = only)
            left, right = part.split("=", 1)
            name = left.strip()
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                raise FormulaError(f"Invalid assignment target: {name}")
            # reject comparison operators leftover
            if right.strip().startswith("="):
                raise FormulaError("Invalid formula")
            val = _eval_expr(right.strip(), env)
            env[name] = val
            last = val
        else:
            last = _eval_expr(part, env)
    return float(last)


def evaluate_formula_program(
    formula_code: str, variables: dict[str, float]
) -> dict[str, float]:
    """Like evaluate_formula but returns all assigned names + last result as _result."""
    expr = (formula_code or "").strip()
    env: dict[str, float] = {k: float(v) for k, v in variables.items()}
    assigned: dict[str, float] = {}
    if not expr:
        raise FormulaError("Empty formula")
    parts = [p.strip() for p in expr.split(";") if p.strip()]
    last = 0.0
    for part in parts:
        if "=" in part and not part.strip().startswith(("=", "==")):
            left, right = part.split("=", 1)
            name = left.strip()
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                raise FormulaError(f"Invalid assignment target: {name}")
            val = _eval_expr(right.strip(), env)
            env[name] = val
            assigned[name] = val
            last = val
        else:
            last = _eval_expr(part, env)
    assigned["_result"] = last
    return assigned


def _eval_expr(expr: str, variables: dict[str, float]) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Invalid formula syntax: {e}") from e
    _validate_ast(tree)
    env: dict[str, Any] = {**_ALLOWED_CONSTS, **_ALLOWED_FUNCS}
    for k, v in variables.items():
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", k):
            raise FormulaError(f"Invalid variable name: {k}")
        env[k] = float(v)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in env:
            raise FormulaError(f"Unbound variable: {node.id}")
    try:
        return float(eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, env))
    except ZeroDivisionError as e:
        raise FormulaError("Division by zero") from e
    except Exception as e:
        raise FormulaError(str(e)) from e


def convert_unit(value: float, from_unit: str | None, to_unit: str | None) -> float | None:
    """Convert when units share a family; None if unknown / incompatible."""
    if value is None:
        return None
    fu = (from_unit or "").strip().lower()
    tu = (to_unit or "").strip().lower()
    if not fu or not tu or fu == tu:
        return float(value)
    if fu not in _UNIT_TO_BASE or tu not in _UNIT_TO_BASE:
        return None
    fam_a, scale_a = _UNIT_TO_BASE[fu]
    fam_b, scale_b = _UNIT_TO_BASE[tu]
    if fam_a != fam_b:
        return None
    base = float(value) * scale_a
    return base / scale_b


# ── Fact binding ─────────────────────────────────────────────────────

def _iter_facts(index: list[dict] | None, state: dict | None) -> list[dict]:
    rows: list[dict] = []
    for item in index or []:
        if not isinstance(item, dict):
            continue
        # flat fact
        if item.get("key") and ("value" in item or "val" in item):
            rows.append(item)
            continue
        # nested facts list
        for f in item.get("facts") or []:
            if isinstance(f, dict) and f.get("key"):
                merged = dict(f)
                if not merged.get("source") and item.get("file"):
                    merged["source"] = item.get("file")
                rows.append(merged)
    for uf in (state or {}).get("user_facts") or []:
        if isinstance(uf, dict) and uf.get("key"):
            rows.append(uf)
        elif isinstance(uf, str):
            rows.append({"key": uf, "value": None})
    return rows


def _parse_number(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().replace(",", ".")
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def _guess_unit(raw: Any, fallback: str | None = None) -> str | None:
    if isinstance(raw, dict) and raw.get("unit"):
        return str(raw["unit"])
    s = str(raw if not isinstance(raw, dict) else raw.get("value") or "")
    for u in ("km/h", "m/s", "mm", "cm", "km", "kPa", "MPa", "Pa", "kN", "m2", "m3", "ohm", "Ω", "kW", "%"):
        if re.search(rf"\b{re.escape(u)}\b", s, re.I):
            return u
    return fallback


def bind_inputs_from_facts(
    profile: dict,
    index: list[dict] | None = None,
    state: dict | None = None,
) -> list[dict]:
    """Map profile inputs → facts. Marks conflicting values as ambiguous."""
    facts = _iter_facts(index, state)
    by_key: dict[str, list[dict]] = {}
    for f in facts:
        k = str(f.get("key") or "").strip().lower()
        if k:
            by_key.setdefault(k, []).append(f)

    bound: list[dict] = []
    for spec in profile.get("inputs") or []:
        key = spec["key"]
        want_unit = spec.get("unit")
        aliases = [str(a).lower() for a in (spec.get("fact_keys") or [])] + [key.lower()]
        candidates: list[tuple[float, str | None, str | None, str]] = []
        for alias in aliases:
            for f in by_key.get(alias, []):
                val = _parse_number(f.get("value") if "value" in f else f.get("val"))
                if val is None:
                    continue
                src_unit = f.get("unit") or _guess_unit(f.get("value"), want_unit)
                converted = convert_unit(val, src_unit, want_unit)
                if converted is None and src_unit and want_unit and src_unit.lower() != str(want_unit).lower():
                    # keep original but flag unit issue later
                    converted = val
                    unit_ok = False
                else:
                    unit_ok = True
                    if converted is None:
                        converted = val
                cite = f.get("source") or f.get("citation") or f.get("file") or f.get("fact_id")
                candidates.append((
                    float(converted),
                    str(cite) if cite else None,
                    str(f.get("id") or f.get("fact_id") or ""),
                    "ok" if unit_ok else "unit_unclear",
                ))

        entry: dict[str, Any] = {
            "key": key,
            "label": spec.get("label") or key,
            "unit": want_unit,
            "value": None,
            "source": None,
            "fact_id": None,
            "status": "missing",
            "notes": [],
        }

        if not candidates and spec.get("default") is not None:
            entry["value"] = float(spec["default"])
            entry["source"] = "profile_default"
            entry["status"] = "bound"
            entry["notes"].append("Using profile default — verify before confirm")
        elif not candidates:
            entry["status"] = "missing"
        else:
            values = {round(c[0], 9) for c in candidates}
            if len(values) > 1:
                entry["status"] = "ambiguous"
                entry["notes"].append(
                    f"Conflicting values in sources: {sorted(values)}"
                )
                entry["candidates"] = [
                    {"value": c[0], "source": c[1], "fact_id": c[2]} for c in candidates
                ]
            else:
                v, cite, fid, flag = candidates[0]
                entry["value"] = v
                entry["source"] = cite or "index"
                entry["fact_id"] = fid or None
                entry["status"] = "bound"
                if flag == "unit_unclear":
                    entry["status"] = "ambiguous"
                    entry["notes"].append("Unit unclear or not convertible — verify")
        bound.append(entry)
    return bound


# ── Calculation lifecycle ────────────────────────────────────────────

def _empty_outputs(profile: dict) -> list[dict]:
    return [
        {
            "key": o.get("key"),
            "label": o.get("label") or o.get("key"),
            "unit": (o.get("quantity") or {}).get("unit") if isinstance(o.get("quantity"), dict) else o.get("unit"),
            "value": None,
            "source": None,
            "status": "missing",
        }
        for o in (profile.get("outputs") or [])
    ]


def _apply_input_override(inputs: list[dict], ui_key: str, ui_val: Any, *, prefer_bound: bool = False) -> None:
    # Allow NEd → N_ed style aliases
    aliases = {ui_key, ui_key.replace("Ed", "_ed").replace("Rd", "_rd")}
    if ui_key == "NEd":
        aliases.add("N_ed")
    if ui_key == "MEd":
        aliases.add("M_ed")
    if ui_key == "N_ed":
        aliases.add("NEd")
    if ui_key == "M_ed":
        aliases.add("MEd")
    for inp in inputs:
        if inp["key"] not in aliases:
            continue
        if prefer_bound and inp.get("status") == "user_provided" and inp.get("value") is not None:
            return
        if isinstance(ui_val, dict):
            num = _parse_number(ui_val.get("value"))
            if num is not None:
                inp["value"] = num
            if ui_val.get("unit"):
                inp["unit"] = ui_val["unit"]
            inp["source"] = ui_val.get("source") or "user_entry"
            if ui_val.get("status"):
                inp["status"] = ui_val["status"]
            else:
                src = str(inp["source"])
                if src.startswith(("material:", "section:", "catalog")):
                    inp["status"] = "bound" if "profile_default" not in src else "assumed"
                elif src == "profile_default":
                    inp["status"] = "assumed"
                else:
                    inp["status"] = "user_provided"
        else:
            num = _parse_number(ui_val)
            if num is not None:
                inp["value"] = num
            inp["source"] = "user_entry"
            inp["status"] = "user_provided"
        inp.pop("candidates", None)
        inp["notes"] = [n for n in inp.get("notes") or [] if "Conflicting" not in n]
        return


def create_calculation(
    profile_id: str,
    *,
    index: list[dict] | None = None,
    state: dict | None = None,
    name: str | None = None,
    user_inputs: dict[str, Any] | None = None,
    material_id: str | None = None,
    section_id: str | None = None,
    material_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Propose a calculation: bind facts (+ optional material/section), evaluate, set status."""
    profile = get_profile(profile_id)
    if not profile:
        raise ValueError(f"Unknown calculation profile: {profile_id}")

    inputs = bind_inputs_from_facts(profile, index, state)
    binding = None
    if material_id or section_id or profile.get("binds"):
        try:
            import materials_engine as meng
        except ImportError:
            meng = None
        if meng is not None:
            bound, binding = meng.resolve_binds(
                profile,
                material_id=material_id,
                section_id=section_id,
                material_overrides=material_overrides,
            )
            for k, v in bound.items():
                _apply_input_override(inputs, k, v, prefer_bound=True)

    for ui_key, ui_val in (user_inputs or {}).items():
        _apply_input_override(inputs, ui_key, ui_val)

    assumptions = list(profile.get("assumptions") or [])
    if binding and binding.get("material"):
        assumptions.extend(binding["material"].get("design_notes") or [])

    calc: dict[str, Any] = {
        "id": f"calc_{uuid.uuid4().hex[:10]}",
        "name": name or profile.get("label") or profile_id,
        "profile": profile_id,
        "formula_latex": profile.get("formula_latex") or "",
        "formula_code": profile.get("formula_code") or "",
        "inputs": inputs,
        "outputs": _empty_outputs(profile),
        "status": "draft",
        "status_label": STATUS_LABELS["draft"],
        "assumptions": assumptions,
        "safety_critical": bool(profile.get("safety_critical")),
        "material_id": material_id,
        "section_id": section_id,
        "binding": binding,
        "confirmed_by": None,
        "confirmed_at": None,
        "revision": 1,
        "disclaimer": DISCLAIMER,
        "legal_compliance_claimed": False,
        "code_compliance_claimed": False,
        "certified_result": False,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "messages": [],
    }
    return refresh_calculation(calc)


def set_input(
    calc: dict,
    key: str,
    value: Any,
    *,
    unit: str | None = None,
    source: str = "user_entry",
) -> dict:
    """User supplies or overrides an input; unlocks confirmed → draft."""
    calc = dict(calc)
    calc["inputs"] = [dict(i) for i in (calc.get("inputs") or [])]
    found = False
    for inp in calc["inputs"]:
        if inp.get("key") == key:
            num = _parse_number(value)
            if num is None:
                inp["value"] = None
                inp["status"] = "missing"
            else:
                inp["value"] = num
                inp["status"] = "user_provided"
                inp["source"] = source
            if unit:
                inp["unit"] = unit
            inp.pop("candidates", None)
            found = True
            break
    if not found:
        raise ValueError(f"Unknown input key: {key}")
    if calc.get("status") == "confirmed":
        calc["confirmed_by"] = None
        calc["confirmed_at"] = None
        calc["revision"] = int(calc.get("revision") or 1) + 1
    calc["updated_at"] = _now_iso()
    return refresh_calculation(calc)


def refresh_calculation(calc: dict) -> dict:
    """Recompute status + outputs from current inputs."""
    calc = dict(calc)
    profile = get_profile(calc.get("profile") or "")
    inputs = list(calc.get("inputs") or [])
    missing = [i for i in inputs if i.get("value") is None or i.get("status") == "missing"]
    ambiguous = [i for i in inputs if i.get("status") == "ambiguous"]
    messages: list[str] = []

    if calc.get("binding") and calc["binding"].get("notes"):
        messages.extend(calc["binding"]["notes"])

    if missing or ambiguous:
        calc["status"] = "needs_input"
        calc["outputs"] = _empty_outputs(profile) if profile else list(calc.get("outputs") or [])
        for i in missing:
            messages.append(f"Missing input: {i.get('label') or i.get('key')}")
        for i in ambiguous:
            messages.append(f"Verify input: {i.get('label') or i.get('key')}")
            messages.extend(i.get("notes") or [])
    else:
        variables = {i["key"]: float(i["value"]) for i in inputs}
        outs = _empty_outputs(profile) if profile else list(calc.get("outputs") or [])
        try:
            assigned = evaluate_formula_program(calc.get("formula_code") or "", variables)
            # Map assigned names onto declared outputs
            for o in outs:
                key = o.get("key")
                if key in assigned:
                    o["value"] = _round_eng(assigned[key])
                    o["source"] = "formula"
                    o["status"] = "bound"
                elif key and key.replace("Rd", "_rd").replace("Ed", "_ed") in assigned:
                    alt = key.replace("Rd", "_rd").replace("Ed", "_ed")
                    o["value"] = _round_eng(assigned[alt])
                    o["source"] = "formula"
                    o["status"] = "bound"
            # Fallback: if no outputs got values, use last result on first out
            if outs and all(o.get("value") is None for o in outs):
                outs[0]["value"] = _round_eng(assigned.get("_result", 0.0))
                outs[0]["source"] = "formula"
                outs[0]["status"] = "bound"

            # Extra per-output formula_code (legacy)
            if profile:
                env = dict(variables)
                env.update({k: v for k, v in assigned.items() if k != "_result"})
                for odef in profile.get("outputs") or []:
                    fcode = odef.get("formula_code")
                    if not fcode:
                        continue
                    val = evaluate_formula(fcode, env)
                    env[odef["key"]] = val
                    for o in outs:
                        if o["key"] == odef["key"]:
                            o["value"] = _round_eng(val)
                            o["source"] = "formula"
                            o["status"] = "bound"
                            break
            calc["outputs"] = outs
            if calc.get("status") == "confirmed" and calc.get("confirmed_at"):
                pass
            else:
                calc["status"] = "ready_for_review"
            if calc.get("safety_critical"):
                messages.append(
                    "Safety-critical profile — confirm assumptions before formal use"
                )
            for i in inputs:
                if i.get("source") == "profile_default" or i.get("status") == "assumed":
                    messages.append(
                        f"Confirm assumed input: {i.get('label') or i.get('key')}"
                    )
        except FormulaError as e:
            calc["status"] = "needs_input"
            calc["outputs"] = _empty_outputs(profile) if profile else list(calc.get("outputs") or [])
            messages.append(f"Formula error: {e}")

    # Preserve confirmed if still valid
    if calc.get("confirmed_at") and calc.get("status") != "needs_input":
        if not missing and not ambiguous:
            calc["status"] = "confirmed"

    calc["status_label"] = STATUS_LABELS.get(calc["status"], calc["status"])
    calc["messages"] = messages
    calc["disclaimer"] = DISCLAIMER
    calc["legal_compliance_claimed"] = False
    calc["code_compliance_claimed"] = False
    calc["certified_result"] = False
    calc["updated_at"] = _now_iso()
    return calc


def _round_eng(x: float) -> float:
    if abs(x) >= 100 or x == 0:
        return round(x, 3)
    if abs(x) >= 1:
        return round(x, 4)
    return round(x, 6)


def confirm_calculation(
    calc: dict,
    *,
    confirmed_by: str = "user",
) -> dict:
    """Lock calculation for report insert. Requires ready_for_review (or reconfirm)."""
    calc = refresh_calculation(dict(calc))
    if calc["status"] == "needs_input":
        raise ValueError("Cannot confirm — missing or ambiguous inputs")
    if not calc.get("outputs") or calc["outputs"][0].get("value") is None:
        raise ValueError("Cannot confirm — no result")
    calc["status"] = "confirmed"
    calc["status_label"] = STATUS_LABELS["confirmed"]
    calc["confirmed_by"] = confirmed_by
    calc["confirmed_at"] = _now_iso()
    calc["updated_at"] = calc["confirmed_at"]
    return calc


def render_calculation_text(calc: dict) -> str:
    """Plain-text report groundwork block."""
    lines = [
        f"Calculation: {calc.get('name') or calc.get('profile')}",
        f"  Profile: {calc.get('profile')}  ·  Status: {calc.get('status_label')}",
        f"  Formula: {calc.get('formula_latex') or calc.get('formula_code')}",
        "",
    ]
    binding = calc.get("binding") or {}
    mat = binding.get("material") or {}
    sec = binding.get("section") or {}
    if mat:
        lines.append(f"Material: {mat.get('label') or mat.get('grade') or mat.get('id')}")
        fy = (mat.get("properties") or {}).get("fy") or (mat.get("properties") or {}).get("ft1")
        if isinstance(fy, dict) and fy.get("value") is not None:
            pk = "fy" if "fy" in (mat.get("properties") or {}) else "ft1"
            lines.append(
                f"  {pk} = {fy['value']} {fy.get('unit') or ''}  "
                f"[catalog / user-confirmed]"
            )
    if sec:
        lines.append(f"Section: {sec.get('designation') or sec.get('id')}")
    if mat or sec:
        lines.append("")
    for inp in calc.get("inputs") or []:
        val = inp.get("value")
        unit = inp.get("unit") or ""
        src = inp.get("source") or "—"
        st = inp.get("status") or ""
        vstr = f"{val} {unit}".strip() if val is not None else f"(missing) [{st}]"
        lines.append(f"  {inp.get('key')} = {vstr}    [Source: {src}]")
    lines.append("")
    for out in calc.get("outputs") or []:
        val = out.get("value")
        unit = out.get("unit") or ""
        if val is None:
            lines.append(f"  {out.get('key')} = (not computed)")
        else:
            conf = ""
            if calc.get("status") == "confirmed" and calc.get("confirmed_at"):
                conf = f"    [User confirmed {calc['confirmed_at'][:10]}]"
            lines.append(f"  {out.get('key')} = {val} {unit}".rstrip() + conf)
    assumptions = calc.get("assumptions") or []
    if assumptions:
        lines.append("")
        lines.append("Assumptions:")
        for a in assumptions:
            lines.append(f"  - {a}")
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def calculation_to_block(calc: dict) -> dict:
    """Dict payload for CalculationBlock / document AST."""
    return {
        "type": "calculation",
        "calculation_id": calc.get("id"),
        "title": calc.get("name"),
        "profile": calc.get("profile"),
        "formula_latex": calc.get("formula_latex"),
        "formula_code": calc.get("formula_code"),
        "inputs": list(calc.get("inputs") or []),
        "outputs": list(calc.get("outputs") or []),
        "assumptions": list(calc.get("assumptions") or []),
        "status": calc.get("status"),
        "status_label": calc.get("status_label"),
        "confirmed_by": calc.get("confirmed_by"),
        "confirmed_at": calc.get("confirmed_at"),
        "revision": calc.get("revision") or 1,
        "material_id": calc.get("material_id"),
        "section_id": calc.get("section_id"),
        "binding": calc.get("binding"),
        "disclaimer": DISCLAIMER,
        "code_compliance_claimed": False,
        "text": render_calculation_text(calc),
    }


# ── Project state helpers ────────────────────────────────────────────

def ensure_calculations(state: dict | None) -> list[dict]:
    state = state if isinstance(state, dict) else {}
    calcs = state.setdefault("calculations", [])
    if not isinstance(calcs, list):
        state["calculations"] = []
        return state["calculations"]
    return calcs


def upsert_calculation(state: dict, calc: dict) -> dict:
    calcs = ensure_calculations(state)
    cid = calc.get("id")
    for i, existing in enumerate(calcs):
        if existing.get("id") == cid:
            calcs[i] = calc
            return calc
    calcs.append(calc)
    return calc


def get_calculation(state: dict, calc_id: str) -> dict | None:
    for c in ensure_calculations(state):
        if c.get("id") == calc_id:
            return c
    return None
