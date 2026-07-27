# WORKORDER_0.59 — «+ Nytt» lager faktisk et dokument, og skisselaget

## Shipped

### A — «+ Nytt» always creates
- Inline picker in Documents rail (recs + skisse + catalog + import)
- `POST /api/doc/create` → shell, open doc, Tools pane
- Low confidence → banner, never block; old toast deleted

### B/C — Sketch mode
- `sketch_document.json` + A4 canvas + tool set
- `sketch_recognize.py`: geometry → type, label → section bind, code fill
- Live placeholders in `doc.sketch`; vertical order = document order
- Annot insert unified with sketch insert (D3)

### C-bis / D
- «Lagre som mal» → `origin: sketched` under Dine maler
- Export blocked on unlabelled placeholders

## Regression
`test_67_wo059_sketch_recognize_and_fill` — suite = **67**.
