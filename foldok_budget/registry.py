"""Citation scope — the blocker that kept every document thin.

``author_doc.CiteRegistry`` tracks ``_body_used`` as a **document-wide** set, and
``_pick_claims`` filters on it::

    if not cites.unused(local.file_id) and out:
        continue

Once a file has been cited anywhere in the document, every other claim from that
file is discarded for the rest of the document. A 30-page EMC basis of design
contributes exactly one sentence and is then spent. A second ceiling sits inside
``_pick_claims`` itself (``files: set[str]``), so a file cannot contribute twice
even within one section.

Three consequences, and they explain every symptom that was reported:

*   **Thin documents.** The ceiling is the number of *files*, not the number of
    statements. Forty files, forty sentences, whatever the page count.
*   **Vendor asides promoted to steps.** Project files are consumed early. By the
    time an installation sequence is authored, the only files still "unused" are
    marginal ones — so a four-word line from page 23 of a supplier manual becomes
    step 1. It did not outrank the project material; the project material was
    banned.
*   **More sections did not help.** Each new section draws from files nobody has
    touched, which is by definition the least relevant material left.

The intent was sound — spread citations, do not let one document dominate. The
scope was wrong. A rich source *should* be quotable many times across a document;
what must not happen is one source dominating a single section.

So the rule becomes per-section, with a document-wide ceiling that is generous
rather than absolute.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

SCHEMA_VERSION = 1

# How often one file may appear in one section before it starts to read like a
# transcription of that file rather than a document.
PER_SECTION_DEFAULT = 3

# How much of a whole document one source may account for. High enough that a
# governing standard can carry a document; low enough to notice a monoculture.
DOCUMENT_SHARE_DEFAULT = 0.45


@dataclass
class CiteScope:
    """Citation bookkeeping with the scope it should always have had.

    Drop-in for ``CiteRegistry``: ``number_for``, ``mark``, ``unused`` and
    ``claim_fresh`` keep their signatures, so ``author_doc`` needs no changes
    beyond calling ``enter_section``.
    """

    per_section: int = PER_SECTION_DEFAULT
    document_share: float = DOCUMENT_SHARE_DEFAULT
    _order: list[str] = field(default_factory=list)
    _claim_texts: set[str] = field(default_factory=set)
    _section: str = ""
    _section_uses: Counter = field(default_factory=Counter)
    _document_uses: Counter = field(default_factory=Counter)
    _total: int = 0

    # -- section lifecycle ------------------------------------------------
    def enter_section(self, section_key: str) -> None:
        """Call once per section. Resets the per-section budget."""
        self._section = section_key or ""
        self._section_uses = Counter()

    # -- the interface author_doc already uses ----------------------------
    def number_for(self, file_id: str) -> int:
        fid = (file_id or "").strip()
        if not fid:
            return 0
        if fid not in self._order:
            self._order.append(fid)
        return self._order.index(fid) + 1

    def mark(self, file_id: str, *, body: bool = True) -> str:
        fid = (file_id or "").strip()
        if not fid:
            return ""
        n = self.number_for(fid)
        if body:
            self._section_uses[fid] += 1
            self._document_uses[fid] += 1
            self._total += 1
        return f"[{n}]" if n else ""

    def unused(self, file_id: str) -> bool:
        """Now means 'not yet used *in this section*'.

        Kept as a ranking preference rather than a filter — a fresh source is
        nicer, but an exhausted one is not forbidden.
        """
        return self._section_uses.get((file_id or "").strip(), 0) == 0

    def claim_fresh(self, text: str) -> bool:
        key = re.sub(r"\s+", " ", (text or "").lower())[:90]
        if not key or key in self._claim_texts:
            return False
        self._claim_texts.add(key)
        return True

    # -- the new question -------------------------------------------------
    def may_cite(self, file_id: str) -> bool:
        """Is this file still allowed here? Two ceilings, both generous."""
        fid = (file_id or "").strip()
        if not fid:
            return False
        if self._section_uses.get(fid, 0) >= self.per_section:
            return False
        if self._total >= 12:
            share = self._document_uses.get(fid, 0) / max(1, self._total)
            if share > self.document_share:
                return False
        return True

    def refusal_reason(self, file_id: str) -> str:
        fid = (file_id or "").strip()
        if self._section_uses.get(fid, 0) >= self.per_section:
            return f"already cited {self.per_section}x in this section"
        share = self._document_uses.get(fid, 0) / max(1, self._total)
        if self._total >= 12 and share > self.document_share:
            return f"accounts for {share:.0%} of the document already"
        return ""

    # -- reporting ---------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "citations": self._total,
            "sources_used": len(self._document_uses),
            "sources_known": len(self._order),
            "per_source": dict(self._document_uses.most_common()),
        }

    def report(self, *, lang: str = "no") -> str:
        s = self.stats()
        if lang.startswith("no"):
            return (f"{s['citations']} siteringer fra {s['sources_used']} av "
                    f"{s['sources_known']} kilder")
        return (f"{s['citations']} citations from {s['sources_used']} of "
                f"{s['sources_known']} sources")


def section_budget(
    available_claims: int,
    *,
    floor: int = 3,
    ceiling: int = 12,
) -> int:
    """Claims per section, scaled to what survived retrieval.

    ``n: int = 2`` is a constant: two claims per section whether four candidates
    were found or four hundred. Scaling keeps a thin section honest and lets a
    well-evidenced one be worth reading.
    """
    if available_claims <= 0:
        return 0
    return max(floor, min(ceiling, available_claims // 2))


def rank_key(
    file_id: str,
    *,
    scope: CiteScope,
    role: str = "unknown",
    signal_match: bool = False,
    kind: str = "",
) -> tuple:
    """Ordering for candidate claims.

    Role comes first and that is the substantive change. A project file outranks
    a vendor manual before any keyword is considered, so a supplier's aside can
    only ever be a fallback — never a competitor to the project's own material.
    """
    role_rank = {"project": 0, "unknown": 1, "reference": 2, "ignore": 3}.get(role, 1)
    return (
        role_rank,
        0 if scope.unused(file_id) else 1,
        0 if signal_match else 1,
        0 if kind in ("measure", "principle", "rule", "constraint") else 1,
    )
