"""WORKORDER_0.25 — Hub session: conversation events + pending_action dispatch."""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

SESSION_PATH = Path(__file__).resolve().parent / "hub_session.json"

AFFIRMATIVE = re.compile(
    r"^\s*(ja|yes|ok|okay|kj[øo]r|gj[øo]r\s+det|go|do\s+it|confirm|bekreft|"
    r"opprett|create|start)\s*[.!?]?\s*$",
    re.I,
)

PROPOSAL_Q = re.compile(
    r"skal\s+jeg\s+(kj[øo]re|opprette|starte|generere)|"
    r"shall\s+i\s+(run|create|start|generate)|"
    r"want\s+me\s+to\s+(run|create|start)",
    re.I,
)


def load_session() -> dict:
    if SESSION_PATH.exists():
        try:
            return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "conversation": [],
        "pending_action": None,
        "staged": [],
        "asked_actions": [],
    }


def save_session(session: dict) -> None:
    SESSION_PATH.write_text(
        json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")


def append_event(session: dict, role: str, text: str, *, meta: dict | None = None) -> dict:
    """A1 — system/tool turns join the conversation the model sees."""
    turn = {"role": role, "text": text, "at": time.time()}
    if meta:
        turn["meta"] = meta
    session.setdefault("conversation", []).append(turn)
    if len(session["conversation"]) > 80:
        session["conversation"] = session["conversation"][-80:]
    return turn


def set_pending(session: dict, tool: str, args: dict | None = None,
                *, offer_label: str | None = None) -> dict:
    """B1 — store proposed action awaiting affirmative."""
    pending = {
        "tool": tool,
        "args": args or {},
        "asked_at": time.time(),
        "offer_label": offer_label,
        "fingerprint": f"{tool}:{json.dumps(args or {}, sort_keys=True)[:120]}",
    }
    session["pending_action"] = pending
    return pending


def clear_pending(session: dict) -> None:
    session["pending_action"] = None


def is_affirmative(msg: str) -> bool:
    return bool(AFFIRMATIVE.match((msg or "").strip()))


def action_already_asked(session: dict, fingerprint: str) -> bool:
    return fingerprint in (session.get("asked_actions") or [])


def mark_action_asked(session: dict, fingerprint: str) -> None:
    asked = session.setdefault("asked_actions", [])
    if fingerprint not in asked:
        asked.append(fingerprint)
    if len(asked) > 40:
        session["asked_actions"] = asked[-40:]


def format_events_for_prompt(session: dict, limit: int = 24) -> str:
    lines = ["=== HUB SESSION EVENTS (engine-owned; ground here) ==="]
    for t in (session.get("conversation") or [])[-limit:]:
        role = (t.get("role") or "?").upper()
        text = (t.get("text") or "").strip()
        if len(text) > 600:
            text = text[:600] + "…"
        if text:
            lines.append(f"{role}: {text}")
    staged = session.get("staged") or []
    if staged:
        lines.append("STAGED FILES (indexed, no project yet):")
        for s in staged[-8:]:
            lines.append(
                f"- {s.get('name')}: Indeksert som: {s.get('caption') or '(ingen caption)'} "
                f"| facts={len(s.get('fact_keys') or [])} "
                f"{', '.join((s.get('fact_keys') or [])[:8])}"
            )
    pending = session.get("pending_action")
    if pending:
        lines.append(
            f"PENDING_ACTION awaiting yes/ja: tool={pending.get('tool')} "
            f"label={pending.get('offer_label')}"
        )
    lines.append("=== END HUB SESSION EVENTS ===")
    return "\n".join(lines)


def hub_indexed_ack(name: str, caption: str, fact_keys: list | None = None,
                    *, lang: str = "no", cost_eur: float = 0) -> str:
    """A2 — cold-start drop acknowledgement from extraction."""
    cap = caption or name
    keys = ", ".join(fact_keys or []) or (
        "ingen nøkkelelementer" if lang == "no" else "no key facts")
    if lang == "en":
        return (
            f"Received and indexed: **{name}** — Indeksert som: {cap}. "
            f"Found: {keys}"
            + (f" (~€{cost_eur:.2f})." if cost_eur else ".")
            + " Shall I create a project around it?"
        )
    return (
        f"Mottatt og indeksert: **{name}** — Indeksert som: {cap}. "
        f"Funnet: {keys}"
        + (f" (~€{cost_eur:.2f})." if cost_eur else ".")
        + " Skal jeg opprette et prosjekt rundt den?"
    )


def proposal_reask_violation(reply: str, session: dict) -> str | None:
    """B3 — don't re-ask the same confirm after it was already asked."""
    pending = session.get("pending_action")
    if not pending:
        return None
    if not PROPOSAL_Q.search(reply or ""):
        return None
    fp = pending.get("fingerprint") or ""
    if action_already_asked(session, fp):
        return "confirm_reask"
    return None


def new_stage_token() -> str:
    return uuid.uuid4().hex[:12]
