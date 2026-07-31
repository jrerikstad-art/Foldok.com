"""Markdown normalisation — headings that are actually headings.

The section rendered ``## Identifiserte dokumenter`` as literal text in the
middle of a paragraph, because the model emitted the heading without a blank
line before it and nothing downstream fixed it. ``foldok_compile`` inserts
``\\n## {title}\\n\\n`` for the section title it controls, and does nothing for
headings the model writes inside the prose.

One pass over every model output fixes every section rather than this one.
"""

from __future__ import annotations

import re

HEADING = re.compile(r"(?<!\n)\n?(#{1,6})\s+(?=\S)")
BLOCKQUOTE = re.compile(r"(?<!\n)\n?(>)\s+(?=\S)")
BULLET = re.compile(r"(?<!\n)\n?([-*+])\s+(?=\S)")
INLINE_HEADING = re.compile(r"([^\n])\s+(#{1,6})\s+(?=\S)")
INLINE_QUOTE = re.compile(r"([^\n])\s+(>)\s+(?=[\S])")


def normalise(text: str) -> str:
    """Give block elements the blank line they need to be block elements."""
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")

    # A heading glued to the end of a sentence is the failure mode seen in the
    # wild: "...i kildematerialet. ## Identifiserte dokumenter - ..."
    out = INLINE_HEADING.sub(lambda m: f"{m.group(1)}\n\n{m.group(2)} ", out)
    out = INLINE_QUOTE.sub(lambda m: f"{m.group(1)}\n\n{m.group(2)} ", out)

    lines = out.split("\n")
    fixed: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        starts_block = (
            stripped.startswith("#")
            or stripped.startswith("> ")
            or re.match(r"^[-*+]\s+\S", stripped)
        )
        if starts_block and fixed and fixed[-1].strip():
            previous = fixed[-1].lstrip()
            same_kind = (
                (stripped.startswith("#") and previous.startswith("#"))
                or (stripped.startswith(">") and previous.startswith(">"))
                or (re.match(r"^[-*+]\s", stripped) and re.match(r"^[-*+]\s", previous))
            )
            if not same_kind:
                fixed.append("")
        fixed.append(line)

    out = "\n".join(fixed)
    out = re.sub(r"\n{4,}", "\n\n\n", out)
    return out.strip() + "\n"


def looks_broken(text: str) -> list[str]:
    """Block markers stranded inside a paragraph. Cheap to check, so checked."""
    problems: list[str] = []
    # The rule is simply that a block marker must start its line. An earlier
    # version required 15 characters of preamble to avoid false positives and
    # therefore missed "Oversikt. ## Identifiserte dokumenter" — the short lead-in
    # is exactly what a model writes.
    for line in (text or "").splitlines():
        if re.search(r"\S\s+#{1,6}\s+\S", line):
            problems.append("heading inside a paragraph")
        elif re.search(r"\S\s+>\s+\S", line):
            problems.append("blockquote inside a paragraph")
    return problems[:10]
