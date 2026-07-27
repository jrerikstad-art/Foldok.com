# Foldok metering proxy (Path B)

The desktop app keeps **all project files on the machine**. This proxy:

- holds the Anthropic key in production (workbench stub uses the local key)
- meters every AI call: tokens + job type only
- decrements the € balance (cost + margin)
- runs Stripe Checkout / Customer portal in production

**Never** send file names, captions, facts, prompts, or document text here.

## Local stub

In-process via `proxy.ledger` (default for workbench). Optional HTTP:

```
python -m proxy.stub_server
```

Env: `FOLDOK_PROXY_DATA` — ledger JSON path (default `proxy/data/ledger.json`).
