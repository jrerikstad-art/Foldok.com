"""Topic brief — thin shell over foldok_ask (question-driven).

No EMC facet allowlists. Sections are composed from ask() answers.
"""
from __future__ import annotations

import hashlib

from foldok_ask import compose_topic_brief

_CACHE: dict[str, dict] = {}


def _cache_key(index, artifact, lang) -> str:
    files = sorted(
        str(e.get("file") or "")
        for e in (index or [])
        if e.get("kind") != "skipped"
    )[:80]
    art = artifact or {}
    blob = "|".join(files) + "|" + str(art.get("name") or "") + "|" + (lang or "no")
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
