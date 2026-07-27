# TEMPLATE_STANDARD.md — how we author templates going forward

**Rules of record** for system templates. Complements `TEMPLATE_LIFECYCLE.md`
(origins / versioning) and `registry/README.md` (document types).

If a proposed template violates this document, do not ship it as a system
default. Domain-locked forms belong as **imports** or **fixtures**, not as
the thing the agent picks for a new project.

---

## 1. The core rule

Templates define **structure and intent**, not fixed domain content.

| Templates answer | Templates must not answer |
|------------------|---------------------------|
| What is the purpose of this document? | What is the VIN / Reg.nr / Km-stand? |
| Which sections are required / recommended / optional? | Which exact car-part checklist rows exist? |
| Which block / field *kinds* fit each section? | What brand or OEM this form was scanned from? |
| Which integrity rules apply (citations, no invented numbers, signatures)? | What the prose must say in every project |

**Shape from the template. Content from sources + agent + user confirmation.**

---

## 2. Two layers (always)

```
┌─────────────────────────────────────────────────────────┐
│  1. Document Type  (registry/document-types/*.yaml)     │
│     High-level intent: inspection_report,               │
│     installation_guide, industrial_report, …            │
│     → purpose, section skeleton, preferred blocks,      │
│       skills, tools, compliance notes                   │
└──────────────────────────┬──────────────────────────────┘
                           │ workbench_template /
                           │ composition_profile
┌──────────────────────────▼──────────────────────────────┐
│  2. Composition Profile  (templates/*.json)             │
│     Runnable skeleton for workbench / form_fill /       │
│     narrative gaps. Adaptable field slots or            │
│     semantic required_facts — not OEM field lists.      │
└─────────────────────────────────────────────────────────┘
```

- **Document type** = “what kind of document is this?”
- **Composition profile** = “what shape should the first draft have?”
- **Imported / owned template** = print-faithful copy of a *specific* form
  the user brought (vehicle multipoint, company SJA sheet, …). Allowed —
  never the system default for a broad intent.

---

## 3. What a good system template contains

Minimum metadata:

```json
{
  "template_key": "inspection_checklist",
  "name": "Inspection Checklist",
  "name_no": "Inspeksjonssjekkliste",
  "document_species": "form_fill",
  "document_type": "inspection_report",
  "purpose": "Record of an inspection / verification with results and sign-off.",
  "adapt_policy": "agent_may_relabel_slots_from_sources",
  "system_default": true,
  "applies_to": ["inspection", "equipment", "installation", "vehicle", "system"],
  "writing_rules_global": {
    "no_invented_values": true,
    "citation_required_for_sourced_facts": true
  },
  "sections": [ ]
}
```

### Per section

Each section should declare:

1. **role** — `required` | `recommended` | `optional`
2. **purpose** — one sentence
3. **preferred_blocks** — e.g. `form_section`, `EngineeringTable`, `Paragraph`
4. **field_slots** (form_fill) *or* **required_facts** (narrative) — by *kind / semantic*, not brand labels
5. **adapt** — what the agent may change (relabel slots, add optional rows, skip empty optional sections)

### Field slots (form_fill) — kinds, not labels

Use kinds the engine understands (`text`, `date`, `measure`, `rating3`, `check`, `signature`, `photo`) plus a **semantic** role:

| semantic | kind | Example label_hint (Norwegian) |
|----------|------|--------------------------------|
| `subject_ref` | text | Objekt / ID |
| `customer` | text | Kunde / eier |
| `location` | text | Sted |
| `inspection_date` | date | Dato |
| `usage_counter` | measure | Driftsmål (km / timer / sykluser) |
| `status_item` | rating3 | Kontrollpunkt |
| `measurement` | measure | Måling |
| `deviation_notes` | text | Avvik |
| `conclusion` | text / rating3 | Konklusjon |
| `signatory` | signature | Signatur |

Concrete `key` / `label_no` on shipped JSON are **starting hints**. The agent
may relabel them from source material when `adapt_policy` allows. Domain
IDs like `vin` or `reg_no` must not be **required** on a system default
unless the document type is explicitly vehicle-registration scoped (it is
not — use import for that).

### Narrative templates

Prefer `required_facts` with abstract keys (`design_load`, `operating_medium`)
and `writing_rules`. Do not bake project-specific component names into the
template.

---

## 4. Good vs bad

### Bad — domain-locked system template

```text
template_key: sample_multipoint
sections: kunde_og_kjoretoy → Reg.nr, VIN, Km-stand
          eksterior → Horn, Lys, Viskere…
          dekk → mønster VF/HF…
```

Problems:
- Picker forces a vehicle-service shape onto unrelated projects
- Content is pre-answered by the template
- Fails outside vehicle service

**Allowed role:** imported / owned template, or form_engine **fixture** for
print tests — never `system_default: true` for broad “inspection” intent.

### Good — flexible system profile

```text
document_type: inspection_report
sections: identification → subject_ref, customer, date, location
          scope → what was inspected / method ref
          checklist → N × status_item slots (relabel from sources)
          measurements → N × measurement slots (optional)
          deviations → free text
          conclusion + signature
```

Problems it avoids:
- Same skeleton works for minirenseanlegg, crane, vehicle, or HVAC
- Agent fills labels and values from indexed sources
- OEM multipoint arrives via **import**, not as the default brain

### Good — narrative shape (excerpt)

```text
document_type: installation_guide
sections: safety, prerequisites, procedure, verification, references
required_facts: abstract (supply_voltage, torque_spec) + citation rules
preferred_blocks: Procedure, CalloutBox, EngineeringTable
```

---

## 5. Decision tree — when to create what

```
User needs a document
        │
        ├─ Matches a Document Type intent?
        │     → use registry type + its composition profile
        │
        ├─ User has their own PDF/paper form?
        │     → IMPORT → owned template (print-faithful fields OK)
        │
        ├─ No type + no form?
        │     → Rung-3 AI draft (warning severity only) OR free_document
        │
        └─ Authoring a new SYSTEM template?
              → Must pass the checklist in §6
```

---

## 6. Author checklist (system templates)

Before merging a new `templates/*.json` or registry YAML:

- [ ] Linked to a **document type** (`document_type` / registry `id`)
- [ ] States **purpose** in one or two sentences
- [ ] Sections are semantic (identification, scope, results…) not OEM chapter titles
- [ ] No brand- or product-specific **required** fields (VIN, Reg.nr, “Horn”, …)
- [ ] Form fields use **kinds + semantics**; labels are hints
- [ ] `adapt_policy` is set
- [ ] `system_default` is true only if trade-agnostic
- [ ] Integrity rules present (citations / no invented values / sign-off as needed)
- [ ] Domain-locked copies live under import / `company_templates` / fixtures
- [ ] `capabilities.json` one-liner does not sell domain lock-in as the default
- [ ] Registry `workbench_template` points at the flexible profile, not a fixture

---

## 7. Species notes

| Species | Shape lives in | Content filled by |
|---------|----------------|-------------------|
| `form_fill` | sections + fields / field_slots | Prefill identity from index; ratings/signatures never auto-invented |
| narrative | sections + `required_facts` + writing_rules | Compile / chat; gaps → MANGLER |
| registry-only | YAML structure + preferred_blocks | CompositionEngine; bridge to workbench JSON when gaps needed |

`free_document` remains the escape hatch — minimal structure, citation rule
still applies. It is not a substitute for a good system profile.

---

## 8. Migration of legacy Multipoint

| Artifact | New role |
|----------|----------|
| `templates/inspection_checklist.json` | **System default** composition profile for `inspection_report` |
| `registry/.../inspection_report.yaml` | Document type → points at inspection_checklist |
| `fixtures/sample_multipoint/sample_multipoint.json` | **Fixture / import example** (`system_default: false`) — recreate only when explicitly named |
| Company-owned multipoint copy | Stays owned import under `company_templates/` |

Intent routing and “multipoint / sjekkliste” asks must prefer
`inspection_checklist`, not the sample fixture fields.

---

## 9. Future (not blocking this standard)

1. Runtime `materialise_field_slots(sources)` → concrete labeled rows before render
2. Agent may insert extra `status_item` / `measurement` rows under adapt_policy
3. Paywall / export tiers remain orthogonal (`export_price_tier`)

Until (1) ships, ship **generic concrete fields** that match the slot
semantics above — still no VIN/Reg.nr as blocking system defaults.
