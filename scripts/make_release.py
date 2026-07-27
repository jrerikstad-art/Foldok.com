#!/usr/bin/env python3
"""Release packaging wrapper — delegates to make_release.ps1 (blocking privacy grep)."""
import subprocess
import sys
from pathlib import Path

script = Path(__file__).resolve().parent / "make_release.ps1"
raise SystemExit(subprocess.call(
    ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
    cwd=script.parent.parent,
))
