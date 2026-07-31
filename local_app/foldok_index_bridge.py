"""Bridge foldok_index watermarks into the workbench (WO 0.65 T3).

The workbench used to diff a JSON file inventory and never call
``context_for_update`` / ``set_watermark``. That made "update with the new
files" a semantic guess. This module opens the project SQLite index, syncs
folders into it, and exposes the recency API the agent path must use.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import foldok_paths as fpaths

DB_NAME = "index.db"


def watermark_key_for(
    template_file: str | None = None,
    *,
    document_id: str | None = None,
) -> str:
    if document_id:
        return f"doc:{document_id}"
    stem = Path(template_file or "document").stem
    return f"doc:{stem}"


def db_path(primary_folder) -> Path:
    root = fpaths.index_dir(primary_folder)
    root.mkdir(parents=True, exist_ok=True)
    return root / DB_NAME


def open_project_index(primary_folder):
    from foldok_index import Index

    return Index(db_path(primary_folder))


def rel_for(path: str | Path, folders: Iterable[str | Path]) -> str:
    """Map an absolute ingest path back to the workbench relative id."""
    p = Path(path)
    for folder in folders:
        root = Path(folder)
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except (ValueError, OSError):
            continue
    return p.name


def sync_project_index(primary_folder, folders: list[str] | list[Path]) -> dict[str, Any]:
    """Idempotent ingest of project folders into foldok_index SQLite."""
    from foldok_index import supported_suffixes

    ix = open_project_index(primary_folder)
    try:
        patterns = tuple(f"*{s}" for s in sorted(supported_suffixes()))
        results = []
        for folder in folders or []:
            root = Path(folder)
            if not root.is_dir():
                continue
            results.extend(ix.ingest_dir(root, patterns=patterns))
        return {
            "ok": True,
            "head_seq": ix.head(),
            "results": len(results),
            "db": str(db_path(primary_folder)),
        }
    finally:
        ix.close()


def context_for_document_update(
    primary_folder,
    folders: list[str] | list[Path],
    *,
    template_file: str | None = None,
    document_id: str | None = None,
    query: str | None = None,
    sync: bool = True,
) -> dict[str, Any] | None:
    """Return foldok_index.context_for_update, or None if the index is unavailable."""
    try:
        if sync:
            sync_project_index(primary_folder, folders)
        ix = open_project_index(primary_folder)
    except Exception:
        return None
    try:
        key = watermark_key_for(template_file, document_id=document_id)
        ctx = ix.context_for_update(key, query=query)
        # Attach workbench-relative paths for source targeting
        rels = []
        for doc in ctx.get("new_documents") or []:
            path = doc.get("path") or ""
            rel = rel_for(path, folders)
            doc["rel"] = rel
            rels.append(rel)
        ctx["new_rels"] = rels
        ctx["watermark_key"] = key
        return ctx
    finally:
        ix.close()


def set_document_watermark(
    primary_folder,
    *,
    template_file: str | None = None,
    document_id: str | None = None,
    note: str = "",
    sync_folders: list[str] | list[Path] | None = None,
) -> dict[str, Any]:
    """Record that this document now sits at the current index head."""
    try:
        if sync_folders:
            sync_project_index(primary_folder, sync_folders)
        ix = open_project_index(primary_folder)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
    try:
        key = watermark_key_for(template_file, document_id=document_id)
        seq = ix.set_watermark(key, note=note or f"written against {key}")
        return {"ok": True, "watermark_key": key, "seq": seq, "head_seq": ix.head()}
    finally:
        ix.close()
