# Start the Foldok workbench (real engine + browser UI) on port 8766
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$Port = 8766

# Kill any stale process still holding the port (old code = broken buttons)
try {
  $owners = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $owners) {
    if ($procId -and $procId -ne 0) {
      Write-Host "Stopper gammel prosess pa port $Port (PID $procId)..." -ForegroundColor Yellow
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
  }
  Start-Sleep -Milliseconds 400
} catch {}

# Optional: load API key from .env (copy .env.example -> .env)
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $parts = $_ -split '=', 2
    $k = $parts[0].Trim()
    $v = $parts[1].Trim().Trim('"').Trim("'")
    if ($k -and -not (Get-Item -Path "Env:$k" -ErrorAction SilentlyContinue)) {
      Set-Item -Path "Env:$k" -Value $v
    }
  }
}

if (-not $env:ANTHROPIC_API_KEY) {
  Write-Host "ADVARSEL: ANTHROPIC_API_KEY er ikke satt." -ForegroundColor Yellow
  Write-Host '  Alternativ 1:  copy .env.example .env   og lim inn nokkelen der' -ForegroundColor Yellow
  Write-Host '  Alternativ 2:  $env:ANTHROPIC_API_KEY = "sk-ant-..."' -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Workbench:     http://127.0.0.1:$Port/"
Write-Host "  Diagram Studio: http://127.0.0.1:$Port/diagram.html"
Write-Host ""
Start-Process "http://127.0.0.1:$Port/"

python -u local_app/server.py
