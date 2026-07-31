"""Probes — one per engine, each turning an existing report into a Panel.

Nothing here computes anything.  Every engine already produces exactly the
numbers a console needs: ``AssetLibrary.summary``, ``Index.diagnose``,
``GapSet.summary``, ``AuditLog.totals``, ``Signals.report``,
``Learner.proposals``.  The console's value is that they are in one place and
that somebody looks.

Every probe is written to survive a missing engine, a broken import and an
unexpected shape.  A dashboard that crashes because one subsystem changed is a
dashboard nobody opens, and a dashboard nobody opens is how two release blockers
live for five builds.
"""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from typing import Any, Callable

from .model import Panel

ENGINES: tuple[tuple[str, str], ...] = (
    ("foldok_diagram", "Diagrams"),
    ("foldok_gaps", "Requirements & gaps"),
    ("foldok_index", "Index"),
    ("foldok_boxes", "Layout"),
    ("foldok_assets", "Asset library"),
    ("foldok_private", "Trust boundary"),
    ("foldok_signals", "Signals"),
    ("foldok_capture", "Capture bridge"),
    ("foldok_learn", "Local learning"),
)


def probe_engines(root: str | Path) -> Panel:
    """Which engines are present, importable, and what version."""
    panel = Panel(area="engines", title="Engines")
    missing: list[str] = []
    broken: list[str] = []
    present = 0
    for module_name, label in ENGINES:
        if not (Path(root) / module_name).exists():
            missing.append(module_name)
            continue
        try:
            module = importlib.import_module(module_name)
            panel.metrics[module_name.replace("foldok_", "")] = getattr(module, "__version__", "?")
            present += 1
        except Exception as exc:  # noqa: BLE001
            broken.append(f"{module_name} ({type(exc).__name__})")
    panel.metrics["present"] = f"{present}/{len(ENGINES)}"

    if broken:
        panel.add(
            "engine_import_failed", f"{len(broken)} engine(s) do not import",
            health="fail", impact=5, effort="hours", detail=", ".join(broken),
            action="fix the import before anything else — nothing downstream is trustworthy",
        )
    if missing:
        panel.add(
            "engine_missing", f"{len(missing)} engine(s) not in this build",
            health="warn", impact=3, effort="minutes", detail=", ".join(missing),
            action="ship them, or drop them from the release checklist",
            evidence={"missing": missing},
        )
    return panel


def probe_assets(root: str | Path) -> Panel:
    panel = Panel(area="assets", title="Content library")
    lib = _try(lambda: importlib.import_module("foldok_assets").AssetLibrary.load(str(root)))
    if lib is None:
        panel.note = "foldok_assets not available"
        return panel

    kinds = lib.kinds()
    panel.metrics["assets"] = len(lib)
    panel.metrics["kinds"] = len(kinds)
    shippable = sum(1 for a in lib.all() if a.source.shippable)
    panel.metrics["shippable"] = f"{shippable}/{len(lib)}"

    unsatisfied = lib.unsatisfied()
    if unsatisfied:
        panel.add(
            "unsatisfied_dependency",
            f"{len(unsatisfied)} asset(s) need something nothing provides",
            health="warn", impact=3, effort="hours",
            detail=", ".join(sorted(unsatisfied)[:5]),
            action="add the missing assets, or drop the dependency — this fails at render time",
            evidence={"assets": dict(list(unsatisfied.items())[:8])},
        )

    broken = [a.id for a in lib.all() if a.meta.get("error")]
    if broken:
        panel.add(
            "unparseable_asset", f"{len(broken)} asset file(s) failed to parse",
            health="warn", impact=3, effort="minutes", detail=", ".join(broken[:5]),
            action="fix the YAML or JSON; they are silently absent until you do",
        )

    thin = [k for k, n in kinds.items() if n <= 1]
    if thin:
        panel.metrics["thin_kinds"] = ",".join(sorted(thin))
    return panel


def probe_index(root: str | Path, db: str | Path | None = None) -> Panel:
    panel = Panel(area="index", title="Index")
    module = _try(lambda: importlib.import_module("foldok_index"))
    if module is None:
        panel.note = "foldok_index not available"
        return panel
    if db is None or not Path(db).exists():
        panel.note = "no index database to inspect"
        panel.metrics["db"] = "none"
        return panel

    index = _try(lambda: module.Index(str(db)))
    if index is None:
        panel.add("index_unreadable", "the index database will not open",
                  health="fail", impact=4, effort="hours",
                  action="delete it and reindex; the manifest is rebuildable")
        return panel

    stats = index.stats()
    panel.metrics.update({
        "documents": stats.get("documents", 0),
        "chunks": stats.get("chunks", 0),
        "vectors": stats.get("vectors", 0),
    })
    diagnosis = _try(index.diagnose)
    if diagnosis is not None:
        failures = diagnosis.failures
        panel.metrics["checks"] = f"{len(diagnosis.checks) - len(failures)}/{len(diagnosis.checks)}"
        for check in failures:
            panel.add(
                "index_check_failed", check.name, health="fail", impact=4, effort="hours",
                detail=check.detail, action=check.fix,
            )
    return panel


def probe_signals(log_path: str | Path | None = None) -> Panel:
    panel = Panel(area="signals", title="Usage")
    module = _try(lambda: importlib.import_module("foldok_signals"))
    if module is None:
        panel.note = "foldok_signals not available"
        return panel
    if log_path is None or not Path(log_path).exists():
        panel.note = "no event log yet"
        panel.add(
            "no_usage_data", "nobody has used this yet",
            health="warn", impact=5, effort="hours",
            detail="every other panel measures the build; none of them measures a customer",
            action="put it in front of one person you can drive to, and watch where they stop",
        )
        return panel

    log = module.EventLog(log_path)
    f = module.funnel(log.events())
    panel.metrics["sessions"] = f.sessions
    panel.metrics.update({k: v for k, v in f.stages.items()})
    worst = f.worst_step
    if worst:
        panel.add(
            "funnel_drop", f"most people stop at: {module.FUNNEL_LABELS[worst[0]]}",
            health="warn", impact=5, effort="hours",
            detail=f"{worst[1]:.0%} lost at that step",
            action="watch one person do exactly that step",
            evidence={"stage": worst[0], "rate": worst[1]},
        )
    failures = module.failure_summary(log.events())
    for name, reasons in failures.items():
        top = max(reasons.items(), key=lambda kv: kv[1]) if reasons else None
        if top and top[1] >= 3:
            panel.add(
                "recurring_refusal", f"{name}: {top[0]} x{top[1]}",
                health="warn", impact=4, effort="hours",
                detail="the product says no to the same thing repeatedly",
                action="either make it possible, or say why better",
                evidence={"event": name, "reasons": reasons},
            )
    return panel


def probe_trust(audit_path: str | Path | None = None) -> Panel:
    panel = Panel(area="trust", title="Trust boundary")
    module = _try(lambda: importlib.import_module("foldok_private"))
    if module is None:
        panel.note = "foldok_private not available"
        return panel
    panel.metrics["purposes"] = len(module.PURPOSES)
    if audit_path is None or not Path(audit_path).exists():
        panel.note = "no model calls recorded"
        return panel

    import json as _json

    records = []
    for line in Path(audit_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(_json.loads(line))
            except _json.JSONDecodeError:
                continue
    sent = [r for r in records if r.get("outcome") == "sent"]
    refused = [r for r in records if r.get("outcome") == "refused"]
    panel.metrics["calls"] = len(sent)
    panel.metrics["refused"] = len(refused)
    panel.metrics["bytes"] = sum(int(r.get("bytes", 0)) for r in sent)

    off_vocab = {r.get("purpose") for r in records} - set(module.PURPOSES)
    if off_vocab:
        panel.add(
            "purpose_outside_the_four",
            f"model called for {len(off_vocab)} purpose(s) outside the declared four",
            health="fail", impact=5, effort="hours",
            detail=", ".join(sorted(str(p) for p in off_vocab)),
            action="the four-purpose claim is on the marketing site — fix the code or the claim",
        )
    return panel


def probe_learning(lessons_path: str | Path | None = None) -> Panel:
    panel = Panel(area="learning", title="Local learning")
    module = _try(lambda: importlib.import_module("foldok_learn"))
    if module is None:
        panel.note = "foldok_learn not available"
        return panel
    if lessons_path is None or not Path(lessons_path).exists():
        panel.note = "nothing learned yet"
        return panel
    learner = module.Learner(lessons_path)
    proposals = learner.proposals()
    panel.metrics["lessons"] = len(learner.lessons())
    panel.metrics["active"] = len(learner.lessons(status="active"))
    panel.metrics["waiting"] = len(proposals)
    if proposals:
        panel.add(
            "lessons_waiting", f"{len(proposals)} lesson(s) ready to apply",
            health="warn", impact=2, effort="minutes",
            detail="; ".join(p.lesson.describe() for p in proposals[:3]),
            action="accept or reject them — an unanswered proposal is a decision not made",
        )
    return panel


def probe_tests(root: str | Path, *, paths: tuple[str, ...] = (), timeout: int = 300) -> Panel:
    """Run the suite. Slow, so the console makes it opt-in."""
    panel = Panel(area="tests", title="Tests")
    targets = [str(Path(root) / p) for p in paths] or [
        str(Path(root) / f"{name}/tests") for name, _ in ENGINES
        if (Path(root) / name / "tests").exists()
    ]
    if not targets:
        panel.note = "no test directories found"
        return panel
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", *targets, "-q", "--no-header"],
            cwd=str(root), capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        panel.add("tests_did_not_run", f"could not run pytest: {type(exc).__name__}",
                  health="warn", impact=3, effort="minutes")
        return panel

    tail = (result.stdout or "").strip().splitlines()[-1:] or [""]
    summary = tail[0]
    panel.metrics["result"] = summary[:60]
    if result.returncode != 0:
        failed = [l for l in (result.stdout or "").splitlines() if l.startswith("FAILED")]
        panel.add(
            "tests_failing", f"{len(failed)} test(s) failing",
            health="fail", impact=5, effort="hours",
            detail="; ".join(f.split("::")[-1] for f in failed[:5]),
            action="green before anything else ships",
            evidence={"failed": failed[:10]},
        )
    return panel


def _try(fn: Callable[[], Any]) -> Any:
    """A probe must never take the console down with it."""
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return None


def probe_shredder(shreds_dir: str | Path | None = None) -> Panel:
    """The shredder's output, as a console panel.

    Consensus needs several documents before it says anything, so the useful
    reading here is "how close are we to a convention", not a count.
    """
    panel = Panel(area="shredder", title="Shredder")
    module = _try(lambda: importlib.import_module("foldok_shredder"))
    if module is None:
        panel.note = "foldok_shredder not available"
        return panel
    if shreds_dir is None or not Path(shreds_dir).exists():
        panel.note = "nothing shredded yet"
        return panel

    import json as _json

    shreds = []
    for path in sorted(Path(shreds_dir).glob("*.json")):
        try:
            shreds.append(_json.loads(path.read_text(encoding="utf-8")))
        except _json.JSONDecodeError:
            continue

    grades: dict[str, int] = {}
    for s in shreds:
        grades[s.get("grade", "?")] = grades.get(s.get("grade", "?"), 0) + 1
    panel.metrics["shredded"] = len(shreds)
    panel.metrics.update(grades)

    exemplary = grades.get("exemplary", 0)
    pending = sum(len(s.get("proposals", [])) for s in shreds)
    if pending:
        panel.add(
            "shred_proposals_waiting", f"{pending} proposal(s) from shredded documents",
            health="warn", impact=2, effort="minutes",
            detail="structure and design measurements nobody has accepted or rejected",
            action="accept or reject them — an unanswered proposal is a decision not made",
        )
    if 0 < exemplary < 3:
        panel.add(
            "not_enough_exemplars", f"only {exemplary} exemplary document(s)",
            health="warn", impact=2, effort="hours",
            detail="one good document is one person's taste; three that agree is a convention",
            action="shred a few more of the documents you want Foldok to be more like",
        )
    return panel


def probe_capabilities(root: str | Path) -> Panel:
    """Does the manifest say what the product does?

    This is the class of bug, not the instance: a build shipping 45 diagram
    symbols told a user it had no drawing tools, because the manifest never
    mentioned them and the assistant is instructed never to claim what is not
    listed. Correct behaviour, wrong inputs, and invisible from every other
    panel.
    """
    panel = Panel(area="capabilities", title="Capability manifest")
    module = _try(lambda: importlib.import_module("foldok_capabilities"))
    if module is None:
        panel.note = "foldok_capabilities not available"
        return panel

    rec = _try(lambda: module.reconcile(str(root)))
    if rec is None:
        panel.note = "could not read the manifest"
        return panel

    panel.metrics["found"] = len(rec.capabilities)
    panel.metrics["declared"] = len(rec.declared)

    for drift in rec.of("undeclared"):
        panel.add(
            "capability_undeclared", drift.detail,
            health="fail", impact=5, effort="minutes",
            detail="the assistant will deny this to every user until the manifest changes",
            action="run foldok_capabilities and write the generated block",
            evidence={"capability": drift.capability},
        )
    for drift in rec.of("contradicted"):
        panel.add(
            "capability_contradicted", drift.detail,
            health="fail", impact=5, effort="minutes",
            detail="the prompt contains an active false statement about the product",
            action=drift.fix,
        )
    for drift in rec.of("unqualified_denial"):
        panel.add(
            "denial_generalises", drift.detail,
            health="warn", impact=3, effort="minutes",
            detail="a bare negative gets applied more widely than intended",
            action=drift.fix,
        )
    for drift in rec.of("overclaimed"):
        panel.add(
            "capability_overclaimed", drift.detail,
            health="warn", impact=4, effort="minutes", action=drift.fix,
        )
    return panel
