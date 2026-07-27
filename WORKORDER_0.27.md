# WORKORDER_0.27.md — Agenten lager maler selv, og endrer layout på forespørsel
Field evidence: «i need a installation manual for this» → agent explained
that no installation manual exists in the sources and asked two questions.
It should have (a) noticed no template covers the type, (b) drafted one
(rung 3 — designed in TEMPLATE_LIFECYCLE, never built), (c) created the
document. Separately: users must be able to change document layout by
asking, not by editing JSON.

────────────────────────────────────────────────────────────────
A. RUNG 3 LIVE — the agent drafts the missing template
────────────────────────────────────────────────────────────────
A1. Tool: draft_template(description, artifact_model) → one Sonnet call
    returning a template JSON in the existing schema (sections,
    required_facts, required_media, writing_rules, gap_severity).
    Prompt carries: the schema, 2 exemplar templates, the artifact
    model, the project's fact-key inventory, and the rules below.
A2. HARD RULES on drafted templates (code-validated after generation,
    one retry on failure, else fall back to free_document):
    · first section MUST be identification with ≥3 identity
      required_facts for the artifact type (0.19B §2)
    · all drafted required_facts default severity 'warning' — NEVER
      'blocking' (blocking implies verified regulatory authority)
    · boilerplate/legal text is never AI-drafted; if the type needs a
      declaration, insert the generic responsibility paragraph
    · every section needs writing_rules incl. fact_citation
    · template marked  "origin": "ai_drafted", "badge": "AI-foreslått
      struktur"  until the user edits it → then "Egen mal"
A3. FLOW when no template matches: the agent does NOT ask permission to
    think. It drafts, then shows the STRUCTURE for confirmation:
      «Ingen ferdig mal for installasjonsmanual — forslag til struktur:
       1. Identifikasjon · 2. Systemoversikt · 3. Forutsetninger og
       krav · 4. Installasjonssekvens · 5. Kontroll og verifikasjon ·
       6. Kilderegister.  [Bruk denne] [Juster ▾]»
    [Bruk denne] → template saved to the user's library + document
    created + generation offered with €. Two clicks from request to
    draft document.
A4. Drafted templates are the demand signal (TEMPLATE_LIFECYCLE):
    log {suggested_name, sections} to local telemetry so popular
    drafts become curated system templates.

────────────────────────────────────────────────────────────────
B. PRESCRIPTIVE DOCUMENTS — new provenance class in PROSE
────────────────────────────────────────────────────────────────
Descriptive templates compile what sources SAY. Prescriptive ones
(installation, procedure, service, commissioning) must state what to
DO — which no source contains. Rule, applied to any section whose
writing_rules carry "prescriptive": true:
  · facts inside steps stay cited (depths, capacities, standards)
  · the SEQUENCE is AI-drafted and visibly badged:
    «AI-foreslått rekkefølge — bekreft mot leverandørens anvisning»
  · each procedure section ends with [AUTHOR: bekreft mot
    leverandøranvisning] placeholder
  · a mandatory section «Hva leverandørens manual må dekke» lists the
    [MANGLER] items only the manufacturer can supply (chamber layout,
    tiltrekkingsmoment, backfill-spesifikasjon …)
  · export declaration gains: «Prosedyresekvenser er AI-foreslåtte
    forslag basert på prosjektets dokumenterte forutsetninger, ikke
    leverandørens anvisning.»

────────────────────────────────────────────────────────────────
C. LAYOUT VIA CHAT — structural edits as tools
────────────────────────────────────────────────────────────────
C1. Tools (all free, all versioned, all reversible):
      move_section(key, position)      rename_section(key, title)
      add_section(title, after, rules?) remove_section(key)  [soft]
      set_section_order([keys])        toggle_section(key, on/off)
      set_block_layout(section, "table"|"list"|"prose")
      set_document_option(key, value)   # språk, nummerering, forside,
                                        # topptekst/bunntekst, logo
C2. Chat examples that must work:
      «flytt materiallisten før installasjonssekvensen» → move_section
      «legg til en seksjon for HMS etter systemoversikt» → add_section
      «gjør tekniske data til en tabell i stedet for punktliste»
         → set_block_layout
      «fjern kilderegisteret fra denne» → toggle_section(off) + warning
         that traceability is reduced in export
C3. Structural edits change THIS document only. Offer once, after the
    third such edit in a document: «Vil du lagre dette som din egen mal
    for neste gang? [Lagre som mal]» → saves modified structure as an
    owned template (origin: "user_modified").
C4. Every structural change: version entry, undo, and NO regeneration
    (moving a section does not re-run generation — content follows).

────────────────────────────────────────────────────────────────
D. SYSTEM TEMPLATE — installation_manual (curated; rung 1)
────────────────────────────────────────────────────────────────
Ship the attached installation_manual.json so the common case is
curated rather than drafted. It is the reference implementation of the
prescriptive rules in §B: identification + system overview + cited
prerequisites/requirements, prescriptive sequence with badge and author
placeholders, verification checklist, «Hva leverandørens manual må
dekke», source register, declaration.

────────────────────────────────────────────────────────────────
E. ACCEPTANCE
────────────────────────────────────────────────────────────────
1. «i need a installation manual for this» in the renseanlegg project →
   document created from installation_manual (no questions first);
   reply ≤120 words naming what was created and one optional question.
2. Ask for a document type with NO template («lag en idriftsettelses-
   rapport») → structure proposed inline → [Bruk denne] → template
   saved + document created; template carries AI-foreslått badge and
   no blocking severities.
3. «flytt materiallisten øverst» → section moves, version logged, no
   tokens spent, no regeneration.
4. After 3 structural edits → save-as-template offer appears once.
5. Prescriptive sections in the generated manual: cited facts intact,
   sequence badged, author placeholders present, «leverandørens manual»
   section lists the real [MANGLER] items.
