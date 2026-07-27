"""WORKORDER_0.27 A4 — opt-in local telemetry for rung-3 demand signals."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import foldok_paths as fpaths

ENGINE_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = fpaths.telemetry_log_path(ENGINE_ROOT)


def _enabled() -> bool:
    flag = fpaths.telemetry_opt_in_path(ENGINE_ROOT)
    return flag.exists()


def log_event(event_type: str, payload: dict) -> None:
    if not _enabled():
        return
    row = {
        "t": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **payload,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def log_rung3_request(template: dict) -> None:
    sections = template.get("sections") or []
    log_event("rung3_request", {
        "suggested_name": template.get("name_no") or template.get("name"),
        "template_key": template.get("template_key"),
        "sections": [s.get("section_key") for s in sections],
        "origin": template.get("origin") or ("ai_drafted" if template.get("ai_drafted") else "unknown"),
    })
