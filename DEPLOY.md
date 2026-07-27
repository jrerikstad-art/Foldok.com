# Deploy Foldok

## Brand
**Foldok** · mark `[…]` · English marketing landing

## GitHub
1. Create an empty repo (e.g. `foldok`)
2. From this engine folder:

```powershell
git init
git add .
git commit -m "Foldok v0.62.0 — engine, English landing, compliance Phase 1"
git branch -M main
git remote add origin https://github.com/<you>/foldok.git
git push -u origin main
```

Do **not** commit `.env`, `local_app/projects.json`, or cache folders (see `.gitignore`).

## Vercel (marketing site — [jrerikstad-arts](https://vercel.com/jrerikstad-arts))

Static English landing in `public/`. The Python workbench is **not** deployed on Vercel.

### One-click import (recommended)

1. Open [Import Git Repository](https://vercel.com/new/import?s=https://github.com/jrerikstad-art/Foldok.com)
2. Sign in with GitHub if prompted
3. **Team:** `jrerikstad-arts` (or your personal scope)
4. **Project name:** `foldok` or `foldok-com`
5. Framework preset: **Other**
6. Root Directory: **leave empty** (repo root)
7. Build Command: **empty**
8. Output Directory: **`public`** (also set in `vercel.json`)
9. Deploy

`vercel.json` at repo root sets `outputDirectory: public` so dashboard import should pick this up automatically.

### Custom domain (optional)

After first deploy: Project → Settings → Domains → add `foldok.com` / `www.foldok.com` and follow DNS instructions.

### CLI (after `vercel login`)

```powershell
cd feltdok-engine
vercel link --project foldok-com
vercel --prod
```

Local preview:

```powershell
npx serve public
```

## Local workbench (engine)
The real product UI is the Python workbench (not Vercel):

```powershell
.\scripts\workbench.ps1
# http://127.0.0.1:8766/
```

## Release zip
```powershell
.\scripts\make_release.ps1
# → releases\foldok-engine-vX.Y.Z.zip
```

Use `-SkipRegression` only when packaging a hotfix zip without the full agent suite:

```powershell
.\scripts\make_release.ps1 -SkipRegression
```
