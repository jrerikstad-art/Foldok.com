# WORKORDER_0.49 — Kallkontrakter + redaksjonelt lag

Reference: AKVA Flexible Feeding System User Manual Rev B (structural benchmark).

## Part A — Call contracts (ENGINE_CONTRACT §4)

Every model call declares shape + validator + fallback (`call_contracts.py`).
`generate_section` is six steps:

1. SELECT FACTS — code  
2. PARTITION — Haiku JSON `{prose_facts, table_facts}` (skipped when structure decides)  
3. WRITE PROSE — Sonnet, contracted; no tables/figs/headings  
4. BUILD TABLE — code, B1 column vocabulary  
5. PLACE FIGURES — code  
6. COMPOSE/PAGINATE — LayoutTree + editorial furniture  

Corollary: prefer computation over validation.

## Part B — Editorial layer (`editorial_layer.py`, zero tokens)

- B1 table column vocabulary (technical / components / drawings / …)  
- B2 numbered figures + «Illustrasjoner og tabeller» appendix  
- B3 editorial rhythm (position = tiebreak)  
- B4 title page, TOC, running header/footer, revision table, glossary  
- B5 DesignSystem caption 7.5pt / table 8.5pt; figure keep-together  
- B6 cross-ref resolve (`se avsnitt N` / `{{ref:}}`); unresolved dropped  

## Regression

`test_63_wo049_call_contracts_and_editorial` — suite = **63**.
