# Grammar v2 — comprehensive documents (manuals, theses, multi-chapter reports)

What changed and why (companion to migration_005; contract rules unchanged):

1. HIERARCHY — template_sections.parent_key. Chapters contain sections;
   numbering (8.2.1) computed by code. Flat templates keep working untouched.
2. REPETITION — repeat_for: section instantiated per item in an
   artifact_model list (experiments, main_components, hazards). This is how
   ONE template serves a 3-experiment thesis and a 12-module manual alike.
   Requires the OUTLINE PASS: checkpoint B first proposes the chapter tree
   → user confirms (outline gate, mirrors the artifact gate) → instances
   created. artifact_models gains an 'experiments' list for research types.
3. NUMBERING + CROSS-REFS — doc_ref_registry, {{ref:block_id}} → "Figure 3.2".
   Pure code, renumbers on structural change. Prose survives drag-reorder.
4. NOMENCLATURE — doc_symbols auto-assembled from symbol-bearing facts,
   injected compactly into every generation call (terminology lock), and
   rendered as a zero-token Nomenclature block. THE mechanism for long-doc
   coherence, together with:
5. DOC MEMORY — documents.doc_memory: rolling <=500-token summary refreshed
   every ~3 sections (cheap Haiku call). Injected per section so chapter 6
   never re-explains chapter 2. Cost: ~€0.02 across an entire thesis draft.
6. NEW BLOCKS — equation (LaTeX; values cite or [MANGLER]; KaTeX in web,
   react-pdf math or SVG-prerender in PDF), figure (auto-numbered), toc,
   nomenclature, page_break, author_placeholder.
7. AUTHOR_PLACEHOLDER — the honesty boundary as a block type. Interpretive
   sections (discussion, motivation, synthesis) generate factual scaffolds
   + explicit '[AUTHOR: ...]' blocks. Enforced by required_content rules,
   rendered visibly, named in the declaration boilerplate.

Are 6 (now 7) templates enough? YES for launch — because the scaling axis
is the grammar + template import, not the template count. Any comprehensive
document is now EXPRESSIBLE; new verticals arrive as JSON (system packs or
user imports), never as engine changes. The universality claim lives here.

Generation cost reality for a full thesis evidence draft (~40 instantiated
sections, 200 indexed files): index ~€1.50 once, outline+mapping ~€0.20,
generation ~€1.20, memory ~€0.02 → ≈ €3 total. Complex-tier pricing holds.

Build order: grammar lands AFTER v1 ships flat templates (CURSOR_BUILD_PLAN
cut list applies). Migration is additive; nothing in v1 blocks on it.
