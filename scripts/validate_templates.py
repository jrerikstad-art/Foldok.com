#!/usr/bin/env python3
"""Validate all templates/*.json and report CLI-engine compatibility gaps."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import foldok_compile as fc

DUMMY_ARTIFACT = {
    "artifact_type": "structure",
    "lifecycle_stages": ["install", "operate", "maintain", "inspect", "transport", "dispose"],
    "hazards": [{"hazard": "test"}, {"hazard": "test2"}],
}

REQUIRED_TOP = {"template_key", "name", "sections", "applies_to", "version"}


def main():
    errors, warnings = [], []
    templates = sorted((ROOT / "templates").glob("*.json"))
    print(f"Validating {len(templates)} templates…\n")

    for path in templates:
        try:
            t = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: invalid JSON — {e}")
            continue

        missing = REQUIRED_TOP - set(t)
        if missing:
            errors.append(f"{path.name}: missing keys {sorted(missing)}")

        keys = [s.get("section_key") for s in t.get("sections", [])]
        if len(keys) != len(set(keys)):
            errors.append(f"{path.name}: duplicate section_key")

        for s in t.get("sections", []):
            sk = s.get("section_key", "?")
            cond = s.get("condition")
            if cond:
                _, recognized = fc._condition_holds(cond, DUMMY_ARTIFACT)
                if not recognized:
                    warnings.append(f"{path.name} [{sk}]: unrecognized section condition {cond!r}")

            if s.get("repeat_for"):
                warnings.append(
                    f"{path.name} [{sk}]: repeat_for={s['repeat_for']!r} — grammar v2, CLI runs once"
                )
            if s.get("parent_key"):
                warnings.append(f"{path.name} [{sk}]: parent_key — hierarchy not in CLI")

            for rf in s.get("required_facts", []):
                cond = rf.get("condition")
                if cond:
                    _, recognized = fc._condition_holds(cond, DUMMY_ARTIFACT)
                    if not recognized:
                        warnings.append(
                            f"{path.name} [{sk}]: unrecognized fact condition on {rf.get('key')!r}"
                        )

    print("═" * 56)
    if errors:
        print(f"ERRORS ({len(errors)}):")
        print("\n".join(f"  ✗ {e}" for e in errors))
    else:
        print("  ✓ All templates parse and have required keys")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}) — expected for grammar v2 / future syntax:")
        print("\n".join(f"  ⚠ {w}" for w in warnings))
    else:
        print("  ✓ No compatibility warnings")
    print("═" * 56)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
