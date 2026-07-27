-- ============================================================
-- FOLDOK ENGINE — migration_009_form_fill.sql
-- WORKORDER_0.29 — form_section block (form_fill document species)
-- ============================================================

alter table document_blocks drop constraint document_blocks_block_type_check;
alter table document_blocks add constraint document_blocks_block_type_check
  check (block_type in
    ('text','bullet_list','numbered_list','table','image','diagram',
     'warning_box','checklist','signature_block','reference_block',
     'missing_placeholder','equation','figure','toc','nomenclature',
     'page_break','author_placeholder','check_note','illustration',
     'bom_table','connection_spec','form_section'));

-- form_section content shape (application-level):
-- { title, columns: 1|2,
--   fields:[{key,label,type,unit,options,value,source,required,note}] }
-- field.type: rating3|check|measure|text|date|signature|photo
-- Templates may set document_species: 'form_fill' | 'narrative'
