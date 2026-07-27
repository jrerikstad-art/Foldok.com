-- ============================================================
-- FOLDOK ENGINE — migration_008_connection_spec.sql
-- WORKORDER_0.24 — connection_spec block (graph → deterministic SVG)
-- ============================================================

alter table document_blocks drop constraint document_blocks_block_type_check;
alter table document_blocks add constraint document_blocks_block_type_check
  check (block_type in
    ('text','bullet_list','numbered_list','table','image','diagram',
     'warning_box','checklist','signature_block','reference_block',
     'missing_placeholder','equation','figure','toc','nomenclature',
     'page_break','author_placeholder','check_note','illustration',
     'bom_table','connection_spec'));

-- connection_spec content shape (application-level):
-- { components:[{id,label,fact_id,image,pins}],
--   connections:[{from,to,label,note,provenance}],
--   svg: text }
