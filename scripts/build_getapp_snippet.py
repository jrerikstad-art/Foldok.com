"""Regenerate local_app/get-capture-snippet.html from foldok_getapp."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "local_app" / "get-capture-snippet.html"
URL = "https://foldok.com/capture"


def main() -> int:
    cmd = [
        sys.executable, "-m", "foldok_getapp",
        "--url", URL,
        "--out", str(OUT),
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    # Re-embed into app.html when snippet changes
    subprocess.run([sys.executable, str(ROOT / "scripts" / "embed_getapp_snippet.py")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
