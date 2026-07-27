-- ============================================================
-- FOLDOK ENGINE — migration_006_contracts.sql
-- Fact types for contract/tender extraction (the engine in reverse:
-- the document is the source; the deliverable is understanding)
-- ============================================================
alter table extracted_facts drop constraint extracted_facts_fact_type_check;
alter table extracted_facts add constraint extracted_facts_fact_type_check
  check (fact_type in
    ('spec','measurement','identifier','date','material','rating',
     'standard_ref','instruction','warning','contact',
     'decision','assumption','load','criterion',
     'obligation','deliverable','deadline','penalty','right','requirement'));
-- obligation  : party X shall do Y            (source_excerpt = clause verbatim,
-- deliverable : item/doc/service to hand over  source_location = 'clause 12.3 / p.14')
-- deadline    : date/duration bound to an obligation
-- penalty     : LDs, sanctions, termination triggers
-- right       : options, entitlements (variation orders, suspension rights)
-- requirement : tender requirement rows (feeds compliance matrix mapping)
