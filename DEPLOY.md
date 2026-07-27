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

## Vercel (marketing site)
Static English page in `public/`.

1. Import the GitHub repo in Vercel
2. Framework preset: **Other**
3. Output / root: Vercel serves `public/` automatically for static assets
4. Deploy

Local preview of the marketing page: open `public/index.html` or:

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
