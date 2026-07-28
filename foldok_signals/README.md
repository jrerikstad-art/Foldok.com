# foldok_signals

Analytics that obeys the same rules as everything else in Foldok.

## The trap this avoids

You sell on *"106 engine files make zero network calls"* and *"here is
everything that left this machine"*. If the product then phones home with usage
data, the first engineer who opens the network tab finds it, and the trust story
dies in one screenshot. These users are exactly the people who check.

So telemetry is content-free **by construction**, not by convention:

```python
Event(name="folder_opened", codes={"project_name": "Johan Sverdrup"})
# SignalRefused: 'project_name' is not a registered code field.
#   Add it to VOCAB with the exact set of values it may take — a field that
#   accepts arbitrary strings is how a file name ends up in analytics.
```

Events carry **counters** (numbers) and **codes** (values from a fixed
vocabulary). There is no field that would accept a file name, a client, or a
sentence of a document.

## One funnel, because you have three users

```
1 session(s)
  opened a folder             1 #
  finished indexing           1 #
  saw the gap list            1 #
  resolved a first gap        1 #
  exported a document         0    -100%

Biggest drop: exported a document (100% lost)

Where it said no:
  extraction_failed    no_text (1)

Telemetry: off · 5 event(s) recorded locally · sink 'local'
```

Cohorts and retention curves at n=3 are noise wearing a lab coat. Where people
stop, and where the product said no, is everything a solo founder can act on.

## Every refusal is feedback

`CallRefused`, `LayoutRefused`, `PackRefused`, `ConnectRefused`,
`ResolverRefused`, `LeakRefused`, `ExportRefused` — each is a moment where the
product said no to somebody trying to work.

```python
except CallRefused as exc:
    signals.on_refusal(exc)        # class + vocabulary code, never the message
```

The refusal *message* is never recorded. Those messages quote the user's content
on purpose — that is what makes them good UX and unfit for analytics.

Put a one-tap **"this blocked me"** on every refusal: `signals.blocked_me()`.

## Consent

Opt-in, asked once, with the full event list visible. Opt-out telemetry from a
privacy-positioned product is the exact hypocrisy people screenshot.

- Events are recorded locally **whether or not** consent was given — that is how
  the product diagnoses itself and how a bug report has a trail.
- Consent governs *sending*.
- Revoking purges the log **and** discards the install id. A revocation that
  keeps the pseudonym is not a revocation.

## Feedback is not telemetry

Separate type, separate rules. A bug report does not need analytics consent —
the user typed it and pressed send. It does need them to have seen what goes
with it, so `send_feedback` refuses without `approved=True`, and
`Feedback.preview()` shows the attached history.

Attachments run through `foldok_private.atrest.assert_exportable`, so the entity
vault physically cannot ride along with a bug report.

## Files

| File | Contains |
|---|---|
| `model.py` | `Event`, `Feedback`, the vocabulary, the guard. |
| `journey.py` | Consent, the local log, the funnel. |
| `signals.py` | The facade, refusal hooks, bug bundler, Activity panel. |

```
python -m pytest foldok_signals/tests -q
```
