"""Tests for the asset library.

Run:  python -m pytest foldok_assets/tests -q
"""

from __future__ import annotations

import pytest

from foldok_assets import Asset, AssetLibrary, Pack, PackRef, PackRefused, Source, asset_id


def lib() -> AssetLibrary:
    return AssetLibrary(
        [
            Asset(id="symbol.piping.valve_ball", kind="symbol", title="Ball valve",
                  domains=("piping",), industries=("marine", "process"),
                  provides=("symbol:valve_ball",), source=Source(redistribution="own")),
            Asset(id="symbol.piping.pipe_tee", kind="symbol", title="Tee",
                  domains=("piping",), provides=("symbol:pipe_tee",)),
            Asset(id="template.piping_manual", kind="template", title="Piping manual",
                  requires=("symbol:valve_ball", "theme.engineering"),
                  industries=("marine",)),
            Asset(id="theme.engineering", kind="theme", title="Engineering theme"),
            Asset(id="requirement_pack.nek400", kind="requirement_pack", title="NEK 400 profile",
                  source=Source(origin="foldok", redistribution="reference_only",
                                cites=("NEK 400:2022",))),
            Asset(id="knowledge.vendor_corrosion", kind="knowledge", title="Vendor corrosion notes",
                  source=Source(origin="acme", redistribution="unknown")),
        ]
    )


# --- indexing ------------------------------------------------------------
def test_the_library_answers_what_do_i_have_for_a_domain():
    assert len(lib().find(kind="symbol", domain="piping")) == 2


def test_industry_is_a_tag_not_a_folder():
    """A ball valve is used in marine and process. One asset, two tags — a
    folder per industry would duplicate it and the copies would drift."""
    found = lib().find(industry="marine")
    assert {a.id for a in found} == {"symbol.piping.valve_ball", "template.piping_manual"}


def test_capabilities_are_resolved_across_assets():
    assert lib().providers_of("symbol:valve_ball") == ["symbol.piping.valve_ball"]


def test_free_text_search_covers_id_title_and_tags():
    assert lib().find(text="valve")


def test_manifest_round_trips():
    a = lib()
    b = AssetLibrary.from_manifest(a.manifest())
    assert len(b) == len(a)
    assert b.get("template.piping_manual").requires == ("symbol:valve_ball", "theme.engineering")


# --- dependencies --------------------------------------------------------
def test_a_template_resolves_through_capabilities_not_just_ids():
    r = lib().resolve("template.piping_manual")
    assert r.ok, r.missing
    assert r.provided_by["symbol:valve_ball"] == "symbol.piping.valve_ball"


def test_a_missing_dependency_is_named():
    l = lib()
    l.add(Asset(id="template.broken", kind="template", requires=("symbol:nonexistent",)))
    r = l.resolve("template.broken")
    assert not r.ok and "symbol:nonexistent" in r.missing


def test_unsatisfied_lists_every_hole_in_the_library():
    l = lib()
    l.add(Asset(id="template.broken", kind="template", requires=("symbol:ghost",)))
    assert "template.broken" in l.unsatisfied()


def test_used_by_answers_which_assets_depend_on_this_one():
    l = lib()
    l.add(Asset(id="template.other", kind="template", requires=("theme.engineering",)))
    assert l.used_by("theme.engineering") == ["template.other", "template.piping_manual"]


# --- the redistribution guard -------------------------------------------
def test_a_pack_of_your_own_work_seals():
    l = lib()
    pack = l.pack("marine_starter", ["symbol.piping.valve_ball", "theme.engineering"],
                  industry="marine")
    assert l.seal(pack).sealed


def test_a_pack_containing_standard_derived_content_is_refused():
    """This is the one that matters. An 'IEC pack' or a 'DNV pack' is a letter
    from a lawyer, not a product."""
    l = lib()
    pack = l.pack("nek_pack", ["requirement_pack.nek400"])
    with pytest.raises(PackRefused) as exc:
        l.seal(pack)
    assert "reference_only" in str(exc.value)
    assert "cited, never shipped" in str(exc.value)


def test_content_of_unknown_origin_is_treated_as_unshippable():
    l = lib()
    with pytest.raises(PackRefused):
        l.seal(l.pack("p", ["knowledge.vendor_corrosion"]))


def test_a_cleared_licence_makes_content_shippable():
    l = lib()
    l.add(Asset(id="knowledge.licensed", kind="knowledge",
                source=Source(origin="acme", redistribution="licensed", licence="CC-BY-4.0")))
    assert l.seal(l.pack("p", ["knowledge.licensed"])).sealed


def test_the_guard_can_be_overridden_only_per_asset_and_explicitly():
    l = lib()
    pack = l.pack("p", ["requirement_pack.nek400"])
    assert l.seal(pack, allow=["requirement_pack.nek400"]).sealed


def test_a_pack_with_a_dangling_dependency_refuses_to_seal():
    l = lib()
    l.add(Asset(id="template.needs_missing", kind="template", requires=("symbol:ghost",)))
    with pytest.raises(PackRefused) as exc:
        l.seal(l.pack("p", ["template.needs_missing"]))
    assert "unresolved dependencies" in str(exc.value)


def test_a_pack_referencing_an_unknown_asset_refuses():
    l = lib()
    with pytest.raises(PackRefused) as exc:
        l.seal(Pack(id="p", refs=(PackRef("template.does_not_exist"),)))
    assert "not in the library" in str(exc.value)


def test_a_pack_references_assets_rather_than_copying_them():
    l = lib()
    pack = l.pack("p", ["symbol.piping.valve_ball"])
    installed = l.install(pack)
    assert installed[0] is l.get("symbol.piping.valve_ball")


def test_packs_round_trip_through_json():
    l = lib()
    pack = l.seal(l.pack("marine", ["theme.engineering"], industry="marine"))
    again = Pack.from_dict(pack.to_dict())
    assert again.asset_ids() == pack.asset_ids() and again.sealed


# --- discovery against a real tree --------------------------------------
def test_discovery_reads_the_existing_registries_without_moving_anything(tmp_path):
    from foldok_assets.discover import discover

    (tmp_path / "registry" / "document-types").mkdir(parents=True)
    (tmp_path / "registry" / "document-types" / "x.yaml").write_text(
        "id: x\nname: Example\nindustries: [marine]\ndomains: [electrical]\n"
        "structure:\n  required: [cover, scope]\n", encoding="utf-8")
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "t.json").write_text(
        '{"template_key":"t","name":"T","sections":[{"key":"cover"}]}', encoding="utf-8")
    (tmp_path / "diagram_engine" / "symbols" / "piping").mkdir(parents=True)
    (tmp_path / "diagram_engine" / "symbols" / "piping" / "v.yaml").write_text(
        "id: v\ndomain: piping\nlabel: Valve\nports: []\n", encoding="utf-8")

    assets = discover(tmp_path)
    ids = {a.id for a in assets}
    assert "document_type.x" in ids
    assert "template.t" in ids
    assert "symbol.piping.v" in ids
    for a in assets:
        assert a.path and not a.path.startswith("/")     # relative, still in place


def test_a_broken_file_becomes_a_note_not_an_exception(tmp_path):
    from foldok_assets.discover import discover

    (tmp_path / "registry" / "document-types").mkdir(parents=True)
    (tmp_path / "registry" / "document-types" / "bad.yaml").write_text(
        "id: [unclosed\n", encoding="utf-8")
    assets = discover(tmp_path)
    assert assets and any(a.meta.get("error") for a in assets)


def test_schema_and_template_files_are_not_indexed_as_assets(tmp_path):
    from foldok_assets.discover import discover

    (tmp_path / "registry" / "materials").mkdir(parents=True)
    (tmp_path / "registry" / "materials" / "_material_schema.yaml").write_text("a: 1\n", encoding="utf-8")
    (tmp_path / "registry" / "materials" / "s355.yaml").write_text("id: s355\nname: S355\n", encoding="utf-8")
    ids = {a.id for a in discover(tmp_path)}
    assert "material.s355" in ids
    assert not any("schema" in i for i in ids)


def test_standards_citing_packs_are_flagged_reference_only_automatically():
    """The guard should fire without anyone remembering to set a flag."""
    from foldok_assets.discover import python_packs
    from pathlib import Path

    assets = python_packs(Path("."))
    citing = [a for a in assets if a.source.cites]
    assert citing, "expected requirement packs that cite standards"
    assert all(a.source.redistribution == "reference_only" for a in citing)
