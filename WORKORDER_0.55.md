# WORKORDER_0.55.md — Pre-scan, chunked indexing, and a stop button

Field trigger: 57.7 GB / 14 830 files — no cost preview, no chunking, no cancel.

**Status: implemented in 0.55.0** (cancel, heartbeat, budget, pre-scan, decision card, chunked run).

See CHANGELOG 0.55.0. Acceptance checks:

1. Attach large folder → decision card in seconds, €0 spent until confirm  
2. «Bare dokumenter» scopes to PDF/Office  
3. «Stopp» mid-run → keep work; [Fortsett] resumes  
4. Close browser → pause within ~60 s (heartbeat)  
5. €10 ceiling → pause + choice  
6. Oversize (>25 MB) skipped; PDFs >200 pages partial (first 60)

Not fully shipped yet: D3 prompt inventory caps at 40 keys; D4 jsonl lazy load
(streaming index) — follow-up when >5k projects hit RAM.
