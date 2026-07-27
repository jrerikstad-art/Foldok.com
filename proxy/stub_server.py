"""Optional HTTP face for the Foldok metering stub.

Workbench uses in-process ledger via account_metering; this module is for
standalone proxy demos / future remote deploy.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .ledger import Ledger, MeterDenied

DATA = Path(os.environ.get("FOLDOK_PROXY_DATA", Path(__file__).parent / "data" / "ledger.json"))
LEDGER = Ledger(DATA)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter
        pass

    def _json(self, code: int, body: dict):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read()
        tok = self.headers.get("X-Device-Token") or body.get("device_token")
        try:
            if path == "/v1/auth/magic-link":
                return self._json(200, LEDGER.request_magic_link(body.get("email", "")))
            if path == "/v1/auth/verify":
                return self._json(200, LEDGER.verify_magic_link(body.get("email", ""), body.get("code", "")))
            if path == "/v1/meter":
                return self._json(200, LEDGER.meter(
                    tok,
                    job_type=body.get("job_type") or "ai",
                    model=body.get("model"),
                    tokens_in=int(body.get("tokens_in") or 0),
                    tokens_out=int(body.get("tokens_out") or 0),
                    purpose=body.get("purpose") or "ai",
                    raw_cost_eur=float(body.get("raw_cost_eur") or 0),
                ))
            if path == "/v1/topup":
                return self._json(200, LEDGER.topup(tok, float(body.get("amount_eur") or 0)))
            return self._json(404, {"error": "not found"})
        except MeterDenied as e:
            return self._json(402, {"error": str(e), "code": e.code})
        except Exception as e:
            return self._json(400, {"error": str(e)})


def main():
    port = int(os.environ.get("FOLDOK_PROXY_PORT", "8770"))
    print(f"Foldok metering stub on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
