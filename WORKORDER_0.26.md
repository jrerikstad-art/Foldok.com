# WORKORDER_0.26.md — Chat er munnen, dokumentet er arbeidet
Root principle, generalizes several open bugs into one rule:

  THE AGENT PRODUCES ARTIFACTS THROUGH TOOLS, INTO DOCUMENTS.
  The chat reply only REFERENCES what was created — one line.
  If the deliverable is IN the reply text, the turn has failed.

Field evidence: agent hand-wrote raw <svg> into chat (typo baked in,
markup truncated mid-tag, €0.009 spent); earlier it offered a loose
wiring_specification.md, enumerated an 8-item intake list, and narrated
BOM updates «in three places». Same error every time.

────────────────────────────────────────────────────────────────
A. WHAT MAY NEVER APPEAR IN A CHAT REPLY
────────────────────────────────────────────────────────────────
A1. Validator-rejected outright (extends 0.22 §B2 machinery):
    · «<svg», «<html», «<table», markdown tables (|---)
    · fenced code blocks EXCEPT when the user explicitly asked for
      code/commands («vis meg python», «hvilken kommando»)
    · numbered requirement/intake lists >5 items
    · any block of document prose >120 words (0.21 §B1 already caps
      total length; this catches "here is your section:" dumps)
A2. On rejection: one retry with the violation named. Second failure →
    fallback: create the artifact with the appropriate tool if one
    exists, else state the missing capability honestly (0.22 §B3).

────────────────────────────────────────────────────────────────
B. TOOL SURFACE — every artifact type has a home
────────────────────────────────────────────────────────────────
  create_diagram(spec, section?)      → connection_spec block +
                                        diagram_engine SVG (0.24)
  add_block(section, type, content)   → table/list/text/warning block
  update_bom()                        → bom_engine recompute
  create_document(template_key)       → new document + tab
  create_project_with_skeleton(...)   → folder + SJEKKLISTE.txt (0.21 §A2)
  write_checklist(template_key)       → SJEKKLISTE.txt in the folder
  resolve_mangler / extract_targeted / toggle_source / regenerate_section
RULE: if a user request maps to an artifact and NO tool exists, the
agent says so plainly and offers the nearest real artifact — it never
substitutes chat text for the missing tool.

────────────────────────────────────────────────────────────────
C. THE REPLY PATTERN AFTER TOOL WORK (three lines maximum)
────────────────────────────────────────────────────────────────
  «Lagt inn funksjonsdiagram i **Designgrunnlag § 3** — 5 blokker,
   4 forbindelser, alle sitert til Søknad om utslippstillatelse.
   Kammerinndeling er ikke oppgitt i kildene, så anlegget er tegnet
   som én integrert modul. [Vis i dokumentet]»
Contains: what was created · where · the honest assumption · a link.
Not: the artifact, not a restatement of its contents.

────────────────────────────────────────────────────────────────
D. THE DIAGRAM FLOW, CONCRETELY (closes 0.24)
────────────────────────────────────────────────────────────────
D1. Request → agent proposes connection_spec JSON (components, pins,
    edges, provenance per edge) → CONFIRM TABLE in chat (rows, not
    markup) → user confirms → create_diagram() → SVG block in the
    document → C-pattern reply.
D2. diagram_engine.py (delivered, selftest green, deterministic) is the
    ONLY renderer. Fixtures for dev/regression, both real:
    excavatorbrain wiring + renseanlegg process flow.
D3. Renderer v1.1 while merging: flatten «\n» in labels to a second
    text line (multiline labels currently collapse).

────────────────────────────────────────────────────────────────
E. REGRESSION ADDITIONS
────────────────────────────────────────────────────────────────
23. No third-party service prices in replies («~€8 for a designer»
    was invented) — currency must match manifest or a tool receipt.
24. «lag et funksjonsdiagram» (renseanlegg project) → reply contains
    NO «<svg»; document gains a diagram block; reply ≤120 words and
    names the section.
25. «lag en sjekkliste for hva jeg trenger» → SJEKKLISTE.txt exists on
    disk; reply does not contain the list itself.
26. Any reply containing a markdown table or >5-item requirement list
    → validator rejects (unit test on the validator).
Release gate unchanged: privacy grep + golden suite (now 28).
