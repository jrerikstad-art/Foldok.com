# BUGFIX_0.19.md — Cross-project chat contamination (state isolation)

Status: **fixed in 0.19.0**; **conversation scope extended in 0.28.0**

## Symptom (screenshot-evidenced, demo treatment-plant project)
Checkpoint-A chat produced "Kjente utfordringer" citing sliding doors
4,00×2,10 m and berggrunn/sandfyll — facts from the TILBYGG project.
Meanwhile the artifact model for the same project is CORRECT
(mini_sewage_treatment_plant, right components). Conclusion: the
compile pipeline resolves the right folder; the CHAT CONTEXT / UI
could show the wrong one.

## Root causes (checked top-down)
1. **Client (confirmed):** `A_CHAT_HTML` was module-level and survived
   project switches. Editor chat (`CHAT_HTML`) was cleared on
   `LAST_PID` change; Checkpoint-A chat was not → opening renseanlegg
   after tilbygg restored the tilbygg conversation while the artifact
   panel loaded the correct model from disk.
2. Server chat handlers already keyed by project id, but lacked a
   single resolver, isolation logging, and a hard folder assert.
3. No regression test covering alternating A/B chat contexts.
4. **Conversation (0.28):** `state.conversation` must follow the same
   isolation rule as the index — turns stamped with `project_id`;
   `conversation_for_project` / `build_project_chat_context` drop
   foreign turns; API responses return the filtered thread only.

## Fix (RULE, not a patch)
**ISOLATION RULE** (server.py, permanent):
- No module-level project / index / “current” state for chat.
- Every request carries project id; folder/state/cache derived via
  `resolve_project` / `load_project_index` / `build_artifact_assist_sources`.
- Chat system context prepends `PROSJEKT: <name> · MAPPE: <folder>`.
- Folder not on the requested project → `IsolationError` → HTTP 500.
- **§A extended:** every `append_turn` stamps `project_id`; conversation
  history in model context and API payloads is filtered to that id.

**Client:** on project switch, clear `A_CHAT_HTML`, `INTENT_RESULT_HTML`,
`A_PENDING_PATCH`, `ARTIFACT_DRAFT` (same block that already clears
editor chat).

## Instrumentation
`[isolation:artifact/assist]` (and gap-assist) logs: request id, name,
folder, state path, index count, first filename.

## Regression test
`python scripts/test_chat_isolation.py` — two synthetic projects,
six alternating context builds; asserts no foreign markers in captions.
Also: alternating conversation turns — no cross-references in
`conversation_for_project` or chat-context history.

## Why this does not mean “the product can't serve strangers”
The engine is stateless per call (folder → index → document). The
workbench was single-user Phase 0.5 with shortcut UI state; this bug
is the tax of outgrowing those shortcuts — paid on the founder machine,
not a customer's. Production isolation is by architecture (RLS or
one-user-per-machine + this project-id rule).
