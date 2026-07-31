"""Reconciliation — does the manifest say what the product does?

Four kinds of drift, and the first two are the ones that produced the bug:

``undeclared``
    The engine ships it, the manifest never mentions it.  Under the hard rule
    *"capability claims must come from CAPABILITIES CONTEXT"*, the assistant will
    deny it to every user, forever, and behave correctly while doing so.

``contradicted``
    The ``cannot`` list denies something that ships.  Worse than silence: it is
    an active false statement in the prompt.

``unqualified_denial``
    A denial containing a broad verb — *tegne*, *draw*, *generate* — with no
    object tying it down.  ``tegne eller modellere i 3D`` was written to disclaim
    CAD; a model under pressure reads it as "cannot draw".  A denial that
    generalises is a denial that will over-apply.

``overclaimed``
    The manifest promises something no engine provides.  Rarer, and the reason
    the check runs in both directions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from .model import BROAD_VERBS, Capability, Denial, Drift, Reconciliation
from .discover import discover

MANIFEST = "capabilities.json"


def load_manifest(root: str | Path = ".", name: str = MANIFEST) -> dict[str, Any]:
    p = Path(root) / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def reconcile(
    root: str | Path = ".",
    manifest: dict[str, Any] | None = None,
    capabilities: Sequence[Capability] | None = None,
) -> Reconciliation:
    manifest = load_manifest(root) if manifest is None else manifest
    found = list(capabilities) if capabilities is not None else discover(root)

    blob = _declaration_blob(manifest)
    declared_ids = {c.get("id") for c in manifest.get("capabilities", []) if isinstance(c, dict)}
    denials = [Denial(text=str(t)) for t in manifest.get("cannot", [])]

    result = Reconciliation(
        capabilities=found,
        declared=sorted(str(d) for d in declared_ids if d),
        denials=denials,
    )

    for capability in found:
        mentioned = capability.id in declared_ids or _mentioned(capability, blob)
        if not mentioned:
            result.drift.append(
                Drift(
                    code="undeclared",
                    capability=capability.id,
                    detail=(
                        f"'{capability.id}' ships ({_evidence_line(capability)}) but the "
                        "manifest never mentions it"
                    ),
                    fix=(
                        "add the generated block — until then the assistant is instructed "
                        "never to claim it, and will deny it to every user"
                    ),
                )
            )
        for denial in denials:
            if _contradicts(denial, capability):
                result.drift.append(
                    Drift(
                        code="contradicted",
                        capability=capability.id,
                        denial=denial.text,
                        detail=f"'{denial.text}' denies something '{capability.id}' does",
                        fix=(
                            "qualify the denial so it names what is actually out of scope, or "
                            "move it into the capability's limits where it stays scoped"
                        ),
                    )
                )

    for denial in denials:
        broad = _broad_terms(denial)
        if broad and not _has_object(denial):
            result.drift.append(
                Drift(
                    code="unqualified_denial",
                    denial=denial.text,
                    detail=(
                        f"'{denial.text}' uses a broad verb ({', '.join(sorted(broad))}) "
                        "with nothing tying it down"
                    ),
                    fix=(
                        "name the format or scope it applies to — a bare negative gets "
                        "generalised by the model"
                    ),
                )
            )

    for declared in manifest.get("capabilities", []):
        if not isinstance(declared, dict):
            continue
        cid = declared.get("id")
        if cid and cid not in {c.id for c in found}:
            result.drift.append(
                Drift(
                    code="overclaimed",
                    capability=str(cid),
                    detail=f"the manifest declares '{cid}' but no engine provides it",
                    fix="remove it, or mark confidence 'planned' so it is not offered as shipped",
                )
            )

    return result


# ----------------------------------------------------------------------
# Fields that say what the *user* must supply, or what we cannot do. A template
# asking for "□ koblingsskjema" is an input checklist, not a claim that Foldok
# draws wiring diagrams — reading it as one is how a checker misses the very
# gap it exists to find.
NOT_A_CLAIM = ("templates", "file_types", "cannot", "cannot_moved_to_limits",
               "forbidden_privacy_phrases")


def _declaration_blob(manifest: dict[str, Any]) -> str:
    claims = {k: v for k, v in manifest.items() if k not in NOT_A_CLAIM}
    return json.dumps(claims, ensure_ascii=False).lower()


def _mentioned(capability: Capability, blob: str) -> bool:
    """Declared means the manifest names the thing, not a word near it.

    An earlier version matched any keyword, so "electrical" appearing anywhere
    counted as declaring the diagram engine. That is the same false negative
    that let the original bug ship, reproduced in the checker meant to catch it.
    Capabilities now state their own anchors.
    """
    if capability.id in blob:
        return True
    anchors = capability.anchors or (capability.id,)
    return any(a.lower() in blob for a in anchors)


def _contradicts(denial: Denial, capability: Capability) -> bool:
    """A denial contradicts a capability when it negates the same verb-object.

    Deliberately conservative: it needs a shared broad verb *and* an overlapping
    object word. Flagging every loose overlap would make the check noise, and a
    noisy check is one that gets switched off.
    """
    denial_verbs = _broad_terms(denial)
    if not denial_verbs:
        return False
    capability_verbs = {
        BROAD_VERBS[w] for w in capability.keywords if w in BROAD_VERBS
    } | {capability.verb}
    if not (denial_verbs & capability_verbs):
        return False

    # If the denial names something the capability explicitly excludes, it is a
    # correct denial, not a contradiction.
    limit_words: set[str] = set()
    for limit in capability.limits:
        limit_words |= {w.lower() for w in limit.text.split()} | {
            w.lower() for w in limit.reason.split()
        }
    if denial.keywords & limit_words:
        return False

    # Compare normalised tokens, not raw ones: "diagrammer" and "diagrams" are
    # the same claim in two languages, and a raw string overlap misses it.
    return bool(_normalise(denial.keywords) & _normalise(capability.keywords))


def _normalise(words: set[str]) -> set[str]:
    return {BROAD_VERBS.get(w, w) for w in words}


def _broad_terms(denial: Denial) -> set[str]:
    return {BROAD_VERBS[w] for w in denial.keywords if w in BROAD_VERBS}


def _has_object(denial: Denial) -> bool:
    """Does the denial name a format, standard or scope that pins it down?"""
    text = denial.text.lower()
    anchors = (
        "dwg", "step", "iges", "cad", "3d", "pdf", "dxf", "revit", "ifc",
        "juridisk", "legal", "beviskjede", "chain of custody", "signere", "sign",
        "beregning", "calculation", "verdier", "values",
    )
    if any(a in text for a in anchors):
        # "3d" alone still generalises when it sits next to a bare verb like
        # "tegne" — the CAD line is exactly that shape.
        broad = _broad_terms(denial)
        return not (broad - {"model"})
    return False


def evidence_summary(capabilities: Iterable[Capability]) -> str:
    return "; ".join(f"{c.id} ({_evidence_line(c)})" for c in capabilities)


def _evidence_line(capability: Capability) -> str:
    ev = capability.evidence
    for key in ("symbols", "requirements", "packs", "formats", "purposes", "page_sizes"):
        if key in ev:
            value = ev[key]
            n = len(value) if isinstance(value, (list, tuple, dict)) else value
            return f"{n} {key}"
    return capability.engine or "shipped"
