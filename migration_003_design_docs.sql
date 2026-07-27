-- ============================================================
-- FOLDOK ENGINE — migration_003_design_docs.sql
-- Fact types for engineering design documents
-- ============================================================
-- Design basis / design reports carry two fact classes the field
-- templates don't: recorded DECISIONS ("design life = 25 years",
-- source: client spec §3.1) and ASSUMPTIONS ("fixed base assumed",
-- source: minutes 2026-03-12). Both are traceable facts — they get
-- first-class types so the assumption register assembles itself.

alter table extracted_facts drop constraint extracted_facts_fact_type_check;
alter table extracted_facts add constraint extracted_facts_fact_type_check
  check (fact_type in
    ('spec','measurement','identifier','date','material','rating',
     'standard_ref','instruction','warning','contact',
     'decision','assumption','load','criterion'));
-- 'load'      : characteristic loads, load cases (q_k = 5.0 kN/m², wind zone …)
-- 'criterion' : acceptance criteria (UR ≤ 1.0, deflection ≤ L/250)
