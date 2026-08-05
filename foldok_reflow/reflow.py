"""PDF text reflow — the point where good extraction became unusable claims.

Measured on a real 30-page technical PDF: ``foldok_index.extract`` returns 66,333
characters, and ``foldok_claims`` finds 104 claims in it. Neither stage is
broken. But the claims look like this::

    [practice]   3 3 Recommended data: 3.3 Recommended data lines...........
    [consequence] It is therefore becoming increasingly impor‐
    [consequence] As a result, only part of the electromagnetic

A PDF has no sentences. ``pypdf`` emits one line per *visual row*, so a sentence
spanning four rows arrives as four lines, and any splitter that treats a newline
as a boundary produces fragments. A table-of-contents row becomes a claim. A word
hyphenated across a line break — ``impor‐`` — becomes the end of one.

Everything downstream then starves in ways that look like different bugs:

*   "no writable claims (budget 0)" — the claims exist and are unusable.
*   "Etter dette — Etter dette —" — ``_transition`` builds a bridge from
    ``prev_summary.split(".")[0]``; with no sentence there is nothing to build
    from, so the fallback repeats.
*   English fragments in Norwegian frames — there is no sentence to translate,
    only a label.

Six passes, in order. Each is small and each is reversible in the sense that it
only ever joins or drops whole lines — nothing rewrites words.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = 1

PAGE_MARK = re.compile(r"^\s*\[page\s+(\d+)\]\s*$", re.I)

# A dotted leader is a table of contents, whatever else it looks like.
TOC_LINE = re.compile(r"\.{4,}\s*\d+\s*$|\s\.\s\.\s\.\s")
TOC_NUMBERING = re.compile(r"^\s*\d+(\.\d+)*\s+\S")

# Hyphenation across a line break: soft hyphen, or a real hyphen at line end.
HYPHEN_END = re.compile(r"([A-Za-zÀ-ÿÆØÅæøå])[-‐‑\u00ad]\s*$")

SENTENCE_END = re.compile(r"[.!?:;][\"'”’)\]]?\s*$")
BULLET_START = re.compile(r"^\s*([-•*▪◦]|\d+[.)]|[a-z][.)])\s+")
HEADING_LIKE = re.compile(r"^\s*\d+(\.\d+){0,3}\s+[A-ZÆØÅ]")

# Lines that are furniture rather than content.
FURNITURE = re.compile(
    r"^\s*(page\s+\d+|side\s+\d+|\d+\s*/\s*\d+|"
    r"subject to change without notice|all rights reserved|"
    r"copyright|©.*\d{4}|"
    r"\d{6,}\s*[/|]\s*\d{4}(-\d{2})*)\s*$",
    re.I,
)

# A line that is mostly digits and separators is a table row, not prose.
TABLE_ROW = re.compile(r"^[\s\d.,;:|/×x+\-–—%°()]+$")


@dataclass
class ReflowStats:
    lines_in: int = 0
    lines_out: int = 0
    joined: int = 0
    hyphens_repaired: int = 0
    toc_dropped: int = 0
    furniture_dropped: int = 0
    repeated_dropped: int = 0
    table_rows_kept: int = 0
    sentences: int = 0

    def summary(self, *, lang: str = "en") -> str:
        if lang.startswith("no"):
            return (
                f"{self.lines_in} linjer → {self.sentences} setninger; "
                f"{self.joined} sammenføyd, {self.hyphens_repaired} orddelinger reparert, "
                f"{self.toc_dropped + self.furniture_dropped + self.repeated_dropped} "
                "linjer med sidestoff fjernet"
            )
        return (
            f"{self.lines_in} lines → {self.sentences} sentences; "
            f"{self.joined} joined, {self.hyphens_repaired} hyphenations repaired, "
            f"{self.toc_dropped + self.furniture_dropped + self.repeated_dropped} "
            "furniture lines dropped"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "lines_in": self.lines_in, "lines_out": self.lines_out,
            "joined": self.joined, "hyphens_repaired": self.hyphens_repaired,
            "toc_dropped": self.toc_dropped,
            "furniture_dropped": self.furniture_dropped,
            "repeated_dropped": self.repeated_dropped,
            "table_rows_kept": self.table_rows_kept,
            "sentences": self.sentences,
        }


@dataclass
class Reflowed:
    text: str
    stats: ReflowStats = field(default_factory=ReflowStats)
    tables: list[str] = field(default_factory=list)

    def sentences(self) -> list[str]:
        return split_sentences(self.text)


# ----------------------------------------------------------------------
def reflow(text: str, *, keep_tables: bool = True) -> Reflowed:
    """Line-wrapped PDF output into sentences.

    Only ever joins or drops whole lines. Nothing rewrites a word except
    de-hyphenation, which reverses a break the layout engine inserted.
    """
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    stats = ReflowStats(lines_in=len(lines))

    kept, repeated = _drop_repeated(lines, stats)
    cleaned: list[str] = []
    tables: list[str] = []

    for line in kept:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if PAGE_MARK.match(stripped):
            cleaned.append("")          # a page break is a paragraph break
            continue
        if FURNITURE.match(stripped):
            stats.furniture_dropped += 1
            continue
        if TOC_LINE.search(stripped):
            stats.toc_dropped += 1
            continue
        if TABLE_ROW.match(stripped) and len(stripped) > 6:
            stats.table_rows_kept += 1
            if keep_tables:
                tables.append(stripped)
            continue
        cleaned.append(stripped)

    joined = _join(cleaned, stats)
    body = _tidy("\n".join(joined))
    stats.lines_out = len([l for l in joined if l.strip()])
    stats.sentences = len(split_sentences(body))
    return Reflowed(text=body, stats=stats, tables=tables)


def _drop_repeated(lines: Sequence[str], stats: ReflowStats) -> tuple[list[str], set[str]]:
    """Headers and footers repeat on every page and are never content.

    Frequency is the only reliable signal — a running header looks exactly like a
    heading on the page it belongs to.
    """
    counts = Counter(l.strip() for l in lines if 4 < len(l.strip()) < 90)
    pages = max(1, sum(1 for l in lines if PAGE_MARK.match(l.strip())))
    # Scaled, not absolute: a header on two of three pages is still a header,
    # and demanding three occurrences means short documents keep their furniture.
    threshold = 2 if pages <= 4 else max(3, pages // 2)
    repeated = {
        line for line, n in counts.items()
        if n >= threshold and not SENTENCE_END.search(line)
    }
    out: list[str] = []
    for line in lines:
        if line.strip() in repeated:
            stats.repeated_dropped += 1
            continue
        out.append(line)
    return out, repeated


def _join(lines: Sequence[str], stats: ReflowStats) -> list[str]:
    """Join a line to the next unless it ends a sentence or starts a new block.

    This is the pass that matters. A sentence spanning four visual rows arrives
    as four lines, and treating each as a unit is what produced
    "As a result, only part of the electromagnetic" as a whole claim.
    """
    out: list[str] = []
    buffer = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                out.append(buffer)
                buffer = ""
            out.append("")
            continue

        starts_block = bool(BULLET_START.match(stripped) or HEADING_LIKE.match(stripped))
        if starts_block and buffer:
            out.append(buffer)
            buffer = ""

        if not buffer:
            buffer = stripped
            continue

        hyphen = HYPHEN_END.search(buffer)
        if hyphen:
            buffer = HYPHEN_END.sub(r"\1", buffer) + stripped
            stats.hyphens_repaired += 1
            stats.joined += 1
            continue

        if SENTENCE_END.search(buffer):
            out.append(buffer)
            buffer = stripped
            continue

        buffer = f"{buffer} {stripped}"
        stats.joined += 1

    if buffer:
        out.append(buffer)
    return out


# Abbreviations that must not end a sentence.
ABBREV = re.compile(
    r"\b(nr|no|jf|osv|bl\.a|f\.eks|e\.g|i\.e|ca|pkt|kap|fig|tab|ref|art|"
    r"vol|ed|pp|sec|min|max|approx|etc|inkl|eks)\.$",
    re.I,
)


def split_sentences(text: str, *, minimum: int = 25) -> list[str]:
    """Sentences, not lines. Protects decimals, dates, initials and clauses."""
    guarded = text or ""
    guards = (
        (re.compile(r"(\d)[.,](\d)"), r"\1<N>\2"),                     # 1.5 mm
        (re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b"), r"\1<D>\2<D>\3"),
        (re.compile(r"\b([A-ZÆØÅ])\.\s(?=[A-ZÆØÅ])"), r"\1<I> "),      # J. R.
        (re.compile(r"§\s?(\d+)[-.](\d+)"), r"§\1<C>\2"),              # §6-61
        (re.compile(r"\b(\d+)\.(\d+)(\.\d+)*\s"), r"\1<S>\2\3 "),      # 3.3.1
    )
    for pattern, repl in guards:
        guarded = pattern.sub(repl, guarded)

    parts: list[str] = []
    for chunk in re.split(r"(?<=[.!?])\s+|\n{2,}", guarded):
        text_part = chunk
        for token, char in (("<N>", "."), ("<D>", "."), ("<I>", "."),
                            ("<C>", "-"), ("<S>", ".")):
            text_part = text_part.replace(token, char)
        text_part = re.sub(r"\s+", " ", text_part).strip()
        if len(text_part) < minimum:
            continue
        if parts and ABBREV.search(parts[-1]):
            parts[-1] = f"{parts[-1]} {text_part}"
            continue
        parts.append(text_part)
    return parts


def _tidy(text: str) -> str:
    out = unicodedata.normalize("NFKC", text or "")
    out = out.replace("\u00ad", "")
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def quality(text: str) -> dict[str, Any]:
    """Is this text usable for claim extraction, and if not, why?

    Reported rather than assumed, because a folder producing thin documents from
    good sources is exactly the situation where nobody thinks to look here.
    """
    lines = [l for l in (text or "").split("\n") if l.strip()]
    sentences = split_sentences(text)
    words = len(re.findall(r"\S+", text or ""))

    # The signal that matters is not how many sentences there are — that barely
    # moves — but how many *lines* are mid-sentence. Raw pypdf output has a
    # sentence ending on roughly one line in five; reflowed text on nearly all
    # of them. Claim extraction reads lines, so this is the number that decides
    # whether a claim comes out whole.
    complete = sum(1 for l in lines if SENTENCE_END.search(l.strip()))
    line_completeness = round(complete / len(lines), 3) if lines else 0.0
    toc = sum(1 for l in lines if TOC_LINE.search(l))

    return {
        "lines": len(lines),
        "sentences": len(sentences),
        "words": words,
        "words_per_line": round(words / len(lines), 1) if lines else 0.0,
        "line_completeness": line_completeness,
        "toc_lines": toc,
        "usable": line_completeness > 0.45 and toc == 0,
        "note": (
            "" if line_completeness > 0.45 else
            "most lines end mid-sentence — this is raw PDF layout, not prose; "
            "claims extracted from it will be fragments"
        ),
    }
