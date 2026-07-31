"""Embed get-capture snippet into local_app/app.html (run after regenerating snippet)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "local_app" / "app.html"
SNIPPET = ROOT / "local_app" / "get-capture-snippet.html"
MARKER = '  <span class="right" id="keystate"></span>'


def main() -> None:
    snippet = SNIPPET.read_text(encoding="utf-8").strip()
    text = APP.read_text(encoding="utf-8")
    if MARKER not in text:
        if "getCapture" in text:
            print("snippet already embedded")
            return
        raise SystemExit(f"marker not found in {APP}")
    replacement = (
        "  <span class=\"right\">\n"
        + snippet
        + "\n    <span id=\"keystate\"></span>\n  </span>"
    )
    APP.write_text(text.replace(MARKER, replacement, 1), encoding="utf-8")
    print(f"embedded {len(snippet)} bytes into app.html")


if __name__ == "__main__":
    main()
