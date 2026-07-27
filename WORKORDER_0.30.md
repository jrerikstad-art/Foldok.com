# WORKORDER_0.30.md — Malimport fra chat (rung 2 — «den brede døren»)
Designed since migration_002, specced in TEMPLATE_LIFECYCLE, never built.
Field evidence: user dropped a Toyota multipoint inspection form; the
agent indexed it, then asked two questions it could answer itself. The
correct behavior is ONE offer: make it a reusable template.

Strategic weight (PRODUCT_DIRECTION): this is the wide door — any
company's existing form becomes a smart template in two minutes. It is
the answer to «vi har våre egne skjemaer», the reason a firm switches,
and a moat no platform copies quickly because it is THEIR paper.

────────────────────────────────────────────────────────────────
A. TRIGGER & CLASSIFICATION (extends 0.26 §B add_file_to_project)
────────────────────────────────────────────────────────────────
A1. On any file drop, the classifier decides: FORM-SHAPED vs PROJECT
    MATERIAL. Form signals (from the index extraction, zero extra cost):
    blank value slots / ruled lines, repeated label:____ patterns,
    checkbox glyphs, company header + form number (e.g. «ITEM #7296-0220»),
    «Kundekopi/Dealer copy» style footers, grid of rating boxes.
A2. Form-shaped → the agent makes ONE offer, no questions:
    «Dette er et skjema — jeg kan gjøre det til en mal du kan bruke på
     hver jobb. Fant: kunde/kjøretøy (dato, navn, VIN, km, reg.nr),
     6 sjekkgrupper, måleverdier (dekkmønster, bremsebelegg) og
     trefarget vurdering. [Lag mal] [Se gjennom feltene]»
    Never ask «is this a template or filled data» when the file is
    blank; never ask what the output should be — a form's output is
    the form.
A3. Filled form dropped (values present) → offer BOTH: «Lag mal av
    strukturen» and «Les inn verdiene som fakta i prosjektet».

────────────────────────────────────────────────────────────────
B. EXTRACTION → TEMPLATE (one model call, then code)
────────────────────────────────────────────────────────────────
B1. extract_form_structure(file) → one Sonnet call, purpose=
    'template_import' (~€0.02, cached on sha256). Returns the 0.28
    field model: sections, fields with type/label/unit/options, layout
    columns, and any fixed legal/boilerplate text found VERBATIM.
B2. Code validation before showing: every field needs key+type;
    keys canonicalized (snake_case, mapped to known fact keys where
    obvious — vin, mileage, reg_no, customer_name); duplicates merged;
    unknown types coerced to text. Boilerplate marked non-editable-by-AI.
B3. document_species set to 'form_fill' when >60 % of fields are
    check/rating3/measure; else 'narrative'.

────────────────────────────────────────────────────────────────
C. THE REVIEW SCREEN (already designed — this is its first real use)
────────────────────────────────────────────────────────────────
C1. Two panes: original file rendered left, extracted structure right.
    Every field row: label · type ▾ · unit · requirement pill
    (Valgfritt / Advarsel / Blokkerende, tap to cycle) · key (advanced).
C2. Actions: rename, retype, reorder, group, delete, add missing field,
    mark boilerplate verbatim. Nothing is generated — this is data
    editing, zero tokens.
C3. Save → owned template (origin: "imported", badge «Egen mal»),
    appears in the picker, in «hva kan du bygge?» (manifest regen), and
    in the intent-matching catalog.
C4. SAME SCREEN serves rung-3 drafts (0.27) and «Lag din variant» of
    system templates — one editor, three entry points, per
    TEMPLATE_LIFECYCLE.

────────────────────────────────────────────────────────────────
D. COMPANY-WIDE VALUE (why this sells)
────────────────────────────────────────────────────────────────
D1. Imported templates carry company profile: logo, org.nr, header/
    footer text — so every exported document looks like THEIR document,
    not ours.
D2. A firm importing 5 forms has migrated its paperwork in ten minutes.
    That is the switching moment; make it feel like it.
D3. Local-first note (LEARNING §L2): imported templates live in the
    user's library; they are never uploaded to us, never used to train
    anything, and can be exported/backed up as plain JSON.

────────────────────────────────────────────────────────────────
E. ACCEPTANCE
────────────────────────────────────────────────────────────────
1. Drop the Toyota form in chat → ONE offer with a field summary, no
   questions → [Lag mal] → review screen shows ~40 fields grouped in
   6 sections with rating3 detected → save → template in picker.
2. Create a document from it in the RAV4 project → identification
   prefilled from index facts, ratings empty (0.29 §C).
3. Drop a Norwegian FDV/kontrollskjema PDF → same flow, Norwegian
   labels preserved verbatim, boilerplate marked non-AI.
4. Drop a filled form → both offers appear; reading values creates
   facts with provenance 'extracted'.
5. Total model cost for an import: one call, shown in the ledger.
