# TEMPLATE_LIFECYCLE.md — how templates are born, edited, and versioned

Templates are DATA (doc_templates + template_sections rows). No code path.

## Three origins, one editor
1. SYSTEM templates (owner_id null): authored as JSON by us, seeded by
   scripts/seed-templates.ts. GUI for internal authoring: not before revenue.
2. IMPORTED templates: the user-facing creator. Upload existing form →
   extraction (once, sha256) → review screen (sections, fields, canonical
   key mapping, requirement pills, verbatim boilerplate) → owned template.
   Covers ~90% of demand: users HAVE forms; they don't design them.
3. FREE document: no structure (escape hatch, per PRODUCT_DIRECTION.md).

## The editor = the import review screen, generalized (Phase 5.1b)
Same screen opens on any owned template:
  - "Rediger mal" on imported templates
  - "Lag din variant" on system templates → duplicates row with
    owner_id=user, opens editor (system originals immutable)
  - Operations: rename section/field, add/remove field, set requirement
    level, toggle section required, edit boilerplate (with a strong
    warning; legal text edits are the user's responsibility)
No from-scratch builder in v1/v2. When demand appears, build it as
chat-to-template-draft feeding this same editor.

## Versioning rules
- doc_templates.version increments on edit; documents reference the
  template row they were created with → old documents never mutate.
- Editing a template affects NEW documents only. UI states this plainly.

## The coverage ladder (settled: no user ever faces a blank page)
Users do NOT know how documents should be structured — that is the product
premise (PRODUCT_DIRECTION.md #1). System templates are the DEFAULT door;
import is for users who have their own forms. When neither exists:

**Authoring rules for system templates:** see `TEMPLATE_STANDARD.md`.
System defaults define *shape and intent*; domain-locked OEM forms
(vehicle multipoint, company sheets) are imports/fixtures — never the
default brain for a broad document type.

  Rung 1 — SYSTEM template. Default. Picker RECOMMENDS from the artifact
    model after checkpoint A ("Dette ser ut som et løfteverktøy →
    Teknisk dokumentasjonspakke"), never just lists.
  Rung 2 — IMPORT. User has a form. Already specified above.
  Rung 3 — AI-DRAFTED template (closes the coverage gap). User describes
    the need in one sentence → one Sonnet call drafts a template in the
    existing sections schema (informed by artifact model + document
    conventions) → opens in the SAME review screen → user adjusts pills,
    confirms → owned template.

Rung 3 safety rules (non-negotiable):
  - Drafted requirements default to severity 'warning', NEVER 'blocking'.
    Blocking implies verified regulatory authority; AI drafts are
    conventions, not certifications.
  - Template carries badge 'AI-foreslått struktur' until user edits it
    (then 'Egen mal'). Provenance always visible.
  - Boilerplate/legal text is never AI-drafted into rung-3 templates;
    if the user needs declaration text, they paste it (kept verbatim).
  - Ledger purpose: reuse 'template_import'. One call, ~€0.02, cached
    against the description hash.
  - Popular rung-3 drafts are signals for which SYSTEM templates to
    author next (curated, standards-checked, promoted to rung 1).

Rung 3 lands in CURSOR_BUILD_PLAN Phase 5 alongside import — same screen,
same pipeline, one extra prompt.
