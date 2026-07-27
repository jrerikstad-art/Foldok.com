# COLD_START_SPEC.md — The conversation before the folder

Users arrive with a question, not a folder. The zero state is a chat
that answers "kan du lage X?" honestly, builds the folder WITH the
user, and explains local-first precisely. Extends FLOW_ONE_OPERATION
(the same stream — this is just its beginning).

────────────────────────────────────────────────────────────────
1. ZERO STATE (hub, no project selected)
────────────────────────────────────────────────────────────────
Chat front and center:
  "Hei — hva vil du lage? Spør gjerne før du har en mappe klar."
Chips: [Kan du lage en samsvarserklæring?] [Hva kan du bygge?]
       [Hvordan behandles filene mine?] [Start med tom mappe]

Language: reply in the user's language. Templates already carry NO/EN
names; the hub mirrors EN↔NO from the message. EPC and diligence
prospects often write English — do not answer them in Norwegian by
default.

────────────────────────────────────────────────────────────────
2. CAPABILITIES MANIFEST — the agent's grounded self-knowledge
────────────────────────────────────────────────────────────────
The agent answers capability questions from capabilities.json, NEVER
from model memory. Generated at release time by scripts/build_caps.py
from the actual tree (always in sync, no drift):
  { "version": "<app version>",
    "templates": [ {key, name_no, name, one_liner, description,
       needs: […], applies_to: […], checklist, group} ],
    "file_types": {reads: [...], cad_policy: "tegnings-PDF, ikke DWG"},
    "cannot": ["verifisere beregninger", "gi juridisk råd",
               "lese native CAD (DWG/STEP)", "signere for deg",
               "finne på verdier som ikke finnes i kilder",
               "tegne eller modellere i 3D"],
    "privacy": [approved NO sentences — see §5],
    "privacy_en": [approved EN sentences — same precision],
    "scale": {
       index_cost_eur_per_file_min/max, parallel_workers,
       cache, multi_folder, example_files / example_cost_eur /
       example_time, large_corpus_recommendation
    },
    "pricing_line": "Gratis å prøve — betal per eksportert dokument." }

Distinction (critical):
  • Capability *claims* are grounded — every promised feature, cost,
    limit, or privacy sentence must exist in the manifest.
  • Capability *matching* is inference — the agent may reason from the
    user's words to the closest listed templates (applies_to +
    descriptions + aliases). It may not invent unlisted features.
  • The manifest is a TOOL, not a wall (WORKORDER_0.20 C1 / C2-BIS).
    Every cold-start user message goes to the model with the §C5
    capabilities payload (full catalog + scale + history). The keyword
    matcher never gates *whether* a reply is generated. Zero-token only
    for privacy approved sentences and unambiguous cannot-list bounds.
    Never replace an answer with «Jeg holder meg til det som står i
    kapabilitetslisten» — that string is deleted.

Chat rule (system prompt): "Capability claims MUST come from the
manifest. Matching user intent to listed templates is allowed and
required. Never promise unlisted features. Reply in the user's
language. Never answer 'I'm not sure' / 'Ikke sikker' when any listed
template plausibly matches. Structure proposals RENDER sections in
chat — showing beats offering a button."

────────────────────────────────────────────────────────────────
3. ANSWER POLICY — "kan du lage X?" / "can you handle …?"
────────────────────────────────────────────────────────────────
Order — "Ikke sikker" with two generic buttons is nearly unreachable:

a) TEMPLATE MATCH (user words vs applies_to + descriptions + aliases)
   → yes + the specific document(s) and their inputs.
   Due diligence / contract-at-volume maps to contract_review,
   spec_coherence_review, tender_compliance_matrix — answer with that
   suite, not a shrug.

b) SCALE / VOLUME ("hundreds of folders", "thousands of files")
   → grounded numbers from the `scale` block: multi-folder link,
     ~€0.001–0.01 per file index (sha256 cache forever), N parallel
     workers, example cost/time for ~2,000 files, and the honest
     recommendation to split very large corpora into workstream
     projects. Prefer this framing when DD + volume are both present.

c) NO TEMPLATE, still documentation domain → honest rung-3 WITH the
   proposed structure printed inline (numbered sections) +
   [Bruk denne strukturen]. Never «Ingen ferdig mal» alone with only a
   button that re-asks.

d) OUT OF SCOPE (genuinely outside documentation — 3D modeling, legal
   advice, calculation verification, native CAD) → boundary + nearest
   capability. Only here, and only when no template match. «Ikke sikker»
   is only permissible in this branch.

e) "HVA KAN DU BYGGE?" → the template catalog as a short grouped list
   + "og firmaets egne skjemaer — last opp malen deres".

Never prefer "I'm not sure" over a plausible match. Soft match before
shrug; last resort answers WITH the catalog (buttons accompany). The
string «Jeg holder meg til det som står i kapabilitetslisten» is
deleted — never ship it.

────────────────────────────────────────────────────────────────
4. FOLDER CREATION — "Start med tom mappe"
────────────────────────────────────────────────────────────────
When the user has no folder (or says so), the agent offers:
  "Skal jeg opprette prosjektmappen for deg?"
POST /api/project/create-with-skeleton {name, template_key?}
  → creates <base_dir>/<name>/ (base_dir configurable, ask once)
  → subfolder skeleton: Bilder/ Tegninger/ Rapporter/ Notater/
    (feeds path-as-role-hints — the skeleton improves future indexing)
  → writes SJEKKLISTE.txt in the folder: the shopping list derived
    from the chosen template's required_facts/media (zero tokens,
    pure template read): "□ Bilde av merkeskilt □ Testrapport (PDF)
    □ Mål og vekt …"
  → registers project, opens it; checkpoint A uses the project-name-
    as-source path (WORKORDER_0.19B §1) so the conversation continues
    with whatever the name already says.
The SJEKKLISTE doubles as the field instruction: the user goes to the
workshop with it, fills the folder, comes back. That loop IS the
product's onboarding.

────────────────────────────────────────────────────────────────
5. LOCAL-FIRST EXPLAINER — approved phrasing (precision matters)
────────────────────────────────────────────────────────────────
The agent uses THESE sentences (manifest-carried), not improvisation:
  "Filene dine ligger på din maskin. Foldok laster dem aldri opp til
   noen Foldok-sky og lagrer ingen kopier hos oss."
  "Når jeg analyserer en fil, sendes utdrag av innholdet (tekst eller
   bilde) til AI-tjenesten for behandling av akkurat det kallet — du
   ser kostnaden i €-måleren. Originalene blir hvor de er."
  "Ferdige og signerte PDF-er lagres heller ikke hos oss — de er dine."
EN equivalents live in privacy_en (same precision, same bans).
FORBIDDEN phrasings (overclaim): "helt offline", "ingenting forlater
maskinen", "vi har ikke tilgang til dataene dine", "completely offline",
"nothing leaves your machine" (excerpts ARE sent per call — precision
is the trust architecture applied to marketing).

────────────────────────────────────────────────────────────────
6. ACCEPTANCE
────────────────────────────────────────────────────────────────
1. Zero state, ask "kan du lage en SJA?" → yes + inputs list from the
   real template, offer to create folder. No project existed at any
   point during the answer.
2. Ask "kan du tegne huset mitt i 3D?" → honest boundary from
   cannot-list + nearest capability. No invented promise.
3. "Start med tom mappe" for brukermanual → folder + skeleton +
   SJEKKLISTE.txt with that template's real requirements; project
   opens; artifact strip shows name-derived understanding.
4. Ask "hvor lagres filene mine?" → the approved sentences, verbatim-
   close; grep the reply: none of the forbidden phrasings.
5. Manifest regenerated at release: add a template → it appears in
   "hva kan du bygge?" with zero prompt edits.
6. English due-diligence + scale: "Can you handle due diligence across
   hundreds of folders and thousands of files?" → English reply that
   names the contract/spec templates, cites scale numbers from the
   manifest, recommends workstream projects, offers to sketch a split.
   Kind is not `unsure`. No Norwegian in the reply.
7. Plain "due diligence" (no volume wording) → still matches
   contract_review / spec_coherence_review / tender_compliance_matrix
   (or scale-framed DD suite), never "Ikke sikker".
