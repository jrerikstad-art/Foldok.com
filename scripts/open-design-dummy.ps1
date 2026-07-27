# Open the Foldok wireframe layout in Capture Design's wireframe tool.
$ErrorActionPreference = "Stop"
$wireframe = "C:\Users\jreri\OneDrive\Documents\Capture Design\Code\outputs\wireframe-tool.html"
$template = Join-Path (Split-Path $wireframe -Parent) "foldok-home.json"
if (-not (Test-Path $wireframe)) {
  Write-Host "Fant ikke wireframe tool: $wireframe" -ForegroundColor Red
  exit 1
}
if (-not (Test-Path $template)) {
  Write-Host "Fant ikke mal: $template" -ForegroundColor Red
  exit 1
}
$url = "file:///" + ($wireframe -replace '\\','/') + "?template=foldok"
Write-Host "Apner wireframe tool (Foldok home)..."
Write-Host "  $wireframe"
Write-Host ""
Write-Host "Pa file://: klikk «Foldok — Home» og velg foldok-home.json i samme mappe." -ForegroundColor Yellow
Start-Process $wireframe
