-- ============================================================
-- FOLDOK ENGINE — migration_002_custom_templates.sql
-- Company branding profiles + user-owned template import
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. COMPANY BRANDING PROFILE (render-time only, never in blocks)
-- ────────────────────────────────────────────────────────────
create table company_profiles (
  id              uuid primary key default gen_random_uuid(),
  owner_id        uuid not null references auth.users(id),
  company_name    text not null,
  org_no          text,
  role_line       text,           -- 'Sakkyndig virksomhet S-1234' etc.
  logo_url        text,           -- private bucket path
  stamp_url       text,           -- transparent PNG
  footer_text     text,
  accent_hex      text default '#16181D',
  address         text,
  phone           text,
  email           text,
  created_at      timestamptz not null default now(),
  unique (owner_id)
);

alter table company_profiles enable row level security;
create policy own_profile on company_profiles
  for all using (owner_id = auth.uid());

-- ────────────────────────────────────────────────────────────
-- 2. TEMPLATE OWNERSHIP  (null owner = built-in system template)
-- ────────────────────────────────────────────────────────────
alter table doc_templates
  add column owner_id        uuid references auth.users(id),  -- null = system
  add column source_file_ref text,      -- original uploaded template pointer
  add column import_status   text default null
        check (import_status in (null,'extracting','review','confirmed','failed')),
  add column import_model    text,
  add column import_tokens_in  integer default 0,
  add column import_tokens_out integer default 0,
  add column import_cost_eur   numeric(8,5) default 0;

-- unique key now scoped per owner (system keys stay globally unique via null)
alter table doc_templates drop constraint doc_templates_template_key_key;
create unique index doc_templates_key_owner
  on doc_templates (template_key, coalesce(owner_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- RLS update: users read system templates + own templates; write own only
drop policy read_templates on doc_templates;
create policy read_templates on doc_templates
  for select using (owner_id is null or owner_id = auth.uid());
create policy write_own_templates on doc_templates
  for insert with check (owner_id = auth.uid());
create policy update_own_templates on doc_templates
  for update using (owner_id = auth.uid());
create policy delete_own_templates on doc_templates
  for delete using (owner_id = auth.uid());

drop policy read_sections on template_sections;
create policy read_sections on template_sections
  for select using (template_id in
    (select id from doc_templates where owner_id is null or owner_id = auth.uid()));
create policy write_own_sections on template_sections
  for all using (template_id in
    (select id from doc_templates where owner_id = auth.uid()));

-- ────────────────────────────────────────────────────────────
-- 3. TEMPLATE IMPORT PIPELINE CONTRACT (documented here, code in Edge Fn)
-- ────────────────────────────────────────────────────────────
-- Flow:
--   a) user uploads template file (docx/pdf/photo) → stored in private bucket
--   b) MarkItDown → Haiku extraction call (purpose='template_import' — add to
--      token_ledger purpose enum below) producing draft template_sections:
--      section titles, field labels (→ required_facts candidates with
--      canonical key guesses), table column headers, boilerplate candidates
--   c) status='review' → UI checkpoint: user confirms sections, marks
--      required fields blocking/warning, approves boilerplate as fixed text
--   d) status='confirmed' → template appears in picker, usable immediately
-- Rules:
--   HARD: extraction call runs ONCE per uploaded file (sha256 dedupe applies)
--   HARD: boilerplate candidates default to verbatim fixed text — AI never
--         rewrites legal text from an imported template
--   Field keys map to canonical vocabulary where confident; otherwise stored
--   as nonstandard_key for the company's own namespace.

alter table token_ledger drop constraint token_ledger_purpose_check;
alter table token_ledger add constraint token_ledger_purpose_check
  check (purpose in
    ('index_photo','index_doc','fact_extract','artifact_model',
     'section_mapping','generate_section','regenerate_block',
     'chat_edit','gap_check','template_import'));
