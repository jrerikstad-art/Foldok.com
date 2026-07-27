#!/usr/bin/env python3
"""
FOLDOK eval harness — measure index + mapping quality against a golden set,
so prompt iteration works WITHOUT external help.

Usage:
  1. Run the compiler once:  python foldok_compile.py ./folder --template ... --yes
  2. Copy eval/expected.example.json → ./folder/expected.json and fill in
     ground truth for each file (you know what each file IS).
  3. Score:                  python eval/eval_harness.py ./folder
  4. Iterate prompts in foldok_compile.py, clear cache for changed prompts
     (delete .foldok_cache/*.json), rerun, rescore.

Scores produced:
  ROLE ACCURACY   — % files whose doc_role_hints overlap expected roles
  FACT RECALL     — % expected facts found (key match, value fuzzy-match)
  FACT PRECISION  — % extracted facts that are real (not hallucinated)
  MAPPING         — % files landing in an expected section (needs mapping.json,
                    written by foldok_compile.py if you add --dump-mapping)

Debugging guide (which prompt to touch per failure):
  Low ROLE ACCURACY  → INDEX_SYSTEM: tighten doc_role_hints vocabulary,
                       add 2 few-shot examples of your file types.
  Low FACT RECALL    → INDEX_SYSTEM facts block: name the missing keys
                       explicitly in the canonical key list.
  Low FACT PRECISION → INDEX_SYSTEM: strengthen "extract only explicit"
                       + raise the confidence bar in postprocessing.
  Low MAPPING        → map_sections prompt: include section descriptions,
                       not just titles; or add doc_role_hints → section
                       affinity table to the prompt.
  Wrong captions     → everything downstream is wrong for that reason;
                       fix caption instruction first, always.
"""
import json, sys, re
from pathlib import Path


def norm(s):
    return re.sub(r"[\s,.]+", "", str(s).lower())


def fuzzy_eq(a, b):
    na, nb = norm(a), norm(b)
    return na in nb or nb in na


def main():
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    expected = json.loads((folder / "expected.json").read_text())
    cache = folder / ".foldok_cache"
    indexed = {}
    for f in cache.glob("*.json"):
        e = json.loads(f.read_text())
        indexed[e["file"]] = e

    role_hits = role_total = 0
    fact_found = fact_expected = 0
    extracted_total = extracted_real = 0
    report = []

    for fname, exp in expected["files"].items():
        e = indexed.get(fname)
        if not e:
            report.append(f"  MISSING from index: {fname}")
            continue
        # roles
        exp_roles = set(exp.get("roles", []))
        got_roles = set(e.get("doc_role_hints", []))
        if exp_roles:
            role_total += 1
            if exp_roles & got_roles:
                role_hits += 1
            else:
                report.append(f"  ROLE  {fname}: expected {sorted(exp_roles)}, got {sorted(got_roles)}")
        # fact recall
        got_facts = e.get("facts", [])
        for ef in exp.get("facts", []):
            fact_expected += 1
            hit = any(f["key"] == ef["key"] and fuzzy_eq(f["value"], ef["value"]) for f in got_facts)
            if hit:
                fact_found += 1
            else:
                report.append(f"  FACT  {fname}: missing {ef['key']}={ef['value']}")
        # fact precision (expected facts + allowed extras count as real)
        allowed = {ef["key"] for ef in exp.get("facts", [])} | set(exp.get("extra_facts_ok", []))
        for f in got_facts:
            extracted_total += 1
            if f["key"] in allowed or exp.get("any_extra_ok", True):
                extracted_real += 1
            else:
                report.append(f"  HALLUCINATION? {fname}: {f['key']}={f['value']} (not in ground truth)")

    # mapping (optional)
    map_line = "  MAPPING       —  (run compiler with --dump-mapping to score)"
    mp = folder / "mapping.json"
    if mp.exists() and "mapping" in expected:
        m = json.loads(mp.read_text())
        hit = tot = 0
        for fname, secs in expected["mapping"].items():
            tot += 1
            landed = [k for k, v in m.items() if fname in v.get("files", [])]
            if set(secs) & set(landed):
                hit += 1
            else:
                report.append(f"  MAP   {fname}: expected {secs}, landed {landed}")
        map_line = f"  MAPPING        {hit}/{tot}  = {100*hit/max(tot,1):.0f}%   (target ≥80%)"

    print("═" * 56)
    print("FOLDOK EVAL")
    print(f"  ROLE ACCURACY  {role_hits}/{role_total}  = {100*role_hits/max(role_total,1):.0f}%   (target ≥80%)")
    print(f"  FACT RECALL    {fact_found}/{fact_expected}  = {100*fact_found/max(fact_expected,1):.0f}%   (target ≥85%)")
    print(f"  FACT PRECISION {extracted_real}/{extracted_total}  = {100*extracted_real/max(extracted_total,1):.0f}%   (target ≥95%)")
    print(map_line)
    print("═" * 56)
    if report:
        print("FAILURES:")
        print("\n".join(report[:40]))
    print("\nSee module docstring for which prompt to touch per failure type.")


if __name__ == "__main__":
    main()
