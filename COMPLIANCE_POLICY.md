# Foldok — Structural profiles, not legal compliance

**Canonical claim boundary.** Marketing, UI, and APIs must follow this.

---

## One sentence

**The engine knows compliance as requirement profiles + evidence coverage; it does not know the law — it knows whether the package has the artifacts the profile asked for, with citations you can check against your own copy of the standard.**

Foldok does not “know compliance” the way a lawyer or a standards body does.  
It knows **what you (or a local pack) said must exist**, then checks **whether evidence is present**.

---

## The real model

```text
Requirement profile          Evidence in the project
(what should exist)    ↔     (what you actually have)
        ↓
    Gap engine
        ↓
  missing / present / cited
```

**Compliance here means:** coverage of required evidence against a profile —  
**not** “this installation is legal” or “certified to NEK 400.”

---

## Where requirements come from

| Source | What the engine stores |
|--------|-------------------------|
| **Built-in / industry packs** | Structural rules: e.g. “board photo,” “insulation measurement per circuit,” “signature on declaration” — **Foldok’s wording + clause citation**, not the full standard text |
| **Your licensed PDF** (via learn / shredder) | Same: clause id, shall/should, evidence kind (photo, measurement, signature…), scope (per circuit, per board) — **never the paragraph sold by NEK/IEC** |
| **Template / document type** | Sections and fields this document species expects |
| **You** | Confirm, mark N/A, add project-specific requirements |

So the engine “knows compliance” only as **a checklist of obligations + evidence types**, optionally anchored with `authority: "NEK 400:2022 §6-61"`.

---

## What it checks

For each requirement it asks roughly:

1. Is there an **artifact** (photo, file, form value, measurement, signature)?  
2. Is it **linked** to this requirement?  
3. Is provenance **confirmed** (not only an unconfirmed AI draft)?  
4. Optional: does Capture sidecar / checksum match?

| Outcome | Meaning |
|---------|---------|
| No → **gap** | Blocking or recommended — profile not covered |
| Yes → **satisfied for that profile** | Evidence present and linked — not a legal determination |

It does **not** independently verify that a measurement was done correctly, that a photo shows the right board, or that the installation meets the law.

---

## What Foldok must not say

Without the full legal text of NEK, ISO, NEC, the Machinery Regulation, etc.,
Foldok **must not** claim that a project is “compliant” with those standards.

| Forbidden product language | Why |
|---------------------------|-----|
| “NEK compliant” / “meets NEK 400 §…” | Implies legal determination |
| “ISO 13849 satisfied” | Implies certification |
| “CE OK” / “CE marking is valid” | Implies conformity assessment |
| “Legally compliant” / “Approved by the standard” | Liability and misleading |

Also deliberately out of scope:

- Read and enforce full NEK / IEC / ISO text as a legal oracle  
- Replace the competent person who signs the samsvarserklæring  
- Invent obligations from a random PDF without a profile / extraction step  

That matches the product line: **you don’t get away with missing pieces** — the pieces are defined by the profile; **you** still own the meaning.

---

## What Foldok can honestly say

| Allowed | Meaning |
|---------|---------|
| “These document sections are present” | Package shape |
| “These evidence types are missing” | Gap list |
| “Declaration draft is incomplete” | Structural readiness |
| “No inspection record linked” | Traceability gap |
| “Package is structurally complete for this profile” | Template / profile coverage |
| “Evidence coverage for selected profile: 82%” | Coverage metric |
| “Ready for review” / “Not ready for export — blocking gaps” | Human handoff |
| “Ready relative to this pack” | Profile coverage — **not** “legally compliant” |

**Product claim:**

> We help you build and check a documentation package against a **requirement profile**.  
> You (or your compliance manager) decide **legal conformity**.

---

## End-to-end example

1. Pack or local extract says: *Photographic record of distribution board (§8-1) — evidential, per board*.  
2. Publish photo task → phone shoots → sidecar.  
3. Ingest links `IMG_….jpg` to that requirement.  
4. Gap closes; document can cite file + time.  
5. Export status can say “ready” relative to **this pack** — not “legally compliant.”

---

## Three uses of “standards”

1. **Requirement / structural profile (what Foldok stores)** — typical evidence *kinds* and document shapes. No copyrighted clause text.  
2. **Customer’s own standards (what the user brings)** — licensed PDFs / internal rules; learn/shredder extract citations and obligations only.  
3. **Legal interpretation (humans only)** — whether evidence is *sufficient* under a clause. Always the competent person’s job.

Foldok operates on (1), supports (2), and stays out of (3).

---

## UI / API rules

- Label frameworks as **structural profiles** / **requirement profiles**, not certification results.  
- Every compliance API response includes `disclaimer` and `legal_compliance_claimed: false`.  
- Prefer `package_status` language (`ready_for_review`, coverage %) over pass/fail standards language.  
- Optional: user attaches a licensed standard PDF → project-local checklist from *their* extraction. Still no global claim that “Foldok certifies ISO.”

---

## Safe marketing one-liner

**Bad:** “Automatic compliance with NEK, ISO, and NEC.”

**Good:** “Build technical documentation packages against requirement profiles. Link evidence. You review and sign off.”

Implementation: `local_app/compliance_engine.py` (`DISCLAIMER`, `package_status`); gaps via `foldok_gaps`; Capture ingest; learn/shred for local citations only.
