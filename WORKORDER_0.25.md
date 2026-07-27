# WORKORDER_0.25.md — Hendelser inn i samtalen, «ja» betyr kjør, ingen fiktive jobber

Field transcript (on file): file dropped + indexed → next turn agent
claims no file received → reasons from FILENAME despite paid extraction
→ user says «ja» twice, agent re-asks twice → finally NARRATES a
started job («klar om noen minutter») with, presumably, no job running.
Four bugs, one session. Also: reply CTA said create-project while the
button said «Start med tom mappe», and a COLD-START drop produced a
gap-match («Dekker 1 mangler: issue_date») — whose gaps?

────────────────────────────────────────────────────────────────
A. SYSTEM EVENTS JOIN THE CONVERSATION (kills the amnesia class)
────────────────────────────────────────────────────────────────
A1. Every system event is appended to the conversation history the
    model receives, as a system/tool turn: file added (+ its indexed
    caption and key facts), indexing done, gap-match result, project
    created, document generated, export done. If the UI shows it, the
    model has it. No parallel realities.
A2. Cold-start drops: with no project open, the agent's NEXT reply
    must acknowledge from the extraction:
    «Mottatt og indeksert: trygg forsikring.pdf — [caption]. Skal jeg
     opprette et prosjekt rundt den?» (one question, then B applies).
A3. INVESTIGATE the cold-start gap-match: a drop outside any project
    matched «issue_date» somewhere. If it matched another project's
    gaps → isolation leak in gap-matching (BUGFIX_0.19 scope: matching
    must be keyed to a project id; no project → no gap-match runs).

────────────────────────────────────────────────────────────────
B. «JA» BETYR KJØR (pending-action dispatch, code-level)
────────────────────────────────────────────────────────────────
B1. When the agent asks a confirm question («Skal jeg kjøre X?»), the
    proposed action is stored as pending_action {tool, args, asked_at}.
B2. Affirmative next message (ja/yes/ok/kjør/gjør det/go) → the server
    DISPATCHES pending_action directly and hands the model the tool
    results to report. The model cannot re-ask: by the time it speaks,
    the job exists.
B3. Validator: a reply containing a proposal question when
    pending_action was just affirmed → rejected. Asking the same
    confirm twice in a session for the same action → rejected.
B4. One confirm maximum per action, and only when required (0.21 §A3:
    money, irreversible, ambiguous). Free actions after an explicit
    request skip the confirm entirely.

────────────────────────────────────────────────────────────────
C. NO FICTIONAL JOBS (extends 0.22 §B to progress claims)
────────────────────────────────────────────────────────────────
C1. Progress/start verbs («starter», «kjører», «analyserer», «klar om»)
    require a job id from a real job-start tool return in the same
    turn. Report includes it implicitly: real step names and the job
    system's ETA — never invented minutes.
C2. The validator's completion-verb list (0.22 §B2) gains the
    progress-verb set. Unreceipted «Jeg starter straks» → rejected.

────────────────────────────────────────────────────────────────
D. INDEXED FILES ARE REASONED FROM THEIR EXTRACTION
────────────────────────────────────────────────────────────────
D1. If a file has index entries, capability/matching answers quote
    them («Indeksert som: forsikringsvilkår … funnet: issue_date,
    parter»). Filename-based inference is permitted ONLY for
    unindexed files and must be labeled («basert på filnavnet —
    ikke indeksert ennå»).

────────────────────────────────────────────────────────────────
E. CTA BINDING
────────────────────────────────────────────────────────────────
E1. Buttons rendered under a reply are generated FROM the reply's
    pending_action / offer — never from a static default. A reply
    proposing project creation renders [Opprett prosjekt →]; «Start
    med tom mappe» appears only when that is the actual offer.

────────────────────────────────────────────────────────────────
F. REGRESSION (this transcript, verbatim, as tests 19–22)
────────────────────────────────────────────────────────────────
19. Cold start: drop a PDF → send «hva kan du hjelpe meg med med
    denne» → reply references the file BY ITS EXTRACTION (contains
    «Indeksert» or the caption); never claims no file received.
20. Agent asks «Skal jeg kjøre Contract Review?» → user «ja» → the
    SAME turn starts the job (tool log has job id); reply contains no
    second question about the same action.
21. Any reply containing «starter»/«klar om» has a matching job-start
    receipt in the tool log; else the turn fails.
22. Reply proposing project creation renders a create-project button;
    static-default button under a mismatched reply fails the test.
Release gate unchanged (privacy grep + golden suite, now 22+ tests).
