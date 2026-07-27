# Regenerate compiled JSX bundles for the web preview.
# Run after editing ui-prototype.jsx or ui-editor-v3.jsx.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# name -> exported global
$targets = @{
  "ui-prototype.jsx" = "FoldokCompiler"
  "ui-editor-v3.jsx" = "FoldokEditorV3"
}

foreach ($src in $targets.Keys) {
  if (-not (Test-Path $src)) { Write-Host "skip (missing): $src"; continue }
  $global = $targets[$src]
  $out = [System.IO.Path]::GetFileNameWithoutExtension($src) + ".compiled.js"
  $tmp = "_regen_tmp.jsx"
  $code = @"
const fs = require('fs');
let s = fs.readFileSync('$src', 'utf8');
s = s.replace(/^import React.*$/m, 'const { useState } = React;');
s = s.replace(/^export default /m, 'window.$global = ');
fs.writeFileSync('$tmp', s);
"@
  node -e $code
  npx --yes esbuild $tmp --loader:.jsx=jsx --outfile=$out
  Remove-Item $tmp
  Write-Host "Done -> $out"
}
