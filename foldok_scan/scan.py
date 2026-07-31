"""Why isn't my file in the index?

The workbench reported "51 files found, 6 indexed" and said nothing about the
other 45. The obvious guess was that it does not recurse — but ``source_files``
does ``root.rglob("*")``, so recursion was never the problem. The files were
dropped by filters that never announce themselves:

    DOC_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".rtf"}

No ``.doc``, no ``.xls``, no ``.ppt``, no ``.msg``. In a standards library those
are everywhere, and every one of them becomes ``file_kind() == "skipped"`` and
disappears without a line of explanation.

So the real limitation is not any single filter. It is that a folder can lose 88%
of its material silently, and the user's only clue is a document that reads thin.
This module makes every drop explain itself, counts them by reason, and says
which single change would recover the most files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

# What the workbench currently accepts.
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff", ".bmp", ".svg"}
DOC_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".rtf"}
CAD_EXT = {".step", ".stp", ".iges", ".igs", ".fcstd", ".dxf", ".dwg", ".stl", ".obj", ".brep"}

# Formats a real engineering folder contains that the current sets drop.
# Legacy Office is the big one: a standards library written over fifteen years
# is full of .doc and .xls, and every one of them is currently invisible.
RECOVERABLE: dict[str, str] = {
    ".doc": "legacy Word — readable with the same extractor as .docx",
    ".xls": "legacy Excel",
    ".ppt": "legacy PowerPoint",
    ".odt": "OpenDocument text",
    ".ods": "OpenDocument spreadsheet",
    ".odp": "OpenDocument presentation",
    ".msg": "Outlook message — often carries the supplier's actual answer",
    ".eml": "email",
    ".htm": "saved web page",
    ".html": "saved web page",
    ".xml": "structured data",
    ".json": "structured data",
    ".tsv": "tabular data",
    ".log": "plain text",
    ".dat": "plain text",
    ".epub": "e-book",
    ".pages": "Apple Pages",
    ".numbers": "Apple Numbers",
    ".key": "Apple Keynote",
}

# Genuinely not worth indexing.
NEVER: dict[str, str] = {
    ".zip": "archive — expand it and index the contents",
    ".rar": "archive", ".7z": "archive", ".tar": "archive", ".gz": "archive",
    ".exe": "executable", ".dll": "executable", ".msi": "installer",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio",
    ".ttf": "font", ".otf": "font", ".woff": "font", ".woff2": "font",
    ".db": "database", ".sqlite": "database", ".lock": "lock file",
    ".tmp": "temporary", ".bak": "backup", ".ini": "settings", ".ds_store": "macOS metadata",
}

SKIP_DIRS = {
    "capture", "foldok-engine", "feltdok-engine", "node_modules", "__pycache__",
    "releases", ".git", ".cursor", "agent-transcripts", "terminals", "assets",
    ".foldok_index", ".feltdok_index", ".foldok_cache", ".feltdok_cache",
}

Reason = str


@dataclass
class Entry:
    path: Path
    rel: str
    depth: int
    size: int = 0
    kind: str = "skipped"          # doc | photo | cad | skipped
    reason: Reason = ""
    recoverable: bool = False
    note: str = ""

    @property
    def indexed(self) -> bool:
        return self.kind != "skipped"

    def to_dict(self) -> dict[str, Any]:
        d = {"rel": self.rel, "depth": self.depth, "kind": self.kind, "size": self.size}
        if self.reason:
            d["reason"] = self.reason
        if self.recoverable:
            d["recoverable"] = True
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class ScanReport:
    root: str
    entries: list[Entry] = field(default_factory=list)
    max_depth: int = 0

    @property
    def indexed(self) -> list[Entry]:
        return [e for e in self.entries if e.indexed]

    @property
    def dropped(self) -> list[Entry]:
        return [e for e in self.entries if not e.indexed]

    @property
    def recoverable(self) -> list[Entry]:
        return [e for e in self.dropped if e.recoverable]

    @property
    def coverage(self) -> float:
        return len(self.indexed) / len(self.entries) if self.entries else 1.0

    def by_reason(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.dropped:
            out[e.reason] = out.get(e.reason, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def by_extension(self, *, dropped_only: bool = True) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in (self.dropped if dropped_only else self.entries):
            ext = e.path.suffix.lower() or "(no extension)"
            out[ext] = out.get(ext, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def by_depth(self) -> dict[int, tuple[int, int]]:
        """depth -> (indexed, dropped). Answers 'is it the subfolders?'"""
        out: dict[int, list[int]] = {}
        for e in self.entries:
            slot = out.setdefault(e.depth, [0, 0])
            slot[0 if e.indexed else 1] += 1
        return {k: (v[0], v[1]) for k, v in sorted(out.items())}

    def biggest_win(self) -> tuple[str, int, str] | None:
        """The single change that recovers the most files."""
        counts: dict[str, int] = {}
        for e in self.recoverable:
            ext = e.path.suffix.lower()
            counts[ext] = counts.get(ext, 0) + 1
        if not counts:
            return None
        ext, n = max(counts.items(), key=lambda kv: kv[1])
        return (ext, n, RECOVERABLE.get(ext, ""))

    def report(self, *, lang: str = "no") -> str:
        total = len(self.entries)
        n_idx = len(self.indexed)
        if lang.startswith("no"):
            lines = [f"{self.root}: {n_idx} av {total} filer indeksert "
                     f"({self.coverage:.0%}), dybde {self.max_depth}"]
        else:
            lines = [f"{self.root}: {n_idx} of {total} files indexed "
                     f"({self.coverage:.0%}), depth {self.max_depth}"]

        depth = self.by_depth()
        if len(depth) > 1:
            head = "  per mappenivå:" if lang.startswith("no") else "  by folder depth:"
            lines.append(head)
            no = lang.startswith("no")
            got_word = "indeksert" if no else "indexed"
            lost_word = "droppet" if no else "dropped"
            for level, (got, lost) in depth.items():
                if no:
                    where = "rotmappe" if level == 0 else f"nivå {level}"
                else:
                    where = "root" if level == 0 else f"level {level}"
                lines.append(f"    {where:<10} {got:>3} {got_word}, {lost:>3} {lost_word}")
            # A level with nothing indexed reads exactly like "it does not do
            # subfolders", which is how this bug was reported. Say which it is.
            empty = [lvl for lvl, (g, l) in depth.items() if lvl > 0 and g == 0 and l > 0]
            if empty:
                lines.append(
                    f"    → nivå {', '.join(map(str, empty))} har filer, men ingen som "
                    "støttes — mappen leses, formatene gjør ikke"
                    if no else
                    f"    → level {', '.join(map(str, empty))} has files but none supported "
                    "— the folder IS read, the formats are not"
                )

        if self.dropped:
            head = "  droppet fordi:" if lang.startswith("no") else "  dropped because:"
            lines.append(head)
            for reason, n in self.by_reason().items():
                lines.append(f"    {n:>3}  {reason}")

        win = self.biggest_win()
        if win:
            ext, n, why = win
            if lang.startswith("no"):
                lines.append(f"\n  Største enkeltgevinst: støtt {ext} og få {n} filer til "
                             f"({why}).")
            else:
                lines.append(f"\n  Biggest single win: support {ext} and recover {n} files "
                             f"({why}).")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "total": len(self.entries),
            "indexed": len(self.indexed),
            "coverage": round(self.coverage, 3),
            "max_depth": self.max_depth,
            "by_reason": self.by_reason(),
            "by_extension_dropped": self.by_extension(),
            "by_depth": {str(k): list(v) for k, v in self.by_depth().items()},
            "recoverable": len(self.recoverable),
            "entries": [e.to_dict() for e in self.entries],
        }


# ----------------------------------------------------------------------
def scan(
    root: str | Path,
    *,
    doc_ext: Iterable[str] = DOC_EXT,
    photo_ext: Iterable[str] = PHOTO_EXT,
    cad_ext: Iterable[str] = CAD_EXT,
    skip_dirs: Iterable[str] = SKIP_DIRS,
    max_bytes: int = 200 * 1024 * 1024,
    follow_symlinks: bool = False,
) -> ScanReport:
    """Walk a folder the way the workbench does, and explain every drop."""
    root = Path(root)
    report = ScanReport(root=str(root))
    if not root.exists():
        return report

    doc_ext, photo_ext, cad_ext = set(doc_ext), set(photo_ext), set(cad_ext)
    skip = {s.lower() for s in skip_dirs}
    seen: set[tuple[int, int]] = set()

    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        here = Path(dirpath)
        rel_dir = here.relative_to(root)
        depth = len(rel_dir.parts)

        # Prune in place — the same rule the workbench applies, but recorded.
        pruned = [d for d in dirnames if d.lower() in skip or d.startswith(".")]
        dirnames[:] = [d for d in dirnames if d not in pruned]
        for name in pruned:
            report.entries.append(Entry(
                path=here / name, rel=str((rel_dir / name).as_posix()), depth=depth,
                kind="skipped", reason=f"folder '{name}' is on the skip list",
            ))

        for name in sorted(filenames):
            path = here / name
            rel = (rel_dir / name).as_posix()
            report.max_depth = max(report.max_depth, depth)
            entry = Entry(path=path, rel=rel, depth=depth)

            if name.startswith("."):
                entry.reason = "hidden file"
                report.entries.append(entry)
                continue
            try:
                stat = path.stat()
                entry.size = stat.st_size
            except OSError as exc:
                entry.reason = f"unreadable ({type(exc).__name__})"
                report.entries.append(entry)
                continue

            if not follow_symlinks and path.is_symlink():
                entry.reason = "symlink"
                report.entries.append(entry)
                continue

            key = (stat.st_dev, stat.st_ino)
            if key in seen and stat.st_ino:
                entry.reason = "duplicate of a file already seen (hard link)"
                report.entries.append(entry)
                continue
            seen.add(key)

            if entry.size == 0:
                entry.reason = "empty file"
                report.entries.append(entry)
                continue
            if entry.size > max_bytes:
                entry.reason = f"larger than {max_bytes // 1024 // 1024} MB"
                report.entries.append(entry)
                continue

            ext = path.suffix.lower()
            if ext in doc_ext:
                entry.kind = "doc"
            elif ext in photo_ext:
                entry.kind = "photo"
            elif ext in cad_ext:
                entry.kind = "cad"
            elif ext in RECOVERABLE:
                entry.reason = f"'{ext}' is not in the supported list"
                entry.recoverable = True
                entry.note = RECOVERABLE[ext]
            elif ext in NEVER:
                entry.reason = f"'{ext}' is not indexable ({NEVER[ext]})"
            elif not ext:
                entry.reason = "no file extension"
                entry.recoverable = True
                entry.note = "may still be text — check one before deciding"
            else:
                entry.reason = f"'{ext}' is not a known format"
                entry.recoverable = True
                entry.note = "unrecognised; add it if these matter"
            report.entries.append(entry)

    return report


def widened_doc_ext(report: ScanReport, *, minimum: int = 1) -> set[str]:
    """The extension set that would index this folder properly.

    Returned rather than applied: widening what counts as a document is a
    decision with consequences downstream, and it should be made once and
    deliberately rather than by a scanner.
    """
    out = set(DOC_EXT)
    counts: dict[str, int] = {}
    for entry in report.recoverable:
        ext = entry.path.suffix.lower()
        if ext in RECOVERABLE:
            counts[ext] = counts.get(ext, 0) + 1
    out |= {ext for ext, n in counts.items() if n >= minimum}
    return out


def compare(root: str | Path, candidate: Iterable[str]) -> tuple[ScanReport, ScanReport]:
    """Before and after, so the gain is a number rather than a hope."""
    return (scan(root), scan(root, doc_ext=candidate))
