-- ============================================================
-- FOLDOK ENGINE — migration_001_engine.sql
-- Project index + template requirement schema
-- Supabase Postgres (pgvector enabled)
-- ============================================================

create extension if not exists vector;

-- ────────────────────────────────────────────────────────────
-- 1. PROJECTS
-- ────────────────────────────────────────────────────────────
create table projects (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references auth.users(id),
  name          text not null,
  created_at    timestamptz not null default now(),
  -- running token economics, updated by every pipeline call
  total_tokens_in   bigint not null default 0,
  total_tokens_out  bigint not null default 0,
  total_cost_eur    numeric(10,4) not null default 0
);

-- ────────────────────────────────────────────────────────────
-- 2. PROJECT FILES  (pointers only — originals never stored)
-- ────────────────────────────────────────────────────────────
create table project_files (
  id            uuid primary key default gen_random_uuid(),
  project_id    uuid not null references projects(id) on delete cascade,
  source_kind   text not null check (source_kind in ('gdrive','onedrive','sharepoint','upload','local')),
  source_ref    text not null,          -- drive fileId or storage path
  filename      text not null,
  mime_type     text,
  size_kb       integer,
  sha256        text not null,          -- dedupe key
  file_kind     text not null check (file_kind in
                  ('photo','pdf','spreadsheet','text','cad','video','other')),
  status        text not null default 'pending' check (status in
                  ('pending','indexed','failed','skipped')),
  fail_reason   text,
  indexed_at    timestamptz,
  index_model   text,                   -- e.g. 'claude-haiku-4-5'
  index_tokens_in   integer default 0,
  index_tokens_out  integer default 0,
  index_cost_eur    numeric(8,5) default 0,
  created_at    timestamptz not null default now(),
  unique (project_id, sha256)           -- same file re-linked = free
);
create index on project_files (project_id, status);

-- ────────────────────────────────────────────────────────────
-- 3. FILE SUMMARIES  (the AI's cached understanding — written once)
-- ────────────────────────────────────────────────────────────
create table file_summaries (
  id              uuid primary key default gen_random_uuid(),
  file_id         uuid not null unique references project_files(id) on delete cascade,
  caption         text not null,        -- <=40 words, dense, factual
  detail_summary  text,                 -- <=200 words, pdf/docs only
  content_tags    text[] not null default '{}',
  doc_role_hints  text[] not null default '{}',
    -- vocabulary: overview | installation_step | technical_data | safety
    --             maintenance | test_result | certificate | wiring | nameplate
    --             damage | packaging | tooling | environment
  quality_flags   text[] not null default '{}',
    -- vocabulary: blurry | dark | duplicate_of:<uuid> | screenshot | irrelevant
  embedding       vector(1536)
);
create index on file_summaries using ivfflat (embedding vector_cosine_ops);

-- ────────────────────────────────────────────────────────────
-- 4. EXTRACTED FACTS  (load-bearing: prose may only cite these)
-- ────────────────────────────────────────────────────────────
create table extracted_facts (
  id              uuid primary key default gen_random_uuid(),
  file_id         uuid not null references project_files(id) on delete cascade,
  project_id      uuid not null references projects(id) on delete cascade,
  fact_type       text not null check (fact_type in
                    ('spec','measurement','identifier','date','material',
                     'rating','standard_ref','instruction','warning','contact')),
  key             text not null,        -- canonical: 'swl','serial_no','test_standard'
  value           text not null,
  unit            text,
  confidence      real not null check (confidence >= 0 and confidence <= 1),
  source_excerpt  text,                 -- verbatim snippet
  source_location text,                 -- 'page 4' | 'nameplate in photo'
  verified_by_user boolean not null default false,
  created_at      timestamptz not null default now()
);
create index on extracted_facts (project_id, key);
create index on extracted_facts (file_id);

-- ────────────────────────────────────────────────────────────
-- 5. ARTIFACT MODEL  (checkpoint A output — one per project)
-- ────────────────────────────────────────────────────────────
create table artifact_models (
  project_id      uuid primary key references projects(id) on delete cascade,
  artifact_type   text not null,        -- 'lifting_tool','electrical_installation',...
  name            text not null,
  purpose         text not null,
  main_components jsonb not null default '[]',
    -- [{ "name": "hook assembly", "seen_in": ["<file_id>", ...] }]
  hazards         jsonb not null default '[]',
    -- [{ "hazard": "suspended load", "source": "<file_id>" | "inferred" }]
  lifecycle_stages text[] not null default '{}',
    -- subset of: transport install operate maintain inspect dispose
  confidence      real not null,
  user_confirmed  boolean not null default false,   -- GENERATION GATE
  corrections_log jsonb not null default '[]',
  model_used      text,
  tokens_in       integer default 0,
  tokens_out      integer default 0,
  updated_at      timestamptz not null default now()
);

-- ────────────────────────────────────────────────────────────
-- 6. TEMPLATE SYSTEM  (requirement schema — gap detection + writing
--    constraints both execute against these rows)
-- ────────────────────────────────────────────────────────────
create table doc_templates (
  id              uuid primary key default gen_random_uuid(),
  template_key    text not null unique, -- 'technical_doc_package','samsvarserklaering','sja'
  name            text not null,
  name_no         text not null,
  description     text,
  applies_to      text[] not null default '{}',  -- artifact_type filter, empty = all
  version         integer not null default 1,
  language_default text not null default 'no',
  export_price_tier text not null default 'standard'
                    check (export_price_tier in ('basic','standard','complex')),
  active          boolean not null default true,
  created_at      timestamptz not null default now()
);

create table template_sections (
  id              uuid primary key default gen_random_uuid(),
  template_id     uuid not null references doc_templates(id) on delete cascade,
  section_key     text not null,
  title           text not null,
  title_no        text not null,
  position        integer not null,
  required        boolean not null default true,
  condition       text,
    -- null = always. Expression over artifact_model, e.g.:
    -- "hazards.length > 0" | "'maintain' = any(lifecycle_stages)"
  gap_severity    text not null default 'warning'
                    check (gap_severity in ('blocking','warning','info')),
    -- blocking: export disabled until resolved or explicitly overridden
  required_facts  jsonb not null default '[]',
    -- [{ "key":"swl", "fact_type":"rating", "severity":"blocking",
    --    "label":"Safe Working Load", "label_no":"Sikker arbeidslast" }]
  required_media  jsonb not null default '{}',
    -- { "min_photos":1, "preferred_roles":["overview","nameplate"] }
  required_content jsonb not null default '[]',
    -- content rules the generated block must satisfy:
    -- "warning_before_hazardous_step" | "numbered_steps" | "imperative_voice"
    -- "table_format" | "no_uncited_specs" | "symbol:crush_hazard" ...
  writing_rules   jsonb not null default '{}',
    -- { "voice":"imperative"|"descriptive",
    --   "structure":"numbered_steps"|"prose"|"table"|"list",
    --   "max_words":300, "reading_level":"field_worker",
    --   "fact_citation":"required" }
  boilerplate     text,      -- fixed legal/standard text inserted verbatim, no AI
  boilerplate_no  text,
  unique (template_id, section_key)
);
create index on template_sections (template_id, position);

-- ────────────────────────────────────────────────────────────
-- 7. DOCUMENTS + SECTION MAPPINGS  (checkpoint B output)
-- ────────────────────────────────────────────────────────────
create table documents (
  id              uuid primary key default gen_random_uuid(),
  project_id      uuid not null references projects(id) on delete cascade,
  template_id     uuid not null references doc_templates(id),
  status          text not null default 'draft' check (status in
                    ('draft','review','confirmed','exported')),
  language        text not null default 'no',
  created_at      timestamptz not null default now()
);

create table section_mappings (
  id              uuid primary key default gen_random_uuid(),
  document_id     uuid not null references documents(id) on delete cascade,
  section_key     text not null,
  mapped_file_ids uuid[] not null default '{}',
  mapped_fact_ids uuid[] not null default '{}',
  gap_flags       jsonb not null default '[]',
    -- [{ "type":"missing_fact", "key":"swl", "severity":"blocking",
    --    "message_no":"Sikker arbeidslast mangler — påkrevd for løfteutstyr" }]
  user_adjusted   boolean not null default false,
  mapping_model   text,
  tokens_in       integer default 0,
  tokens_out      integer default 0,
  unique (document_id, section_key)
);

-- ────────────────────────────────────────────────────────────
-- 8. DOCUMENT BLOCKS + VERSIONS  (carried over from v15 spec,
--    trimmed to what the compiler needs)
-- ────────────────────────────────────────────────────────────
create table document_blocks (
  id              uuid primary key default gen_random_uuid(),
  document_id     uuid not null references documents(id) on delete cascade,
  section_key     text not null,
  block_type      text not null check (block_type in
                    ('text','bullet_list','numbered_list','table','image',
                     'diagram','warning_box','checklist','signature_block',
                     'reference_block','missing_placeholder')),
  position        integer not null,
  content         jsonb not null,
  cited_fact_ids  uuid[] not null default '{}',   -- traceability enforcement
  ai_generated    boolean not null default false,
  version_current integer not null default 1,
  updated_at      timestamptz not null default now()
);
create index on document_blocks (document_id, section_key, position);

create table document_versions (
  id              uuid primary key default gen_random_uuid(),
  document_id     uuid not null references documents(id) on delete cascade,
  block_id        uuid references document_blocks(id) on delete cascade,
  scope           text not null check (scope in ('document','block')),
  version_number  integer not null,
  snapshot        jsonb not null,
  change_summary  text not null,
  author_type     text not null check (author_type in ('user','ai')),
  ai_action       text,   -- 'generate'|'regenerate'|'shorten'|'voice_edit'|null
  tokens_in       integer default 0,
  tokens_out      integer default 0,
  created_at      timestamptz not null default now()
);

-- ────────────────────────────────────────────────────────────
-- 9. TOKEN LEDGER  (every API call, no exceptions)
-- ────────────────────────────────────────────────────────────
create table token_ledger (
  id            bigint generated always as identity primary key,
  project_id    uuid references projects(id) on delete set null,
  user_id       uuid,
  purpose       text not null check (purpose in
                  ('index_photo','index_doc','fact_extract','artifact_model',
                   'section_mapping','generate_section','regenerate_block',
                   'chat_edit','gap_check')),
  model         text not null,
  tokens_in     integer not null,
  tokens_out    integer not null,
  cost_eur      numeric(8,5) not null,
  created_at    timestamptz not null default now()
);
create index on token_ledger (project_id, created_at);

-- ────────────────────────────────────────────────────────────
-- RLS (owner-scoped; expand for teams later)
-- ────────────────────────────────────────────────────────────
alter table projects        enable row level security;
alter table project_files   enable row level security;
alter table file_summaries  enable row level security;
alter table extracted_facts enable row level security;
alter table artifact_models enable row level security;
alter table documents       enable row level security;
alter table section_mappings enable row level security;
alter table document_blocks enable row level security;
alter table document_versions enable row level security;
alter table token_ledger    enable row level security;

create policy own_projects on projects
  for all using (owner_id = auth.uid());
create policy own_files on project_files
  for all using (project_id in (select id from projects where owner_id = auth.uid()));
create policy own_summaries on file_summaries
  for all using (file_id in (select f.id from project_files f
                 join projects p on p.id = f.project_id where p.owner_id = auth.uid()));
create policy own_facts on extracted_facts
  for all using (project_id in (select id from projects where owner_id = auth.uid()));
create policy own_artifact on artifact_models
  for all using (project_id in (select id from projects where owner_id = auth.uid()));
create policy own_docs on documents
  for all using (project_id in (select id from projects where owner_id = auth.uid()));
create policy own_mappings on section_mappings
  for all using (document_id in (select d.id from documents d
                 join projects p on p.id = d.project_id where p.owner_id = auth.uid()));
create policy own_blocks on document_blocks
  for all using (document_id in (select d.id from documents d
                 join projects p on p.id = d.project_id where p.owner_id = auth.uid()));
create policy own_versions on document_versions
  for all using (document_id in (select d.id from documents d
                 join projects p on p.id = d.project_id where p.owner_id = auth.uid()));
create policy own_ledger on token_ledger
  for select using (user_id = auth.uid());

-- doc_templates + template_sections: readable by all authenticated users
alter table doc_templates     enable row level security;
alter table template_sections enable row level security;
create policy read_templates on doc_templates for select using (auth.role() = 'authenticated');
create policy read_sections  on template_sections for select using (auth.role() = 'authenticated');
