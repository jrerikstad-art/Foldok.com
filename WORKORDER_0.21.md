# WORKORDER_0.21.md — Agenten HANDLER (og skriver kortere)
Amends WORKORDER_0.20 §B and ONE_AGENT_SPEC §2–3. One root defect:
the agent reasons excellently and acts timidly — it DESCRIBES work,
enumerates what it needs, and asks permission it already has, in
replies 3–5× longer than they should be.

Field evidence (verbatim): user wrote «Start med Design Basis» — an
instruction, after the agent had already offered «Opprett
prosjektmappe →». Reply was ~350 words, an 8-item intake list, the
sentence «Lag en ny mappe i Foldok og dra inn alle kildedokumentene»
(asking the user to do what the agent's own tool does), and ended
«Klar til å starte?» — having started nothing.

────────────────────────────────────────────────────────────────
A. ACT, DON'T DESCRIBE
────────────────────────────────────────────────────────────────
A1. NEVER instruct the user to perform an action a tool can perform.
    Forbidden when the corresponding tool exists:
      «lag en ny mappe», «dra inn filene», «velg templaten»,
      «opprett dokumentet», «legg til bildet»
    Tools that must be wired and callable from chat:
      create_project_with_skeleton(name, template_key?)
      create_document(template_key)
      add_file_to_project(file)      resolve_mangler(key, value)
      extract_targeted(key, file)    regenerate_section(key, instr)
      toggle_source(file, on)        list_gaps()
A2. ASK-LIST → ARTIFACT. If the reply would enumerate what the agent
    needs from the user, it must instead CREATE the container and put
    the list there: SJEKKLISTE.txt in the new project folder
    (COLD_START_SPEC §4), derived from the template's real
    required_facts/required_media. Chat then references it in one line.
    The agent may enumerate requirements ONLY while simultaneously
    creating the place they belong.
A3. Instruction verbs (start, lag, bruk, sett, legg til, fjern, endre,
    generer, opprett) → execute the free/cheap action, report result,
    then AT MOST ONE follow-up question. Confirm first only when:
    irreversible, costs money (€ confirm card), or 2+ candidate targets
    and none active.
A4. Banned closers: «Klar til å starte?», «Skal vi gjøre det?»,
    «Si fra når du er klar» — when the action was free and the intent
    was explicit. Replace with the completed action + optional
    follow-up.

REFERENCE REPLY for «Start med Design Basis» (shape and length):
  «Opprettet prosjektmappe **ROV — Design Basis** med Bilder/,
   Tegninger/, Rapporter/, Notater/ og SJEKKLISTE.txt (8 punkter fra
   malen: kravspesifikasjon, hovedtegning, DNV-referanser, testlogger…).
   Legg inn det du har — jeg indekserer fortløpende.
   Har prosjektet et dokumentnummer, eller setter jeg Rev. A / Draft?»
  (≈60 words, one action, one question.)

────────────────────────────────────────────────────────────────
B. LENGTH BUDGET (system prompt, enforced)
────────────────────────────────────────────────────────────────
B1. Default reply ≤ 120 words. Hard ceiling 200 words unless the user
    explicitly asks for a list, an overview, or «forklar».
B2. No markdown headings (##) in chat replies. Bold for the document
    name or the single key term only. Max ONE short list per reply,
    max 5 items; anything longer belongs in an artifact (A2).
B3. Structure of a good reply: [what I did / what fits] →
    [one concrete next step or offer with €] → [≤1 question]. Nothing
    else. No restating what the user just said, no recapping the
    project unless asked, no closing pleasantries.
B4. Capability answers (cold start): name the template(s), one line
    each on what it produces, the offer. Not a curriculum.
B5. The €-estimate and the action button carry information that does
    not need prose duplication.

────────────────────────────────────────────────────────────────
C. REGRESSION SUITE ADDITIONS (scripts/agent_regression.py)
────────────────────────────────────────────────────────────────
Extends WORKORDER_0.20 §D. Assert on reply text:
 7. (cold, after ROV capability answer) «Start med Design Basis» →
    MUST contain a completion marker («Opprettet» / «✓»);
    MUST NOT contain «Lag en ny mappe» or «dra inn»;
    MUST NOT contain «Klar til å starte»;
    word count ≤ 120; question marks ≤ 1.
 8. Every golden utterance from 0.20 §D additionally asserts
    word count ≤ 200 and heading count == 0.
 9. (project) «hva mangler?» → answer ≤ 80 words, list ≤ 5 items,
    remainder as «…og N til [Vis alle]».
Any failure blocks release (same gate as the privacy grep, 0.19 §4).

────────────────────────────────────────────────────────────────
D. ACCEPTANCE
────────────────────────────────────────────────────────────────
1. The ROV conversation replayed: «Start med Design Basis» creates the
   folder + skeleton + SJEKKLISTE, reply ≈60 words, one question.
2. SJEKKLISTE.txt content matches design_basis required_facts/media —
   not a generic list.
3. No reply in a full session (cold start → folder → index → document
   → gap fixing) exceeds 200 words or contains an ## heading.
4. Regression suite green before packaging.
