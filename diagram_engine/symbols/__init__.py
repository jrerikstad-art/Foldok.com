"""Symbol library loader for piping / mechanical / electrical."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("PyYAML required") from e

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def load_symbols() -> dict[str, dict]:
    out = {}
    for domain_dir in sorted(ROOT.iterdir()):
        if not domain_dir.is_dir():
            continue
        for path in sorted(domain_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            sid = data.get("id") or path.stem
            data["id"] = sid
            data["_domain_dir"] = domain_dir.name
            svg = domain_dir / (data.get("svg") or f"{sid}.svg")
            data["_svg_path"] = str(svg) if svg.exists() else None
            out[sid] = data
    return out


def get_symbol(symbol_id: str) -> dict | None:
    return load_symbols().get(symbol_id)


def list_symbols(domain: str | None = None) -> list[dict]:
    rows = []
    for sid, d in load_symbols().items():
        if domain and d.get("domain") != domain and d.get("_domain_dir") != domain:
            continue
        rows.append({
            "id": sid,
            "label": d.get("label") or sid,
            "domain": d.get("domain") or d.get("_domain_dir"),
            "ports": list(d.get("ports") or []),
        })
    return rows
