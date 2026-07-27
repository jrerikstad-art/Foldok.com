-- ============================================================
-- FOLDOK ENGINE — migration_004_editor.sql
-- Block layout + chat sessions for the design-tool editor
-- ============================================================

-- Per-block layout: presentation only, never content.
-- PDF renderer and web canvas both read this.
alter table document_blocks
  add column layout jsonb not null default '{}';
  -- shape: { "width": "full"|"half"|"third",
  --          "align": "left"|"center"|"right",
  --          "group_id": "uuid-or-null",   -- side-by-side pairing
  --          "group_slot": 1|2 }
  -- Constraint kept soft (jsonb) — validated in code (zod), so new
  -- layout options never need a migration.

-- Chat sessions: scoped, metered, fully attributable.
create table chat_messages (
  id            uuid primary key default gen_random_uuid(),
  document_id   uuid not null references documents(id) on delete cascade,
  user_id       uuid not null,
  scope         text not null check (scope in ('block','section','document')),
  scope_ref     text,            -- block_id or section_key, null for document
  role          text not null check (role in ('user','assistant')),
  content       text not null,
  -- when assistant reply proposes a change:
  proposal      jsonb,           -- {action:'update'|'insert'|'delete',
                                 --  block_id?, section_key?, new_content,
                                 --  cited_fact_ids[], missing_keys[]}
  proposal_status text check (proposal_status in (null,'pending','accepted','rejected')),
  tokens_in     integer default 0,
  tokens_out    integer default 0,
  created_at    timestamptz not null default now()
);
create index on chat_messages (document_id, created_at);

alter table chat_messages enable row level security;
create policy own_chat on chat_messages
  for all using (document_id in (select d.id from documents d
    join projects p on p.id = d.project_id where p.owner_id = auth.uid()));

-- Bundle metering lives on the document (contract §6: 30 regens + 20 chat turns)
alter table documents
  add column regen_count integer not null default 0,
  add column chat_turn_count integer not null default 0;
