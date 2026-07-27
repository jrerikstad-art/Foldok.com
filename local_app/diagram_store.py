"""Persist Foldok diagrams as text graph + pins JSONL (WO 0.63 T3)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from foldok_diagram import PinStore
from foldok_diagram.migrate import migrate
from foldok_diagram.model import Graph


def diagrams_dir(project_folder: str | Path) -> Path:
    d = Path(project_folder) / "diagrams"
    d.mkdir(parents=True, exist_ok=True)
    return d


def graph_path(project_folder: str | Path, graph_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (graph_id or "diagram"))
    return diagrams_dir(project_folder) / f"{safe}.json"


def pins_path(project_folder: str | Path, graph_id: str, profile_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (graph_id or "diagram"))
    prof = "".join(c if c.isalnum() or c in "-_" else "_" for c in (profile_id or "wiring"))
    return diagrams_dir(project_folder) / f"{safe}.{prof}.pins.jsonl"


def save_diagram(
    project_folder: str | Path,
    graph: Graph | dict,
    pins: PinStore | str | None,
    *,
    profile_id: str = "wiring",
) -> dict[str, str]:
    if isinstance(graph, Graph):
        gdict = graph.to_dict()
        gid = graph.id
    else:
        gdict = dict(graph)
        gid = str(gdict.get("id") or "diagram")
    gp = graph_path(project_folder, gid)
    gp.write_text(json.dumps(gdict, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pp = pins_path(project_folder, gid, profile_id)
    if isinstance(pins, PinStore):
        text = pins.to_jsonl()
    else:
        text = pins or ""
    pp.write_text(text if text.endswith("\n") or not text else text + "\n", encoding="utf-8")
    return {"graph": str(gp), "pins": str(pp)}


def load_diagram(
    project_folder: str | Path,
    graph_id: str,
    *,
    profile_id: str = "wiring",
) -> tuple[Graph, PinStore, list[str]]:
    gp = graph_path(project_folder, graph_id)
    if not gp.exists():
        raise FileNotFoundError(f"diagram not found: {gp}")
    doc = json.loads(gp.read_text(encoding="utf-8"))
    pins = PinStore()
    pp = pins_path(project_folder, graph_id, profile_id)
    if pp.exists():
        pins = PinStore.from_jsonl(pp.read_text(encoding="utf-8"))
    return migrate(doc, pins)


def list_diagrams(project_folder: str | Path) -> list[dict[str, Any]]:
    d = diagrams_dir(project_folder)
    out = []
    for p in sorted(d.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "graph_id": data.get("id") or p.stem,
                "title": data.get("title") or p.stem,
                "jurisdiction": data.get("jurisdiction") or "",
                "path": str(p),
            })
        except Exception:
            continue
    return out
