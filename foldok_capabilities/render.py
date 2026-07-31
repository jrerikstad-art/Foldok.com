"""Rendering — the manifest block, and the sentences the assistant may say.

Two outputs from one source:

``manifest_block`` goes into ``capabilities.json`` and satisfies the hard rule in
``hub_chat.py`` that claims must come from the manifest.

``prompt_lines`` is what a person would read in the prompt. Both are generated,
so they cannot disagree with each other or with the code.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Sequence

from .model import Capability


def manifest_block(capabilities: Sequence[Capability]) -> dict[str, Any]:
    """The block to merge into capabilities.json."""
    return {
        "capabilities": [c.to_dict() for c in sorted(capabilities, key=lambda c: c.id)],
        "capabilities_generated": True,
        "capabilities_note": (
            "Generated from the engines by foldok_capabilities. Do not hand-edit: "
            "a hand-maintained list falls behind the code and the assistant then "
            "denies features that ship."
        ),
    }


def merge_into(manifest: dict[str, Any], capabilities: Sequence[Capability]) -> dict[str, Any]:
    """Merge, and rewrite denials that a capability already qualifies.

    The ``cannot`` line that caused the bug — 'tegne eller modellere i 3D' —
    disappears here, because '3D' is already a limit on the diagrams capability
    where it stays scoped to the thing it qualifies.
    """
    out = dict(manifest)
    out.update(manifest_block(capabilities))

    # Denials are Norwegian and limits are English, so raw word overlap misses.
    # Normalise the verbs the same way the contradiction check does, and require
    # a shared concrete token (3d, cad, dwg) so nothing is moved on a verb alone.
    from .model import BROAD_VERBS, _words

    def signature(text: str) -> tuple[set[str], set[str]]:
        words = _words(text)
        verbs = {BROAD_VERBS[w] for w in words if w in BROAD_VERBS}
        concrete = words & {"3d", "cad", "dwg", "step", "iges", "dxf", "ifc", "revit"}
        return verbs, concrete

    limit_signatures = [
        signature(f"{l.text} {l.reason}") for c in capabilities for l in c.limits
    ]
    kept: list[str] = []
    moved: list[str] = []
    for denial in manifest.get("cannot", []):
        verbs, concrete = signature(str(denial))
        covered = any(
            (verbs & lv) and (concrete & lc)
            for lv, lc in limit_signatures
        )
        (moved if covered else kept).append(str(denial))
    out["cannot"] = kept
    if moved:
        out["cannot_moved_to_limits"] = moved
    return out


def prompt_lines(capabilities: Iterable[Capability], *, lang: str = "en") -> list[str]:
    """One line per capability, for a human reading the system prompt."""
    lines: list[str] = []
    for c in sorted(capabilities, key=lambda x: x.id):
        lines.append(f"- {c.summary or c.sentence()}")
        for limit in c.limits:
            lines.append(f"    not: {limit.text}")
    return lines


def write_manifest(path, manifest: dict[str, Any]) -> str:
    from pathlib import Path

    p = Path(path)
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    p.write_text(text, encoding="utf-8")
    return text
