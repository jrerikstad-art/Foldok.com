# WORKORDER_0.20.md — Én agent som VET hvor den er, GJØR det den blir bedt om, og SVARER folk
Consolidates four field failures from live testing (screenshots on file).
All four have ONE root cause: the agent reasons over too little context
and falls back on canned replies. Implement all sections in one pass.

Related specs: ONE_AGENT_SPEC.md (§1–3), COLD_START_SPEC.md (§2–3),
FLOW_ONE_OPERATION.md. This work order AMENDS those where noted.

────────────────────────────────────────────────────────────────
A. CONTEXT PAYLOAD — attach to EVERY chat call (root fix)
────────────────────────────────────────────────────────────────
FAILURE: in project "excavator_brain" with a 97 %-confirmed artifact
and 109 indexed files, the agent asked «Er det basert på
excavator_brain-prosjektet her, eller er det noe helt nytt?»

A1. Every in-project chat call attaches, without exception:
    · project name, folder path, file count, indexed count
    · FULL artifact model incl. confidence (not a summary)
    · document list with gap counts and current active document
    · FACT-KEY INVENTORY: the ~40 most frequent fact keys in the index
      with counts — KEYS ONLY, never values (cheap: ~200 tokens, and it
      is what lets the agent say "jeg ser hardware-, kode- og
      loggfakta" instead of asking whether the project exists)
    · full conversation history for the project
A2. RULE (system prompt): «Aldri spør om noe som finnes i konteksten
    eller kan slås opp i indeksen. Søk først (0 tokens), spør etterpå.»
A3. RULE: max 2 questions per reply, and only about things the sources
    cannot contain (intent, institution, preference, future decisions).
    Five-question intake walls are forbidden.
A4. Voice: warm but professional. NO emoji, no «Kult!»-style openers.
    Mirror the USER'S LANGUAGE (NO/EN) — templates already carry both.

ACCEPTANCE A: in excavator_brain, «jeg vil lage et phd forskningsprosjekt»
→ first paragraph names the project and its real content; no question
answerable from the index; ≤2 questions; ends with a concrete document
offer incl. €. Reply must NOT contain «eller er det noe helt nytt».

────────────────────────────────────────────────────────────────
B. INSTRUCTIONS ARE EXECUTED, NOT INTERVIEWED
────────────────────────────────────────────────────────────────
FAILURE: «bruk dette bildet på forsiden» (image already indexed, one
document active) → agent asked 2 questions + «Skal vi gjøre det?».

B1. Detect imperatives (bruk, sett, legg til, fjern, endre, oppdater,
    lag, generer…) → EXECUTE the free/cheap action, then report.
    Ask first ONLY if: irreversible, costs money (→ € confirm card), or
    genuinely ambiguous (2+ candidate targets AND none active).
B2. Active-object default: if exactly one document is open/active, it
    IS the target. Correct afterwards with ONE optional follow-up, e.g.
    «Satt som forside på Forskningsprosjektrapport ✓ — vil du ha den på
    Teknisk dokumentasjonspakke også?»
B3. Visual claims cite the index: image descriptions in chat are quoted
    from the extracted caption («Indeksert som: …»), never free-form
    vision commentary written in the reply.
B4. No overpromising: «klar for innlevering» and similar are banned.
    State literally what was done («genererer PDF med bildet på forsiden»).

ACCEPTANCE B: the cover-image instruction results in ONE action + ONE
optional follow-up question, zero permission-seeking.

────────────────────────────────────────────────────────────────
C. COLD START MUST REASON (amends COLD_START_SPEC §2–3)
────────────────────────────────────────────────────────────────
FAILURES (same session, one prospect — an insurance company doing due
diligence): «can you handle hundreds of folders / thousands of files?»
→ «Jeg er ikke sikker…»; «sjekk først om du kan» → same canned reply
again; «kan du lage et forslag til hvordan en endelig rapport kunne
sett ut» → «Ingen ferdig mal for det» + a button. All three are WRONG:
contract_review / spec_coherence_review / tender_compliance_matrix are
exactly this work.

C1. THE MANIFEST IS A TOOL, NOT A WALL. Capability questions call
    list_capabilities() and the agent REASONS over it. Grounding
    applies to CLAIMS («I can produce X»), not to matching — inferring
    that a due-diligence report ≈ contract_review is required behavior.
C2. DELETE the string «Jeg holder meg til det som står i
    kapabilitetslisten» and every canned two-button fallback used as a
    REPLACEMENT for an answer. Buttons accompany answers; never replace.

C2-BIS (diagnostic): the fallback string is byte-identical across four
    unrelated inputs → it is returned by a code path, not by the model.
    Grep the tree for "kapabilitetslisten" and for the two-button fallback
    payload. Instrument the cold-start handler: log whether an API call
    was made per message. Expected finding: an intent/whitelist precheck
    returns canned text without calling the model. **Remove the precheck
    entirely** — every cold-start message goes to the model with the §C5
    context payload; the manifest constrains *claims* inside the reply,
    never gates *whether* a reply is generated. No user message may be
    answered without a model call except pure zero-token lookups the
    agent itself invokes (list_gaps, privacy approved sentences,
    unambiguous cannot-list boundaries).

C3. Answer order for «kan du …?»:
    (a) template match → name it, what it produces, what inputs help,
        offer next step;
    (b) documentation domain, no exact match → rung 3, and SHOW the
        proposed structure inline (see C4);
    (c) outside documentation (3D-modellering, juridisk råd, verifisere
        beregninger) → boundary + nearest real capability.
    «Ikke sikker» is only permissible when (c) applies.
C4. «Foreslå struktur» RENDERS THE STRUCTURE IN CHAT, e.g.
    «Forslag: 1. Sammendrag · 2. Partsforhold og avtaler · 3.
    Forpliktelser og frister · 4. Åpne punkter og risiko · 5.
    Kilderegister» + [Bruk denne strukturen]. Showing beats offering.
C5. Cold-start context payload = manifest + FULL template catalog with
    descriptions + pricing line + scale block (C6) + history.
C6. SCALE BLOCK in capabilities.json (so scale answers are grounded):
    { "per_file_index_cost_eur": [0.001, 0.01],
      "parallel_workers": 5, "cache": "sha256, re-index is free",
      "multi_folder": true,
      "recommendation": "Very large corpora (1000+ files) run better as
       several focused projects (one per workstream) than one index." }
    Enables the correct answer: «Ja — hundrevis av mapper er greit;
    2 000 filer ≈ €10–20 og noen timer, én gang. Skal jeg skissere en
    oppdeling?»

ACCEPTANCE C: the three utterances above each produce a substantive
answer naming real templates; «foreslå struktur» prints sections;
scale question answers with numbers; nowhere does the canned
capability-list sentence appear.

────────────────────────────────────────────────────────────────
D. REGRESSION SUITE (scripts/agent_regression.py — run before release)
────────────────────────────────────────────────────────────────
Golden utterances, assert on the REPLY TEXT:
 1. (project) «jeg vil lage et phd forskningsprosjekt» → contains
    project name; ≤2 «?»; no «helt nytt».
 2. (project, image just added) «bruk dette bildet på forsiden» →
    contains «✓» or «Satt som»; ≤1 «?».
 3. (project) «den mangler registrerings nummer» → asks for the value
    or offers source lookup; NOT a feature menu (ONE_AGENT_SPEC §3).
 4. (cold) «can you handle thousands of files?» → contains a number
    and «€»; language = English (A4).
 5. (cold) «kan du lage et forslag til en endelig rapport, det er et
    forsikringsselskap» → names ≥1 real template OR prints a numbered
    structure; does NOT contain «ingen ferdig mal» alone.
 6. (cold) «sjekk først om du kan» → names templates; does not repeat
    the previous reply verbatim.
Any failure blocks the release, same gate as the privacy grep (0.19 §4).
