# foldok_tier

Three tiers between raw sentences and section prose:

| Tier | Meaning |
|------|---------|
| **strong** | Matched a claim pattern (rule, quantity, …) |
| **candidate** | Well-formed sentence about the subject — no pattern |
| **rejected** | Furniture, fragments, TOC, copyright |

Sections take strong first; candidates fill only when the section would be thin.
A candidate cites *source*, not *requirement type* — that difference travels with
the sentence.

```python
from foldok_tier import tier_sentences, fill_section, section_terms

report = tier_sentences(sentences, source="x.pdf", strong_ids=claims, topics=topics)
chosen = fill_section(report, section_terms=section_terms("installation"), want=6)
```

```
python -m pytest foldok_tier/tests -q
```
