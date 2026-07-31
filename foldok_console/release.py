"""Release checks — the audit that has been done by hand, automated.

These are exactly the checks that found the problems in 0.73 and found the same
ones still open in 0.78.  That gap is the argument for this file: the checks
worked, but they only ran when somebody remembered to run them, and nobody did
for five builds.

Nothing here is clever.  It reads the deploy config, works out which files
actually ship, and looks for links pointing at things that will not be there.
A check that a person could do in ten minutes, run on every build instead of
never.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .model import Panel

SECRET_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
)

LOCAL_HOSTS = re.compile(r"https?://(?:127\.0\.0\.1|localhost)(?::\d+)?")


def check_release(root: str | Path) -> Panel:
    root = Path(root)
    panel = Panel(area="release", title="Release")

    config = _vercel(root)
    out_dir = root / (config.get("outputDirectory") or ".")
    panel.metrics["ships"] = str(out_dir.relative_to(root)) if out_dir.is_relative_to(root) else str(out_dir)

    if not out_dir.exists():
        panel.add(
            "no_output_dir", f"output directory '{out_dir.name}' does not exist",
            health="fail", impact=5, effort="minutes",
            action="fix outputDirectory in vercel.json, or create the folder",
        )
        return panel

    shipped = {p.name for p in out_dir.rglob("*") if p.is_file()}
    panel.metrics["files"] = len(shipped)

    html_files = [p for p in out_dir.rglob("*.html")]
    for page in html_files:
        text = page.read_text(encoding="utf-8", errors="replace")
        _check_dead_links(panel, page, text, shipped)
        _check_localhost(panel, page, text)
        _check_social(panel, page, text)
        _check_weight(panel, page, text)

    _check_secrets(panel, root)
    _check_versions(panel, root, out_dir)
    return panel


# ----------------------------------------------------------------------
def _vercel(root: Path) -> dict[str, Any]:
    p = root / "vercel.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _check_dead_links(panel: Panel, page: Path, text: str, shipped: set[str]) -> None:
    """Links to files that are not in the deploy.

    This is the check that would have caught the diagram and box-editor buttons
    in 0.73 — both open a new tab, both 404 in production, and neither is
    guarded by the marketing-mode fallback the API calls use.
    """
    targets: set[str] = set()
    for pattern in (
        r'window\.open\(\s*["\'](/[^"\'?]+)',
        r'href="(/[^"#?]+\.[a-z]{2,5})"',
        r'<script[^>]+src="(/[^"?]+)"',
        r'<link[^>]+href="(/[^"?]+\.css)"',
    ):
        targets.update(re.findall(pattern, text))

    dead = sorted(
        t for t in targets
        if not t.startswith("/api/") and Path(t).name and Path(t).name not in shipped
    )
    if dead:
        panel.add(
            "dead_link",
            f"{len(dead)} link(s) in {page.name} point at files that do not ship",
            health="fail", impact=5, effort="minutes",
            detail=", ".join(dead[:6]),
            action=(
                "copy them into the output directory, or gate the buttons behind the "
                "workbench-only state — a new tab that 404s is worse than no button"
            ),
            evidence={"targets": dead[:12], "page": page.name},
        )


def _check_localhost(panel: Panel, page: Path, text: str) -> None:
    hits = LOCAL_HOSTS.findall(text)
    clickable = len(re.findall(r'href="https?://(?:127\.0\.0\.1|localhost)', text))
    if not hits:
        return
    panel.add(
        "localhost_on_production",
        f"{len(hits)} localhost reference(s) in {page.name}"
        + (f", {clickable} clickable" if clickable else ""),
        health="fail" if clickable else "warn",
        impact=4 if clickable else 2,
        effort="minutes",
        detail="a visitor gets a link to their own machine",
        action="remove the anchor; keep the instruction as plain text if it is still needed",
        evidence={"clickable": clickable, "total": len(hits)},
    )


def _check_social(panel: Panel, page: Path, text: str) -> None:
    if "og:title" not in text:
        return                       # not a page meant for sharing
    if "og:image" in text:
        return
    panel.add(
        "no_og_image",
        f"{page.name} has no og:image",
        health="warn", impact=3, effort="minutes",
        detail="every share on LinkedIn, Slack or iMessage renders as a text box",
        action="add one 1200x630 image — cheapest high-return fix on the page",
    )


def _check_weight(panel: Panel, page: Path, text: str) -> None:
    size = len(text.encode("utf-8"))
    scripts = sum(len(s) for s in re.findall(r"<script[^>]*>.*?</script>", text, flags=re.S))
    markup = size - scripts
    panel.metrics[f"{page.name}_kb"] = round(size / 1024)
    if size > 250_000 and markup < size * 0.1:
        panel.add(
            "js_heavy_page",
            f"{page.name} is {size // 1024} KB, {round(100 * scripts / size)}% inline script",
            health="warn", impact=3, effort="hours",
            detail=f"only {markup} bytes of markup — that is all a crawler or an AI sees",
            action="server-render the body copy; keep JS for the interactive parts",
            evidence={"bytes": size, "script_bytes": scripts, "markup_bytes": markup},
        )


def _check_secrets(panel: Panel, root: Path) -> None:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix in (".png", ".jpg", ".zip", ".pdf", ".ico"):
            continue
        if any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if path.name.endswith(".example"):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(str(path.relative_to(root)))
                break
    if hits:
        panel.add(
            "secret_in_repo", f"{len(hits)} file(s) contain something shaped like a key",
            health="fail", impact=5, effort="minutes",
            detail=", ".join(hits[:5]),
            action="rotate the key first, then remove it — a rotated key in history is harmless",
            evidence={"files": hits[:10]},
        )
    else:
        panel.metrics["secrets"] = "clean"


def _check_versions(panel: Panel, root: Path, out_dir: Path) -> None:
    versions: dict[str, str] = {}
    for name in ("VERSION", "public/VERSION"):
        p = root / name
        if p.exists():
            versions[name] = p.read_text(encoding="utf-8").strip()
    meta = root / "site-meta.json"
    if meta.exists():
        try:
            versions["site-meta.json"] = str(json.loads(meta.read_text(encoding="utf-8")).get("version", ""))
        except json.JSONDecodeError:
            pass
    distinct = {v for v in versions.values() if v}
    panel.metrics["version"] = sorted(distinct)[0] if len(distinct) == 1 else "mismatch"
    if len(distinct) > 1:
        panel.add(
            "version_mismatch", "version strings disagree",
            health="warn", impact=2, effort="minutes",
            detail=", ".join(f"{k}={v}" for k, v in sorted(versions.items())),
            action="single source of truth, generated into the others at build time",
        )
