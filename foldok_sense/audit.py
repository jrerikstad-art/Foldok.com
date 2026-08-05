"""Run the whole chain over a folder, outside the app.

Written to answer one question: **is this an engine problem or a plumbing
problem?**

The app reported "38 indexed of 37 files" and "0/1 sections with substance,
0 hull funnet". One section from 37 files means the sense-making chain is not
being called at all — the old fixed-outline path is still generating documents,
so every engine built since then has been improving code that nothing invokes.

This script calls the chain directly:

    scan → extract → reflow → tier → claims → sense

and prints the draft plus a stage-by-stage yield table. Compare its output to the
app's on the same folder. If this produces topics and the app produces one empty
section, the engines work and the wiring is the fault — which is a much smaller
fix than another round of extraction work.

    python -m foldok_sense.audit /path/to/folder
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StageCount:
    name: str
    value: int = 0
    note: str = ""
    seconds: float = 0.0

    def line(self) -> str:
        base = f"  {self.name:<26} {self.value:>7}"
        if self.seconds >= 0.05:
            base += f"   {self.seconds:>5.1f}s"
        if self.note:
            base += f"   {self.note}"
        return base


@dataclass
class AuditResult:
    stages: list[StageCount] = field(default_factory=list)
    draft: Any = None
    problems: list[str] = field(default_factory=list)

    def add(self, name: str, value: int, note: str = "", seconds: float = 0.0) -> None:
        self.stages.append(StageCount(name, value, note, seconds))

    def report(self) -> str:
        lines = ["", "STAGE YIELD", ""]
        lines += [s.line() for s in self.stages]
        if self.problems:
            lines += ["", "PROBLEMS", ""]
            lines += [f"  - {p}" for p in self.problems]
        return "\n".join(lines)


def audit(folder: str | Path, *, lang: str = "no", max_files: int = 200) -> AuditResult:
    from foldok_claims import extract as extract_claims
    from foldok_reflow import harvest, quality, reflow, split_sentences
    from foldok_scan import scan
    from foldok_sense import assemble, passages_from
    from foldok_tier import tier_sentences

    root = Path(folder)
    result = AuditResult()

    # -- 1. what is in the folder ---------------------------------------
    t0 = time.time()
    scan_report = scan(root)
    result.add("files found", len(scan_report.entries), seconds=time.time() - t0)
    result.add("files indexable", len(scan_report.indexed),
               note=f"{scan_report.coverage:.0%} coverage")
    if scan_report.recoverable:
        win = scan_report.biggest_win()
        if win:
            result.problems.append(
                f"{len(scan_report.recoverable)} file(s) dropped for format; "
                f"supporting {win[0]} would recover {win[1]}"
            )
    if not scan_report.indexed:
        result.problems.append("nothing indexable — the chain cannot start")
        return result

    # -- 2. text -----------------------------------------------------------
    from foldok_index.extract import extract as extract_text

    raw_chars = clean_chars = 0
    all_passages: list[Any] = []
    all_figures: list[dict[str, Any]] = []
    sentences_total = 0
    unreadable: list[str] = []
    t0 = time.time()

    for entry in scan_report.indexed[:max_files]:
        path = entry.path
        try:
            raw = extract_text(str(path)).text or ""
        except Exception as exc:  # noqa: BLE001
            unreadable.append(f"{path.name}: {type(exc).__name__}")
            continue
        if len(raw) < 200:
            unreadable.append(f"{path.name}: {len(raw)} chars")
            continue
        raw_chars += len(raw)

        text = reflow(raw).text
        clean_chars += len(text)
        sentences = split_sentences(text)
        sentences_total += len(sentences)

        claims = extract_claims(text, source=path.name).claims
        strong = {c.text: c.type for c in claims}
        topics: set[str] = set()
        for claim in claims:
            topics.update(w.lower() for w in claim.text.split() if len(w) > 5)

        tiered = tier_sentences(sentences, source=path.name,
                                strong_ids=strong, topics=topics)
        all_passages.extend(passages_from(tiered))

        if path.suffix.lower() == ".pdf":
            try:
                all_figures.extend(f.to_dict()
                                   for f in harvest(path, text=text).usable_figures())
            except Exception:  # noqa: BLE001
                pass

    elapsed = time.time() - t0
    result.add("characters extracted", raw_chars, seconds=elapsed)
    result.add("sentences", sentences_total)
    result.add("passages usable", len(all_passages),
               note=f"{len(all_passages) / sentences_total:.0%} of sentences"
               if sentences_total else "")
    result.add("figures", len(all_figures))

    if unreadable:
        result.problems.append(
            f"{len(unreadable)} file(s) yielded no readable text: "
            + ", ".join(unreadable[:4])
        )
    if sentences_total and len(all_passages) / sentences_total < 0.15:
        result.problems.append(
            "under 15% of sentences are usable — check reflow is running "
            "(raw PDF lines produce fragments)"
        )
    if not all_passages:
        result.problems.append("no usable passages — nothing can be assembled")
        return result

    # -- 3. the draft ------------------------------------------------------
    t0 = time.time()
    draft = assemble(
        all_passages, figures=all_figures,
        title=root.name,
        files_read=len(scan_report.indexed),
        sentences_seen=sentences_total,
        lang=lang,
    )
    result.add("topics discovered", len(draft.justified()), seconds=time.time() - t0)
    result.add("sentences placed", draft.sentences_used,
               note=f"{draft.coverage:.0%} of passages")
    result.add("figures placed",
               sum(len(g.figures) for g in draft.justified()),
               note=f"{len(draft.orphan_figures)} unplaced")
    result.draft = draft

    if len(draft.justified()) <= 1:
        result.problems.append(
            "one topic or fewer from the whole folder — the corpus may be "
            "single-subject, or topic discovery is being starved"
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="foldok_sense.audit",
        description="Run scan → extract → reflow → tier → sense over a folder.",
    )
    parser.add_argument("folder")
    parser.add_argument("--lang", default="no")
    parser.add_argument("--out", default="", help="write the draft markdown here")
    parser.add_argument("--max-files", type=int, default=200)
    args = parser.parse_args(argv)

    result = audit(args.folder, lang=args.lang, max_files=args.max_files)
    print(result.report())

    if result.draft is None:
        print("\nNo draft produced.")
        return 1

    print()
    print("DRAFT")
    print()
    print("  " + result.draft.summary(lang=args.lang))
    print()
    for group in result.draft.justified()[:20]:
        print(f"  {group.title:<24} {group.weight:>4} passages, "
              f"{len(group.figures)} figure(s), {group.strong_share:.0%} strong, "
              f"{len(group.sources)} source(s)")

    if args.out:
        Path(args.out).write_text(result.draft.markdown(lang=args.lang), encoding="utf-8")
        print(f"\nWrote {args.out}")
    else:
        print("\nRun with --out draft.md to write the full document.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
