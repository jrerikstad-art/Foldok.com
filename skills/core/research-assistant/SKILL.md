---
name: research-assistant
description: |
  Technical research skill. Look up standards, components, similar products, competitors,
  or regulatory requirements and return scored, structured cards with sources and gaps.
  Use when the document needs external context that is not already in the project index.
use_when: |
  user asks for standards lookup, component research, competitor comparison,
  regulatory requirements, or “what else do we need for this document type”
---

# Research Assistant Skill (Technical)

## Goal
Produce high-signal, citable research cards that can be turned into EngineeringTable rows, CalloutBoxes, or missing-facts entries. Never invent facts. Always cite sources.

## Instructions
1. Clarify the research target (standard, component, product family, regulation, competitor, etc.).
2. Search only reliable public sources or the user’s own licensed documents (if linked).
3. For each finding produce a structured card:
   - Title / name
   - Why it is relevant
   - Key facts (with source)
   - Confidence / fit score (1–10)
   - Gaps or open questions
   - Suggested next action (add to document, request user confirmation, etc.)
4. Rank cards by relevance.
5. Explicitly list anything that could not be verified.

## Output contract
```json
{
  "query": "...",
  "cards": [
    {
      "title": "...",
      "relevance": "high|medium|low",
      "score": 8,
      "key_facts": ["...", "..."],
      "sources": ["url or document id"],
      "gaps": ["..."],
      "suggested_action": "add_to_section X | flag_as_missing | ..."
    }
  ],
  "unverified": ["..."],
  "summary": "..."
}
```

These cards can be converted by the Composition engine into EngineeringTable rows, CalloutBoxes, or entries in the missing-facts table.  
Do not write free-form prose into the Document AST. Do not invent values.
