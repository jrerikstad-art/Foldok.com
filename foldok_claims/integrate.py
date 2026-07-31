"""Wiring claims into retrieval — the change that fills the empty sections.

The Temabrief had a section called "Kabelklasser og separasjon" with the right
heading, in the right place in the narrative, and it never named a single class.
Not a writing failure. ``foldok_ask/retrieve.py`` offers two retrievable units:

    _add("caption", e.get("caption"))          # a summary of the whole file
    _add("detail",  e.get("detail_summary"))   # a longer summary of the whole file

A caption is a sentence about a *document*. "Klasse 1A omfatter
millivolt-transdusere og radiomottakere" is a sentence about the *subject*. The
index held nothing at the second grain, so the section had nothing to say and the
composer spliced a file abstract into a Norwegian frame instead:

    "I praksis handler det blant annet om electromagnetic compatibility testing
     of Marco Steel Wire Cable Tray, independently verified by York EMC..."

Three changes here, none of them a new engine:

1. ``as_chunks`` emits claims in the shape retrieve.py already uses, with
   ``kind="claim"``, so nothing downstream needs to know they are new.
2. ``RANKING_PATCH`` puts a claim above a caption, and a binding claim above a
   loose one. A summary should never outrank a statement.
3. ``standards_register`` builds the register from rule claims instead of
   character windows — which is why the old one printed entries beginning with
   "); cable classification".
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .coherence import check
from .extract import extract
from .model import Claim, ClaimSet

# Fields on a workbench index entry that carry prose worth reading for claims.
TEXT_FIELDS = ("detail_summary", "text", "body", "caption", "summary")

STANDARD_RX = re.compile(
    r"\b((?:EN|IEC|ISO|IEEE|NEMA|UL|BS|ASTM|MIL[- ]STD|HD|NEK|DNV)"
    r"[\s\-]?[A-Z]{0,4}[\s\-]?\d{2,5}(?:[-–:]\d{1,4})*(?::\d{4})?)\b"
)


@dataclass
class IndexedClaims:
    claims: ClaimSet
    per_file: dict[str, int]
    files_read: int = 0
    files_without_text: int = 0

    def summary(self) -> str:
        counts = ", ".join(f"{v} {k}" for k, v in self.claims.counts().items())
        line = f"{len(self.claims)} claim(s) from {self.files_read} file(s)"
        if self.files_without_text:
            line += f" ({self.files_without_text} had no readable prose)"
        return line + (f" — {counts}" if counts else "")


def claims_from_index(
    index: Iterable[Mapping[str, Any]],
    *,
    min_confidence: float = 0.4,
    max_files: int = 400,
) -> IndexedClaims:
    """Read claims out of an indexed folder.

    Prefers ``detail_summary`` over ``caption``: the detail is prose about the
    content, the caption is a label for the file. Both are read, because a
    caption occasionally carries the only statement of a rule.
    """
    all_claims: list[Claim] = []
    per_file: dict[str, int] = {}
    read = 0
    empty = 0

    for entry in list(index or [])[:max_files]:
        if entry.get("kind") == "skipped":
            continue
        path = str(entry.get("file") or "")
        if not path:
            continue
        file_id = Path(path).name
        prose = "\n".join(
            str(entry.get(field) or "") for field in TEXT_FIELDS
        ).strip()
        if len(prose) < 40:
            empty += 1
            continue
        read += 1
        found = extract(prose, source=file_id, min_confidence=min_confidence).claims.claims
        if found:
            per_file[file_id] = len(found)
            all_claims.extend(found)

    return IndexedClaims(
        claims=ClaimSet(all_claims), per_file=per_file,
        files_read=read, files_without_text=empty,
    )


def as_chunks(claims: ClaimSet | Sequence[Claim], *, paths: Mapping[str, str] | None = None) -> list[dict]:
    """Claims in retrieve.py's chunk shape.

    ``text`` is the claim in full. The old citation path did ``span=text[:80]``,
    which is where "enabling more efficie relevant for samme argument" came from
    — a summary cut mid-word with a connector glued on. A claim is already one
    sentence; it is cited whole or not at all.
    """
    paths = paths or {}
    items = list(claims.claims if isinstance(claims, ClaimSet) else claims)
    out: list[dict] = []
    for claim in items:
        file_id = claim.source or ""
        cid = hashlib.sha1(f"claim|{claim.id}".encode()).hexdigest()[:16]
        out.append({
            "chunk_id": cid,
            "file_id": file_id,
            "path": paths.get(file_id, file_id),
            "text": claim.text,
            "pages": "",
            "kind": "claim",
            "tags": " ".join(filter(None, [
                claim.type, claim.modality, claim.predicate,
                claim.scope.cable_class and f"klasse {claim.scope.cable_class}",
            ])),
            "fact_key": claim.predicate or claim.type,
            # Claim metadata, so ranking and rendering can use it without
            # re-parsing the sentence.
            "claim_type": claim.type,
            "claim_modality": claim.modality,
            "claim_binding": claim.binding,
            "claim_subject": claim.subject,
            "claim_scope": str(claim.scope) if claim.scope.known else "",
            "claim_quantity": str(claim.quantity) if claim.quantity else "",
            "claim_negated": claim.negated,
            "confidence": claim.confidence,
        })
    return out


# ----------------------------------------------------------------------
def standards_register(claims: ClaimSet | Sequence[Claim]) -> list[dict[str, Any]]:
    """A register of what each standard actually requires.

    The old register printed entries like::

        UL 870 — ); cable classification (Class 1-6); development roadmap from
        ISO 9001 — ), corrosion mechanisms and surface treatments (galvanic,

    Those are substring windows taken from wherever the standard's name appeared.
    This groups the *rule* claims that cite each standard, so the register says
    what the standard demands rather than what happened to follow its name.
    """
    items = list(claims.claims if isinstance(claims, ClaimSet) else claims)
    register: dict[str, dict[str, Any]] = {}

    for claim in items:
        for match in STANDARD_RX.finditer(claim.text):
            name = _normalise_standard(match.group(1))
            entry = register.setdefault(name, {
                "standard": name, "requirements": [], "sources": set(), "claim_ids": [],
            })
            if claim.binding or claim.type in ("rule", "constraint", "reference"):
                entry["requirements"].append(claim.text)
                entry["claim_ids"].append(claim.id)
            if claim.source:
                entry["sources"].add(claim.source)

    out: list[dict[str, Any]] = []
    for name, entry in sorted(register.items()):
        requirements = list(dict.fromkeys(entry["requirements"]))
        out.append({
            "standard": name,
            "requirement_count": len(requirements),
            "requirements": requirements[:6],
            "sources": sorted(entry["sources"]),
            "claim_ids": entry["claim_ids"][:6],
            # An entry with no requirement is a name that was mentioned, not a
            # standard the project is held to. Say so rather than inventing a
            # description for it.
            "mentioned_only": not requirements,
        })
    return out


def register_markdown(register: Sequence[Mapping[str, Any]], *, lang: str = "no") -> str:
    if not register:
        return ""
    held = [r for r in register if not r["mentioned_only"]]
    named = [r for r in register if r["mentioned_only"]]
    lines: list[str] = []
    if held:
        lines.append("**Krav fra standarder**" if lang.startswith("no") else "**Requirements from standards**")
        for r in held:
            lines.append(f"- **{r['standard']}** — {r['requirements'][0]}"
                         + (f" (+{r['requirement_count'] - 1} flere)" if r["requirement_count"] > 1 else ""))
    if named:
        lines.append("")
        lines.append(
            "**Nevnt, men uten krav i underlaget**" if lang.startswith("no")
            else "**Named, with no requirement in the material**"
        )
        lines.append(", ".join(r["standard"] for r in named))
    return "\n".join(lines)


def _normalise_standard(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).strip().upper()
    text = text.replace("MIL STD", "MIL-STD")
    return re.sub(r"\s*-\s*", "-", text) if text.count("-") > 1 else text


# ----------------------------------------------------------------------
# Patches to foldok_ask/retrieve.py
# ----------------------------------------------------------------------
RANKING_PATCH = '''
    # --- claims outrank summaries -------------------------------------
    # A caption is a sentence about a document; a claim is a sentence about the
    # subject. Ranking them equally is why a section about cable classes filled
    # up with file abstracts instead of classes.
    if chunk.get("kind") == "claim":
        score += 0.18
        if chunk.get("claim_binding"):
            score += 0.07          # a requirement beats a loose statement
    elif chunk.get("kind") in ("caption", "detail"):
        score += 0.05
'''

RELEVANCE_PATCH = '''
    # A claim that matches the question's intent is the best possible hit.
    if kind == "claim" and intent_boost > 0:
        intent_boost += 0.14
    elif kind in ("caption", "detail") and intent_boost > 0:
        intent_boost += 0.08
'''

OLD_RANKING = '''    if chunk.get("kind") in ("caption", "detail"):
        score += 0.05'''

OLD_RELEVANCE = '''    if kind in ("caption", "detail") and intent_boost > 0:
        intent_boost += 0.08'''


def apply_ranking_patch(path: str | Path, *, dry_run: bool = False) -> tuple[bool, str]:
    """Make claims outrank captions in retrieve.py. Idempotent."""
    p = Path(path)
    if not p.exists():
        return (False, f"{p} does not exist")
    text = p.read_text(encoding="utf-8", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    flat = text.replace("\r\n", "\n")

    if 'chunk.get("kind") == "claim"' in flat:
        return (True, "already patched")

    changed = 0
    if OLD_RANKING in flat:
        flat = flat.replace(OLD_RANKING, RANKING_PATCH.strip("\n"), 1)
        changed += 1
    if OLD_RELEVANCE in flat:
        flat = flat.replace(OLD_RELEVANCE, RELEVANCE_PATCH.strip("\n"), 1)
        changed += 1
    if not changed:
        return (False, "the caption boosts in retrieve.py no longer look the way they did — "
                       "add the claim branches by hand next to them")
    if dry_run:
        return (True, f"would patch {changed} ranking site(s)")
    p.write_text(flat.replace("\n", newline), encoding="utf-8")
    return (True, f"patched {changed} ranking site(s): claims now outrank captions")


def coherence_section(claims: ClaimSet, *, lang: str = "no") -> str:
    """The findings block — the part a summary cannot produce."""
    report = check(claims)
    if not report.findings:
        return ""
    head = ("**Konflikter og åpne spørsmål**" if lang.startswith("no")
            else "**Conflicts and open questions**")
    lines = [head]
    for finding in report.findings:
        lines.append(f"- {finding.summary}")
        if finding.detail:
            lines.append(f"  {finding.detail.replace(chr(10), ' ')}")
        if finding.question:
            lines.append(f"  → {finding.question}")
    return "\n".join(lines)
