"""Placeholder resolve — never invent values."""
from __future__ import annotations

import re
from typing import Any

PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def deep_get(data: dict | None, key: str, default=None):
    if not data or not key:
        return default
    cur: Any = data
    for k in key.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def facts_lookup(facts: dict | list | None, key: str):
    if facts is None:
        return None
    if isinstance(facts, dict):
        if key in facts:
            slot = facts[key]
            if isinstance(slot, dict) and "value" in slot:
                return slot.get("value")
            return slot
        return deep_get(facts, key)
    if isinstance(facts, list):
        for row in facts:
            if isinstance(row, dict) and row.get("key") == key:
                return row.get("value")
    return None


def resolve_placeholder(
    text: str,
    *,
    artifact: dict | None = None,
    facts: dict | list | None = None,
    missing: str | None = None,
) -> str:
    """
    Replace {{key}} from artifact / facts.
    missing=None → leave blank (print-safe); missing="[MANGLER]" for draft/md.
    """
    if not isinstance(text, str) or "{{" not in text:
        return text if isinstance(text, str) else str(text)

    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        val = deep_get(artifact, key)
        if val is None:
            val = facts_lookup(facts, key)
        if val is None or val == "":
            return "" if missing is None else str(missing)
        return str(val)

    return PLACEHOLDER_RE.sub(repl, text)
