"""The folder is the bus.

The Capture app already binds a project to a folder through Android's Storage
Access Framework — OneDrive, Drive, or local.  That single decision removes the
hardest part of a mobile companion: the photo reaches the laptop through the
customer's own already-approved sync tool, and Foldok never touches the network.
No pairing, no QR code, no server, nothing for an IT department to review.

So both directions travel through the folder:

    <project folder>/
        .foldok/
            capture_tasks.json          desktop -> phone   (open photo gaps)
            binding.json                which Foldok job this folder is
        IMG_1710000000000.jpg           the photo            (phone writes)
        IMG_1710000000000.foldok.json   the sidecar          (phone writes)

**One file per capture, written once, never edited.**  That is not a style
choice.  A single appended log across two devices over a sync service produces
conflict copies — ``log (Jan's laptop conflicted copy).jsonl`` — and then the
evidence trail has two heads.  Create-only files sync cleanly everywhere.

**The sidecar is the provenance.**  A photo alone is a JPEG somebody has to
match to a requirement by hand, which is the job Foldok exists to remove.  A
photo with a sidecar knows which gap it closes, when it was taken and on what,
so the gap closes itself and the document can cite the file.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1

FOLDOK_DIR = ".foldok"
TASKS_FILE = "capture_tasks.json"
BINDING_FILE = "binding.json"
SIDECAR_SUFFIX = ".foldok.json"

PHOTO_SUFFIXES = (".jpg", ".jpeg", ".png", ".heic", ".webp")
VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v")


def sidecar_name(photo: str | Path) -> str:
    """``IMG_123.jpg`` -> ``IMG_123.foldok.json``.

    Keyed on the stem rather than the full name so a re-encoded or renamed
    extension does not orphan the record.
    """
    return f"{Path(photo).stem}{SIDECAR_SUFFIX}"


def is_capture(path: str | Path) -> bool:
    return Path(path).suffix.lower() in PHOTO_SUFFIXES + VIDEO_SUFFIXES


# ----------------------------------------------------------------------
@dataclass
class CaptureTask:
    """One open photo gap, written for the phone to read.

    ``instruction`` is the text ``PhotoCaptureResolver`` already generates —
    "Photograph the board with the cover off, labels legible" — so the work list
    writes itself from the gap engine.
    """

    gap_id: str
    requirement_key: str
    title: str
    instruction: str
    subject: str = ""                    # "circuit:K3" — which thing this is about
    subject_label: str = ""
    authority: str = ""                  # the clause behind the requirement
    severity: str = "required"
    kind: str = "photo"                  # photo | video
    done: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = {
            "gap_id": self.gap_id,
            "requirement_key": self.requirement_key,
            "title": self.title,
            "instruction": self.instruction,
            "kind": self.kind,
            "severity": self.severity,
        }
        for name in ("subject", "subject_label", "authority"):
            value = getattr(self, name)
            if value:
                d[name] = value
        if self.done:
            d["done"] = True
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "CaptureTask":
        return CaptureTask(
            gap_id=d["gap_id"],
            requirement_key=d.get("requirement_key", ""),
            title=d.get("title", ""),
            instruction=d.get("instruction", ""),
            subject=d.get("subject", ""),
            subject_label=d.get("subject_label", ""),
            authority=d.get("authority", ""),
            severity=d.get("severity", "required"),
            kind=d.get("kind", "photo"),
            done=bool(d.get("done", False)),
        )


@dataclass
class TaskList:
    project_id: str
    project_title: str = ""
    tasks: list[CaptureTask] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    document_id: str = ""
    note: str = ""

    @property
    def open_tasks(self) -> list[CaptureTask]:
        return [t for t in self.tasks if not t.done]

    def get(self, gap_id: str) -> CaptureTask | None:
        for t in self.tasks:
            if t.gap_id == gap_id:
                return t
        return None

    def age_hours(self, clock=time.time) -> float:
        return max(0.0, (clock() - self.generated_at) / 3600.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": self.project_id,
            "project_title": self.project_title,
            "document_id": self.document_id,
            "generated_at": round(self.generated_at, 3),
            "note": self.note or (
                "Open capture tasks from Foldok. Take each photo in the Capture app; "
                "the gap closes itself when the folder syncs back."
            ),
            "tasks": [t.to_dict() for t in self.tasks],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "TaskList":
        return TaskList(
            project_id=d.get("project_id", ""),
            project_title=d.get("project_title", ""),
            document_id=d.get("document_id", ""),
            generated_at=float(d.get("generated_at", 0.0)),
            note=d.get("note", ""),
            tasks=[CaptureTask.from_dict(t) for t in d.get("tasks", [])],
        )


# ----------------------------------------------------------------------
@dataclass
class Sidecar:
    """What the phone writes next to each photo.

    Everything here is either generated by the app or chosen by the person
    holding it. ``location`` is present only when they turned it on: for a
    compliance record a GPS fix is either proof somebody was on site or a log of
    a worker's movements, and which one it is depends on consent.
    """

    capture_id: str
    file_name: str
    captured_at: float
    project_id: str = ""
    gap_id: str = ""
    requirement_key: str = ""
    subject: str = ""
    captured_by: str = ""                 # person, if the app knows one
    device: str = ""                      # model string, not an identifier
    app_version: str = ""
    checksum: str = ""                    # of the photo, for tamper evidence
    location: dict[str, float] | None = None
    may_leave: bool = False               # a photo cannot be masked — never auto-send
    note: str = ""
    schema_version: int = SCHEMA_VERSION

    @property
    def linked(self) -> bool:
        return bool(self.gap_id or self.requirement_key)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema_version": self.schema_version,
            "capture_id": self.capture_id,
            "file_name": self.file_name,
            "captured_at": round(self.captured_at, 3),
            "may_leave": self.may_leave,
        }
        for name in ("project_id", "gap_id", "requirement_key", "subject",
                     "captured_by", "device", "app_version", "checksum", "note"):
            value = getattr(self, name)
            if value:
                d[name] = value
        if self.location:
            d["location"] = {k: round(v, 6) for k, v in sorted(self.location.items())}
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Sidecar":
        return Sidecar(
            capture_id=d["capture_id"],
            file_name=d.get("file_name", ""),
            captured_at=float(d.get("captured_at", 0.0)),
            project_id=d.get("project_id", ""),
            gap_id=d.get("gap_id", ""),
            requirement_key=d.get("requirement_key", ""),
            subject=d.get("subject", ""),
            captured_by=d.get("captured_by", ""),
            device=d.get("device", ""),
            app_version=d.get("app_version", ""),
            checksum=d.get("checksum", ""),
            location=d.get("location"),
            may_leave=bool(d.get("may_leave", False)),
            note=d.get("note", ""),
            schema_version=int(d.get("schema_version", 1)),
        )

    def citation(self) -> str:
        """What goes into the document as ``provenance.ref``."""
        stamp = time.strftime("%Y-%m-%d %H:%M", time.gmtime(self.captured_at))
        return f"{self.file_name} (captured {stamp} UTC)"


@dataclass
class Binding:
    """Which Foldok job a folder belongs to. Written once by the desktop."""

    project_id: str
    project_title: str = ""
    document_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": self.project_id,
            "project_title": self.project_title,
            "document_id": self.document_id,
            "created_at": round(self.created_at, 3),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Binding":
        return Binding(
            project_id=d["project_id"],
            project_title=d.get("project_title", ""),
            document_id=d.get("document_id", ""),
            created_at=float(d.get("created_at", 0.0)),
        )


def checksum_of(path: str | Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()[:32]


def folder_paths(folder: str | Path) -> dict[str, Path]:
    base = Path(folder) / FOLDOK_DIR
    return {
        "dir": base,
        "tasks": base / TASKS_FILE,
        "binding": base / BINDING_FILE,
    }
