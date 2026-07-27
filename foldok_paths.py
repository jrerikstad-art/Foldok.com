"""Foldok on-disk names — prefer foldok_*, still read legacy feltdok_*."""
from __future__ import annotations

from pathlib import Path

ENGINE_DIR_NAMES = ("foldok-engine", "feltdok-engine")
PRODUCT_DIR_NAMES = ("foldok", "feltdok")

STATE_FILE = ".foldok_state.json"
STATE_FILE_LEGACY = ".feltdok_state.json"
CACHE_DIR = ".foldok_cache"
CACHE_DIR_LEGACY = ".feltdok_cache"
REF_CACHE_DIR = ".foldok_ref_cache"
REF_CACHE_DIR_LEGACY = ".feltdok_ref_cache"
DRAFTS_DIR = ".foldok_drafts"
DRAFTS_DIR_LEGACY = ".feltdok_drafts"
TEMPLATES_DIR = ".foldok_templates"
TEMPLATES_DIR_LEGACY = ".feltdok_templates"
QUARANTINE_DIR = ".foldok_quarantine"
QUARANTINE_DIR_LEGACY = ".feltdok_quarantine"
INDEX_DIR = ".foldok_index"
INDEX_DIR_LEGACY = ".feltdok_index"
INDEX_MANIFEST = ".foldok_index_manifest.json"
INDEX_MANIFEST_LEGACY = ".feltdok_index_manifest.json"
TELEMETRY_LOG = ".foldok_telemetry.jsonl"
TELEMETRY_LOG_LEGACY = ".feltdok_telemetry.jsonl"
TELEMETRY_OPT_IN = ".foldok_telemetry_opt_in"
TELEMETRY_OPT_IN_LEGACY = ".feltdok_telemetry_opt_in"

SKIP_PRODUCT_DIRS = {
    "capture", "foldok-engine", "feltdok-engine",
    "node_modules", "__pycache__", "releases",
}
SKIP_CACHE_DIR_NAMES = {
    ".foldok_index", ".feltdok_index",
    ".foldok_cache", ".feltdok_cache",
}


def _first_existing(folder: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        cand = folder / name
        if cand.exists():
            return cand
    return None


def resolve_file(folder, preferred: str, legacy: str) -> Path:
    """Return existing preferred or legacy path; else preferred (for writes)."""
    root = Path(folder)
    found = _first_existing(root, (preferred, legacy))
    return found if found is not None else root / preferred


def resolve_dir(folder, preferred: str, legacy: str) -> Path:
    return resolve_file(folder, preferred, legacy)


def state_path(folder) -> Path:
    return resolve_file(folder, STATE_FILE, STATE_FILE_LEGACY)


def cache_dir(folder) -> Path:
    return resolve_dir(folder, CACHE_DIR, CACHE_DIR_LEGACY)


def drafts_dir(folder) -> Path:
    return resolve_dir(folder, DRAFTS_DIR, DRAFTS_DIR_LEGACY)


def templates_dir(folder) -> Path:
    return resolve_dir(folder, TEMPLATES_DIR, TEMPLATES_DIR_LEGACY)


def quarantine_dir(folder) -> Path:
    return resolve_dir(folder, QUARANTINE_DIR, QUARANTINE_DIR_LEGACY)


def index_dir(folder) -> Path:
    return resolve_dir(folder, INDEX_DIR, INDEX_DIR_LEGACY)


def index_manifest_path(folder) -> Path:
    return resolve_file(folder, INDEX_MANIFEST, INDEX_MANIFEST_LEGACY)


def ref_cache_dir(engine_root) -> Path:
    return resolve_dir(engine_root, REF_CACHE_DIR, REF_CACHE_DIR_LEGACY)


def telemetry_log_path(engine_root) -> Path:
    return resolve_file(engine_root, TELEMETRY_LOG, TELEMETRY_LOG_LEGACY)


def telemetry_opt_in_path(engine_root) -> Path:
    return resolve_file(engine_root, TELEMETRY_OPT_IN, TELEMETRY_OPT_IN_LEGACY)


def is_product_tree(root: Path) -> bool:
    root = Path(root)
    for eng in ENGINE_DIR_NAMES:
        if (root / eng / "VERSION").exists() and (root / "capture").is_dir():
            return True
    if root.name.lower() in PRODUCT_DIR_NAMES or root.name.lower() in ENGINE_DIR_NAMES:
        return True
    if (root / "VERSION").exists() and (root / "foldok_compile.py").exists():
        return True
    if (root / "VERSION").exists() and (root / "feltdok_compile.py").exists():
        return True
    return False
