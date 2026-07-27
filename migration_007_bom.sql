-- ============================================================
-- FOLDOK ENGINE — migration_007_bom.sql
-- Minimal schema for BOM extraction + completeness suggestions
-- ============================================================

-- 1. Element instances are facts with structured props (qty, length,
--    spacing, material). One nullable jsonb column — no new table:
alter table extracted_facts add column props jsonb not null default '{}';

alter table extracted_facts drop constraint extracted_facts_fact_type_check;
alter table extracted_facts add constraint extracted_facts_fact_type_check
  check (fact_type in
    ('spec','measurement','identifier','date','material','rating',
     'standard_ref','instruction','warning','contact',
     'decision','assumption','load','criterion',
     'obligation','deliverable','deadline','penalty','right','requirement',
     'element'));

-- 2. BOM as a first-class block (code-rendered, like source_register):
alter table document_blocks drop constraint document_blocks_block_type_check;
alter table document_blocks add constraint document_blocks_block_type_check
  check (block_type in
    ('text','bullet_list','numbered_list','table','image','diagram',
     'warning_box','checklist','signature_block','reference_block',
     'missing_placeholder','equation','figure','toc','nomenclature',
     'page_break','author_placeholder','check_note','illustration',
     'bom_table'));

-- 3. Suggestions: computed in code (zero tokens); persisted only so
--    dismissals stick. Suggest, never push.
create table project_suggestions (
  id            uuid primary key default gen_random_uuid(),
  project_id    uuid not null references projects(id) on delete cascade,
  rule_id       text not null,
  name          text not null,
  template_key  text,
  reason        text not null,
  evidence      text,
  dismissed     boolean not null default false,
  created_at    timestamptz not null default now(),
  unique (project_id, name)
);
alter table project_suggestions enable row level security;
create policy own_suggestions on project_suggestions
  for all using (project_id in (select id from projects where owner_id = auth.uid()));
