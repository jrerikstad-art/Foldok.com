"""Foldok metering ledger — Path B.

Privacy contract: every meter entry may contain only:
  job_type, model, tokens_in, tokens_out, purpose, eur, ts, account_id
Never: file names, captions, facts, prompts, document text.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
import uuid
from pathlib import Path
from typing import Any

EXPORT_TIERS_EUR = {"basic": 9, "standard": 19, "complex": 49}
FREE_CREDIT_EUR = 2.0
MARGIN_MULT = 2.0  # charged = raw_model_cost * margin
LOW_BALANCE_EUR = 1.0


class MeterDenied(Exception):
    def __init__(self, message: str, *, code: str = "insufficient_balance"):
        super().__init__(message)
        self.code = code


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Ledger:
    """Thread-safe JSON ledger used by the workbench stub and tests."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else Path(__file__).resolve().parent / "data" / "ledger.json"
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"accounts": {}, "tokens": {}, "log": [], "receipts": []})

    def _read(self) -> dict:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def _account(self, data: dict, account_id: str) -> dict:
        acc = data["accounts"].get(account_id)
        if not acc:
            raise MeterDenied("Ukjent konto", code="no_account")
        return acc

    # ── auth (magic-link stub) ─────────────────────────────────────────

    def request_magic_link(self, email: str) -> dict:
        email = (email or "").strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Ugyldig e-post")
        code = f"{secrets.randbelow(1_000_000):06d}"
        with self._lock:
            data = self._read()
            data.setdefault("pending", {})[email] = {
                "code": code, "expires": time.time() + 900,
            }
            self._write(data)
        # Stub returns the code so workbench/tests can verify without SMTP.
        return {"ok": True, "email": email, "stub_code": code, "stub": True}

    def verify_magic_link(self, email: str, code: str) -> dict:
        email = (email or "").strip().lower()
        code = (code or "").strip()
        with self._lock:
            data = self._read()
            pend = (data.get("pending") or {}).get(email)
            if not pend or pend.get("code") != code or time.time() > float(pend.get("expires") or 0):
                raise MeterDenied("Ugyldig eller utløpt lenke", code="bad_link")
            data["pending"].pop(email, None)
            # Find or create account
            account_id = None
            for aid, acc in data["accounts"].items():
                if acc.get("email") == email:
                    account_id = aid
                    break
            if not account_id:
                account_id = "acc_" + uuid.uuid4().hex[:12]
                data["accounts"][account_id] = {
                    "id": account_id,
                    "email": email,
                    "name": email.split("@")[0],
                    "balance_eur": FREE_CREDIT_EUR,
                    "created_at": _now(),
                    "auto_refill": {
                        "enabled": False,
                        "amount_eur": 25,
                        "threshold_eur": 5,
                        "monthly_ceiling_eur": 100,
                        "month_spent_eur": 0,
                        "month_key": "",
                    },
                    "company": {},
                    "payment_method": None,
                }
                data["log"].append({
                    "ts": _now(), "account_id": account_id,
                    "job_type": "credit_grant", "model": None,
                    "tokens_in": 0, "tokens_out": 0,
                    "purpose": "new_account_free", "eur": -FREE_CREDIT_EUR,
                })
            token = "dev_" + secrets.token_hex(24)
            data["tokens"][token] = {
                "account_id": account_id, "created_at": _now(),
            }
            self._write(data)
            acc = data["accounts"][account_id]
            return {
                "device_token": token,
                "account": self._public_account(acc),
            }

    def resolve_token(self, device_token: str | None) -> dict | None:
        if not device_token:
            return None
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                return None
            acc = data["accounts"].get(meta["account_id"])
            return self._public_account(acc) if acc else None

    def _public_account(self, acc: dict) -> dict:
        return {
            "id": acc["id"],
            "email": acc.get("email"),
            "name": acc.get("name") or (acc.get("email") or "").split("@")[0],
            "balance_eur": round(float(acc.get("balance_eur") or 0), 4),
            "auto_refill": acc.get("auto_refill") or {},
            "company": acc.get("company") or {},
            "payment_method": acc.get("payment_method"),
            "low_balance": float(acc.get("balance_eur") or 0) < LOW_BALANCE_EUR,
        }

    def sign_out(self, device_token: str) -> None:
        with self._lock:
            data = self._read()
            data.get("tokens", {}).pop(device_token, None)
            self._write(data)

    def delete_account(self, device_token: str) -> None:
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                return
            aid = meta["account_id"]
            data["tokens"] = {t: m for t, m in data["tokens"].items() if m.get("account_id") != aid}
            data["accounts"].pop(aid, None)
            data["receipts"] = [r for r in data.get("receipts", []) if r.get("account_id") != aid]
            data["log"] = [e for e in data.get("log", []) if e.get("account_id") != aid]
            self._write(data)

    # ── balance / top-up ───────────────────────────────────────────────

    def topup(self, device_token: str, amount_eur: float, *, stub: bool = True) -> dict:
        amount = float(amount_eur)
        if amount < 1 or amount > 500:
            raise ValueError("Beløp må være mellom €1 og €500")
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            acc = self._account(data, meta["account_id"])
            acc["balance_eur"] = round(float(acc.get("balance_eur") or 0) + amount, 4)
            acc["payment_method"] = acc.get("payment_method") or {
                "brand": "stub", "last4": "4242", "stub": True,
            }
            data["log"].append({
                "ts": _now(), "account_id": acc["id"],
                "job_type": "topup", "model": None,
                "tokens_in": 0, "tokens_out": 0,
                "purpose": "stripe_checkout_stub" if stub else "stripe_checkout",
                "eur": -amount,
            })
            self._write(data)
            return {"ok": True, "account": self._public_account(acc), "credited_eur": amount}

    def set_auto_refill(self, device_token: str, cfg: dict) -> dict:
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            acc = self._account(data, meta["account_id"])
            ar = acc.setdefault("auto_refill", {})
            if "enabled" in cfg:
                ar["enabled"] = bool(cfg["enabled"])
            if "amount_eur" in cfg:
                ar["amount_eur"] = float(cfg["amount_eur"])
            if "threshold_eur" in cfg:
                ar["threshold_eur"] = float(cfg["threshold_eur"])
            if "monthly_ceiling_eur" in cfg:
                ar["monthly_ceiling_eur"] = float(cfg["monthly_ceiling_eur"])
            self._write(data)
            return self._public_account(acc)

    def update_company(self, device_token: str, company: dict) -> dict:
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            acc = self._account(data, meta["account_id"])
            cur = acc.setdefault("company", {})
            for k in ("name", "org_nr", "address", "logo_data_url", "signature_block"):
                if k in company:
                    cur[k] = company[k]
            self._write(data)
            return self._public_account(acc)

    def update_profile(self, device_token: str, *, name: str | None = None) -> dict:
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            acc = self._account(data, meta["account_id"])
            if name is not None:
                acc["name"] = (name or "").strip() or acc.get("name")
            self._write(data)
            return self._public_account(acc)

    # ── metering ───────────────────────────────────────────────────────

    def precheck(self, device_token: str | None, *, min_eur: float = 0.01) -> dict | None:
        """Return account if OK to spend; raise MeterDenied if balance ≤ 0."""
        if not device_token:
            return None  # guest / local key mode — caller decides
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            acc = self._account(data, meta["account_id"])
            bal = float(acc.get("balance_eur") or 0)
            if bal <= 0:
                raise MeterDenied(
                    "Saldo er €0 — fyll på for å bruke AI. Redigering, gap-fylling "
                    "og re-eksport av betalte dokumenter fungerer fortsatt.",
                    code="insufficient_balance",
                )
            if bal < min_eur:
                raise MeterDenied(
                    f"Lav saldo (€{bal:.2f}) — fyll på for å fortsette.",
                    code="insufficient_balance",
                )
            return self._public_account(acc)

    def meter(
        self,
        device_token: str | None,
        *,
        job_type: str,
        model: str | None,
        tokens_in: int,
        tokens_out: int,
        purpose: str,
        raw_cost_eur: float,
    ) -> dict:
        """Debit cost×margin. Zero-token / zero-cost → no debit, no log spend."""
        tokens_in = int(tokens_in or 0)
        tokens_out = int(tokens_out or 0)
        raw = float(raw_cost_eur or 0)
        if tokens_in == 0 and tokens_out == 0 and raw <= 0:
            return {"charged_eur": 0.0, "skipped": True, "reason": "zero_token"}

        charged = round(raw * MARGIN_MULT, 5)
        if not device_token:
            # Guest: record local-only skip (no account debit)
            return {"charged_eur": 0.0, "skipped": True, "reason": "no_account",
                    "would_charge_eur": charged}

        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            acc = self._account(data, meta["account_id"])
            bal = float(acc.get("balance_eur") or 0)
            if bal <= 0:
                raise MeterDenied("Saldo er €0", code="insufficient_balance")
            # Allow the call to complete even if it overshoots slightly; clamp to 0
            new_bal = round(max(0.0, bal - charged), 4)
            acc["balance_eur"] = new_bal
            entry = {
                "ts": _now(),
                "account_id": acc["id"],
                "job_type": job_type or "ai",
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "purpose": (purpose or "ai")[:80],
                "eur": charged,
            }
            # Privacy assert: only allowlisted keys
            assert set(entry) <= {
                "ts", "account_id", "job_type", "model",
                "tokens_in", "tokens_out", "purpose", "eur",
            }
            data["log"].append(entry)
            self._maybe_auto_refill(data, acc)
            self._write(data)
            return {
                "charged_eur": charged,
                "raw_cost_eur": raw,
                "balance_eur": acc["balance_eur"],
                "account": self._public_account(acc),
            }

    def _maybe_auto_refill(self, data: dict, acc: dict) -> None:
        ar = acc.get("auto_refill") or {}
        if not ar.get("enabled"):
            return
        bal = float(acc.get("balance_eur") or 0)
        thr = float(ar.get("threshold_eur") or 5)
        amt = float(ar.get("amount_eur") or 25)
        ceiling = float(ar.get("monthly_ceiling_eur") or 100)
        month = time.strftime("%Y-%m", time.gmtime())
        if ar.get("month_key") != month:
            ar["month_key"] = month
            ar["month_spent_eur"] = 0.0
        spent = float(ar.get("month_spent_eur") or 0)
        if bal < thr and spent + amt <= ceiling:
            acc["balance_eur"] = round(bal + amt, 4)
            ar["month_spent_eur"] = round(spent + amt, 4)
            data["log"].append({
                "ts": _now(), "account_id": acc["id"],
                "job_type": "topup", "model": None,
                "tokens_in": 0, "tokens_out": 0,
                "purpose": "auto_refill", "eur": -amt,
            })

    # ── export charge / receipts ───────────────────────────────────────

    def charge_export(
        self,
        device_token: str,
        *,
        tier: str,
        project_id: str,
        project_name: str,
        doc_name: str,
        template: str,
        revision: str,
        pdf_sha256: str,
        block_snapshot: dict | None,
        pdf_bytes: bytes | None = None,
    ) -> dict:
        price = int(EXPORT_TIERS_EUR.get(tier or "standard", 19))
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Logg inn for å eksportere", code="no_auth")
            acc = self._account(data, meta["account_id"])
            bal = float(acc.get("balance_eur") or 0)
            if bal < price:
                raise MeterDenied(
                    f"Saldo €{bal:.2f} er for lav for eksport (€{price}). Fyll på først.",
                    code="insufficient_balance",
                )
            acc["balance_eur"] = round(bal - price, 4)
            receipt_id = "rcp_" + uuid.uuid4().hex[:12]
            receipt = {
                "id": receipt_id,
                "account_id": acc["id"],
                "ts": _now(),
                "project_id": project_id,
                "project_name": project_name,
                "doc_name": doc_name,
                "template": template,
                "tier": tier,
                "price_eur": price,
                "revision": revision or "A",
                "pdf_sha256": pdf_sha256,
                "block_snapshot": block_snapshot or {},
            }
            if pdf_bytes:
                # Stored for cross-machine re-download in stub; production uses object store.
                store = self.path.parent / "receipts"
                store.mkdir(parents=True, exist_ok=True)
                fpath = store / f"{receipt_id}.bin"
                fpath.write_bytes(pdf_bytes)
                receipt["pdf_path"] = str(fpath)
            data.setdefault("receipts", []).append(receipt)
            data["log"].append({
                "ts": _now(), "account_id": acc["id"],
                "job_type": "export", "model": None,
                "tokens_in": 0, "tokens_out": 0,
                "purpose": f"export:{tier}", "eur": float(price),
            })
            self._write(data)
            return {
                "ok": True,
                "receipt": {k: v for k, v in receipt.items() if k != "block_snapshot"},
                "account": self._public_account(acc),
                "price_eur": price,
            }

    def refund_export(self, device_token: str, receipt_id: str, *, reason: str = "render_failed") -> dict:
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            acc = self._account(data, meta["account_id"])
            rcpt = next((r for r in data.get("receipts", [])
                         if r["id"] == receipt_id and r["account_id"] == acc["id"]), None)
            if not rcpt:
                raise MeterDenied("Kvittering ikke funnet", code="not_found")
            if rcpt.get("refunded"):
                return {"ok": True, "already": True, "account": self._public_account(acc)}
            price = float(rcpt.get("price_eur") or 0)
            acc["balance_eur"] = round(float(acc.get("balance_eur") or 0) + price, 4)
            rcpt["refunded"] = True
            rcpt["refund_reason"] = reason
            data["log"].append({
                "ts": _now(), "account_id": acc["id"],
                "job_type": "refund", "model": None,
                "tokens_in": 0, "tokens_out": 0,
                "purpose": reason[:80], "eur": -price,
            })
            self._write(data)
            return {"ok": True, "account": self._public_account(acc)}

    def usage(self, device_token: str) -> dict:
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            aid = meta["account_id"]
            month = time.strftime("%Y-%m", time.gmtime())
            entries = [e for e in data.get("log", [])
                       if e.get("account_id") == aid and (e.get("ts") or "").startswith(month)]
            by_cat = {"indeksering": 0.0, "generering": 0.0, "eksport": 0.0, "annet": 0.0}
            spark = []
            for e in entries:
                eur = float(e.get("eur") or 0)
                if eur <= 0:
                    continue
                jt = e.get("job_type") or ""
                purpose = (e.get("purpose") or "").lower()
                if jt == "export":
                    by_cat["eksport"] += eur
                elif "index" in purpose or jt == "index":
                    by_cat["indeksering"] += eur
                elif "generat" in purpose or jt in ("generate", "section", "ai"):
                    by_cat["generering"] += eur
                else:
                    by_cat["annet"] += eur
                spark.append({"ts": e.get("ts"), "eur": eur, "job_type": jt})
            receipts = [r for r in data.get("receipts", []) if r.get("account_id") == aid]
            # Strip heavy snapshot from list view
            docs = [{k: v for k, v in r.items() if k != "block_snapshot"} for r in receipts]
            return {
                "month": month,
                "spent_eur": round(sum(by_cat.values()), 4),
                "by_category": {k: round(v, 4) for k, v in by_cat.items()},
                "sparkline": spark[-60:],
                "token_details": [
                    {k: e.get(k) for k in (
                        "ts", "job_type", "model", "tokens_in", "tokens_out", "purpose", "eur"
                    )}
                    for e in entries if float(e.get("eur") or 0) > 0
                ],
                "documents": list(reversed(docs)),
                "account": self._public_account(self._account(data, aid)),
            }

    def get_receipt_pdf(self, device_token: str, receipt_id: str) -> tuple[bytes, dict]:
        with self._lock:
            data = self._read()
            meta = (data.get("tokens") or {}).get(device_token)
            if not meta:
                raise MeterDenied("Ikke innlogget", code="no_auth")
            rcpt = next((r for r in data.get("receipts", [])
                         if r["id"] == receipt_id and r["account_id"] == meta["account_id"]), None)
            if not rcpt:
                raise MeterDenied("Ikke funnet", code="not_found")
            path = rcpt.get("pdf_path")
            if not path or not Path(path).is_file():
                raise MeterDenied("PDF ikke lagret på denne maskinen", code="no_pdf")
            raw = Path(path).read_bytes()
            return raw, rcpt

    def privacy_log_scan(self, forbidden_substrings: list[str]) -> list[str]:
        """Return hits if any log entry / field contains forbidden content."""
        hits = []
        with self._lock:
            data = self._read()
            blob = json.dumps(data.get("log") or [], ensure_ascii=False)
            for s in forbidden_substrings:
                if s and s in blob:
                    hits.append(s)
        return hits


def content_sha256(text: str | bytes) -> str:
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()
