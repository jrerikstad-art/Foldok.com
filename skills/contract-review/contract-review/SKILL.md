---
name: contract-review
description: |
  Clause-by-clause review of construction or technical contracts.
  Flag risks (RED/YELLOW/GREEN), check statutory compliance, identify missing
  clauses, and suggest negotiation priorities. Use for source contracts
  before generating manuals or for QA of generated documents.
use_when: |
  user uploads or references a contract / subcontract,
  need risk analysis or compliance check before document generation
---

# Contract Review

## Workflow
1. Read the full contract.  
2. Clause-by-clause analysis.  
3. Risk scoring:  
   - RED = high risk / deal-breaker  
   - YELLOW = needs negotiation  
   - GREEN = acceptable  
4. Check against jurisdiction laws and (if provided) company policies.  
5. Identify missing standard clauses.  

## Output
Structured report only:
- Executive summary  
- Risk table (color-coded)  
- Negotiation priorities  
- Missing clauses list  
- Recommended next steps  

This output can be converted into CalloutBox + EngineeringTable blocks.  
Does not invent clauses. Does not paint layout.
