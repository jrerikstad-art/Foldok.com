"""Local account session + document payment status (WORKORDER 0.60 Path B).

Device token lives on disk; metering goes through proxy.ledger (in-process stub).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from proxy.ledger import (  # noqa: E402
    EXPORT_TIERS_EUR,
    FREE_CREDIT_EUR,
    LOW_BALANCE_EUR,
    Ledger,
    MeterDenied,
    content_sha256,
)

__all__ = [
    "MeterDenied", "content_sha256", "get_ledger", "account_snapshot",
    "document_status", "doc_content_fingerprint", "export_price_for_template",
    "export_pricing_enabled", "export_entitlement", "install_compile_hooks",
    "stamp_utkast_watermark", "mark_document_paid",
]

SESSION_PATH = Path(__file__).resolve().parent / "account_session.json"
_GUEST_ALLOWANCE_PATH = Path(__file__).resolve().parent / "guest_allowance.json"

_ledger: Ledger | None = None


def get_ledger() -> Ledger:
    global _ledger
    if _ledger is None:
        _ledger = Ledger()
    return _ledger


def load_session() -> dict:
    if not SESSION_PATH.exists():
        return {"device_token": None, "mode": "signed_out"}
    try:
        return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"device_token": None, "mode": "signed_out"}


def save_session(sess: dict) -> None:
    SESSION_PATH.write_text(json.dumps(sess, indent=2), encoding="utf-8")


def device_token() -> str | None:
    sess = load_session()
    if sess.get("mode") == "guest":
        return None
    return sess.get("device_token")


def account_snapshot() -> dict:
    """Public bootstrap payload for the UI."""
    sess = load_session()
    mode = sess.get("mode") or "signed_out"
    out = {
        "mode": mode,
        "signed_in": False,
        "guest": mode == "guest",
        "account": None,
        "export_tiers_eur": dict(EXPORT_TIERS_EUR),
        "free_credit_eur": FREE_CREDIT_EUR,
        "low_balance_eur": LOW_BALANCE_EUR,
        "privacy_line": "Filene dine forlater aldri maskinen — bare AI-kallene måles.",
    }
    tok = sess.get("device_token")
    if mode == "signed_in" and tok:
        acc = get_ledger().resolve_token(tok)
        if acc:
            out["signed_in"] = True
            out["account"] = acc
        else:
            # Stale token
            save_session({"device_token": None, "mode": "signed_out"})
            out["mode"] = "signed_out"
    elif mode == "guest":
        out["guest"] = True
        out["account"] = {
            "name": "Gjest",
            "balance_eur": guest_balance(),
            "guest": True,
        }
    return out


def guest_balance() -> float:
    if not _GUEST_ALLOWANCE_PATH.exists():
        data = {"balance_eur": FREE_CREDIT_EUR}
        _GUEST_ALLOWANCE_PATH.write_text(json.dumps(data), encoding="utf-8")
        return FREE_CREDIT_EUR
    try:
        return float(json.loads(_GUEST_ALLOWANCE_PATH.read_text(encoding="utf-8")).get("balance_eur") or 0)
    except Exception:
        return 0.0


def guest_debit(amount: float) -> float:
    bal = guest_balance()
    new = round(max(0.0, bal - float(amount)), 4)
    _GUEST_ALLOWANCE_PATH.write_text(
        json.dumps({"balance_eur": new}), encoding="utf-8")
    return new


def try_without_account() -> dict:
    save_session({"device_token": None, "mode": "guest"})
    if not _GUEST_ALLOWANCE_PATH.exists():
        guest_balance()  # init €2
    return account_snapshot()


def magic_link(email: str) -> dict:
    return get_ledger().request_magic_link(email)


def verify(email: str, code: str) -> dict:
    r = get_ledger().verify_magic_link(email, code)
    save_session({"device_token": r["device_token"], "mode": "signed_in", "email": email})
    return {"ok": True, **account_snapshot(), "device_token": r["device_token"]}


def sign_out() -> dict:
    tok = device_token()
    if tok:
        get_ledger().sign_out(tok)
    save_session({"device_token": None, "mode": "signed_out"})
    return account_snapshot()


def delete_account() -> dict:
    tok = device_token()
    if tok:
        get_ledger().delete_account(tok)
    save_session({"device_token": None, "mode": "signed_out"})
    return account_snapshot()


# ── document status chips ──────────────────────────────────────────────

def doc_content_fingerprint(state: dict) -> str:
    doc = state.get("doc") or {}
    sections = doc.get("sections") or {}
    parts = []
    for k in sorted(sections.keys()):
        sec = sections[k] or {}
        parts.append(k)
        parts.append(sec.get("md") or "")
        fields = sec.get("fields") or {}
        for fk in sorted(fields.keys()):
            parts.append(fk)
            parts.append(str((fields[fk] or {}).get("value") if isinstance(fields[fk], dict) else fields[fk]))
    sketch = (doc.get("sketch") or {}).get("placeholders") or []
    for ph in sketch:
        parts.append(str(ph.get("id")))
        parts.append(ph.get("md") or "")
        parts.append(ph.get("label") or "")
    return content_sha256("\n".join(parts))


def document_status(doc_entry: dict | None, *, blocking_gaps: int = 0, state: dict | None = None) -> dict:
    """Return {key, label, class} for consistent chips."""
    d = doc_entry or {}
    pay = d.get("payment") or {}
    if pay.get("status") == "paid":
        rev = pay.get("revision") or "A"
        paid_fp = pay.get("content_sha256")
        if state is not None and paid_fp:
            cur = doc_content_fingerprint(state)
            if cur != paid_fp:
                next_rev = _next_rev(rev)
                return {
                    "key": "revised",
                    "label": f"⟳ Rev {next_rev} – utkast",
                    "class": "st-revised",
                    "paid": True,
                    "dirty": True,
                    "revision": next_rev,
                }
        return {
            "key": "paid",
            "label": f"€ Betalt · rev {rev}",
            "class": "st-paid",
            "paid": True,
            "dirty": False,
            "revision": rev,
        }
    if blocking_gaps and blocking_gaps > 0:
        return {
            "key": "gaps",
            "label": f"● {blocking_gaps} mangler",
            "class": "st-gaps",
            "paid": False,
        }
    # Has content / generated → ready; else draft
    has_export = bool(d.get("export_path"))
    generated = bool(d.get("generated_at")) or has_export
    if generated or (state and (state.get("doc") or {}).get("sections")):
        # Still draft if never generated and empty? Prefer ready when no blocking gaps
        if generated or blocking_gaps == 0:
            # empty new shell → Utkast; if gaps computed and 0 blocking after gen → Klar
            if generated and blocking_gaps == 0:
                return {"key": "ready", "label": "✓ Klar for eksport", "class": "st-ready", "paid": False}
            if not generated and blocking_gaps == 0:
                return {"key": "draft", "label": "○ Utkast", "class": "st-draft", "paid": False}
    return {"key": "draft", "label": "○ Utkast", "class": "st-draft", "paid": False}


def _next_rev(rev: str) -> str:
    rev = (rev or "A").strip().upper()
    if len(rev) == 1 and "A" <= rev <= "Y":
        return chr(ord(rev) + 1)
    return rev + "2"


def export_pricing_enabled() -> bool:
    """Paid export gate. Off by default for local development.

    Set FOLDOK_EXPORT_PRICE=1 in .env to re-enable wallet charges / paywall.
    """
    import os
    v = (os.environ.get("FOLDOK_EXPORT_PRICE") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    # Also honour value from .env if server loaded it into os.environ already;
    # if not set, default free (dev).
    try:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if env_path.exists() and "FOLDOK_EXPORT_PRICE" not in os.environ:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, val = line.partition("=")
                if k.strip() == "FOLDOK_EXPORT_PRICE":
                    vv = val.strip().strip('"').strip("'").lower()
                    return vv in ("1", "true", "yes", "on")
    except Exception:
        pass
    return False


def export_price_for_template(template: dict | None, caps: dict | None = None) -> tuple[str, int]:
    if not export_pricing_enabled():
        return "dev_free", 0
    tier = (template or {}).get("export_price_tier") or "standard"
    tiers = dict(EXPORT_TIERS_EUR)
    if caps:
        pj = caps.get("pricing") or caps.get("pricing_json") or {}
        tiers.update(pj.get("export_tiers_eur") or {})
    return tier, int(tiers.get(tier, 19))


def uses_local_anthropic_key() -> bool:
    """Local workbench with ANTHROPIC_API_KEY — AI billed to Anthropic, not Foldok € wallet."""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "") or ""
    if len(key) > 30 and key != "missing-key":
        return True
    # Mirror server.py load_env_file so imports outside server still see .env
    try:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, val = line.partition("=")
                if k.strip() == "ANTHROPIC_API_KEY":
                    key = val.strip().strip('"').strip("'")
                    break
    except Exception:
        pass
    return len(key) > 30 and key != "missing-key"


def can_ai_call() -> tuple[bool, str | None]:
    # Local engine + API key: Anthropic USD/credits pay for calls.
    # Foldok balance_eur is the product wallet (export / hosted metering), not the API console.
    if uses_local_anthropic_key():
        return True, None
    snap = account_snapshot()
    if snap.get("signed_in"):
        bal = float((snap.get("account") or {}).get("balance_eur") or 0)
        if bal <= 0:
            return False, "Saldo er €0 — fyll på for AI-kall. Redigering og re-eksport av betalte dokumenter fungerer fortsatt."
        return True, None
    if snap.get("guest"):
        if guest_balance() <= 0:
            return False, "Gratis kvote brukt opp — opprett konto og fyll på for mer AI."
        return True, None
    # signed out, not guest: allow workbench with local API key (dev), no account debit
    return True, None


def precheck_ai() -> None:
    ok, msg = can_ai_call()
    if not ok:
        raise MeterDenied(msg or "Insufficient balance", code="insufficient_balance")
    if uses_local_anthropic_key():
        return  # Anthropic key present — skip Foldok wallet gate
    tok = device_token()
    if tok:
        get_ledger().precheck(tok)


def meter_ai(*, purpose: str, model: str, tokens_in: int, tokens_out: int, raw_cost_eur: float) -> dict:
    job = "ai"
    p = (purpose or "").lower()
    if "index" in p:
        job = "index"
    elif "generat" in p or "section" in p:
        job = "generate"
    tok = device_token()
    sess = load_session()
    if sess.get("mode") == "guest":
        # Guest: debit local allowance at margin
        from proxy.ledger import MARGIN_MULT
        charged = round(float(raw_cost_eur or 0) * MARGIN_MULT, 5)
        if charged > 0:
            guest_debit(charged)
        return {"charged_eur": charged, "guest": True}
    if uses_local_anthropic_key():
        # Prefer recording against Foldok wallet when it has balance; never block local key usage.
        try:
            return get_ledger().meter(
                tok,
                job_type=job,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                purpose=purpose,
                raw_cost_eur=raw_cost_eur,
            )
        except MeterDenied:
            return {
                "charged_eur": 0.0,
                "skipped": True,
                "reason": "local_anthropic_key",
                "raw_cost_eur": float(raw_cost_eur or 0),
            }
    return get_ledger().meter(
        tok,
        job_type=job,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        purpose=purpose,
        raw_cost_eur=raw_cost_eur,
    )


def install_compile_hooks() -> None:
    """Wire foldok_compile.ask to Path B metering (never sends content)."""
    import foldok_compile as fc

    if getattr(fc, "_wo060_metering", False):
        return
    _orig_ask = fc.ask

    def ask(purpose, model, messages, system=None, max_tokens=1500):
        precheck_ai()
        text = _orig_ask(purpose, model, messages, system=system, max_tokens=max_tokens)
        # Last LEDGER entry is this call
        if fc.LEDGER:
            last = fc.LEDGER[-1]
            try:
                meter_ai(
                    purpose=purpose,
                    model=model,
                    tokens_in=int(last.get("in") or 0),
                    tokens_out=int(last.get("out") or 0),
                    raw_cost_eur=float(last.get("eur") or 0),
                )
            except MeterDenied:
                raise
            except Exception:
                pass
        return text

    fc.ask = ask
    fc._wo060_metering = True


def stamp_utkast_watermark(content: str) -> str:
    banner = (
        "\n\n---\n"
        "**UTKAST — ikke betalt.** Dette er en forhåndsvisning med vannmerke. "
        "Eksporter (trekkes fra saldoen) for en ren, merket PDF.\n"
        "---\n\n"
    )
    return banner + (content or "")


def mark_document_paid(
    state: dict,
    template_file: str,
    *,
    price_eur: float,
    revision: str,
    receipt_id: str,
    pdf_sha256: str,
) -> dict:
    docs = state.setdefault("documents", [])
    entry = None
    for d in docs:
        if d.get("template") == template_file:
            entry = d
            break
    if not entry:
        entry = {"template": template_file}
        docs.append(entry)
    entry["payment"] = {
        "status": "paid",
        "price_eur": price_eur,
        "revision": revision,
        "receipt_id": receipt_id,
        "pdf_sha256": pdf_sha256,
        "content_sha256": doc_content_fingerprint(state),
        "paid_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
    return entry


def export_entitlement(doc_entry: dict | None, state: dict | None) -> dict:
    """Decide charge vs free re-export."""
    if not export_pricing_enabled():
        return {"charge": False, "reason": "dev_free", "revision": "A"}
    st = document_status(doc_entry, blocking_gaps=0, state=state)
    if st.get("key") == "paid" and not st.get("dirty"):
        return {"charge": False, "reason": "reexport_free", "revision": st.get("revision") or "A"}
    rev = "A"
    if st.get("key") == "revised":
        rev = st.get("revision") or "B"
    elif (doc_entry or {}).get("payment", {}).get("revision"):
        rev = _next_rev(doc_entry["payment"]["revision"])
    return {"charge": True, "reason": "new_export", "revision": rev}
