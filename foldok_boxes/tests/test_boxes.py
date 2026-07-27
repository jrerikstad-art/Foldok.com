"""Tests for the box layout engine.

Run:  python -m pytest foldok_boxes/tests -q
"""

from __future__ import annotations

import pytest

from foldok_boxes import (
    BlockInput,
    Box,
    LayoutRefused,
    LayoutSession,
    LayoutTemplate,
    PageGrid,
    PinStore,
    compare,
    compliance_a4,
    fingerprint,
    resize,
    snap_rect,
    solve,
)
from foldok_boxes.snap import drop_target, handle_at


def doc() -> list[BlockInput]:
    return [
        BlockInput("h1", "heading", section="scope", text="Scope of work"),
        BlockInput("t1", "text", section="scope", text="x" * 1200),
        BlockInput("img1", "image", section="scope", aspect=1.5),
        BlockInput("img2", "image", section="scope", aspect=1.5),
        BlockInput("t2", "text", section="verify", text="y" * 700),
        BlockInput("tb1", "table", section="verify", rows_hint=10),
        BlockInput("legal", "text", section="handover", text="z" * 400, locked=True),
    ]


def session(**kw) -> LayoutSession:
    return LayoutSession(doc(), **kw)


# --- flow is preserved --------------------------------------------------
def test_document_order_survives_layout():
    geo = solve(doc())
    order = [b.block_id for b in sorted(geo.boxes, key=lambda b: (b.page, b.y, b.col))]
    assert order.index("h1") < order.index("t1") < order.index("t2")


def test_half_width_blocks_share_a_band():
    geo = session().geometry()          # the template puts images at half width
    a, b = geo.of("img1"), geo.of("img2")
    assert a.y == b.y                      # same top edge
    assert a.col == 0 and b.col == 6       # side by side


def test_a_full_width_block_closes_the_band():
    geo = session().geometry()
    assert geo.of("tb1").y > geo.of("img2").y


def test_solver_is_deterministic():
    assert fingerprint(solve(doc())) == fingerprint(solve(doc()))


def test_geometry_snaps_to_the_baseline():
    geo = session().geometry()
    for box in geo.boxes:
        assert abs((box.y - geo.grid.margin_top) % geo.grid.baseline) < 1e-6
        assert abs(box.height % geo.grid.baseline) < 1e-6


def test_boxes_never_overlap_within_a_page():
    geo = session().geometry()
    boxes = geo.on_page(1)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            overlap = (
                a.x < b.x + b.width and b.x < a.x + a.width
                and a.y < b.y + b.height and b.y < a.y + a.height
            )
            assert not overlap, f"{a.block_id} overlaps {b.block_id}"


def test_nothing_escapes_the_page_margins():
    geo = session().geometry()
    g = geo.grid
    for box in geo.boxes:
        assert box.x >= g.margin_left - 0.01
        assert box.x + box.width <= g.page_width - g.margin_right + 0.01
        assert box.y >= g.margin_top - 0.01


# --- the user is in control ---------------------------------------------
def test_a_hand_resize_survives_reflow():
    s = session()
    s.resize("img1", "e", dx=200, dy=0)
    before = s.placed("img1").span
    s.blocks.insert(0, BlockInput("new", "text", text="w" * 900))   # content added above
    s.invalidate()
    assert s.placed("img1").span == before


def test_pins_beat_the_template():
    s = session()
    assert s.placed("t1").span == 12
    s.set_span("t1", 6)
    assert s.placed("t1").span == 6


def test_release_returns_a_block_to_the_template():
    s = session()
    auto = s.placed("img1").span
    s.set_span("img1", 12)
    assert s.placed("img1").span == 12
    s.release("img1")
    assert s.placed("img1").span == auto


def test_reset_layout_clears_the_whole_document():
    s = session()
    s.set_span("t1", 4)
    s.set_rows("img1", 20)
    assert s.reset_layout() >= 2
    assert len(s.pins.user_pins()) == 0


def test_width_can_be_pinned_while_height_stays_automatic():
    s = session()
    s.set_span("t1", 6)
    tall = s.placed("t1").height
    s.blocks[1] = BlockInput("t1", "text", text="x" * 4000)
    s.invalidate()
    assert s.placed("t1").span == 6
    assert s.placed("t1").height > tall            # height still follows content


def test_locked_blocks_refuse_layout_edits():
    s = session()
    with pytest.raises(LayoutRefused):
        s.set_span("legal", 6)


def test_locking_a_pin_protects_it_from_the_template_layer():
    s = session()
    s.set_span("img1", 12)
    s.lock("img1")
    s.pins.pin("img1", "span", 3, layer="template", scope=s.grid.scoped())
    s.invalidate()
    assert s.placed("img1").span == 12


def test_pins_are_scoped_to_the_page_geometry():
    s = session()
    s.set_span("t1", 6)
    assert s.placed("t1").span == 6
    s.set_page_size("Letter")
    assert s.placed("t1").span == 12               # Letter has its own layout


def test_history_records_every_layout_change():
    s = session()
    s.resize("img1", "e", 120, 0)
    s.move("tb1", "t1")
    s.release("img1")
    assert [c.action for c in s.history] == ["resize", "move", "release"]
    assert all(c.summary for c in s.history)


# --- snapping ------------------------------------------------------------
def test_dragging_the_east_edge_changes_span_only():
    s = session()
    before = s.placed("img1")
    r = s.resize("img1", "e", dx=s.grid.column_width * 2, dy=0)
    assert "span" in r.changed and "col" not in r.changed
    assert r.span > before.span


def test_dragging_the_west_edge_moves_the_left_column():
    s = session()
    s.set_span("img2", 6, col=6)
    r = s.resize("img2", "w", dx=-s.grid.column_width * 2, dy=0)
    assert r.col < 6 and "col" in r.changed


def test_an_aspect_locked_image_resizes_proportionally():
    s = session()
    r = s.resize("img1", "se", dx=s.grid.column_width * 3, dy=0)
    assert "rows" in r.changed
    box = s.placed("img1")
    assert abs(box.width / box.height - 1.5) < 0.35


def test_the_north_handle_changes_height_and_says_so():
    s = session()
    r = s.resize("t1", "n", dx=0, dy=-60)
    assert "rows" in r.changed
    assert "top edge follows the flow" in r.note


def test_a_span_can_never_leave_the_page():
    s = session()
    r = s.resize("img2", "e", dx=10_000, dy=0)
    assert r.col + r.span <= s.grid.columns


def test_span_has_a_floor_of_one_column():
    s = session()
    r = s.resize("img1", "e", dx=-10_000, dy=0)
    assert r.span >= 1


def test_the_ghost_matches_what_the_commit_produces():
    s = session()
    ghost_box = s.preview_resize("img1", "e", dx=140, dy=0)
    s.resize("img1", "e", dx=140, dy=0)
    real = s.placed("img1")
    assert (ghost_box.col, ghost_box.span) == (real.col, real.span)
    assert abs(ghost_box.width - real.width) < 0.01


def test_handle_hit_testing_finds_corners_before_edges():
    geo = session().geometry()
    box = geo.of("img1")
    assert handle_at(geo, 1, box.x, box.y) == ("img1", "nw")
    assert handle_at(geo, 1, box.x + box.width, box.y + box.height / 2) == ("img1", "e")
    assert handle_at(geo, 1, box.x + box.width / 2, box.y + box.height / 2) is None


def test_snap_rect_lands_on_legal_grid_positions():
    grid = PageGrid()
    r = snap_rect(grid.column_x(3) + 4, 200, grid.span_width(5) - 6, 97, grid)
    assert r.col == 3 and r.span == 5 and r.rows >= 1


# --- drag to make a two-column band -------------------------------------
def test_dropping_on_the_right_third_puts_a_block_beside_another():
    geo = session().geometry()
    box = geo.of("img1")                 # half width, so there is room beside it
    target = drop_target(geo, 1, box.x + box.width - 4, box.y + box.height / 2, dragging="tb1")
    assert target.side == "beside"


def test_dropping_low_on_a_block_places_after_it():
    geo = session().geometry()
    box = geo.of("h1")
    target = drop_target(geo, 1, box.x + box.width / 2, box.y + box.height - 1, dragging="tb1")
    assert target.side == "below"


def test_move_changes_document_order():
    s = session()
    s.move("tb1", "t1")
    order = [b.block_id for b in sorted(s.geometry().boxes, key=lambda b: (b.page, b.y, b.col))]
    assert order.index("tb1") < order.index("t2")


# --- pagination ----------------------------------------------------------
def test_long_documents_paginate_without_splitting_a_band():
    blocks = [BlockInput(f"t{i}", "text", text="x" * 1400) for i in range(30)]
    geo = solve(blocks)
    assert geo.page_count > 1
    for page in range(1, geo.page_count + 1):
        for box in geo.on_page(page):
            assert box.y + box.height <= geo.grid.page_height - geo.grid.margin_bottom + 0.01


def test_break_before_starts_a_new_page():
    s = session()
    s.set_break_before("tb1")
    assert s.placed("tb1").page == 2


def test_keep_with_next_does_not_strand_a_heading():
    blocks = [BlockInput(f"t{i}", "text", text="x" * 1500) for i in range(9)]
    blocks.append(BlockInput("h_end", "heading", text="Verification"))
    blocks.append(BlockInput("tb_end", "table", rows_hint=14))
    pins = PinStore()
    pins.pin("h_end", "keep_with_next", True, scope=PageGrid().scoped())
    geo = solve(blocks, pins=pins)
    assert geo.of("h_end").page == geo.of("tb_end").page


def test_a_band_too_tall_for_the_page_is_reported_not_hidden():
    blocks = [BlockInput("huge", "table", rows_hint=200)]
    geo = solve(blocks)
    assert geo.warnings
    assert geo.of("huge").overflow


# --- templates that learn -------------------------------------------------
def test_a_repeated_edit_becomes_a_rule_not_twelve_exceptions():
    s = session()
    s.set_span("img1", 4)
    s.set_span("img2", 4)
    report = s.promote_to_template()
    assert any("image.span" in r for r in report["rules"])
    assert report["block_count"] == 0


def test_a_one_off_edit_stays_a_block_default():
    s = session()
    s.set_span("t1", 6)
    report = s.promote_to_template()
    assert report["rule_count"] == 0
    assert any("t1.span" in b for b in report["block_defaults"])


def test_a_promoted_template_reproduces_the_layout_on_a_fresh_document():
    s = session()
    s.set_span("img1", 4)
    s.set_span("img2", 4)
    s.promote_to_template()
    fresh = LayoutSession(doc(), template=s.template)
    assert fresh.placed("img1").span == 4          # no pins at all, template alone


def test_promotion_versions_rather_than_mutates():
    s = session()
    before = s.template.version
    s.set_span("img1", 4)
    s.set_span("img2", 4)
    s.promote_to_template()
    assert s.template.version == before + 1
    assert s.template.parent_version == before


def test_template_diff_is_readable():
    a = compliance_a4()
    b = LayoutTemplate.from_dict(a.to_dict())
    b.role_defaults["image"]["span"] = 4
    assert a.diff(b) == ["image.span: 6 -> 4"]


def test_adopting_a_template_keeps_the_users_own_edits():
    s = session()
    s.set_span("t1", 6)
    s.adopt_template(compliance_a4())
    assert s.placed("t1").span == 6


def test_templates_round_trip_through_json():
    t = compliance_a4()
    assert LayoutTemplate.from_dict(t.to_dict()).to_dict() == t.to_dict()


# --- print parity ---------------------------------------------------------
def test_canvas_and_renderer_read_the_same_geometry():
    s = session()
    s.set_span("img1", 8)
    canvas = s.geometry()
    renderer = solve(s.blocks, s.grid, s.pins, s.template.defaults_for(s.blocks, s.grid), s.measurer)
    assert compare(canvas, renderer).ok


def test_parity_breaks_loudly_when_geometry_diverges():
    s = session()
    canvas = s.geometry()
    renderer = solve(s.blocks, PageGrid(columns=6), s.pins, None, s.measurer)
    report = compare(canvas, renderer)
    assert not report.ok
    assert "PARITY BROKEN" in str(report)


def test_every_edit_changes_the_fingerprint():
    s = session()
    before = fingerprint(s.geometry())
    s.set_span("img1", 3)
    assert fingerprint(s.geometry()) != before


# --- serialisation --------------------------------------------------------
def test_pins_serialise_sorted_and_round_trip():
    s = session()
    s.set_span("t1", 6)
    s.set_rows("img1", 14)
    text = s.pins.to_jsonl()
    assert text.splitlines() == sorted(text.splitlines())
    assert len(PinStore.from_jsonl(text)) == len(s.pins)


def test_orphan_pins_are_reported_not_dropped():
    s = session()
    s.pins.pin("ghost", "span", 4, scope=s.grid.scoped())
    assert any("ghost" in w for w in s.geometry().warnings)


def test_state_payload_has_everything_the_canvas_needs():
    s = session()
    s.select("img1")
    s.set_span("img1", 4)
    state = s.state()
    assert state["geometry"]["boxes"]
    assert state["selection"] == ["img1"]
    assert "legal" in state["locked_blocks"]
    assert state["user_override_count"] == 1


# --- integration with the 0.72 build --------------------------------------
def test_existing_full_half_third_layouts_migrate_without_reshaping():
    from foldok_boxes.integration import migrate_layout

    grid = PageGrid()
    rows = [
        {"block_id": "a", "layout": {"width": "full"}},
        {"block_id": "b", "layout": {"width": "half"}},
        {"block_id": "c", "layout": {"width": "third", "align": "center"}},
    ]
    pins, notes = migrate_layout(rows, grid)
    scope = grid.scoped()
    assert pins.value("a", "span", scope) == 12
    assert pins.value("b", "span", scope) == 6
    assert pins.value("c", "span", scope) == 4
    assert pins.value("c", "align", scope) == "center"
    assert notes


def test_migrated_layouts_land_on_the_template_layer_so_reset_still_works():
    from foldok_boxes.integration import migrate_layout

    grid = PageGrid()
    pins, _ = migrate_layout([{"block_id": "t1", "layout": {"width": "half"}}], grid)
    s = LayoutSession(doc(), grid=grid, pins=pins)
    assert s.placed("t1").span == 6
    assert len(s.pins.user_pins()) == 0          # nothing pretends the user chose it
    s.reset_layout()
    assert s.placed("t1").span == 12


def test_two_column_groups_become_adjacent_columns():
    from foldok_boxes.integration import migrate_layout

    grid = PageGrid()
    rows = [
        {"block_id": "l", "layout": {"group_id": "g1", "group_slot": 1}},
        {"block_id": "r", "layout": {"group_id": "g1", "group_slot": 2}},
    ]
    pins, _ = migrate_layout(rows, grid)
    scope = grid.scoped()
    assert (pins.value("l", "col", scope), pins.value("l", "span", scope)) == (0, 6)
    assert (pins.value("r", "col", scope), pins.value("r", "span", scope)) == (6, 6)


def test_pins_write_back_into_the_existing_layout_column():
    from foldok_boxes.integration import layout_jsonb

    s = session()
    s.set_span("img1", 6)
    out = layout_jsonb("img1", s.pins, s.grid)
    assert out["span"] == 6 and out["width"] == "half"


def test_unknown_block_types_degrade_to_full_width_text():
    from foldok_boxes.integration import blocks_from

    blocks = blocks_from([{"id": "x", "type": "mystery_widget", "content": "hello"}])
    assert blocks[0].role == "text"
    assert solve(blocks).of("x").span == 12
