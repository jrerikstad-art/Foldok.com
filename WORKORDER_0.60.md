# WORKORDER_0.60 — Konto, kreditt, betaling og dokumentstatus

The money round. Road to 1.0.0 («one stranger pays for one export»).

## Architecture — Path B (decided)

**Local-first + metering proxy.** Files and index stay on the user's machine.
A thin Foldok proxy holds the API key (in production), meters every call,
decrements the balance, and takes payment. The proxy sees token counts and
job types — NEVER file contents, captions, facts or documents.

Workbench ships an in-process stub (`proxy/`) so acceptance runs without
Stripe/email. Production swaps the stub URL; schemas stay identical.

## Shipped in 0.60.0

### Sign-in
- Hamburger top-right: Logg inn / Opprett konto (e-mail + magic link stub),
  «Prøv uten konto», signed-in: name, balance, tabs.

### Credits
- Sell euros; €2 free on new account; top-up stub (€10/€25/€50/custom);
  auto-refill opt-in; AI = cost × margin; zero-token = €0; export tiers
  €9/€19/€49; re-export of paid rev free forever.

### Account panel tabs
Konto · Saldo · Forbruk · Dokumenter · Firma

### Document status chips
○ Utkast · ● N mangler · ✓ Klar for eksport · € Betalt · rev X · ⟳ Rev B – utkast

### Proxy privacy
Meter payloads: `job_type`, `model`, `tokens_in`, `tokens_out`, `purpose` only.

## Regression
`test_68_wo060_account_credits_and_status` — suite = **68**.
