# foldok_console

What is true about Foldok right now — and what is worth doing about it.

```python
from foldok_console import Console

print(Console(".").report())          # one page
ok, blockers = Console(".").gate()    # in CI, before a deploy
```

## Why this exists

Not a SaaS admin panel — there are no users to watch yet. It exists because the
thing that actually went wrong was invisible: two release blockers survived from
0.73 to 0.78 untouched, and were only found by reading files by hand.

Run against the real 0.78 build, it found them in under a second, plus one that
had been missed entirely (`site-meta.json` still on 0.73.0):

```
FOLDOK CONSOLE  v0.78.0  [FAIL]

Release  [fail]
  [FAIL] 2 link(s) in index.html point at files that do not ship
           /boxes-demo.html, /diagram.html
  [FAIL] 6 localhost reference(s) in index.html, 2 clickable
  [warn] index.html has no og:image
  [warn] version strings disagree — site-meta.json=0.73.0

WORTH YOUR TUESDAY
  1. 2 link(s) point at files that do not ship   [minutes, score 60.0]
  2. 6 localhost references, 2 clickable         [minutes, score 48.0]
  3. no og:image                                 [minutes, score 18.0]
  4. version strings disagree                    [minutes, score 12.0]
  5. nobody has used this yet                    [hours,   score 1.88]
```

## Two design decisions

**It aggregates; it computes nothing.** Every engine already produces the
numbers — `AssetLibrary.summary`, `Index.diagnose`, `AuditLog.totals`,
`Signals.report`, `Learner.proposals`. The console's value is that they are in
one place and that somebody looks. That is why it is small and why it will not
rot.

**A queue, not a wall.** Metrics are something to look at; decisions are
something to do. Every finding carries evidence, an effort estimate and an
action, and the queue ranks by impact per hour. A one-line fix that breaks a
customer outranks a rewrite that might help one.

**No probe can take it down.** A dashboard that crashes because one subsystem
changed is a dashboard nobody opens — which is exactly how two blockers lived
for five builds.

## The last line of the queue

`nobody has used this yet` is a finding, deliberately. Every other panel
measures the build. None of them measures a customer.

## Files

| File | Contains |
|---|---|
| `model.py` | Panel, Finding, Snapshot, the ranking. |
| `release.py` | Dead links, localhost on production, og:image, secrets, versions. |
| `probes.py` | One probe per engine, all failure-tolerant. |
| `console.py` | The facade and the CI gate. |

```
python -m pytest foldok_console/tests -q
```
