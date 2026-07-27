"""WORKORDER 0.61 — folder-optional project I/O.

Documents may exist before the user picks a folder. State lives in
local_app/project_states/<id>.json until a folder is bound; then it is
written into that folder's .foldok_state.json (never a silent invent).
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
STATES_DIR = APP_DIR / "project_states"
PROJECTS_FILE = APP_DIR / "projects.json"

OUTPUT_FORMATS = ("pdf", "html", "pptx", "docx")


def primary_folder(project: dict | None) -> Path | None:
    """Safe first folder — None when folder-less (never IndexError)."""
    if not project:
        return None
    folders = project.get("folders") or []
    if not folders:
        return None
    try:
        p = Path(folders[0])
    except Exception:
        return None
    return p if str(p).strip() else None


def has_folder(project: dict | None) -> bool:
    f = primary_folder(project)
    return bool(f and f.is_dir())


def memory_state_path(project_id: str) -> Path:
    STATES_DIR.mkdir(parents=True, exist_ok=True)
    return STATES_DIR / f"{project_id}.json"


def load_memory_state(project_id: str) -> dict:
    path = memory_state_path(project_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_memory_state(project_id: str, state: dict) -> None:
    path = memory_state_path(project_id)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def provisional_name_from_request(text: str, template_name: str | None = None) -> str:
    t = (text or "").strip()
    t = re.sub(
        r"^(lag|opprett|start med|bruk|generer)\s+(en\s+|et\s+|ei\s+)?",
        "", t, flags=re.I,
    ).strip()
    t = t[:48] or (template_name or "Nytt dokument")
    return t.split("\n")[0].strip() or "Nytt dokument"


def create_folderless_project(
    name: str,
    *,
    template_file: str | None = None,
    template: dict | None = None,
    output_format: str = "pdf",
    load_projects,
    save_projects,
    create_document_shell,
    default_state,
) -> dict:
    """Project with folders=[] + optional document shell in memory state."""
    fmt = (output_format or "pdf").lower()
    if fmt not in OUTPUT_FORMATS:
        fmt = "pdf"
    projects = load_projects()
    proj = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "folders": [],
        "folderless": True,
    }
    if template_file:
        proj["preferred_template"] = template_file
    projects.append(proj)
    save_projects(projects)

    state = default_state()
    state["project_id"] = proj["id"]
    state["folderless"] = True
    state["need_folder_banner"] = True
    if template_file and template:
        created = create_document_shell(state, template_file, template)
        if state.get("doc"):
            state["doc"]["output_format"] = fmt
        for d in state.get("documents") or []:
            if d.get("template") == template_file:
                d["output_format"] = fmt
        save_memory_state(proj["id"], state)
        return {
            **proj,
            "template": template_file,
            "name_no": created.get("name_no"),
            "output_format": fmt,
            "need_folder": True,
        }
    save_memory_state(proj["id"], state)
    return {**proj, "output_format": fmt, "need_folder": True}


def bind_folder_to_project(
    project: dict,
    folder: str | Path,
    *,
    load_state_fn,
    save_state_fn,
    load_projects,
    save_projects,
) -> dict:
    """Attach a user-chosen folder; migrate memory state into it."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Mappen finnes ikke: {folder}")
    pid = project["id"]
    mem = load_memory_state(pid)
    project["folders"] = [str(folder)]
    project["folderless"] = False
    projects = load_projects()
    for p in projects:
        if p.get("id") == pid:
            p["folders"] = [str(folder)]
            p["folderless"] = False
    save_projects(projects)
    # Merge memory into folder state
    disk = load_state_fn(folder, project_id=pid)
    if mem:
        for k, v in mem.items():
            if k in ("versions",) and disk.get(k):
                disk[k] = (mem.get(k) or []) + (disk.get(k) or [])
            elif v is not None and (k not in disk or not disk.get(k)):
                disk[k] = v
            elif k in ("doc", "documents", "active_template", "template", "need_folder_banner"):
                disk[k] = v
        disk["folderless"] = False
        disk["need_folder_banner"] = False
        disk["bound_folder_at"] = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()
    save_state_fn(folder, disk)
    # Keep memory as backup but mark bound
    mem["folderless"] = False
    mem["bound_to"] = str(folder)
    save_memory_state(pid, mem)
    return project
