"""Suggest retrieval probes from the index — not a domain schema."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .model import Question

STOP = {
    "the", "and", "for", "with", "from", "document", "pdf", "page",
    "og", "i", "på", "av", "til", "en", "et", "de", "det", "som", "er", "om",
    "guide", "report", "product", "system", "standard", "test",
}


def suggest_questions(index, *, lang: str = "no", limit: int = 5) -> list[Question]:
    """Cheap probes from tags, filenames, repeated caption terms."""
    tag_c: Counter = Counter()
    term_c: Counter = Counter()
    for e in index or []:
        if e.get("kind") == "skipped":
            continue
        for t in e.get("content_tags") or []:
            t = str(t).strip().lower().replace("-", "_")
            if t and t not in STOP and len(t) > 2:
                tag_c[t] += 2
        name = Path(e.get("file") or "").stem.lower()
        for tok in re.findall(r"[a-z0-9æøå]{4,}", name):
            if tok not in STOP:
                term_c[tok] += 1
        cap = (e.get("caption") or "").lower()
        for tok in re.findall(r"[a-z0-9æøå]{5,}", cap):
            if tok not in STOP:
                term_c[tok] += 1

    probes: list[str] = []
    no = lang.lower().startswith("no")

    # Always offer a scope question
    probes.append(
        "Hva handler dette korpuset om?" if no else "What is this corpus about?"
    )

    # Map strong signals to natural-language questions (probes, not section keys)
    SIGNAL_Q = [
        (("emc", "electromagnetic", "shield", "shielding", "skjerm"),
         "EMC-soner og skjerming" if no else "EMC zones and shielding"),
        (("cable", "tray", "kabel", "class", "klasse", "separation", "separa"),
         "Kabelklasser og avstandskrav" if no else "Cable classes and separation distances"),
        (("earth", "jord", "ground", "bonding", "equipotential"),
         "Jording og bonding" if no else "Earthing and bonding"),
        (("standard", "iec", "ieee", "mil", "en_", "nek"),
         "Hvilke standarder nevnes?" if no else "Which standards are mentioned?"),
        (("install", "mount", "monter", "safety", "sikker"),
         "Installasjons- og sikkerhetskrav" if no else "Installation and safety requirements"),
        (("weld", "sveis", "ndt"),
         "Sveise- og NDT-krav" if no else "Welding and NDT requirements"),
    ]

    blob = " ".join(t for t, _ in tag_c.most_common(20))
    blob += " " + " ".join(t for t, _ in term_c.most_common(30))

    for needles, qtext in SIGNAL_Q:
        if any(n in blob for n in needles):
            if qtext not in probes:
                probes.append(qtext)
        if len(probes) >= limit:
            break

    # Fill with top tag probes if still short
    for tag, _ in tag_c.most_common(8):
        if len(probes) >= limit:
            break
        label = tag.replace("_", " ")
        qtext = f"Hva sier kildene om {label}?" if no else f"What do sources say about {label}?"
        if qtext not in probes:
            probes.append(qtext)

    out = []
    for i, text in enumerate(probes[:limit]):
        out.append(Question(
            id=f"sug{i}",
            text=text,
            locale=lang,
            source="suggested" if i else "job_default",
        ))
    return out
