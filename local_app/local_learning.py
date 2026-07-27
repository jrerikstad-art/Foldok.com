"""LEARNING_AND_BOUNDARIES §3 L2 — local, inspectable, deletable adaptation."""
from __future__ import annotations

import json
from pathlib import Path

LEARNING_PATH = Path(__file__).resolve().parent / "local_learning.json"
DEFAULT = {
    "version": 1,
    "aliases": {},          # observed_or_label → canonical gap/fact key
    "column_aliases": {},   # table column key → preferred fact key
    "notes": [],
}


def path() -> Path:
    return LEARNING_PATH


def load() -> dict:
    if not LEARNING_PATH.exists():
        return json.loads(json.dumps(DEFAULT))
    try:
        data = json.loads(LEARNING_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(DEFAULT))
    data.setdefault("version", 1)
    data.setdefault("aliases", {})
    data.setdefault("column_aliases", {})
    data.setdefault("notes", [])
    return data


def save(data: dict) -> dict:
    LEARNING_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEARNING_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    return data


def clear() -> None:
    if LEARNING_PATH.exists():
        LEARNING_PATH.unlink()


def record_alias(from_key: str, to_key: str, *, kind: str = "alias") -> dict:
    """Remember a mapping. from_key may be a label ('utgiver') or nonstandard key."""
    from_key = (from_key or "").strip().lower().replace(" ", "_")
    to_key = (to_key or "").strip()
    if not from_key or not to_key or from_key == to_key:
        return load()
    data = load()
    bucket = "column_aliases" if kind == "column" else "aliases"
    data.setdefault(bucket, {})[from_key] = to_key
    # Also keep reverse-friendly entry under aliases for matchers
    if kind == "column":
        data.setdefault("aliases", {})[from_key] = to_key
    save(data)
    return data


def merged_fact_aliases(base: dict) -> dict:
    """FACT_ALIASES + local learning: canonical → list of alternate keys."""
    out = {k: list(v) for k, v in (base or {}).items()}
    data = load()
    # aliases: observed → canonical  ⇒  add observed under canonical's list
    for observed, canonical in (data.get("aliases") or {}).items():
        if not canonical:
            continue
        out.setdefault(canonical, [])
        if observed not in out[canonical]:
            out[canonical].append(observed)
        # also allow looking up by column key that points at canonical
        out.setdefault(observed, [])
        if canonical not in out[observed]:
            out[observed].append(canonical)
    for col, preferred in (data.get("column_aliases") or {}).items():
        out.setdefault(col, [])
        if preferred not in out[col]:
            out[col].append(preferred)
        out.setdefault(preferred, [])
        if col not in out[preferred]:
            out[preferred].append(col)
    return out


def resolve_key(key: str, base_aliases: dict | None = None) -> str:
    """If learning maps this label/key elsewhere, return the preferred key."""
    if not key:
        return key
    data = load()
    k = key.strip()
    low = k.lower().replace(" ", "_")
    for bucket in ("column_aliases", "aliases"):
        hit = (data.get(bucket) or {}).get(low) or (data.get(bucket) or {}).get(k)
        if hit:
            return hit
    return k
