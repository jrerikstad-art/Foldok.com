# Foldok — Structural profiles, not legal compliance

**Canonical claim boundary.** Marketing, UI, and APIs must follow this.

## What Foldok must not say

Without the full legal text of NEK, ISO, NEC, the Machinery Regulation, etc.,
Foldok **must not** claim that a project is “compliant” with those standards.

| Forbidden product language | Why |
|---------------------------|-----|
| “NEK compliant” / “meets NEK 400 §…” | Implies legal determination |
| “ISO 13849 satisfied” | Implies certification |
| “CE OK” / “CE marking is valid” | Implies conformity assessment |
| “Legally compliant” / “Approved by the standard” | Liability and misleading |

## What Foldok can honestly say

| Allowed | Meaning |
|---------|---------|
| “These document sections are present” | Package shape |
| “These evidence types are missing” | Gap list |
| “Declaration draft is incomplete” | Structural readiness |
| “No inspection record linked” | Traceability gap |
| “Package is structurally complete for this profile” | Template coverage |
| “Evidence coverage for selected profile: 82%” | Coverage metric |
| “Ready for review” / “Not ready for export — blocking gaps” | Human handoff |

**Product claim:**

> We help you build and check a documentation package against a **structural profile**.  
> You (or your compliance manager) decide **legal conformity**.

## Three uses of “standards”

1. **Structural profile (what Foldok stores)** — typical evidence *kinds* and document shapes. No copyrighted clause text.
2. **Customer’s own standards (what the user brings)** — licensed PDFs / internal rules indexed as project sources. Engine can cite “present in file X” or “not found in sources.”
3. **Legal interpretation (humans only)** — whether evidence is *sufficient* under a clause. Always the competent person’s job.

Foldok operates on (1), supports (2), and stays out of (3).

## UI / API rules

- Label frameworks as **structural profiles**, not certification results.
- Every compliance API response includes `disclaimer` and `legal_compliance_claimed: false`.
- Prefer `package_status` language (`ready_for_review`, coverage %) over pass/fail standards language.
- Optional later: user attaches a licensed standard PDF → project-local checklist from *their* headings. Still no global claim that “Foldok certifies ISO.”

## Safe marketing one-liner

**Bad:** “Automatic compliance with NEK, ISO, and NEC.”

**Good:** “Build technical documentation packages mapped to common regulatory *structures*. Link your own standards and evidence. You review and sign off.”

Implementation: `local_app/compliance_engine.py` (`DISCLAIMER`, `package_status`).
