"""Workbench integration: publish → sidecar → ingest closes a photo gap.

Run:  python -m pytest scripts/test_capture_bridge_integration.py -q
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from foldok_capture import checksum_of, read_binding, read_tasks, sidecar_name
from foldok_capture.model import Sidecar
from local_app.capture_bridge import capture_bind, capture_ingest, capture_publish


def _project(tmp_path: Path) -> dict:
    folder = tmp_path / "job"
    folder.mkdir()
    return {
        "id": "job_114",
        "name": "Storgata 14",
        "folders": [str(folder)],
    }


def _state() -> dict:
    return {"completion": {"mode": "build", "pack_id": "no_electrical_installation"}}


def _shoot(folder: Path, name: str, gap_id: str, requirement_key: str, subject: str) -> None:
    photo = folder / name
    photo.write_bytes(b"\xff\xd8\xff" + name.encode() + b"x" * 2000)
    side = Sidecar(
        capture_id=f"cap_{name}",
        file_name=name,
        captured_at=time.time(),
        project_id="job_114",
        gap_id=gap_id,
        requirement_key=requirement_key,
        subject=subject,
        device="Pixel 8",
        app_version="0.4.0",
        checksum=checksum_of(photo),
    )
    (folder / sidecar_name(photo)).write_text(side.to_json(), encoding="utf-8")


def test_publish_sidecar_ingest_closes_gap(tmp_path: Path):
  project = _project(tmp_path)
  folder = Path(project["folders"][0])
  state = _state()

  bind_out = capture_bind(folder, project, state)
  assert bind_out["ok"]
  assert read_binding(folder) is not None

  pub = capture_publish(folder, project, state)
  assert pub["open_tasks"] >= 1
  tasks = read_tasks(folder)
  assert tasks and tasks.open_tasks
  task = tasks.open_tasks[0]

  _shoot(folder, "IMG_bridge.jpg", task.gap_id, task.requirement_key, task.subject)

  ing = capture_ingest(folder, project, state)
  assert task.gap_id in ing["resolved"]

  from foldok_gaps import CompletionSession, Document, default_registry
  from foldok_gaps.packs import PACKS

  doc = Document.from_dict(state["completion"]["document"])
  session = CompletionSession(doc, PACKS["no_electrical_installation"], default_registry())
  gap = session.gaps().get(task.gap_id)
  assert gap is not None and not gap.open
  ref = session.document.artifact(gap.artifact_id).provenance.ref
  assert "IMG_bridge.jpg" in ref and "captured" in ref
