# foldok_reflow

The point where good extraction became unusable claims.

## Measured, not assumed

On the real 40-page SICK PDF:

```
PDF text extraction     ok, 66,333 characters
claim extraction        104 claims (87 factual, 17 non-factual)
```

Neither stage is broken. But the claims looked like this:

```
[practice]    3 3 Recommended data: 3.3 Recommended data lines...........
[consequence] It is therefore becoming increasingly impor‐
[consequence] As a result, only part of the electromagnetic
```

**A PDF has no sentences.** pypdf emits one line per *visual row*, so a sentence
spanning four rows arrives as four lines, and any newline-based splitter produces
fragments. A table-of-contents row becomes a claim. `impor‐` becomes the end of
one.

```
                    before   after
  lines               1581      498
  words_per_line       6.5     19.2
  line_completeness   0.184     0.58
  toc_lines             75        0
  usable               False     True

fragments among factual claims:  55  →  6
```

Same claim count. Now they are whole statements — *"An FE connection must never
be used as a protective equipotential bonding"* instead of a truncated line.

That one defect explains three separate symptoms: `no writable claims (budget 0)`,
the repeated `Etter dette — Etter dette —` (`_transition` builds a bridge from
`prev_summary.split(".")[0]`, and with no sentence there is nothing to build
from), and English fragments in Norwegian frames.

## Figures were never extracted at all

That same PDF contains **23 embedded images**. `foldok_index.extract` does not
mention images, figures, tables or XObjects anywhere — it returns text and
nothing else. So "there are pictures in the folder" and "the document has no
illustrations" were both true: the pictures are *inside* the PDFs.

```
20 figures extracted, with captions:
  FIG0C8C1E  Figure 6: Recommended cable structure using the example of a CAN/DeviceNet cable
  FIGB030ED  Figure 7: M12 Ethernet cable
  FIG8B3E7C  Figure 18: Shielding effect for cable trays
```

Uncaptioned figures are still returned and marked — a person can look at one, a
heuristic cannot.

## Two things this is honest about

**Reflow destroys tables.** Joining short cells into sentences is exactly what
fixes fragmented prose, and exactly what removes the column structure a table is
made of. Tables must be found in raw text, before reflow — a real ordering trap
with a test on it.

**pypdf flattens tables anyway.** On the real document it emits one cell per
line, so no column runs survive to detect. `table_note` says so rather than
returning a bare zero, because *"this document has no tables"* and *"this
extractor cannot see tables"* are different facts and only the second tells you
what to do: use a layout-aware extractor for table-heavy sources.

```
python -m pytest foldok_reflow/tests -q
```
