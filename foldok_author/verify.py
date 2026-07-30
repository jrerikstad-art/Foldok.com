"""Verification — silence is not safety.

The design this replaces classified a sentence as grounded when it matched no
fact and contained no number. Tested on three invented safety instructions, all
three passed:

    [grounded] Disconnect the battery before servicing the hydraulic manifold.
    [grounded] Release the residual pressure by cycling the boom lever.
    [grounded] Remove the counterweight before lifting the upper structure.

Matching on values catches an invented *number*. It cannot catch an invented
*action*, because an action has no value to match — and an invented action in a
manual is the one that hurts somebody.

So the default is inverted. A sentence that asserts anything and links to no
fact is **ungrounded**, whether or not it contains a digit. Connective prose
that asserts nothing is ``unverifiable`` and reported separately, because
"cannot be checked" and "checked and fine" are different things and collapsing
them is how the first version passed a safety instruction.
"""

from __future__ import annotations

import re

from .model import Claim, Fact, Plan, Result

NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")

# An imperative opening is an instruction, and an instruction with no fact
# behind it is the dangerous case rather than the neutral one.
IMPERATIVE = re.compile(
    r"^\s*(?:do not|never|always|"
    r"disconnect|connect|remove|install|fit|tighten|loosen|check|verify|ensure|"
    r"release|isolate|lock|secure|measure|test|replace|clean|inspect|start|stop|"
    r"koble|fjern|monter|kontroller|sjekk|sikre|løsne|stram|mål|test|start|stopp|"
    r"ikke |aldri |alltid )",
    re.I,
)

# Words that carry a factual assertion about the subject.
ASSERTIVE = re.compile(
    r"\b(is|are|was|were|has|have|shall|must|delivers?|operates?|weighs?|consists?|"
    r"contains?|requires?|rated|supplied|measured|connects?|provides?|"
    r"er|har|skal|må|veier|består|inneholder|krever|leverer|måler)\b",
    re.I,
)


def verify(prose: str, plan: Plan, facts: list[Fact]) -> Result:
    by_id = {f.id: f for f in facts}
    claims: list[Claim] = []
    used: set[str] = set()

    for sentence in _sentences(prose):
        linked = [f.id for f in facts if any(t in sentence.lower() for t in f.tokens())]
        used.update(linked)

        if linked:
            claims.append(Claim(sentence, linked, "grounded"))
            continue

        if IMPERATIVE.match(sentence):
            claims.append(Claim(
                sentence, [], "ungrounded",
                "an instruction with no fact behind it — this engine does not write "
                "procedures; author them instead",
            ))
            continue

        if NUMBER.search(sentence):
            claims.append(Claim(sentence, [], "ungrounded", "a number that matches no fact"))
            continue

        if ASSERTIVE.search(sentence):
            claims.append(Claim(sentence, [], "ungrounded", "asserts something no fact supports"))
            continue

        claims.append(Claim(sentence, [], "unverifiable", "connective prose, asserts nothing"))

    gaps = [c.text for c in claims if c.status == "ungrounded"]
    unused = [fid for fid in plan.must_include if fid not in used and fid in by_id]

    return Result(
        intent=plan.intent, prose=(prose or "").strip(), plan=plan,
        claims=claims, gaps=gaps, unused_facts=unused,
    )


# A naive split on "." cuts "27.07.2026" into three sentences and "J. R.
# Erikstad" into two, so a correct record fails verification on its own date.
_PROTECT = (
    (re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b"), r"\1<D>\2<D>\3"),   # 27.07.2026
    (re.compile(r"\b([A-ZÆØÅ])\.\s(?=[A-ZÆØÅ])"), r"\1<I> "),                    # J. R.
    (re.compile(r"\b(nr|no|jf|osv|bl\.a|f\.eks|e\.g|i\.e|ca|pkt|kap)\.", re.I), r"\1<A>"),
)


def _sentences(text: str) -> list[str]:
    guarded = text or ""
    for pattern, repl in _PROTECT:
        guarded = pattern.sub(repl, guarded)
    parts = re.split(r"(?<=[.!?])\s+|\n+", guarded)
    out: list[str] = []
    for part in parts:
        restored = part.replace("<D>", ".").replace("<I>", ".").replace("<A>", ".")
        if restored.strip():
            out.append(restored.strip())
    return out
