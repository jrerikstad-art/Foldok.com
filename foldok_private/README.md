# foldok_private

The model works on masked text. The machine holds the truth.

```
foldok_diagram   0 of 14 files touch the network
foldok_gaps      0 of  9        foldok_index   0 of 10
foldok_boxes     0 of 11        foldok_assets  0 of  5
artifact_engine  0 of 34        diagram_engine 0 of 23
```

106 of 106 engine files make zero network calls. Only **four purposes** ever
reach a model: `index_file`, `partition_facts`, `generate_section_prose`,
`gap_fill_code`. This package is the gate they all pass through.

## Why this works here and nowhere else

ChatGPT and Claude must see the real text, because for them the text *is* the
working memory. Foldok holds ground truth locally — "AI proposes, code decides" —
so the model can work on `CLIENT_A · PROJECT_B · TAG_1` and the fact base puts
the real values back afterwards.

```python
from foldok_private import PrivateClient, EntityVault, EchoTransport

client = PrivateClient(EchoTransport(), EntityVault(), model="claude-sonnet-4-6")
env = client.prepare("generate_section_prose", text, facts=facts)
print(env.preview())            # what leaves this machine, before it leaves
result = client.send(env, approved=True)
result.text                     # real values restored locally
result.invented_entities        # entities the model made up
```

Masked out:

    Equinor ASA confirmed that Aker Solutions AS delivered the unit
    for Johan Sverdrup. Signed by Jan Rune Erikstad.
    ->
    CLIENT_A confirmed that VENDOR_A delivered the unit
    for PROJECT_A. Signed by PERSON_A.

## What it guarantees

- **No leak.** Every masked payload is re-scanned for every real value the vault
  knows, in any case or accent form. Anything that survives refuses the call
  rather than sending it.
- **Exact restoration.** Possessives, hyphens and case variants all come back
  correctly.
- **Invented entities are reported.** A token the vault never issued is a
  hallucinated entity, surfaced rather than passed through.
- **The audit log holds no content.** purpose, model, bytes, entity count, hash,
  outcome. Nothing you would hesitate to hand to a customer's IT department.
- **Images are blocked by default.** A nameplate photo cannot be masked — it
  carries the serial number, the client's logo and sometimes a face. Opt in per
  file.
- **The vault never leaves the machine.** It is the one file that must not be
  uploaded, synced, or attached to a support bundle.

## Enterprise is a transport swap

```python
from foldok_private import enterprise
client = enterprise(CustomerAzureEndpoint())   # nothing else changes
```

Same engine, same masking, same audit log — their deployment, their tokens,
their retention terms, and Foldok is not in the data path. That is a licence
conversation, not a fork: a junior engineer opens the tab and works on day one;
procurement buys the enterprise build later.

## Files

| File | Contains |
|---|---|
| `vault.py` | Entities, masking, unmasking, the leak guard. |
| `detect.py` | Deterministic patterns + the fact base. No NER model. |
| `envelope.py` | The outbound payload, the preview panel, the content-free log. |
| `client.py` | Policy and the client wrapping the four call sites. |

```
python -m pytest foldok_private/tests -q
```
