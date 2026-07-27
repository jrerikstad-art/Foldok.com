/* foldok-box-editor.js — pointer tool for the Foldok document canvas.
 *
 * Zero dependencies. Drop it next to app.html and give it the geometry payload
 * from foldok_boxes.solve(). It renders an overlay of selectable, resizable
 * boxes on top of whatever is painting the page underneath.
 *
 * ARCHITECTURE, and the one thing not to change:
 *
 *   This file does NO layout. It mirrors the snap maths in foldok_boxes/snap.py
 *   so the ghost under the cursor is instant, then it sends an intent and lets
 *   the engine recompute the authoritative geometry. Optimistic locally,
 *   authoritative on the server, identical formulas on both sides. The moment
 *   this file starts deciding where things go, the canvas and the PDF drift and
 *   the parity test is the only thing that will tell you.
 *
 * Intents emitted (wire these to the LayoutSession API):
 *   {type:'select',  blockIds}
 *   {type:'resize',  blockId, handle, dx, dy}      -> session.resize(...)
 *   {type:'move',    blockId, page, x, y}          -> session.drop(...)
 *   {type:'release', blockId}                      -> session.release(...)
 *   {type:'span',    blockId, span, col}           -> session.set_span(...)
 *   {type:'reset'}                                 -> session.reset_layout()
 */

(function (global) {
  "use strict";

  var HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
  var GRAB = 6;          // points, matches snap.GRAB
  var MIN_DRAG = 3;      // px before a press becomes a drag

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(v, hi)); }

  // ---- grid maths: line-for-line with foldok_boxes/model.py --------------
  function Grid(g) {
    this.g = g;
    this.contentWidth = g.page_width - g.margin_left - g.margin_right;
    this.columnWidth = g.columns <= 1
      ? this.contentWidth
      : (this.contentWidth - g.gutter * (g.columns - 1)) / g.columns;
  }
  Grid.prototype.columnX = function (col) {
    col = clamp(col, 0, this.g.columns - 1);
    return this.g.margin_left + col * (this.columnWidth + this.g.gutter);
  };
  Grid.prototype.spanWidth = function (span) {
    span = clamp(span, 1, this.g.columns);
    return span * this.columnWidth + (span - 1) * this.g.gutter;
  };
  Grid.prototype.colAt = function (x) {
    var pitch = this.columnWidth + this.g.gutter;
    return clamp(Math.round((x - this.g.margin_left) / pitch), 0, this.g.columns - 1);
  };
  Grid.prototype.spanAt = function (w) {
    var pitch = this.columnWidth + this.g.gutter;
    return clamp(Math.round((w + this.g.gutter) / pitch), 1, this.g.columns);
  };

  // ---- snap: mirrors foldok_boxes/snap.resize ----------------------------
  function snapResize(box, handle, dx, dy, grid, opts) {
    opts = opts || {};
    var maxSpan = Math.min(opts.maxSpan || grid.g.columns, grid.g.columns);
    var minSpan = opts.minSpan || 1;
    var left = box.x, right = box.x + box.width;
    var col = box.col, span = box.span, rows = box.rows, changed = [];

    if (handle.indexOf("e") >= 0) {
      span = clamp(grid.spanAt(Math.max(grid.columnWidth, right + dx - left)),
                   minSpan, Math.min(maxSpan, grid.g.columns - col));
      if (span !== box.span) changed.push("span");
    }
    if (handle.indexOf("w") >= 0) {
      var newCol = clamp(grid.colAt(left + dx), 0, col + span - minSpan);
      var newSpan = clamp(grid.spanAt(Math.max(grid.columnWidth, right - grid.columnX(newCol))),
                          minSpan, Math.min(maxSpan, grid.g.columns - newCol));
      if (newCol !== col) changed.push("col");
      if (newSpan !== span) changed.push("span");
      col = newCol; span = newSpan;
    }
    if (opts.aspect) {
      rows = Math.max(1, Math.round(grid.spanWidth(span) / opts.aspect / grid.g.baseline));
      if (changed.indexOf("rows") < 0) changed.push("rows");
    } else if (handle.indexOf("n") >= 0 || handle.indexOf("s") >= 0) {
      var delta = handle.indexOf("s") >= 0 ? dy : -dy;
      rows = Math.max(1, Math.round(Math.max(grid.g.baseline, box.height + delta) / grid.g.baseline));
      if (rows !== box.rows) changed.push("rows");
    }
    return { col: col, span: span, rows: rows, changed: changed };
  }

  function handleAt(box, px, py, tol) {
    tol = tol || GRAB;
    if (px < box.x - tol || px > box.x + box.width + tol) return null;
    if (py < box.y - tol || py > box.y + box.height + tol) return null;
    var v = Math.abs(py - box.y) <= tol ? "n" : (Math.abs(py - (box.y + box.height)) <= tol ? "s" : "");
    var h = Math.abs(px - box.x) <= tol ? "w" : (Math.abs(px - (box.x + box.width)) <= tol ? "e" : "");
    return (v + h) || null;
  }

  function cursorFor(handle, overBlock) {
    if (handle === "e" || handle === "w") return "ew-resize";
    if (handle === "n" || handle === "s") return "ns-resize";
    if (handle === "nw" || handle === "se") return "nwse-resize";
    if (handle === "ne" || handle === "sw") return "nesw-resize";
    return overBlock ? "move" : "default";
  }

  // ---- editor -------------------------------------------------------------
  function FoldokBoxEditor(container, options) {
    options = options || {};
    this.container = container;
    this.onIntent = options.onIntent || function () {};
    this.scale = options.scale || 1;            // px per point
    this.page = options.page || 1;
    this.readOnly = !!options.readOnly;
    this.state = null;
    this.grid = null;
    this.selection = [];
    this.locked = {};
    this.aspects = options.aspects || {};
    this.drag = null;

    this.layer = document.createElement("div");
    this.layer.className = "fbx-layer";
    this.layer.style.cssText = "position:absolute;inset:0;z-index:5;";
    container.appendChild(this.layer);

    this.ghost = document.createElement("div");
    this.ghost.className = "fbx-ghost";
    this.ghost.style.cssText =
      "position:absolute;display:none;pointer-events:none;border:2px solid #F2B705;" +
      "background:rgba(242,183,5,.10);border-radius:2px;z-index:40;";
    this.layer.appendChild(this.ghost);

    this.rail = document.createElement("div");
    this.rail.className = "fbx-rail";
    this.rail.style.cssText =
      "position:absolute;display:none;pointer-events:none;z-index:39;top:0;bottom:0;" +
      "border-left:1px dashed #F2B70588;border-right:1px dashed #F2B70588;";
    this.layer.appendChild(this.rail);

    this.drop = document.createElement("div");
    this.drop.style.cssText =
      "position:absolute;display:none;pointer-events:none;height:3px;background:#F2B705;z-index:41;";
    this.layer.appendChild(this.drop);

    this._bind();
    if (options.state) this.setState(options.state);
  }

  FoldokBoxEditor.prototype.setState = function (state) {
    this.state = state;
    this.grid = new Grid(state.geometry.grid);
    this.selection = state.selection || [];
    this.locked = {};
    (state.locked_blocks || []).forEach(function (id) { this.locked[id] = true; }.bind(this));
    this.render();
  };

  FoldokBoxEditor.prototype.setPage = function (page) { this.page = page; this.render(); };

  FoldokBoxEditor.prototype.boxes = function () {
    if (!this.state) return [];
    var page = this.page;
    return this.state.geometry.boxes.filter(function (b) { return b.page === page; });
  };

  FoldokBoxEditor.prototype.render = function () {
    var self = this;
    Array.prototype.slice.call(this.layer.querySelectorAll(".fbx-box")).forEach(function (n) {
      n.parentNode.removeChild(n);
    });
    this.boxes().forEach(function (box) {
      var el = document.createElement("div");
      el.className = "fbx-box";
      el.setAttribute("data-block-id", box.block_id);
      var selected = self.selection.indexOf(box.block_id) >= 0;
      var pinned = (box.pinned || []).length > 0;
      el.style.cssText =
        "position:absolute;box-sizing:border-box;border-radius:2px;" +
        "left:" + (box.x * self.scale) + "px;top:" + (box.y * self.scale) + "px;" +
        "width:" + (box.width * self.scale) + "px;height:" + (box.height * self.scale) + "px;" +
        "border:" + (selected ? "2px solid #F2B705" : (pinned ? "1px dashed #B9B3A2" : "1px solid transparent")) + ";" +
        (box.overflow ? "outline:2px solid #C4441F;" : "") +
        "cursor:" + (self.locked[box.block_id] ? "not-allowed" : "move") + ";";
      if (selected && !self.readOnly && !self.locked[box.block_id]) {
        HANDLES.forEach(function (h) { el.appendChild(self._handle(h)); });
        el.appendChild(self._badge(box));
      }
      self.layer.appendChild(el);
    });
  };

  FoldokBoxEditor.prototype._handle = function (h) {
    var d = document.createElement("i");
    var pos = {
      nw: "left:-4px;top:-4px;", n: "left:calc(50% - 4px);top:-4px;",
      ne: "right:-4px;top:-4px;", e: "right:-4px;top:calc(50% - 4px);",
      se: "right:-4px;bottom:-4px;", s: "left:calc(50% - 4px);bottom:-4px;",
      sw: "left:-4px;bottom:-4px;", w: "left:-4px;top:calc(50% - 4px);"
    }[h];
    d.setAttribute("data-handle", h);
    d.style.cssText =
      "position:absolute;width:8px;height:8px;background:#fff;border:1.5px solid #F2B705;" +
      "border-radius:1px;" + pos + "cursor:" + cursorFor(h, true) + ";";
    return d;
  };

  FoldokBoxEditor.prototype._badge = function (box) {
    var b = document.createElement("span");
    b.style.cssText =
      "position:absolute;left:0;top:-19px;font:600 10px/1 'IBM Plex Mono',monospace;" +
      "background:#F2B705;color:#16181D;padding:3px 5px;border-radius:3px;white-space:nowrap;";
    b.textContent = box.span + "/" + this.grid.g.columns +
      ((box.pinned || []).length ? " · edited" : " · auto");
    return b;
  };

  // ---- pointer ------------------------------------------------------------
  FoldokBoxEditor.prototype._pt = function (ev) {
    var r = this.container.getBoundingClientRect();
    return { x: (ev.clientX - r.left) / this.scale, y: (ev.clientY - r.top) / this.scale };
  };

  FoldokBoxEditor.prototype._hit = function (p) {
    var boxes = this.boxes();
    for (var i = boxes.length - 1; i >= 0; i--) {
      var b = boxes[i];
      var h = handleAt(b, p.x, p.y, GRAB);
      if (h && this.selection.indexOf(b.block_id) >= 0) return { box: b, handle: h };
      if (p.x >= b.x && p.x <= b.x + b.width && p.y >= b.y && p.y <= b.y + b.height) {
        return { box: b, handle: null };
      }
    }
    return null;
  };

  FoldokBoxEditor.prototype._bind = function () {
    var self = this;

    this.layer.addEventListener("pointermove", function (ev) {
      if (self.drag) return self._dragMove(ev);
      var hit = self._hit(self._pt(ev));
      self.layer.style.cursor = hit ? cursorFor(hit.handle, true) : "default";
    });

    this.layer.addEventListener("pointerdown", function (ev) {
      if (self.readOnly || ev.button !== 0) return;
      var p = self._pt(ev);
      var hit = self._hit(p);
      if (!hit) { self.selection = []; self.onIntent({ type: "select", blockIds: [] }); return self.render(); }
      if (self.locked[hit.box.block_id]) return;

      if (self.selection.indexOf(hit.box.block_id) < 0) {
        self.selection = ev.shiftKey ? self.selection.concat([hit.box.block_id]) : [hit.box.block_id];
        self.onIntent({ type: "select", blockIds: self.selection.slice() });
        self.render();
      }
      self.drag = {
        box: hit.box, handle: hit.handle, start: p, moved: false,
        pointerId: ev.pointerId
      };
      self.layer.setPointerCapture(ev.pointerId);
      ev.preventDefault();
    });

    this.layer.addEventListener("pointerup", function (ev) {
      if (!self.drag) return;
      var d = self.drag;
      self.drag = null;
      self.ghost.style.display = "none";
      self.rail.style.display = "none";
      self.drop.style.display = "none";
      try { self.layer.releasePointerCapture(d.pointerId); } catch (e) {}
      if (!d.moved) return;
      var p = self._pt(ev);
      var dx = p.x - d.start.x, dy = p.y - d.start.y;
      if (d.handle) {
        self.onIntent({ type: "resize", blockId: d.box.block_id, handle: d.handle, dx: dx, dy: dy });
      } else {
        self.onIntent({ type: "move", blockId: d.box.block_id, page: self.page, x: p.x, y: p.y });
      }
    });

    this.layer.addEventListener("dblclick", function (ev) {
      var hit = self._hit(self._pt(ev));
      if (hit && !self.locked[hit.box.block_id]) {
        self.onIntent({ type: "release", blockId: hit.box.block_id });
      }
    });

    document.addEventListener("keydown", function (ev) {
      if (self.readOnly || !self.selection.length) return;
      var id = self.selection[0];
      var box = self.boxes().filter(function (b) { return b.block_id === id; })[0];
      if (!box) return;
      if (ev.key === "Escape") {
        self.selection = []; self.onIntent({ type: "select", blockIds: [] }); return self.render();
      }
      var step = ev.shiftKey ? 1 : 1;
      if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        var dir = ev.key === "ArrowRight" ? step : -step;
        if (ev.altKey) {
          self.onIntent({ type: "span", blockId: id, span: box.span, col: clamp(box.col + dir, 0, self.grid.g.columns - box.span) });
        } else {
          self.onIntent({ type: "span", blockId: id, span: clamp(box.span + dir, 1, self.grid.g.columns - box.col), col: null });
        }
        ev.preventDefault();
      }
    });
  };

  FoldokBoxEditor.prototype._dragMove = function (ev) {
    var d = this.drag, p = this._pt(ev);
    var dx = p.x - d.start.x, dy = p.y - d.start.y;
    if (!d.moved && Math.abs(dx * this.scale) < MIN_DRAG && Math.abs(dy * this.scale) < MIN_DRAG) return;
    d.moved = true;

    if (d.handle) {
      var r = snapResize(d.box, d.handle, dx, dy, this.grid, { aspect: this.aspects[d.box.block_id] });
      var x = this.grid.columnX(r.col), w = this.grid.spanWidth(r.span);
      var h = (r.rows || d.box.rows) * this.grid.g.baseline;
      this.ghost.style.display = "block";
      this.ghost.style.left = (x * this.scale) + "px";
      this.ghost.style.top = (d.box.y * this.scale) + "px";
      this.ghost.style.width = (w * this.scale) + "px";
      this.ghost.style.height = (h * this.scale) + "px";
      this.rail.style.display = "block";
      this.rail.style.left = (x * this.scale) + "px";
      this.rail.style.width = (w * this.scale) + "px";
    } else {
      var target = this._dropTarget(p, d.box.block_id);
      this.drop.style.display = "block";
      this.drop.style.left = (target.x * this.scale) + "px";
      this.drop.style.width = (target.width * this.scale) + "px";
      this.drop.style.top = (target.y * this.scale) + "px";
    }
  };

  /* Mirrors snap.drop_target: left/right third of a box means "beside it",
     which is how a two-column band gets made without a separate gesture. */
  FoldokBoxEditor.prototype._dropTarget = function (p, dragging) {
    var boxes = this.boxes().filter(function (b) { return b.block_id !== dragging; });
    if (!boxes.length) return { x: this.grid.g.margin_left, y: this.grid.g.margin_top, width: this.grid.spanWidth(this.grid.g.columns) };
    var over = null;
    boxes.forEach(function (b) {
      if (p.x >= b.x && p.x <= b.x + b.width && p.y >= b.y && p.y <= b.y + b.height) over = b;
    });
    if (over) {
      var third = over.width / 3;
      if (p.x < over.x + third) return { x: over.x - 2, y: over.y, width: 4 };
      if (p.x > over.x + over.width - third) return { x: over.x + over.width - 2, y: over.y, width: 4 };
      var below = p.y > over.y + over.height / 2;
      return { x: over.x, y: below ? over.y + over.height : over.y, width: over.width };
    }
    var nearest = boxes.reduce(function (a, b) {
      return Math.abs(b.y + b.height / 2 - p.y) < Math.abs(a.y + a.height / 2 - p.y) ? b : a;
    });
    return {
      x: nearest.x, width: nearest.width,
      y: p.y > nearest.y + nearest.height / 2 ? nearest.y + nearest.height : nearest.y
    };
  };

  FoldokBoxEditor.prototype.destroy = function () {
    if (this.layer && this.layer.parentNode) this.layer.parentNode.removeChild(this.layer);
  };

  global.FoldokBoxEditor = FoldokBoxEditor;
  global.FoldokBoxEditor.snapResize = snapResize;
  global.FoldokBoxEditor.handleAt = handleAt;
  global.FoldokBoxEditor.cursorFor = cursorFor;
  global.FoldokBoxEditor.Grid = Grid;
})(typeof window !== "undefined" ? window : this);
