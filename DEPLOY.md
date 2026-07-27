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

`public/index.html` is synced from `local_app/app.html` — same landing UI as
`http://127.0.0.1:8766/`. Vercel has no Python engine; hub/projects fall back to
marketing mode. Full product: `.\scripts\workbench.ps1`.

```powershell
Copy-Item local_app\app.html public\index.html -Force
vercel --prod --yes
```

Import: [Foldok.com on Vercel](https://vercel.com/new/import?s=https://github.com/jrerikstad-art/Foldok.com)  
Settings: Framework **Other**, Output Directory **`public`**, empty build command.

### Custom domain (optional)

Project → Settings → Domains → add `foldok.com` / `www.foldok.com`.

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
