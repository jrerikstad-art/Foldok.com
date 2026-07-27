# FLOW_ONE_OPERATION.md — Samtalen ER operasjonen

Supersedes the split FORSTÅ/BYGG interaction. One stream: talk → agree →
the agreement card generates → document renders below → tabs toggle
between documents. Nothing is copied between steps, ever.

## 1. WHAT DIES

- The separate "BYGG — SJEKKPUNKT B+C" card as a step the user walks to:
  its standalone template dropdown + "Generer utkast →" button.
- "Bekreft artefakt →" as a required manual stop (folds into the
  agreement card, see 3).

Manual path survives, demoted: one line under the chat —
"Vet du allerede hva du trenger? Velg mal manuelt ▾" → dropdown inline,
same generation path.

## 2. THE STREAM (one card: PROSJEKT — forstå og bygg)

Top: compact artifact strip, always visible:
"Tilbygg og fasadeendring — Example Road 12 · 91% · [Vis modell]"
(chat corrections keep updating it in background — unchanged).
Then the chat with existing chips.

## 3. THE AGREEMENT CARD (the one operation)

When intent is clear (intent call per WORKORDER_0.19 §1d, or a tapped
suggestion/chip), the ASSISTANT posts a card IN the stream:

  Da lager jeg:
  **Spesifikasjonsgjennomgang — konflikter og avklaringer**
  fordi du nevner motstridende krav i tegningene.
  Basert på: Tilbygg og fasadeendring · 91% ✎
  Estimert: €0,18 · ~40 s
  [ Lag dokumentet → ]   Annen mal ▾

Rules:

- [Lag dokumentet →] IS the consent (cost rule: € on the button).
  No further screens.
- Click AUTO-CONFIRMS the artifact if confidence ≥ 70% — agreement
  subsumes confirmation; ✎ edits first if wanted. Confidence < 70% →
  button reads [Bekreft forståelsen og lag dokumentet →] and the model
  one-liner expands for a look-over. Either way: ONE click total.
- "Annen mal ▾" opens the catalog inline in the card; pick → card
  re-renders. No navigation.

## 4. GENERATION LIVES IN THE STREAM

On click, the card becomes a progress message in the same chat:
"Bygger Spesifikasjonsgjennomgang … kartlegger 8/12 seksjoner"
(per-section ticks, NAVIGATION_SPEC >3s rule). On completion the
assistant posts: "Ferdig — 51 hull funnet, 3 blokkerende. Dokumentet er
åpnet nedenfor. [Gå til første mangel]" — and the rendered document
block below updates + scrolls into view.

## 5. DOCUMENT TABS (toggle, not navigation)

The DOKUMENTER row becomes tabs directly ABOVE the rendered document:
[Spesifikasjonsgjennomgang · 51] [Konstruksjonsrapport · 119]
[Designgrunnlag · 51] [Teknisk dok.pakke ✓] [+ Nytt]

- Click = instant toggle of the rendered block (per-doc state kept).
- Active tab: signal-yellow underline; gap counts live-update.
- [+ Nytt] scrolls up to the chat (the stream is how documents are
  born). FORSLAG cards stay under the tabs, quiet, dismissible.

## 6. ACCEPTANCE (walk it literally)

1. Fresh project → type "kunden vil ha komplett teknisk mappe" →
   agreement card (template + why + €) → ONE click → progress in
   stream → document renders below, tab added. Total user actions
   from story to rendered document: 2 (type, click).
2. Artifact at 65% → button reads "Bekreft forståelsen og lag …",
   model shown, one click still does both.
3. "Annen mal ▾" → pick Prosjektplan → generate → second tab; tab
   toggling swaps the rendered doc instantly, no reload.
4. The manual line produces the IDENTICAL generation path — no second
   code path for B+C.
5. Nothing anywhere asks the user to re-state or copy something the
   chat already knows.
