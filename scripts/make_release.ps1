# Foldok engine release zip — blocking privacy grep (WORKORDER 0.14-A packaging rule)
# Usage:  .\scripts\make_release.ps1 [-SkipRegression]
# Output: releases\foldok-engine-vX.Y.Z.zip

param(
  [switch]$SkipRegression
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$ver = (Get-Content (Join-Path $root "VERSION") -Raw).Trim()
$releases = Join-Path $root "releases"
New-Item -ItemType Directory -Force -Path $releases | Out-Null
$zipPath = Join-Path $releases "foldok-engine-v$ver.zip"
$staging = Join-Path $env:TEMP "foldok-zip-$ver"

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

robocopy $root $staging /E `
  /XD releases __pycache__ .git .pytest_cache .tmp_* temp-foldok-* _import_foldok12 _import_foldok13 _import_foldok14 _import_foldok_author86 `
  /XF *.pyc *.zip .env local_app\projects.json local_app\projects.json.bak formlayout-*.json RENAME_FOLDOK.md _tmp_svg.pdf *.apk `
  /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit $LASTEXITCODE" }

# Belt-and-suspenders: never ship formlayout / formimport contamination
Get-ChildItem $staging -Recurse -File -Filter "formlayout-*.json" -ErrorAction SilentlyContinue |
  Remove-Item -Force
Get-ChildItem $staging -Recurse -File -Filter "formimport-*.json" -ErrorAction SilentlyContinue |
  Remove-Item -Force
$stagedRef = Join-Path $staging ".foldok_ref_cache"
if (Test-Path $stagedRef) { Remove-Item $stagedRef -Recurse -Force }

$stagedProjectsJson = Join-Path $staging "local_app\projects.json"
if (Test-Path $stagedProjectsJson) { Remove-Item $stagedProjectsJson -Force }

Copy-Item (Join-Path $root "local_app\projects.example.json") `
          (Join-Path $staging "local_app\projects.example.json") -Force

$grepRoots = @(
  (Join-Path $staging "local_app"),
  (Join-Path $staging "examples"),
  (Join-Path $staging "scripts"),
  (Join-Path $staging "web"),
  (Join-Path $staging "templates"),
  (Join-Path $staging "skills"),
  (Join-Path $staging "registry"),
  (Join-Path $staging "tools"),
  (Join-Path $staging "form_engine"),
  (Join-Path $staging "diagram_engine"),
  (Join-Path $staging "document_engine"),
  (Join-Path $staging "artifact_engine"),
  (Join-Path $staging "foldok_index"),
  (Join-Path $staging "foldok_gaps"),
  (Join-Path $staging "foldok_diagram"),
  (Join-Path $staging "foldok_boxes"),
  (Join-Path $staging "foldok_assets"),
  (Join-Path $staging "foldok_private"),
  (Join-Path $staging "foldok_signals"),
  (Join-Path $staging "foldok_capture"),
  (Join-Path $staging "foldok_getapp"),
  (Join-Path $staging "foldok_learn"),
  (Join-Path $staging "foldok_console"),
  (Join-Path $staging "foldok_shred")
)
$grepFiles = @()
foreach ($dir in $grepRoots) {
  if (Test-Path $dir) {
    $grepFiles += Get-ChildItem $dir -Recurse -File -Include *.py,*.html,*.json,*.jsx,*.js,*.md,*.yaml,*.yml -ErrorAction SilentlyContinue
  }
}
# Root-level shipped docs (specs, flows, changelog, workorders, …)
$grepFiles += Get-ChildItem $staging -File -Filter *.md -ErrorAction SilentlyContinue
$grepFiles += Get-ChildItem $staging -File -Filter *.py -ErrorAction SilentlyContinue
# Deduplicate by full path
$grepFiles = $grepFiles | Sort-Object FullName -Unique

# Abort if projects.json slipped into staging
$stagedProjects = Get-ChildItem $staging -Recurse -Filter "projects.json" -File -ErrorAction SilentlyContinue
if ($stagedProjects) {
  Write-Host "PRIVACY GREP FAILED - projects.json must not ship:" -ForegroundColor Red
  $stagedProjects | ForEach-Object { Write-Host "  $($_.FullName)" }
  Remove-Item $staging -Recurse -Force
  exit 1
}

# Regenerate capabilities manifest from live templates (COLD_START_SPEC §2 / §6.5)
Write-Host "Building capabilities.json…"
python (Join-Path $root "scripts\build_caps.py")
if ($LASTEXITCODE -ne 0) { throw "build_caps.py failed" }
Copy-Item (Join-Path $root "capabilities.json") (Join-Path $staging "capabilities.json") -Force

# Keep marketing site (Vercel public/) identical to workbench home UI
Write-Host "Syncing public/index.html from local_app/app.html…"
Copy-Item (Join-Path $root "local_app\app.html") (Join-Path $root "public\index.html") -Force
Copy-Item (Join-Path $root "VERSION") (Join-Path $root "public\VERSION") -Force
Copy-Item (Join-Path $root "local_app\app.html") (Join-Path $staging "public\index.html") -Force
Copy-Item (Join-Path $root "VERSION") (Join-Path $staging "public\VERSION") -Force

# WORKORDER_0.20 D — agent regression gate (same severity as privacy grep)
# unittest writes progress to stderr; with ErrorActionPreference=Stop that
# becomes a terminating NativeCommandError even when exit code is 0.
if (-not $SkipRegression) {
  Write-Host "Running agent regression…"
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & python (Join-Path $root "scripts\agent_regression.py")
  $regExit = $LASTEXITCODE
  $ErrorActionPreference = $prevEap
  if ($regExit -ne 0) {
    Write-Host "AGENT REGRESSION FAILED - fix replies before release." -ForegroundColor Red
    Remove-Item $staging -Recurse -Force
    exit 1
  }
} else {
  Write-Host "Skipping agent regression (-SkipRegression)" -ForegroundColor Yellow
}

$patterns = @(
  'Ryfylkeveien',
  'Sandnes Kommune',
  'OneDrive\Documents\',
  'C:\Users\'
)
$regexPatterns = @(
  'BYGG-\d'
)
$hits = @()
foreach ($file in $grepFiles) {
  # Self-referential docs that mention the privacy patterns by name
  $bn = $file.Name
  if ($bn -in @("CHANGELOG.md", "DEPLOY.md", "make_release.ps1", "make_release.py")) { continue }
  $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
  if (-not $content) { continue }
  foreach ($pat in $patterns) {
    if ($content.Contains($pat)) {
      $hits += [PSCustomObject]@{ Path = $file.FullName; Pattern = $pat }
    }
  }
  foreach ($rx in $regexPatterns) {
    if ($content -match $rx) {
      $hits += [PSCustomObject]@{ Path = $file.FullName; Pattern = $rx }
    }
  }
}
if ($hits.Count -gt 0) {
  Write-Host "PRIVACY GREP FAILED - remove real paths/names before zipping:" -ForegroundColor Red
  $hits | ForEach-Object { Write-Host "  $($_.Pattern) in $($_.Path)" }
  Remove-Item $staging -Recurse -Force
  exit 1
}

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$staging\*" -DestinationPath $zipPath -CompressionLevel Optimal -Force
Remove-Item $staging -Recurse -Force
$sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
Write-Host "OK: $zipPath ($sizeMB MB)" -ForegroundColor Green
