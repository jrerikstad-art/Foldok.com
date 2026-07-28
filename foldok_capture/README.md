# foldok_capture

The folder is the bus. No pairing, no QR, no server.

```python
from foldok_capture import bind, publish, tasks_from_gaps, ingest

bind(folder, project_id="job_114")                                   # desktop
publish(folder, tasks_from_gaps(session.gaps()), project_id="job_114")
...                                                                   # phone shoots
report = ingest(folder, session)                                      # gaps close themselves
```

Capture v0.3.0 already binds a project to a SAF folder — OneDrive, Drive, local —
so the photo reaches the laptop through the customer's own already-approved sync
tool. Foldok never touches the network, and there is nothing for an IT
department to review.

```
<project folder>/
    .foldok/
        capture_tasks.json          desktop -> phone   (open photo gaps)
        binding.json                which Foldok job this folder is
    IMG_1710000000000.jpg           the photo          (phone)
    IMG_1710000000000.foldok.json   the sidecar        (phone)
```

**One file per capture, written once, never edited.** A single appended log
across two devices over a sync service produces conflict copies, and then the
evidence trail has two heads. Create-only files sync cleanly everywhere.

**The sidecar is the provenance.** A photo alone is a JPEG someone has to match
to a requirement by hand — the job Foldok exists to remove. A photo with a
sidecar closes its own gap and the document can cite the file and the moment.

## It never guesses

| Situation | What happens |
|---|---|
| photo with no sidecar | reported as `unlinked_photo` |
| sidecar for a gap this document lacks | reported as `unknown_gap` |
| photo not synced yet | reported as `missing_photo`, gap stays open |
| photo edited after capture | `checksum_mismatch`, gap stays open |
| capture taken in free mode | reported as `unassigned_capture` |
| requirement pack version bumped | still matches, on requirement + subject |

Matching a photo to a requirement by filename or timestamp is how fabricated
evidence enters a compliance document. `ingest` is idempotent and refuses to
infer.

## Privacy defaults

- `may_leave: false` on every photo. A photograph cannot be masked — nameplate,
  serial, client logo, sometimes a face. `foldok_private` blocks it unless a
  person approves that specific image.
- `location` omitted unless the user turned it on. For a compliance record a GPS
  fix is either proof someone was on site or a log of a worker's movements.
- `device` is a model string. Never IMEI, serial or advertising id.

## Files

| File | Contains |
|---|---|
| `model.py` | Sidecar, CaptureTask, TaskList, Binding, folder layout. |
| `bridge.py` | `publish`, `scan`, `ingest`, and the matching rules. |
| `CAPTURE_APP_SPEC.md` | The Dart-side changes for the Capture app. |

```
python -m pytest foldok_capture/tests -q
```
