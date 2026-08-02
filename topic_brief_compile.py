"""Topic brief — document-first shell over foldok_ask.

Plan outline → author prose with [n] cites → gaps + source appendix.
No EMC facet allowlists.
"""
from __future__ import annotations

import hashlib

from foldok_ask import compose_topic_brief

_CACHE: dict[str, dict] = {}


def _cache_key(index, artifact, lang) -> str:
    from pathlib import Path as _P
    ver = ""
    try:
        ver = (_P(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        pass
    files = sorted(
        str(e.get("file") or "")
        for e in (index or [])
        if e.get("kind") != "skipped"
    )[:80]
    art = artifact or {}
    blob = "|".join(files) + "|" + str(art.get("name") or "") + "|" + (lang or "no") + "|" + ver + "|scrub-v3"
    return hashlib.sha1(blob.encode("utf-8", errors="replace")).hexdigest()[:20]


def _parts_for(index, artifact, lang):
    key = _cache_key(index, artifact, lang)
    if key not in _CACHE:
        _CACHE[key] = compose_topic_brief(
            index, questions=None, artifact=artifact, lang=lang,
        )
        # Bound cache size
        if len(_CACHE) > 8:
            oldest = next(iter(_CACHE))
            if oldest != key:
                _CACHE.pop(oldest, None)
    return _CACHE[key]


def compile_topic_brief_section(sec_key, mapping, index, artifact, lang="no"):
    """Map template section keys to ask-composed bodies."""
    sk = (sec_key or "").strip().lower()
    # Legacy facet section keys — no longer generated
    if sk in ("emc_zones", "cable_classes", "earthing", "standards_register"):
        return ""
    parts = _parts_for(index, artifact, lang)
    if sk in ("overview", "answers", "gaps", "source_register"):
        return parts.get(sk) or ""
    return None


def blueprint_for(index, artifact, lang="no") -> dict | None:
    """NarrativeBlueprint dict for persistence on the document."""
    parts = _parts_for(index, artifact, lang)
    return parts.get("_blueprint")
