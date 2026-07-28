"""Publishing tasks, and ingesting what comes back.

Two functions carry the whole feature:

``publish`` turns the open photo gaps into a work list the phone can read.  It
uses the instruction ``PhotoCaptureResolver`` already writes, so nobody authors
capture guidance twice.

``ingest`` walks the folder, reads sidecars, and closes the gaps they belong to.
Three rules make it safe to run on every folder scan:

*  **Idempotent.**  Keyed on ``capture_id``; re-running never double-resolves.
*  **Never guesses.**  A photo with no sidecar, a sidecar for an unknown gap, a
   sidecar whose photo is missing — each is reported, none is matched by
   filename or timestamp. Guessing which requirement a photo satisfies is how
   fabricated evidence gets into a compliance document.
*  **Tamper-evident.**  The checksum recorded at capture is re-verified. A photo
   that changed after it was taken is flagged, not silently accepted.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from .model import (
    FOLDOK_DIR,
    Binding,
    Sidecar,
    TaskList,
    CaptureTask,
    checksum_of,
    folder_paths,
    is_capture,
    sidecar_name,
)


# ----------------------------------------------------------------------
# desktop -> phone
# ----------------------------------------------------------------------
def tasks_from_gaps(gaps: Iterable[Any], *, kinds: Sequence[str] = ("photo",)) -> list[CaptureTask]:
    """Build tasks from a ``foldok_gaps`` GapSet (or any iterable of Gaps)."""
    out: list[CaptureTask] = []
    for gap in gaps:
        requirement = getattr(gap, "requirement", None)
        if requirement is None or requirement.kind not in kinds:
            continue
        instruction = (
            requirement.capture_prompt
            or requirement.description
            or f"Photograph: {requirement.title}"
        )
        subject = getattr(gap, "subject", None)
        out.append(
            CaptureTask(
                gap_id=gap.id,
                requirement_key=requirement.key,
                title=gap.title,
                instruction=instruction,
                subject=subject.key() if subject is not None else "",
                subject_label=(subject.label or subject.id) if subject is not None else "",
                authority=requirement.authority,
                severity=requirement.severity,
                kind="photo",
                done=not gap.open,
            )
        )
    return sorted(out, key=lambda t: (t.done, t.requirement_key, t.subject))


def publish(
    folder: str | Path,
    tasks: Sequence[CaptureTask],
    *,
    project_id: str,
    project_title: str = "",
    document_id: str = "",
    clock=time.time,
) -> Path:
    """Write ``.foldok/capture_tasks.json`` into the project folder."""
    paths = folder_paths(folder)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    task_list = TaskList(
        project_id=project_id,
        project_title=project_title,
        document_id=document_id,
        tasks=list(tasks),
        generated_at=clock(),
    )
    # Write-then-rename: a phone reading mid-write must never see half a file.
    tmp = paths["tasks"].with_suffix(".json.tmp")
    tmp.write_text(task_list.to_json(), encoding="utf-8")
    tmp.replace(paths["tasks"])
    return paths["tasks"]


def bind(
    folder: str | Path,
    project_id: str,
    *,
    project_title: str = "",
    document_id: str = "",
    clock=time.time,
) -> Path:
    paths = folder_paths(folder)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    binding = Binding(
        project_id=project_id, project_title=project_title,
        document_id=document_id, created_at=clock(),
    )
    paths["binding"].write_text(
        json.dumps(binding.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return paths["binding"]


def read_tasks(folder: str | Path) -> TaskList | None:
    p = folder_paths(folder)["tasks"]
    if not p.exists():
        return None
    try:
        return TaskList.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError):
        return None


def read_binding(folder: str | Path) -> Binding | None:
    p = folder_paths(folder)["binding"]
    if not p.exists():
        return None
    try:
        return Binding.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError):
        return None


# ----------------------------------------------------------------------
# phone -> desktop
# ----------------------------------------------------------------------
@dataclass
class Capture:
    sidecar: Sidecar
    photo: Path | None
    verified: bool = True

    @property
    def usable(self) -> bool:
        return self.photo is not None and self.verified


@dataclass
class Issue:
    code: str
    detail: str
    fix: str = ""

    def __str__(self) -> str:
        return f"[{self.code}] {self.detail}" + (f" — {self.fix}" if self.fix else "")


@dataclass
class IngestReport:
    folder: str
    captures: list[Capture] = field(default_factory=list)
    resolved: list[str] = field(default_factory=list)      # gap ids closed
    already_done: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def of(self, code: str) -> list[Issue]:
        return [i for i in self.issues if i.code == code]

    def summary(self) -> str:
        lines = [
            f"{self.folder}: {len(self.captures)} capture(s), "
            f"{len(self.resolved)} gap(s) closed"
        ]
        if self.already_done:
            lines.append(f"  {len(self.already_done)} already recorded")
        for issue in self.issues[:20]:
            lines.append(f"  {issue}")
        return "\n".join(lines)


def scan(folder: str | Path, *, verify_checksums: bool = True) -> IngestReport:
    """Read every sidecar in a folder and pair it with its photo."""
    base = Path(folder)
    report = IngestReport(folder=str(base))
    if not base.exists():
        report.issues.append(Issue("no_folder", f"{base} does not exist"))
        return report

    sidecars = sorted(base.glob(f"*{'.foldok.json'}"))
    photos = {
        p.stem: p for p in sorted(base.iterdir())
        if p.is_file() and is_capture(p)
    }
    seen_stems: set[str] = set()

    for path in sidecars:
        try:
            record = Sidecar.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError) as exc:
            report.issues.append(
                Issue("bad_sidecar", f"{path.name}: {exc}", "the capture app wrote a malformed record")
            )
            continue

        stem = Path(record.file_name).stem or path.name.replace(".foldok.json", "")
        seen_stems.add(stem)
        photo = photos.get(stem)
        if photo is None:
            report.issues.append(
                Issue(
                    "missing_photo", f"{record.file_name} is described but not present",
                    "the folder may still be syncing; re-scan, or the photo was deleted",
                )
            )
            report.captures.append(Capture(sidecar=record, photo=None, verified=False))
            continue

        verified = True
        if verify_checksums and record.checksum:
            if checksum_of(photo) != record.checksum:
                verified = False
                report.issues.append(
                    Issue(
                        "checksum_mismatch", f"{photo.name} changed after it was captured",
                        "an edited photo is not the evidence that was taken — confirm it by hand",
                    )
                )
        report.captures.append(Capture(sidecar=record, photo=photo, verified=verified))

    for stem, photo in photos.items():
        if stem in seen_stems:
            continue
        if (base / sidecar_name(photo)).exists():
            continue
        report.issues.append(
            Issue(
                "unlinked_photo", f"{photo.name} has no capture record",
                "it was taken outside Foldok, or by an older Capture build — attach it to a "
                "gap by hand rather than letting the engine guess which requirement it meets",
            )
        )
    return report


def ingest(
    folder: str | Path,
    session: Any | None = None,
    *,
    by: str = "",
    verify_checksums: bool = True,
) -> IngestReport:
    """Scan, then close the gaps the captures belong to.

    ``session`` is a ``foldok_gaps.CompletionSession``. Without one this is a
    read-only scan, which is what the desktop does before showing the user what
    arrived.
    """
    report = scan(folder, verify_checksums=verify_checksums)
    if session is None:
        return report

    for capture in report.captures:
        record = capture.sidecar
        if not record.linked:
            report.issues.append(
                Issue(
                    "unassigned_capture", f"{record.file_name} is not linked to a gap",
                    "taken in free-capture mode; assign it in the gap list",
                )
            )
            continue
        if not capture.usable:
            continue

        gap = _find_gap(session, record)
        if gap is None:
            report.issues.append(
                Issue(
                    "unknown_gap", f"{record.file_name} refers to a gap this document does not have",
                    "the requirement pack may have changed since the photo was taken",
                )
            )
            continue
        if not gap.open:
            report.already_done.append(gap.id)
            continue

        try:
            artifact = gap.artifact_id and session.document.artifact(gap.artifact_id)
            if artifact is None:
                artifact = session.resolve(gap.id, "photo_capture").artifact
            path = str(capture.photo)
            artifact.path = path
            artifact.provenance.source = "import"
            artifact.provenance.ref = record.citation()
            artifact.fill({"path": path}, by=by or record.captured_by or record.device or "capture app")
            session.invalidate()
            report.resolved.append(gap.id)
        except Exception as exc:  # noqa: BLE001
            report.issues.append(
                Issue("resolve_failed", f"{record.file_name}: {type(exc).__name__}: {exc}")
            )
    return report


def _find_gap(session: Any, record: Sidecar) -> Any | None:
    """Match by gap id first, then by requirement + subject.

    The second path matters because a gap id is a hash of (pack, requirement,
    subject) — re-attaching the pack keeps the id stable, but bumping the pack
    version does not.
    """
    gaps = session.gaps()
    if record.gap_id:
        found = gaps.get(record.gap_id)
        if found is not None:
            return found
    if record.requirement_key:
        for gap in gaps.gaps:
            if gap.requirement.key != record.requirement_key:
                continue
            if record.subject and gap.subject.key() != record.subject:
                continue
            return gap
    return None
