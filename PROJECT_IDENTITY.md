# Project Identity — the missing layer

> The project identifies, the folder proposes, the user disposes, the engine holds the order.

That sentence stays. What it left out is *what* is being proposed for.

Product shape (compose vs generate, three-pane editor, Content Director):
`ENGINEERING_EDITOR.md`.

## The failure mode

Same folder: installation notes, drawings, photos, standards, and a dense OEM
manual. Without identity, theme voting and section markets treat the OEM PDF as
the richest signal. The document becomes a product manual. We saw this with
vendor brochures and with earlier vehicle work — never again as engine constants.

**Hard rule:** no development project paths, client names, or vendor catalogues
in production code. Terms come from the artifact and folder the user named.
Fixtures may invent names; the engine may not.

## Pipeline

```text
Corpus
  → Project Identity          # what is this work about?
  → Narrative Blueprint       # which arc / purpose?
  → Topics                    # cluster claims under the story
  → Document / Section Market # score Relevant / Somewhat / Background / Ignore
  → User chooses
  → Author → Publish
```

Naming a *document type label* can wait. **Identity cannot.**

Identity is purpose, audience, primary vs secondary subjects, and what to exclude.
"Installation Manual" is a name. "Install this system safely for field engineers,
primary subject = whole plant, sensors are secondary" is identity.

## Objects

```python
ProjectIdentity
  document_kind      # installation | research | inspection | …
  audience
  purpose
  central_question
  primary_topics     # from role-weighted project themes
  secondary_topics   # reference themes that still inform
  excluded_topics    # reference-only noise (OEM product lines, …)
  project_terms      # from artifact / folder name only

NarrativeBlueprint
  identity
  preferred_arc      # purpose-shaped, not band decoration
  required_sections
  required_assets
```

Package: `foldok_identity`.

## Arcs are purpose

| Kind | Arc |
|------|-----|
| Installation | purpose → safety → preparation → installation → verification → maintenance |
| Research | question → theory → method → results → discussion |
| Failure | incident → evidence → analysis → root cause → corrective actions |

Same folder. Different blueprints. The section market consumes the blueprint; it
does not invent the story.

## Topics between claims and sections

Claims → Topics (Installation, EMC, Safety, …) → Sections.
Assets attach to topics (drawings, photos, procedures), so the author never
"searches the folder" ad hoc.

## Relation to foldok_corpus

Corpus extraction vocabulary and narrative bands remain. Identity is the first
consumer of the folder sketch; `build_offer(..., identity=…)` marks each offer
Relevant / Somewhat / Background / Ignore so OEM density cannot become 95% of
the document.
