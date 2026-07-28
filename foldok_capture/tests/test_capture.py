"""Tests for the capture bridge.

The "never guesses" tests are the important ones: matching a photo to a
requirement by filename or timestamp would put fabricated evidence into a
compliance document.

Run:  python -m pytest foldok_capture/tests -q
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from foldok_capture import (
    FOLDOK_DIR,
    Binding,
    Sidecar,
    TaskList,
    bind,
    checksum_of,
    ingest,
    is_capture,
    publish,
    read_binding,
    read_tasks,
    scan,
    sidecar_name,
    tasks_from_gaps,
)
from foldok_gaps import CompletionSession, Document, default_registry, packs


def job(tmp_path: Path):
    folder = tmp_path / "job"
    folder.mkdir()
    doc = Document(id="job_114", title="Storgata 14", segment="electrical",
                   jurisdiction="NO_IT_230")
    doc.add_subject("board", "DB1", "Hovedtavle")
    for i in (1, 2):
        doc.add_subject("circuit", f"K{i}")
    session = CompletionSession(doc, packs.NO_ELECTRICAL, default_registry(), mode="build")
    return folder, session


def shoot(folder: Path, name: str, *, gap_id: str = "", requirement_key: str = "",
          subject: str = "", checksum: bool = True, **kw) -> Path:
    photo = folder / name
    photo.write_bytes(b"\xff\xd8\xff" + name.encode() + b"x" * 2000)
    side = Sidecar(
        capture_id=f"cap_{name}", file_name=name, captured_at=time.time(),
        project_id="job_114", gap_id=gap_id, requirement_key=requirement_key,
        subject=subject, device="Pixel 8", app_version="0.3.0",
        checksum=checksum_of(photo) if checksum else "", **kw,
    )
    (folder / sidecar_name(photo)).write_text(side.to_json(), encoding="utf-8")
    return photo


# --- desktop -> phone ----------------------------------------------------
def test_tasks_are_built_only_from_photo_gaps(tmp_path):
    _, session = job(tmp_path)
    tasks = tasks_from_gaps(session.gaps())
    assert tasks
    assert all(t.kind == "photo" for t in tasks)
    assert all("photo" in t.requirement_key or "photo" in t.title.lower() for t in tasks)


def test_the_instruction_comes_from_the_gap_engine(tmp_path):
    """Nobody authors capture guidance twice."""
    _, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    assert "cover off" in task.instruction
    assert task.authority or task.severity


def test_tasks_round_trip_through_the_folder(tmp_path):
    folder, session = job(tmp_path)
    publish(folder, tasks_from_gaps(session.gaps()), project_id="job_114")
    loaded = read_tasks(folder)
    assert loaded and loaded.project_id == "job_114"
    assert loaded.open_tasks


def test_publishing_is_atomic(tmp_path):
    """A phone reading mid-write must never see half a file."""
    folder, session = job(tmp_path)
    publish(folder, tasks_from_gaps(session.gaps()), project_id="job_114")
    leftovers = list((folder / FOLDOK_DIR).glob("*.tmp"))
    assert leftovers == []


def test_binding_records_which_job_a_folder_belongs_to(tmp_path):
    folder, _ = job(tmp_path)
    bind(folder, "job_114", project_title="Storgata 14")
    b = read_binding(folder)
    assert b and b.project_id == "job_114" and b.project_title == "Storgata 14"


def test_a_stale_task_list_can_be_detected_by_the_phone(tmp_path):
    folder, session = job(tmp_path)
    publish(folder, tasks_from_gaps(session.gaps()), project_id="job_114",
            clock=lambda: time.time() - 7200)
    assert read_tasks(folder).age_hours() > 1.5


# --- phone -> desktop ----------------------------------------------------
def test_a_linked_capture_closes_its_own_gap(tmp_path):
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    shoot(folder, "IMG_1.jpg", gap_id=task.gap_id,
          requirement_key=task.requirement_key, subject=task.subject)

    report = ingest(folder, session)
    assert report.resolved == [task.gap_id]
    assert session.gaps().get(task.gap_id).state == "resolved"


def test_the_document_can_cite_the_file_and_the_moment(tmp_path):
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    shoot(folder, "IMG_1.jpg", gap_id=task.gap_id, requirement_key=task.requirement_key,
          subject=task.subject, captured_by="J. R. Erikstad")
    ingest(folder, session)
    gap = session.gaps().get(task.gap_id)
    ref = session.document.artifact(gap.artifact_id).provenance.ref
    assert "IMG_1.jpg" in ref and "captured" in ref


def test_ingest_is_idempotent(tmp_path):
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    shoot(folder, "IMG_1.jpg", gap_id=task.gap_id, requirement_key=task.requirement_key,
          subject=task.subject)
    first = ingest(folder, session)
    second = ingest(folder, session)
    assert first.resolved and second.resolved == []
    assert second.already_done == [task.gap_id]


def test_a_capture_still_matches_after_the_pack_version_changes(tmp_path):
    """Gap ids hash the pack, so a version bump moves them. Requirement plus
    subject is the durable key."""
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    shoot(folder, "IMG_1.jpg", gap_id="stale_id_from_last_month",
          requirement_key=task.requirement_key, subject=task.subject)
    assert ingest(folder, session).resolved == [task.gap_id]


# --- never guesses -------------------------------------------------------
def test_a_photo_without_a_record_is_reported_never_matched(tmp_path):
    """Matching by filename or timestamp would put fabricated evidence into a
    compliance document."""
    folder, session = job(tmp_path)
    (folder / "IMG_stray.jpg").write_bytes(b"\xff\xd8\xffxxxx")
    report = ingest(folder, session)
    assert report.of("unlinked_photo")
    assert report.resolved == []


def test_a_capture_with_no_gap_link_is_reported(tmp_path):
    folder, session = job(tmp_path)
    shoot(folder, "IMG_free.jpg")
    report = ingest(folder, session)
    assert report.of("unassigned_capture")


def test_a_record_for_an_unknown_gap_is_reported(tmp_path):
    folder, session = job(tmp_path)
    shoot(folder, "IMG_1.jpg", gap_id="nope", requirement_key="el.does_not_exist")
    report = ingest(folder, session)
    assert report.of("unknown_gap")


def test_a_missing_photo_is_reported_rather_than_closing_the_gap(tmp_path):
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    shoot(folder, "IMG_1.jpg", gap_id=task.gap_id, requirement_key=task.requirement_key,
          subject=task.subject)
    (folder / "IMG_1.jpg").unlink()          # still syncing, or deleted
    report = ingest(folder, session)
    assert report.of("missing_photo")
    assert report.resolved == []


def test_a_photo_edited_after_capture_is_flagged(tmp_path):
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    photo = shoot(folder, "IMG_1.jpg", gap_id=task.gap_id,
                  requirement_key=task.requirement_key, subject=task.subject)
    photo.write_bytes(b"\xff\xd8\xff" + b"different content entirely")
    report = ingest(folder, session)
    assert report.of("checksum_mismatch")
    assert report.resolved == []


def test_a_malformed_record_does_not_poison_the_scan(tmp_path):
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    shoot(folder, "IMG_good.jpg", gap_id=task.gap_id,
          requirement_key=task.requirement_key, subject=task.subject)
    (folder / "IMG_bad.foldok.json").write_text("{ not json", encoding="utf-8")
    report = ingest(folder, session)
    assert report.of("bad_sidecar")
    assert report.resolved == [task.gap_id]


# --- privacy defaults ----------------------------------------------------
def test_a_photo_is_never_marked_sendable_by_default():
    """A photograph cannot be masked — nameplate, client logo, sometimes a face."""
    s = Sidecar(capture_id="c", file_name="a.jpg", captured_at=0.0)
    assert s.may_leave is False
    assert "may_leave" in s.to_dict()


def test_location_is_absent_unless_someone_turned_it_on():
    plain = Sidecar(capture_id="c", file_name="a.jpg", captured_at=0.0)
    assert "location" not in plain.to_dict()
    located = Sidecar(capture_id="c", file_name="a.jpg", captured_at=0.0,
                      location={"lat": 58.9, "lon": 5.7})
    assert located.to_dict()["location"]["lat"] == 58.9


def test_the_record_carries_a_device_model_not_an_identifier():
    s = Sidecar(capture_id="c", file_name="a.jpg", captured_at=0.0, device="Pixel 8")
    blob = json.dumps(s.to_dict())
    assert "Pixel 8" in blob
    assert "imei" not in blob.lower() and "serial" not in blob.lower()


# --- file handling -------------------------------------------------------
def test_video_captures_are_recognised():
    assert is_capture("clip.mp4") and is_capture("IMG.HEIC") and not is_capture("notes.txt")


def test_sidecar_naming_survives_an_extension_change():
    assert sidecar_name("IMG_1.jpg") == sidecar_name("IMG_1.heic")


def test_scanning_an_empty_folder_is_not_an_error(tmp_path):
    folder = tmp_path / "empty"
    folder.mkdir()
    report = scan(folder)
    assert report.ok and report.captures == []


def test_scanning_a_folder_that_does_not_exist_says_so(tmp_path):
    assert scan(tmp_path / "nope").of("no_folder")


def test_scan_without_a_session_is_read_only(tmp_path):
    folder, session = job(tmp_path)
    task = tasks_from_gaps(session.gaps())[0]
    shoot(folder, "IMG_1.jpg", gap_id=task.gap_id, requirement_key=task.requirement_key,
          subject=task.subject)
    before = session.gaps().get(task.gap_id).state
    ingest(folder, None)
    assert session.gaps().get(task.gap_id).state == before
