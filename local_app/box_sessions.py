"""In-memory foldok_boxes layout sessions (WO 0.73)."""
from __future__ import annotations

import uuid
from typing import Any

from foldok_boxes import LayoutRefused, LayoutSession
from foldok_boxes.demo import apply_intent, build_session

_SESSIONS: dict[str, LayoutSession] = {}


def create_session() -> dict[str, Any]:
    sid = uuid.uuid4().hex[:12]
    _SESSIONS[sid] = build_session()
    return session_payload(sid)


def get_session(session_id: str) -> LayoutSession | None:
    return _SESSIONS.get(session_id)


def drop_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)


def session_payload(session_id: str) -> dict[str, Any]:
    session = _SESSIONS[session_id]
    state = session.state()
    state["session_id"] = session_id
    return state


def apply(session_id: str, intent: dict) -> dict[str, Any]:
    session = _SESSIONS.get(session_id)
    if not session:
        raise KeyError("unknown layout session")
    try:
        apply_intent(session, intent or {})
    except LayoutRefused as exc:
        session._log("refused", (intent or {}).get("blockId", "*"), str(exc))  # noqa: SLF001
    return session_payload(session_id)
