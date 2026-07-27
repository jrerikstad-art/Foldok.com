-- ============================================================
-- FOLDOK ENGINE — migration_005_grammar_v2.sql
-- Template grammar v2: hierarchy, repetition, numbering,
-- nomenclature, equations/figures — comprehensive documents
-- ============================================================

-- 1. SECTION HIERARCHY + REPETITION
alter table template_sections
  add column parent_key text,          -- null = top-level chapter
  add column repeat_for text,          -- null | 'main_components' | 'experiments'
                                       -- | 'hazards' | custom artifact list key
  add column numbering_style text not null default 'decimal'
        check (numbering_style in ('decimal','none','appendix'));
-- repeat_for: at checkpoint B the section is INSTANTIATED once per item
-- in artifact_model.<repeat_for>; instance key = '<section_key>@<item_slug>'.

-- section_mappings must address instances:
alter table section_mappings
  add column instance_of text,         -- template section_key when repeated
  add column instance_item jsonb;      -- the artifact item this instance covers

-- 2. NEW BLOCK TYPES
alter table document_blocks drop constraint document_blocks_block_type_check;
alter table document_blocks add constraint document_blocks_block_type_check
  check (block_type in
    ('text','bullet_list','numbered_list','table','image','diagram',
     'warning_box','checklist','signature_block','reference_block',
     'missing_placeholder','equation','figure','page_break','toc',
     'nomenclature','author_placeholder'));
-- equation: content {latex, cited_fact_ids[]} — values cite or [MANGLER]
-- figure:   content {source_file_id|image_url, caption, auto_number:true}
-- toc:      rendered by code from section tree, zero tokens
-- nomenclature: rendered by code from symbol registry, zero tokens
-- author_placeholder: reserved editable block "[AUTHOR: ...]" — the
--   engine's explicit hand-off for interpretation/argument sections.

-- 3. NUMBERING & CROSS-REFERENCES (all pure code, zero tokens)
create table doc_ref_registry (
  id            uuid primary key default gen_random_uuid(),
  document_id   uuid not null references documents(id) on delete cascade,
  block_id      uuid not null references document_blocks(id) on delete cascade,
  ref_kind      text not null check (ref_kind in ('figure','table','equation','section')),
  ref_number    text not null,       -- '3.2' — recomputed on any structural change
  label         text,
  unique (document_id, block_id)
);
-- Prose carries {{ref:block_id}}; renderer resolves to 'Figure 3.2'.
-- Move a block → renumber pass → all references stay correct.

-- 4. SYMBOL / NOMENCLATURE REGISTRY (auto-assembled, like assumptions)
create table doc_symbols (
  id            uuid primary key default gen_random_uuid(),
  document_id   uuid not null references documents(id) on delete cascade,
  symbol        text not null,       -- 'σ_y', 'K_IC', 'E'
  definition    text not null,
  unit          text,
  source_fact_id uuid,               -- traceable like everything else
  unique (document_id, symbol)
);
-- Injected (compact) into every generate_section call → terminology
-- consistency across chapters. Rendered as the Nomenclature block.

-- 5. DOCUMENT MEMORY (rolling summary for long-document coherence)
alter table documents
  add column doc_memory text,               -- <=500 tok compressed summary
  add column outline_confirmed boolean not null default false;
-- Outline pass: for templates with repeat_for/hierarchy, checkpoint B
-- first proposes the chapter tree ("4 experiments found → 4 chapters?")
-- → user confirms (outline gate, mirrors artifact gate) → instances
-- created → generation proceeds. doc_memory updated after each section
-- (one cheap Haiku summarize call per ~3 sections, purpose='gap_check').

alter table doc_ref_registry enable row level security;
alter table doc_symbols enable row level security;
create policy own_refs on doc_ref_registry
  for all using (document_id in (select d.id from documents d
    join projects p on p.id = d.project_id where p.owner_id = auth.uid()));
create policy own_symbols on doc_symbols
  for all using (document_id in (select d.id from documents d
    join projects p on p.id = d.project_id where p.owner_id = auth.uid()));
