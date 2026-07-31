# foldok_shred

Measure a document. Keep structure and numbers. Drop the text.

```python
from foldok_shred import Shredder

shred = Shredder().shred("some_manual.pdf", grade="exemplary")
print(shred.report())
shred.proposals  # console queue — never applied
```

## Order is the product

```
read bytes → measure → build proposals → drop the text → return
```

`Shred` has no field that can hold body text. Section titles stay (a skeleton
without them is useless). Bodies never stay. Obligations go through
`foldok_learn` (citations only).

## Grades

| Grade | Behaviour |
|-------|-----------|
| `sample` / `ours` | Measure only |
| `exemplary` | Skeleton + design + obligation proposals |

## Console

```python
from foldok_shred.console_bridge import probe_shred
# Console snapshot includes shred bay proposals as decisions
```

```
python -m pytest foldok_shred/tests -q
```
