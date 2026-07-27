# foldok_assets

One index over the registries Foldok already has. Nothing is moved.

    lib = AssetLibrary.load(".")
    lib.find(kind="symbol", domain="piping")        # 14 in the 0.73 tree
    lib.resolve("template.installation_manual")     # deps, and what is missing
    lib.seal(lib.pack("piping_starter", ids))       # refuses anything unshippable

Against the real 0.73 tree: **127 assets across 11 kinds** — 45 symbols,
17 document types, 16 templates, 13 knowledge files, 12 calculations,
5 section profiles, 5 skills, 5 frameworks, 4 materials, 4 requirement packs,
1 layout template. 124 shippable, 3 reference-only.

## Two decisions

**Index, don't migrate.** Assets stay where they live. `discover()` reads six
registries in three formats and emits one index. Moving ~170 files buys a nicer
directory listing and costs a week of merge pain. Adding a seventh registry is
one function in `discover.py`.

**Redistribution is enforced, not remembered.** Every asset declares where it
came from and whether it may travel: `own | licensed | reference_only | unknown`.
`seal()` refuses a pack containing anything that isn't `own` or `licensed`.

An "IEC pack" or a "DNV pack" is a letter from a lawyer, not a product. You ship
your own templates, symbols and structural profiles and *cite* the clause — you
never ship the clause. The requirement packs that name NEK 400, 2006/42/EC and
NS 9415 are flagged `reference_only` automatically, without anyone remembering.

**Industry is a tag, not a folder.** A ball valve is used in marine, process,
water and building services. A folder per industry duplicates it four times and
the copies drift.

## Files

| File | Contains |
|---|---|
| `model.py` | `Asset`, `Source`, `Pack`. The redistribution field lives here. |
| `discover.py` | One adapter per existing registry. Add a registry, add a function. |
| `library.py` | Query, dependency resolution, `seal()`. |

## Quick start

```python
from foldok_assets import AssetLibrary, PackRefused

lib = AssetLibrary.load(".")
print(lib.summary())

# what would this template need?
r = lib.resolve("template.installation_manual")
print(r.missing or "all dependencies present")

# ship your own work
pack = lib.pack("piping_starter", [a.id for a in lib.find(kind="symbol", domain="piping")],
                industry="process")
lib.seal(pack)          # -> sealed

# try to ship someone else's standard
try:
    lib.seal(lib.pack("nek", ["requirement_pack.no_electrical_installation"]))
except PackRefused as e:
    print(e)            # names the assets and says what to do instead
```

```
python -m pytest foldok_assets/tests -q
```
