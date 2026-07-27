# Start local preview server (port 8765 — 8000 blocked on some Windows installs)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "Foldok engine v$(Get-Content VERSION -Raw).Trim()"
Write-Host ""
Write-Host "  Hub:          http://localhost:8765/web/"
Write-Host "  Design dummy: http://localhost:8765/web/design-dummy.html"
Write-Host "  Results:      http://localhost:8765/web/results.html"
Write-Host "  Prototype:    http://localhost:8765/web/prototype.html"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
python -m http.server 8765 --bind 127.0.0.1
