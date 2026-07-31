"""WORKORDER 0.55 — Pre-scan (filesystem only, zero tokens).

scan_folders walks trees without reading file contents for classification.
SHA cache checks are optional and capped. Cost/time estimates feed the
decision card before any indexing spend.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Callable, Iterable

import foldok_paths as fpaths

# Honest per-file cost model (EUR) — WORKORDER_0.55 §A2
COST_PHOTO = 0.004
COST_PDF_PER_3_PAGES = 0.002
COST_SHEET_TEXT = 0.001
COST_SKIPPED = 0.0

OVERSIZE_BYTES = 25 * 1024 * 1024  # 25 MB
PDF_PAGE_CAP_HINT = 60

DEFAULT_THROUGHPUT = 0.35  # files/sec/worker fallback
DEFAULT_WORKERS = 5

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff", ".bmp", ".svg"}
DOC_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".rtf"}
CAD_EXT = {".step", ".stp", ".iges", ".igs", ".fcstd", ".dxf", ".dwg", ".stl", ".obj", ".brep"}
NO_EXTRACTOR_EXT = {
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v", ".webm",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso", ".dmg",
    ".exe", ".dll", ".bin", ".img", ".vmdk",
}

PRESCAN_THRESHOLD = 200  # above → decision card required


def _kind(ext: str) -> str:
    e = (ext or "").lower()
    if e in PHOTO_EXT:
        return "photo"
    if e in DOC_EXT:
        return "doc"
    if e in CAD_EXT:
        return "cad"
    if e in NO_EXTRACTOR_EXT:
        return "no_extractor"
    return "skipped"


def _est_file_cost(kind: str, size: int, ext: str) -> float:
    if kind in ("skipped", "cad", "no_extractor"):
        return COST_SKIPPED
    if kind == "photo":
        return COST_PHOTO
    if ext == ".pdf":
        pages = max(1, min(200, size // 40_000))
        chunks = (min(pages, PDF_PAGE_CAP_HINT) + 2) // 3
        return round(COST_PDF_PER_3_PAGES * chunks, 5)
    return COST_SHEET_TEXT


def _cache_hit(path: Path, cache_dir: Path) -> bool:
    try:
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return False
    return (cache_dir / f"{sha}.json").exists()


def scan_folders(
    folders: list[str] | list[Path],
    *,
    skip_dir_names: Iterable[str] | None = None,
    check_cache: bool = True,
    max_cache_checks: int = 50_000,
    last_throughput: float | None = None,
    workers: int = DEFAULT_WORKERS,
) -> dict[str, Any]:
    """Walk folders WITHOUT model calls. Returns ScanReport dict (§A1)."""
    t0 = time.time()
    skip_dirs = set(skip_dir_names or ())
    by_ext: dict[str, int] = {}
    folder_stats: dict[str, dict] = {}
    oversize: list[dict] = []
    total_files = 0
    total_bytes = 0
    indexable = 0
    skipped = 0
    already_cached = 0
    cache_checks = 0
    est_lo = 0.0
    est_hi = 0.0
    pending_photo = 0
    pending_doc = 0

    roots = [Path(f) for f in folders]

    for root in roots:
        if not root.is_dir():
            continue
        cache_dir = fpaths.cache_dir(root)
        prefix = f"{root.name}/" if len(roots) > 1 else ""
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                rel_parts = p.relative_to(root).parts
            except ValueError:
                continue
            if any(part.startswith(".") for part in rel_parts):
                continue
            if skip_dirs and any(part in skip_dirs for part in rel_parts[:-1]):
                continue
            if len(rel_parts) >= 2 and rel_parts[0] == "Rapporter" and rel_parts[1] == "media":
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            total_files += 1
            total_bytes += size
            ext = p.suffix.lower() or "(none)"
            by_ext[ext] = by_ext.get(ext, 0) + 1
            kind = _kind(ext)
            top = rel_parts[0] if len(rel_parts) > 1 else "(rot)"
            bucket = folder_stats.setdefault(top, {
                "rel": top, "files": 0, "bytes": 0, "ext_profile": {},
                "indexable": 0, "est_lo": 0.0, "est_hi": 0.0,
            })
            bucket["files"] += 1
            bucket["bytes"] += size
            bucket["ext_profile"][ext] = bucket["ext_profile"].get(ext, 0) + 1

            if size > OVERSIZE_BYTES:
                oversize.append({
                    "file": prefix + Path(*rel_parts).as_posix(),
                    "bytes": size,
                    "kind": kind,
                })
                skipped += 1
                continue

            if kind in ("skipped", "cad", "no_extractor"):
                skipped += 1
                continue

            cached = False
            if check_cache and cache_checks < max_cache_checks:
                cache_checks += 1
                cached = _cache_hit(p, cache_dir)
            if cached:
                already_cached += 1
                continue

            indexable += 1
            bucket["indexable"] += 1
            cost = _est_file_cost(kind, size, ext)
            lo, hi = cost, round(cost * 1.9, 5)
            est_lo += lo
            est_hi += hi
            bucket["est_lo"] += lo
            bucket["est_hi"] += hi
            if kind == "photo":
                pending_photo += 1
            else:
                pending_doc += 1

    by_folder = sorted(
        folder_stats.values(),
        key=lambda b: (-b["files"], b["rel"]),
    )[:40]
    for b in by_folder:
        b["est_lo"] = round(b["est_lo"], 2)
        b["est_hi"] = round(b["est_hi"], 2)
        b["gb"] = round(b["bytes"] / (1024 ** 3), 3)

    thr = float(last_throughput or DEFAULT_THROUGHPUT)
    workers = max(1, int(workers or DEFAULT_WORKERS))
    if indexable <= 0:
        est_min_lo = est_min_hi = 0
    else:
        secs = indexable / (workers * thr)
        est_min_lo = max(1, int(secs / 60 * 0.75)) if indexable > 20 else max(1, int(secs / 60) or 1)
        est_min_hi = max(est_min_lo, int(secs / 60 * 1.5) or est_min_lo)

    report = {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "total_gb": round(total_bytes / (1024 ** 3), 2),
        "folder_count": sum(1 for r in roots if r.is_dir()),
        "by_ext": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])),
        "by_folder": by_folder,
        "indexable": indexable,
        "skipped": skipped,
        "oversize": oversize[:100],
        "oversize_count": len(oversize),
        "est_cost_eur": [round(est_lo, 2), round(est_hi, 2)],
        "est_minutes": [est_min_lo, est_min_hi],
        "already_cached": already_cached,
        "needs_decision_card": indexable > PRESCAN_THRESHOLD,
        "prescan_ms": int((time.time() - t0) * 1000),
        "pending_kinds": {"photo": pending_photo, "doc": pending_doc},
    }
    return attach_coverage_scan(
        report,
        [str(r) for r in roots if r.is_dir()],
        doc_ext=DOC_EXT,
        photo_ext=PHOTO_EXT,
        cad_ext=CAD_EXT,
        skip_dir_names=skip_dirs,
    )


def filter_pending(
    files: list[tuple],
    *,
    mode: str = "all",
    subfolders: list[str] | None = None,
    newest_n: int | None = None,
    skip_oversize: bool = True,
    disabled_files: list[str] | None = None,
    disabled_folders: list[str] | None = None,
) -> list[tuple]:
    """Apply decision-card scope + user on/off selection to source_files triples."""
    sel = {
        "disabled_files": list(disabled_files or []),
        "disabled_folders": list(disabled_folders or []),
    }
    out = []
    for item in files:
        p, rel, cd = item[0], item[1], item[2]
        if not source_is_enabled(rel, sel):
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if skip_oversize and size > OVERSIZE_BYTES:
            continue
        ext = p.suffix.lower()
        kind = _kind(ext)
        if kind in ("skipped", "cad", "no_extractor"):
            continue
        if mode == "documents" and kind != "doc":
            continue
        if subfolders:
            top = rel.replace("\\", "/").split("/", 1)[0]
            if not any(
                rel == sf or rel.startswith(str(sf).rstrip("/") + "/") or top == sf
                for sf in subfolders
            ):
                continue
        out.append(item)

    if newest_n and newest_n > 0:
        def mtime(item):
            try:
                return item[0].stat().st_mtime
            except OSError:
                return 0.0
        out = sorted(out, key=mtime, reverse=True)[: int(newest_n)]
    return out


def normalize_source_selection(sel: dict | None) -> dict:
    sel = sel if isinstance(sel, dict) else {}
    files = []
    seen_f = set()
    for x in sel.get("disabled_files") or []:
        r = str(x or "").replace("\\", "/").strip()
        if r and r not in seen_f:
            seen_f.add(r)
            files.append(r)
    folders = []
    seen_d = set()
    for x in sel.get("disabled_folders") or []:
        r = str(x or "").replace("\\", "/").rstrip("/").strip()
        if r and r not in seen_d:
            seen_d.add(r)
            folders.append(r)
    return {"disabled_files": files, "disabled_folders": folders}


def source_is_enabled(rel: str, sel: dict | None) -> bool:
    """True unless the file or an ancestor folder was toggled off."""
    rel_n = str(rel or "").replace("\\", "/").strip()
    if not rel_n:
        return True
    sel = normalize_source_selection(sel)
    if rel_n in sel["disabled_files"]:
        return False
    for folder in sel["disabled_folders"]:
        if rel_n == folder or rel_n.startswith(folder + "/"):
            return False
        # root chip: "Pictures" matches top segment
        if "/" not in folder and rel_n.split("/", 1)[0] == folder:
            return False
    return True


def toggle_source_selection(
    sel: dict | None,
    *,
    kind: str,
    path: str,
    on: bool,
) -> dict:
    """Return updated selection. kind is 'file' or 'folder'. on=True means include."""
    out = normalize_source_selection(sel)
    path_n = str(path or "").replace("\\", "/").rstrip("/").strip()
    if not path_n:
        return out
    key = "disabled_folders" if kind == "folder" else "disabled_files"
    cur = list(out[key])
    if on:
        out[key] = [x for x in cur if x != path_n]
    else:
        if path_n not in cur:
            cur.append(path_n)
        out[key] = cur
    return out


def format_decision_card_no(report: dict) -> str:
    gb = report.get("total_gb") or round((report.get("total_bytes") or 0) / (1024 ** 3), 2)
    lo, hi = report.get("est_cost_eur") or [0, 0]
    mlo, mhi = report.get("est_minutes") or [0, 0]
    lines = [
        f"Mappen inneholder {report.get('total_files', 0)} filer ({gb} GB).",
        f"Indekserbare: {report.get('indexable', 0)} · "
        f"hoppes over: {report.get('skipped', 0)} · "
        f"allerede indeksert: {report.get('already_cached', 0)}",
        f"Estimat: €{lo:.0f}–{hi:.0f} · {mlo}–{mhi} min",
    ]
    # foldok_scan: explain silent drops (legacy .doc/.xls/.msg etc.)
    cov = report.get("coverage")
    if cov is not None and cov < 0.95 and report.get("coverage_text"):
        text = str(report["coverage_text"]).strip()
        if len(text) > 1800:
            text = text[:1800].rstrip() + "\n…"
        lines.append("")
        lines.append(text)
    elif report.get("biggest_win"):
        win = report["biggest_win"]
        lines.append(
            f"\nStørste enkeltgevinst: støtt {win.get('ext')} og få "
            f"{win.get('count')} filer til"
            + (f" ({win.get('why')})." if win.get("why") else ".")
        )
    return "\n".join(lines)


def attach_coverage_scan(
    report: dict,
    folders: list[str] | list[Path],
    *,
    lang: str = "no",
    doc_ext: Iterable[str] | None = None,
    photo_ext: Iterable[str] | None = None,
    cad_ext: Iterable[str] | None = None,
    skip_dir_names: Iterable[str] | None = None,
) -> dict:
    """Enrich a pre-scan dict with foldok_scan explanations (zero tokens)."""
    try:
        from foldok_scan import scan as foldok_scan_fn
    except ImportError:
        return report

    texts = []
    merged_reasons: dict[str, int] = {}
    merged_depth: dict[str, list] = {}
    biggest = None
    total_e = indexed_e = 0

    for folder in folders:
        root = Path(folder)
        if not root.is_dir():
            continue
        kwargs = {}
        if doc_ext is not None:
            kwargs["doc_ext"] = doc_ext
        if photo_ext is not None:
            kwargs["photo_ext"] = photo_ext
        if cad_ext is not None:
            kwargs["cad_ext"] = cad_ext
        if skip_dir_names is not None:
            kwargs["skip_dirs"] = set(skip_dir_names) | {
                "capture", "foldok-engine", "feltdok-engine", "node_modules",
                "__pycache__", "releases", ".git", ".cursor",
            }
        sr = foldok_scan_fn(root, **kwargs)
        total_e += len(sr.entries)
        indexed_e += len(sr.indexed)
        texts.append(sr.report(lang=lang))
        for reason, n in sr.by_reason().items():
            merged_reasons[reason] = merged_reasons.get(reason, 0) + n
        for depth, pair in sr.by_depth().items():
            key = str(depth)
            slot = merged_depth.setdefault(key, [0, 0])
            slot[0] += pair[0]
            slot[1] += pair[1]
        win = sr.biggest_win()
        if win and (biggest is None or win[1] > biggest[1]):
            biggest = win

    if total_e:
        report["coverage"] = round(indexed_e / total_e, 3)
        report["coverage_indexed"] = indexed_e
        report["coverage_total"] = total_e
        report["by_reason"] = dict(sorted(merged_reasons.items(), key=lambda kv: -kv[1]))
        report["by_depth"] = merged_depth
        report["coverage_text"] = "\n\n".join(t for t in texts if t)
        if biggest:
            report["biggest_win"] = {
                "ext": biggest[0], "count": biggest[1], "why": biggest[2],
            }
    return report
