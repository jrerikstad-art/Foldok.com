"""Reject fictional progress / recycled job ids without receipts."""
from __future__ import annotations

from local_app import agent_truth as atruth


def test_handbook_fiction_without_receipt_fails():
    reply = (
        "EMC Fullstendig teknisk håndbok — jobb db474d05 er i gang. "
        "Jeg bygger nå dokumentet. Håndbok blir ~40–50 sider. Ferdig innen ca. 10–15 minutter."
    )
    ok, _, reason = atruth.validate_completion_claims(reply, tools_run=None, lang="en")
    assert ok is False
    assert reason in ("progress_without_receipt", "fictional_job_id")


def test_job_id_must_match_receipt():
    reply = "Starting document regenerate — job `db474d05` is running."
    ok, _, reason = atruth.validate_completion_claims(
        reply,
        tools_run=[{"tool": "run_generate", "ok": True, "job_id": "aabbcc11"}],
        lang="en",
    )
    assert ok is False
    assert reason == "fictional_job_id"


def test_matching_job_receipt_passes():
    reply = "Starting document regenerate — job `aabbcc11` is running."
    ok, out, reason = atruth.validate_completion_claims(
        reply,
        tools_run=[{"tool": "run_generate", "ok": True, "job_id": "aabbcc11"}],
        lang="en",
    )
    assert ok is True
    assert reason is None
    assert "aabbcc11" in out
