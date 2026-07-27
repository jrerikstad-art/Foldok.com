# FORMATS.md — ingestion and export (settled policy)

## Ingestion — what the index reads
V1 (already in foldok_compile.py / Phase 2 port):
  Photos: jpg jpeg png webp heic        → Haiku vision (caption + facts)
  Docs:   pdf docx xlsx pptx txt md csv → MarkItDown → Haiku (summary + facts)
  Anything else → status='skipped', filename still searchable. Never an error.

CAD policy (honest, permanent-ish):
  Native CAD (dwg, step, sldprt, ipt): NOT parsed. The drawing PDF is the
  compliance artifact anyway — instruct users to include drawing PDFs.
  Title blocks are fact-rich (drawing_no, revision, material, scale) and
  extract via vision today. Phase 2: DXF (text-based; ezdxf) for title
  block + layer text. Full native CAD parsing: not on any roadmap.

Near-term additions (post-v1, cheap):
  Voice notes (m4a/mp3/wav) → Whisper → indexed as text (Capture app ties in)
  .eml/.msg email files → MarkItDown (decision/assumption goldmine for
  design-basis work)
  Video → skipped until demand proves otherwise (frame extraction is a
  cost trap).

## Export — formats and editing policy
1. THE PDF IS A RENDERING, NOT THE MASTER. The document is blocks+versions
   in Foldok; it remains editable there forever.
2. PAID = FREE RE-EXPORTS. Payment is per document, not per render. Edit
   and re-export at no charge (iteration bundle still meters AI usage).
3. SIGNED = LOCKED. Editing a signed document creates revision B requiring
   re-signature. The signed PDF of rev A remains immutable in the audit
   trail. No silent edits to signed compliance documents, ever.
4. DOCX EXPORT (v1.5): blocks → Word for "client demands editable" cases.
   Fact chips render as values + numbered source footnotes; a final page
   carries the Source Register. Traceability interactivity lives only in
   Foldok — honest, and the reason to return.
5. Raw export (v1.5, trivial): blocks as JSON + markdown, because
   "your files stay yours" includes the document itself. No lock-in.

## Storage ledger (precision on "zero storage" — say it exactly this way)
STORED, in the user's account (this is what makes edit + re-export work):
  - The document: blocks, versions, mappings, chat proposals
  - The index: captions, facts, embeddings, render-resolution image
    derivatives (~200KB; kept so re-export survives source deletion)
  - Templates, company profile, token ledger
NEVER stored:
  - Final exported/signed PDFs — rendered in memory, streamed, discarded
  - Original files when connected via Drive/OneDrive/SharePoint (pointers only)
MVP nuance: upload-only ingestion necessarily keeps uploads in the user's
private bucket (user-deletable). Pure pointer model arrives with OAuth
connectors. Public phrasing stays accurate: "Ingen originalfiler lagres
(ved skykobling), ingen signerte PDF-er beholdes."

## Source staleness detection (post-v1; the one good idea from outside)
When a source file is re-uploaded/re-synced with a new sha256, or a
connector reports modification: re-index that file only, diff its
extracted_facts against the prior version, and flag every document
whose blocks cite changed/removed fact ids:
  document banner: "Kilden er endret — N verdier kan være utdatert.
  [Gjennomgå endringer]" → per-fact diff (old vs new, both cited) →
  user accepts per fact → new document version → re-export (free if paid).
NEVER auto-mutates a document. Exported/signed revisions stay immutable;
staleness creates a proposed rev B. Cost: one re-index of one file.
This is the honest version of "manuals that update themselves" — and a
real enterprise selling point once the wedge has proven the engine.
