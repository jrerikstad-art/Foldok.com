"""Index incremental tools — reindex, diff_index, update_document_from_sources.

Manifest lives at <primary>/.foldok_index_manifest.json so the agent can
see added/changed/removed without inventing state. SHA cache under
.foldok_cache/ remains the source of truth for facts.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import foldok_paths as fpaths

MANIFEST_NAME = fpaths.INDEX_MANIFEST
# Confirm required when |added|+|changed|+|removed| exceeds this (ENGINE_TOOLS)
REINDEX_CONFIRM_THRESHOLD = 15


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def manifest_path(primary_folder) -> Path:
    return fpaths.index_manifest_path(primary_folder)


def load_manifest(primary_folder) -> dict:
    path = manifest_path(primary_folder)
    if not path.exists():
        return {"index_version": "0", "updated_at": None, "files": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"index_version": "0", "updated_at": None, "files": {}}
    data.setdefault("index_version", "0")
    data.setdefault("files", {})
    return data


def save_manifest(primary_folder, manifest: dict) -> dict:
    path = manifest_path(primary_folder)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def bump_version(prev: str | int | None) -> str:
    try:
        return str(int(prev or 0) + 1)
    except (TypeError, ValueError):
        return "1"


def file_kind_for(path: Path, fc) -> str:
    ext = path.suffix.lower()
    if ext in fc.PHOTO_EXT:
        return "photo"
    if ext in fc.DOC_EXT:
        return "doc"
    if ext in getattr(fc, "CAD_EXT", set()):
        return "cad"
    return "skipped"


def build_live_inventory(folders, fc, source_files_fn) -> dict:
    """Cheap SHA walk of the project folders — no model calls."""
    files = {}
    for p, rel, cache_dir in source_files_fn(folders):
        kind = file_kind_for(p, fc)
        if kind == "skipped":
            continue
        try:
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue
        cache = Path(cache_dir) / f"{sha}.json"
        facts = 0
        caption = None
        if cache.exists():
            try:
                entry = fc.read_json_file(cache)
                facts = len(entry.get("facts") or [])
                caption = entry.get("caption")
            except Exception:
                pass
        files[rel] = {
            "id": rel,
            "path": rel,
            "type": kind,
            "sha": sha,
            "indexed": cache.exists(),
            "facts": facts,
            "caption": caption,
        }
    return files


def _source_row(rel: str, meta: dict | None) -> dict:
    meta = meta or {}
    return {
        "id": meta.get("id") or rel,
        "path": meta.get("path") or rel,
        "type": meta.get("type") or "unknown",
        "sha": meta.get("sha"),
        "facts": meta.get("facts"),
        "caption": meta.get("caption"),
    }


def diff_inventories(before: dict, after: dict) -> dict:
    """Compare two {rel: {sha,...}} maps → added / changed / removed Source rows."""
    before = before or {}
    after = after or {}
    added, changed, removed = [], [], []
    for rel, meta in after.items():
        if rel not in before:
            added.append(_source_row(rel, meta))
        elif (before[rel] or {}).get("sha") != (meta or {}).get("sha"):
            changed.append(_source_row(rel, meta))
    for rel, meta in before.items():
        if rel not in after:
            removed.append(_source_row(rel, meta))
    return {"added": added, "changed": changed, "removed": removed}


def delta_count(diff: dict) -> int:
    return len(diff.get("added") or []) + len(diff.get("changed") or []) + len(diff.get("removed") or [])


def names_only(diff: dict) -> dict:
    return {
        "added": [s.get("path") or s.get("id") for s in (diff.get("added") or [])],
        "changed": [s.get("path") or s.get("id") for s in (diff.get("changed") or [])],
        "removed": [s.get("path") or s.get("id") for s in (diff.get("removed") or [])],
    }


def diff_index(
    primary_folder,
    folders,
    fc,
    source_files_fn,
    since_version: str | None = None,
    *,
    template_file: str | None = None,
    document_id: str | None = None,
) -> dict:
    """Read-only: live inventory vs stored manifest (or empty if no baseline).

    Also attaches foldok_index recency (``context_for_update``) when a document
    watermark key can be resolved — that channel answers "what arrived since
    this document was written" without a semantic search.
    """
    manifest = load_manifest(primary_folder)
    live = build_live_inventory(folders, fc, source_files_fn)
    # since_version: if given and does not match current, still compare to stored
    # baseline — we do not keep full version history of inventories yet.
    baseline = manifest.get("files") or {}
    if since_version and str(since_version) != str(manifest.get("index_version")):
        # Soft note: we only keep the latest baseline; still return live vs latest
        pass
    diff = diff_inventories(baseline, live)
    out = {
        **diff,
        "index_version": str(manifest.get("index_version") or "0"),
        "since_version": since_version,
        "total_files": len(live),
        "live_unindexed": sum(1 for m in live.values() if not m.get("indexed")),
    }
    try:
        import foldok_index_bridge as fib

        key_tf = template_file
        if not key_tf and not document_id:
            # Project-level peek: last written document stem if any in state later;
            # without a key, still sync and expose head via a synthetic probe.
            key_tf = "project"
        ctx = fib.context_for_document_update(
            primary_folder, folders,
            template_file=key_tf, document_id=document_id, sync=True,
        )
        if ctx:
            out["recency"] = {
                "watermark": ctx.get("watermark_key") or ctx.get("watermark"),
                "since_seq": ctx.get("since_seq"),
                "head_seq": ctx.get("head_seq"),
                "first_time": ctx.get("first_time"),
                "new_document_count": ctx.get("new_document_count"),
                "new_rels": ctx.get("new_rels") or [],
                "problems": ctx.get("problems") or [],
                "note": ctx.get("note"),
            }
    except Exception as exc:
        out["recency_error"] = str(exc)[:200]
    return out


def reindex_plan(primary_folder, folders, fc, source_files_fn, confirm: bool = False) -> dict:
    """Dry-run + confirm gate. Does not index."""
    manifest = load_manifest(primary_folder)
    live = build_live_inventory(folders, fc, source_files_fn)
    diff = diff_inventories(manifest.get("files") or {}, live)
    n = delta_count(diff)
    needs_confirm = n > REINDEX_CONFIRM_THRESHOLD and not confirm
    unindexed = [m for m in live.values() if not m.get("indexed")]
    return {
        "needs_confirm": needs_confirm,
        "confirm_threshold": REINDEX_CONFIRM_THRESHOLD,
        "delta_count": n,
        "diff": diff,
        "names": names_only(diff),
        "total_files": len(live),
        "unindexed_count": len(unindexed),
        "index_version": str(manifest.get("index_version") or "0"),
        "live": live,
    }


def commit_manifest_after_index(primary_folder, folders, fc, source_files_fn, live=None) -> dict:
    """Write new manifest after a successful reindex job."""
    prev = load_manifest(primary_folder)
    live = live or build_live_inventory(folders, fc, source_files_fn)
    diff = diff_inventories(prev.get("files") or {}, live)
    version = bump_version(prev.get("index_version"))
    manifest = {
        "index_version": version,
        "updated_at": _iso_now(),
        "files": live,
        "last_diff": names_only(diff),
    }
    save_manifest(primary_folder, manifest)
    foldok_sync = None
    try:
        import foldok_index_bridge as fib

        foldok_sync = fib.sync_project_index(primary_folder, folders)
    except Exception as exc:
        foldok_sync = {"ok": False, "error": str(exc)[:200]}
    return {
        **names_only(diff),
        "total_files": len(live),
        "index_version": version,
        "updated_at": manifest["updated_at"],
        "foldok_index": foldok_sync,
    }


def resolve_source_ids(source_ids, last_diff_names: dict | None, live: dict) -> list[str]:
    """If source_ids omitted, use added+changed from last reindex diff."""
    if source_ids:
        return [str(s) for s in source_ids]
    names = last_diff_names or {}
    out = list(names.get("added") or []) + list(names.get("changed") or [])
    if out:
        return out
    return list(live.keys())


def update_document_from_sources(
    state,
    template,
    folders,
    template_file,
    fc,
    *,
    load_index_fn,
    refresh_code_tables_fn,
    refresh_bom_fn,
    persist_helpers: dict,
    source_ids=None,
    mode: str = "merge",
    documents=None,
) -> dict:
    """Merge new/changed source facts into the existing Document AST.

    mode=merge (default): fill open MANGLER from index + refresh engine-owned
    tables. Never overwrites user-verified facts / cell_overrides / filled prose.

    mode=replace_sections: same as merge for MANGLER, but also force-refresh
    compiled sections (doc_control, spec_overview, drawings_register, bom).
    Does not regenerate free-prose sections (those need regenerate_section + confirm).
    """
    import doc_state as ds

    mode = (mode or "merge").strip().lower()
    if mode not in ("merge", "replace_sections"):
        mode = "merge"

    primary = folders[0]
    manifest = load_manifest(primary)
    live = build_live_inventory(folders, fc, persist_helpers["source_files"])

    # WO 0.65 T3 — recency is a watermark lookup, not a search.
    foldok_ctx = None
    try:
        import foldok_index_bridge as fib

        foldok_ctx = fib.context_for_document_update(
            primary, folders, template_file=template_file, sync=True,
        )
    except Exception:
        foldok_ctx = None

    # Prefer files that arrived after this document's watermark.
    effective_source_ids = source_ids
    nothing_new = False
    if (
        effective_source_ids is None
        and foldok_ctx is not None
        and not foldok_ctx.get("first_time")
    ):
        if (foldok_ctx.get("new_document_count") or 0) == 0:
            nothing_new = True
        elif foldok_ctx.get("new_rels"):
            effective_source_ids = list(foldok_ctx["new_rels"])

    if nothing_new:
        problems = foldok_ctx.get("problems") or []
        note = foldok_ctx.get("note") or "Ingen nye kilder siden siste skriving."
        if problems:
            bad = ", ".join(
                f"{p.get('path') or '?'} ({p.get('status')})" for p in problems[:8]
            )
            note = f"{note} Uleste: {bad}."
        mark = None
        try:
            import foldok_index_bridge as fib

            mark = fib.set_document_watermark(
                primary, template_file=template_file,
                note="checked; nothing new",
            )
        except Exception:
            mark = None
        return {
            "updated_sections": [],
            "added_blocks": 0,
            "remaining_gaps": [
                {"key": g.get("key"), "reason": g.get("label") or g.get("severity") or "open"}
                for g in (state.get("gaps") or []) if g.get("key")
            ],
            "change_summary": note,
            "applied": [],
            "source_ids_used": [],
            "mode": mode,
            "gaps_before": len(state.get("gaps") or []),
            "gaps_after": len(state.get("gaps") or []),
            "gap_summary": None,
            "foldok_update": foldok_ctx,
            "foldok_watermark": mark,
            "nothing_new": True,
        }

    targets = resolve_source_ids(effective_source_ids, manifest.get("last_diff"), live)
    target_set = set(targets)

    index = load_index_fn(
        folders, "no", state.get("user_facts"),
        project_name=persist_helpers.get("project_name"),
    )
    # Narrow facts for gap-fill when specific sources requested
    if effective_source_ids is not None or (manifest.get("last_diff") and targets):
        narrowed = []
        for e in index:
            f = e.get("file") or ""
            if f in target_set or e.get("kind") in ("user", "project_name"):
                narrowed.append(e)
        # Always keep user + project_name; if nothing matched keep full index
        if any(e.get("kind") not in ("user", "project_name") for e in narrowed):
            index_for_fill = narrowed
        else:
            index_for_fill = index
    else:
        index_for_fill = index

    documents = documents if documents is not None else (state.get("documents") or [])
    before_gaps = list(state.get("gaps") or [])

    updated_sections = []
    added_blocks = 0

    if mode == "replace_sections" or mode == "merge":
        if refresh_code_tables_fn(state, folders, template_file, "no"):
            for sk in ("doc_control", "spec_overview", "drawings_register"):
                if sk in (state.get("doc") or {}).get("sections", {}):
                    if sk not in updated_sections:
                        updated_sections.append(sk)
        if refresh_bom_fn and refresh_bom_fn(state, folders, template_file, "no"):
            if "bom" not in updated_sections:
                updated_sections.append("bom")

    fill = fc.fill_known_gaps(
        state, template, index_for_fill, state.get("artifact"), fc,
        documents=documents,
    )
    applied = fill.get("applied") or []
    # applied is a list of gap keys (strings)
    added_blocks = len(applied)

    for sec in fill.get("repaired_sections") or []:
        if sec not in updated_sections:
            updated_sections.append(sec)

    gaps = fill.get("gaps") or state.get("gaps") or []
    remaining = [
        {"key": g.get("key"), "reason": g.get("label") or g.get("severity") or "open"}
        for g in gaps if g.get("key")
    ]

    summary_parts = []
    if foldok_ctx and foldok_ctx.get("new_document_count"):
        summary_parts.append(
            f"{foldok_ctx['new_document_count']} nye kilder siden siste watermark"
        )
    if applied:
        summary_parts.append(f"Fylte {len(applied)} MANGLER fra kilder")
    if updated_sections:
        summary_parts.append("Oppdaterte seksjoner: " + ", ".join(updated_sections))
    if not summary_parts:
        summary_parts.append("Ingen nye fakta å flette inn — dokumentet uendret")
    if mode == "replace_sections":
        summary_parts.append("(modus: replace_sections — kun motor-eide tabeller)")
    if foldok_ctx and foldok_ctx.get("problems"):
        summary_parts.append(
            f"{len(foldok_ctx['problems'])} filer kunne ikke leses"
        )
    change_summary = ". ".join(summary_parts) + "."

    ds.add_version(
        state, "engine", "update_from_sources",
        change_summary[:200],
    )

    mark = None
    try:
        import foldok_index_bridge as fib

        mark = fib.set_document_watermark(
            primary, template_file=template_file,
            note="update_document_from_sources",
        )
    except Exception:
        mark = None

    return {
        "updated_sections": updated_sections,
        "added_blocks": added_blocks,
        "remaining_gaps": remaining,
        "change_summary": change_summary,
        "applied": applied,
        "source_ids_used": targets,
        "mode": mode,
        "gaps_before": len(before_gaps),
        "gaps_after": len(gaps),
        "gap_summary": ds.gaps_summary(gaps) if hasattr(ds, "gaps_summary") else None,
        "foldok_update": foldok_ctx,
        "foldok_watermark": mark,
        "nothing_new": False,
    }


def format_diff_reply(diff: dict, lang: str = "no") -> str:
    added = diff.get("added") or []
    changed = diff.get("changed") or []
    removed = diff.get("removed") or []
    recency = diff.get("recency") or {}
    if lang == "en":
        if not (added or changed or removed):
            base = "Index is up to date — no added, changed, or removed files."
        else:
            parts = []
            if added:
                parts.append("**Added:** " + ", ".join((s.get("path") or s) for s in added[:12]))
            if changed:
                parts.append("**Changed:** " + ", ".join((s.get("path") or s) for s in changed[:12]))
            if removed:
                parts.append("**Removed:** " + ", ".join((s.get("path") or s) for s in removed[:12]))
            base = "\n".join(parts)
        if recency.get("note"):
            base += f"\n\n_{recency['note']}_"
            if recency.get("problems"):
                bad = ", ".join(
                    f"{p.get('path') or '?'} ({p.get('status')})"
                    for p in recency["problems"][:6]
                )
                base += f"\nUnreadable: {bad}"
        return base
    if not (added or changed or removed):
        base = "Indeksen er ajour — ingen nye, endrede eller fjernede filer."
    else:
        parts = []
        if added:
            parts.append("**Nye:** " + ", ".join((s.get("path") or s) for s in added[:12]))
        if changed:
            parts.append("**Endret:** " + ", ".join((s.get("path") or s) for s in changed[:12]))
        if removed:
            parts.append("**Fjernet:** " + ", ".join((s.get("path") or s) for s in removed[:12]))
        base = "\n".join(parts)
    if recency.get("note"):
        base += f"\n\n_{recency['note']}_"
        if recency.get("problems"):
            bad = ", ".join(
                f"{p.get('path') or '?'} ({p.get('status')})"
                for p in recency["problems"][:6]
            )
            base += f"\nUleste: {bad}"
    return base
