# WORKORDER_0.29.md — Form-fill: en ny dokumentart (skjemaer, ikke prosa)
Trigger: Toyota multipoint inspection form. Every template so far produces
NARRATIVE documents with cited prose. A checklist/inspection form is a
different species: a DATA-CAPTURE INSTRUMENT — ~40 tri-state ratings,
measurement fields, signature. This is what the trades wedge fills out
every day (kontrollskjema, FDV-skjema, egenkontroll, sjekklister), so it
is likely the most wedge-relevant remaining build.

DESIGN PRINCIPLE: the engine's job on a form is (a) reproduce structure
faithfully, (b) PRE-FILL what the index already knows, (c) leave the rest
as clean capture fields — with the same MANGLER/citation discipline.

────────────────────────────────────────────────────────────────
A. SCHEMA — minimal, one new block type + field model
────────────────────────────────────────────────────────────────
A1. block_type += 'form_section' (migration_008). Content model:
    { "title": "Under Hood", "columns": 1|2,
      "fields": [ {field}, ... ] }
A2. FIELD MODEL (the decision to get right once):
    { "key": "brake_lining_lf",          // canonical, joins fact keys
      "label": "Bremsebelegg venstre foran",
      "type": "rating3|check|measure|text|date|signature|photo",
      "unit": "mm|32nds|bar|°C|null",
      "options": ["ok","attention","immediate"],   // rating3 only
      "value": null,                     // user-entered or prefilled
      "source": null,                    // fact_id if prefilled, else null
      "required": true|false,
      "note": ""                          // free text per field
    }
    TYPES:
      rating3   — the green/yellow/red pattern (ok / may require future
                  attention / requires immediate attention). Renders as
                  three-state control; exports as colored box.
      check     — binary done/not done
      measure   — number + unit; optional min/max for out-of-range flag
      text/date/signature/photo — self-evident; photo binds an indexed file
A3. Fact linkage: a filled field with a canonical key BECOMES a fact
    (fact_type='measurement' for measure, 'spec' for text/date,
    provenance='user' unless prefilled from an existing fact). This means
    today's inspection form feeds tomorrow's report — the index grows
    from routine work. THIS IS THE COMPOUNDING BIT.

────────────────────────────────────────────────────────────────
B. TEMPLATE FLAGS
────────────────────────────────────────────────────────────────
B1. Template-level: "document_species": "narrative" | "form_fill"
    (default narrative — all 13 existing templates unaffected).
B2. form_fill templates skip prose generation ENTIRELY: no Sonnet calls,
    no citation postprocess on fields. Cost of producing a blank filled
    form ≈ €0 beyond indexing. Sections render as form_section blocks.
B3. Optional narrative sections may coexist (e.g. a "Kommentarer"
    prose block) — species controls the DEFAULT, not a prohibition.

────────────────────────────────────────────────────────────────
C. PRE-FILL FROM INDEX (the reason this beats a paper form)
────────────────────────────────────────────────────────────────
C1. On document creation, for every field whose key matches an existing
    fact key in the project index: value = fact value, source = fact_id,
    rendered as a cited chip (blue). E.g. reg_no, vin, model_year,
    mileage, customer_name, date.
C2. Fields with no match stay empty and capture-ready. Required empty
    fields count as gaps (severity from template), so the gap pill works
    identically to narrative documents: "● 12 blokkerende" = 12 required
    fields unfilled. Export gate unchanged.
C3. NEVER auto-fill a rating or measurement from inference — only from
    an existing fact with the same key. A tri-state rating is always the
    technician's judgment (0.19B reference-value rules apply: no
    reference suggestions for ratings, ever).

────────────────────────────────────────────────────────────────
D. RENDERING & EXPORT (print fidelity matters here)
────────────────────────────────────────────────────────────────
D1. Editor: form_section renders as an actual fillable form — tap a
    rating to cycle green→yellow→red, numeric keypad for measures,
    signature pad, photo binder per field.
D2. Export PDF must be PRINT-FAITHFUL: two-column layouts preserved,
    rating boxes colored, measurement lines shown, footer with technician
    and date. A filled form must be recognizable to someone who knows the
    paper original.
D3. Mobile-first: this is filled standing next to a machine, not at a
    desk. Large tap targets, one section per screen on narrow viewports.

────────────────────────────────────────────────────────────────
E. FIRST SYSTEM TEMPLATE (ships with this order)
────────────────────────────────────────────────────────────────
E1. `inspection_checklist` — generic, trade-agnostic form_fill template:
    identification (prefilled), 1..n inspection groups (rating3 rows),
    measurements group, comments (narrative), technician + signature.
    Serves as the reference implementation and the target for imports.
E2. Do NOT ship a Toyota-specific template. Vehicle inspection arrives
    via template import (WORKORDER_0.29) — that is the wide door.

────────────────────────────────────────────────────────────────
F. ACCEPTANCE
────────────────────────────────────────────────────────────────
1. Create inspection_checklist in a project with reg_no/mileage facts →
   identification prefilled with cited chips; rest empty.
2. Fill 3 ratings + 2 measurements + signature → gap count drops
   accordingly; export produces a print-faithful PDF.
3. A filled measurement (e.g. brake_lining_lf = 6 mm) appears as a FACT
   in the project index and is citable by a later narrative document.
4. Zero model calls in the whole flow (ledger shows only indexing).
5. Ratings never auto-fill, never receive AI suggestions.
