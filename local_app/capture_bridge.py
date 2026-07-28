"""Thin bridge: workbench project state ↔ foldok_capture + foldok_gaps.

The Capture app reads/writes through the project folder (.foldok/*, sidecars).
This module keeps CompletionSession document state in `.foldok_state.json`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from foldok_capture import bind, ingest, publish, read_binding, read_tasks, tasks_from_gaps
from foldok_gaps import CompletionSession, Document, default_registry
from foldok_gaps.packs import NO_ELECTRICAL, PACKS

DEFAULT_PACK_ID = "no_electrical_installation"
DEFAULT_CIRCUITS = 5


def _issue_dict(issue: Any) -> dict[str, str]:
    return {"code": issue.code, "detail": issue.detail, "fix": issue.fix}


def report_dict(report: Any) -> dict[str, Any]:
    return {
        "folder": report.folder,
        "resolved": list(report.resolved),
        "already_done": list(report.already_done),
        "capture_count": len(report.captures),
        "issues": [_issue_dict(i) for i in report.issues],
        "summary": report.summary(),
        "ok": report.ok,
    }


def pack_for_state(state: dict[str, Any]) -> Any:
    comp = state.get("completion") or {}
    pack_id = comp.get("pack_id")
    if pack_id and pack_id in PACKS:
        return PACKS[pack_id]
    compliance = state.get("compliance") or {}
    domains = {str(d).lower() for d in (compliance.get("domains") or [])}
    if "electrical" in domains or "el" in domains or "nek" in domains:
        return PACKS["no_electrical_installation"]
    if "machinery" in domains or "machine" in domains:
        return PACKS["eu_machinery_technical_file"]
    if "aquaculture" in domains or "fish" in domains:
        return PACKS["aquaculture_site"]
    segment = str((state.get("artifact") or {}).get("segment") or "").lower()
    if segment == "electrical":
        return PACKS["no_electrical_installation"]
    if segment == "machinery":
        return PACKS["eu_machinery_technical_file"]
    return NO_ELECTRICAL


def _facts_from_state(state: dict[str, Any]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    art = state.get("artifact") or {}
    if "has_rcd" in art:
        facts["has_rcd"] = bool(art.get("has_rcd"))
    comps = art.get("main_components") or art.get("components") or []
    if comps:
        facts["bom"] = [
            {
                "id": c.get("id") or c.get("tag") or f"C{i}",
                "type": c.get("type") or "",
                "tag": c.get("tag") or "",
                "ref": (c.get("seen_in") or [None])[0] or c.get("ref") or "",
            }
            for i, c in enumerate(comps[:40], 1)
            if isinstance(c, dict)
        ]
    return facts


def _default_subjects(doc: Document, state: dict[str, Any]) -> None:
    if not doc.subjects_of("board"):
        label = (state.get("artifact") or {}).get("board_label") or "Main board"
        doc.add_subject("board", "DB1", label)
    circuits = doc.subjects_of("circuit")
    if not circuits:
        n = int((state.get("completion") or {}).get("circuit_count") or DEFAULT_CIRCUITS)
        for i in range(1, max(1, n) + 1):
            doc.add_subject("circuit", f"K{i}", f"Circuit {i}")


def document_from_project(project: dict[str, Any], state: dict[str, Any]) -> Document:
    comp = state.get("completion") or {}
    if comp.get("document"):
        doc = Document.from_dict(comp["document"])
        if not doc.id:
            doc.id = project.get("id") or "project"
        return doc
    pack = pack_for_state(state)
    doc = Document(
        id=project.get("id") or "project",
        title=project.get("name") or "Project",
        segment=pack.segment,
        jurisdiction=pack.jurisdiction,
        facts=_facts_from_state(state),
        mode=str(comp.get("mode") or "build"),
    )
    _default_subjects(doc, state)
    return doc


def session_for_project(project: dict[str, Any], state: dict[str, Any]) -> CompletionSession:
    pack = pack_for_state(state)
    doc = document_from_project(project, state)
    session = CompletionSession(doc, pack, default_registry(), mode=doc.mode)
    state.setdefault("completion", {})
    state["completion"]["pack_id"] = pack.id
    state["completion"]["document"] = doc.to_dict()
    state["completion"]["mode"] = doc.mode
    return session


def persist_session(state: dict[str, Any], session: CompletionSession) -> None:
    state.setdefault("completion", {})
    state["completion"]["document"] = session.document.to_dict()
    state["completion"]["pack_id"] = session.pack.id
    state["completion"]["mode"] = session.document.mode


def capture_status(folder: str | Path) -> dict[str, Any]:
    base = Path(folder)
    binding = read_binding(base)
    tasks = read_tasks(base)
    open_photo_gaps = 0
    return {
        "folder": str(base),
        "bound": binding is not None,
        "binding": binding.to_dict() if binding else None,
        "tasks": tasks.to_dict() if tasks else None,
        "open_task_count": len(tasks.open_tasks) if tasks else 0,
        "task_count": len(tasks.tasks) if tasks else 0,
        "tasks_stale_hours": round(tasks.age_hours(), 2) if tasks else 0.0,
        "tasks_stale": bool(tasks and tasks.age_hours() > 1.5),
        "open_photo_gaps": open_photo_gaps,
    }


def capture_bind(folder: str | Path, project: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    session = session_for_project(project, state)
    path = bind(
        folder,
        project.get("id") or "",
        project_title=project.get("name") or "",
        document_id=session.document.id,
    )
    persist_session(state, session)
    return {
        "ok": True,
        "binding_path": str(path),
        "project_id": project.get("id"),
        "pack_id": session.pack.id,
        "status": capture_status(folder),
    }


def capture_publish(folder: str | Path, project: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    session = session_for_project(project, state)
    tasks = tasks_from_gaps(session.gaps())
    path = publish(
        folder,
        tasks,
        project_id=project.get("id") or "",
        project_title=project.get("name") or "",
        document_id=session.document.id,
    )
    persist_session(state, session)
    return {
        "ok": True,
        "tasks_path": str(path),
        "task_count": len(tasks),
        "open_tasks": len([t for t in tasks if not t.done]),
        "gap_ids": [t.gap_id for t in tasks if not t.done],
        "status": capture_status(folder),
    }


def capture_ingest(
    folder: str | Path,
    project: dict[str, Any],
    state: dict[str, Any],
    *,
    by: str = "",
) -> dict[str, Any]:
    session = session_for_project(project, state)
    report = ingest(folder, session, by=by or "capture bridge")
    persist_session(state, session)
    out = report_dict(report)
    out["ok"] = True
    out["status"] = capture_status(folder)
    out["completion_summary"] = session.gaps().summary()
    return out
