"""Runnable reference implementation.

    python -m foldok_boxes.demo        ->  http://127.0.0.1:8899

Exists so Cursor has a working thing to port rather than a description to
interpret.  It is deliberately the whole loop and nothing else:

    pointer gesture -> intent -> LayoutSession -> solve() -> geometry -> redraw

Note what the browser never does: decide where a box goes.  It draws the ghost
locally using the mirrored snap maths so the drag feels instant, then sends the
intent and redraws from whatever the engine says.  Optimistic locally,
authoritative on the server.  Keep that split when porting into app.html.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .flow import BlockInput
from .session import LayoutRefused, LayoutSession
from .template import compliance_a4

EDITOR_JS = Path(__file__).with_name("editor") / "foldok-box-editor.js"


def demo_blocks() -> list[BlockInput]:
    return [
        BlockInput("h1", "heading", section="scope", text="1  Omfang"),
        BlockInput("t1", "text", section="scope", text="Denne dokumentasjonen dekker " + "installasjonen " * 60),
        BlockInput("img1", "image", section="scope", aspect=1.5),
        BlockInput("img2", "image", section="scope", aspect=1.5),
        BlockInput("h2", "heading", section="verify", text="2  Verifikasjon"),
        BlockInput("t2", "text", section="verify", text="Målinger utført " + "med kalibrert instrument " * 30),
        BlockInput("tb1", "table", section="verify", rows_hint=10),
        BlockInput("cal1", "callout", section="verify", text="Advarsel: " + "spenning " * 18),
        BlockInput("dia1", "diagram", section="verify", aspect=1.9),
        BlockInput("t3", "text", section="handover", text="Overlevering " + "og dokumentasjon " * 70),
        BlockInput("legal", "text", section="handover", text="Standardvilkår " * 30, locked=True),
    ]


def build_session() -> LayoutSession:
    return LayoutSession(demo_blocks(), template=compliance_a4())


PAGE = """<!doctype html>
<meta charset="utf-8"><title>Foldok — box editor</title>
<style>
  :root { --ink:#16181D; --paper:#FAF9F5; --sheet:#F2F0E9; --line:#DAD7CC;
          --signal:#F2B705; --steel:#8A8577; }
  * { box-sizing:border-box }
  body { margin:0; background:var(--sheet); color:var(--ink);
         font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif }
  header { display:flex; gap:10px; align-items:center; padding:10px 16px;
           background:var(--ink); color:#fff }
  header b { color:var(--signal) }
  header button { font:600 12px/1 inherit; padding:7px 12px; border:0; border-radius:6px;
                  background:#ffffff1a; color:#fff; cursor:pointer }
  header button:hover { background:#ffffff2e }
  header .sp { flex:1 }
  #hint { font-size:12px; color:#ffffff99 }
  main { display:flex; gap:20px; padding:20px; align-items:flex-start }
  #stage { position:relative; background:#fff; box-shadow:0 2px 12px #0002 }
  #stage .col { position:absolute; top:0; bottom:0; background:var(--signal); opacity:.05 }
  #stage .content { position:absolute; border:1px dashed #0000000f }
  aside { width:280px; background:var(--paper); border:1px solid var(--line);
          border-radius:8px; padding:14px; font-size:12.5px }
  aside h3 { margin:0 0 8px; font-size:11px; letter-spacing:.08em; color:var(--steel) }
  aside ul { margin:0 0 14px; padding-left:16px } aside li { margin-bottom:3px }
  .k { font-family:'IBM Plex Mono',monospace; font-size:11px }
</style>
<header>
  <b>Foldok</b> <span>box editor — reference implementation</span>
  <span class="sp"></span>
  <span id="hint">drag a box · drag its corners · double-click to un-pin</span>
  <button id="prev">‹</button><span id="pageno" class="k">1</span><button id="next">›</button>
  <button id="promote">Save as my layout</button>
  <button id="reset">Reset layout</button>
</header>
<main>
  <div id="stage"></div>
  <aside>
    <h3>SELECTED</h3><div id="sel">nothing selected</div>
    <h3 style="margin-top:14px">HISTORY</h3><ul id="hist"><li>—</li></ul>
    <h3>TEMPLATE</h3><div id="tpl" class="k">—</div>
    <h3 style="margin-top:14px">WARNINGS</h3><ul id="warn"><li>none</li></ul>
  </aside>
</main>
<script src="/foldok-box-editor.js"></script>
<script>
const SCALE = 0.82;
let editor = null, page = 1;

async function send(intent) {
  const r = await fetch("/api/intent", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(intent)
  });
  paint(await r.json());
}

function paint(state) {
  const g = state.geometry.grid;
  const stage = document.getElementById("stage");
  stage.style.width = (g.page_width * SCALE) + "px";
  stage.style.height = (g.page_height * SCALE) + "px";
  [...stage.querySelectorAll(".col,.content")].forEach(n => n.remove());

  const cw = (g.page_width - g.margin_left - g.margin_right - g.gutter * (g.columns - 1)) / g.columns;
  for (let c = 0; c < g.columns; c++) {
    const d = document.createElement("div");
    d.className = "col";
    d.style.left = ((g.margin_left + c * (cw + g.gutter)) * SCALE) + "px";
    d.style.width = (cw * SCALE) + "px";
    stage.appendChild(d);
  }
  const box = document.createElement("div");
  box.className = "content";
  box.style.cssText = "left:" + (g.margin_left * SCALE) + "px;top:" + (g.margin_top * SCALE) +
    "px;width:" + ((g.page_width - g.margin_left - g.margin_right) * SCALE) +
    "px;height:" + ((g.page_height - g.margin_top - g.margin_bottom) * SCALE) + "px;";
  stage.appendChild(box);

  if (!editor) {
    editor = new FoldokBoxEditor(stage, { scale: SCALE, page: page, onIntent: send });
  }
  editor.page = page;
  editor.setState(state);

  document.getElementById("pageno").textContent = page + " / " + state.geometry.page_count;
  const sel = state.selection[0];
  const b = sel && state.geometry.boxes.find(x => x.block_id === sel);
  document.getElementById("sel").innerHTML = b
    ? `<span class="k">${b.block_id}</span> · ${b.role}<br>${b.span}/${g.columns} columns · ${b.rows} rows` +
      `<br><small>${(b.pinned || []).length ? "edited by you: " + b.pinned.join(", ") : "automatic"}</small>`
    : "nothing selected";
  document.getElementById("hist").innerHTML =
    (state.history.slice(-8).reverse().map(h => "<li>" + h.summary + "</li>").join("")) || "<li>—</li>";
  document.getElementById("tpl").textContent =
    state.template.id + " v" + state.template.version + " · " + state.user_override_count + " override(s)";
  document.getElementById("warn").innerHTML =
    (state.warnings.map(w => "<li>" + w + "</li>").join("")) || "<li>none</li>";
}

document.getElementById("reset").onclick = () => send({ type: "reset" });
document.getElementById("promote").onclick = () => send({ type: "promote" });
document.getElementById("prev").onclick = () => { if (page > 1) { page--; send({ type: "noop" }); } };
document.getElementById("next").onclick = () => { page++; send({ type: "noop" }); };

fetch("/api/state").then(r => r.json()).then(paint);
</script>
"""


class Handler(BaseHTTPRequestHandler):
    session: LayoutSession

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/state"):
            return self._send(json.dumps(self.session.state()).encode(), "application/json")
        if self.path.startswith("/foldok-box-editor.js"):
            return self._send(EDITOR_JS.read_bytes(), "application/javascript")
        return self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        intent = json.loads(self.rfile.read(length) or b"{}")
        try:
            apply_intent(self.session, intent)
        except LayoutRefused as exc:
            # A refusal is a real answer — record it so the user sees why the
            # gesture did nothing, instead of the canvas silently ignoring them.
            self.session._log("refused", intent.get("blockId", "*"), str(exc))  # noqa: SLF001
        return self._send(json.dumps(self.session.state()).encode(), "application/json")

    def log_message(self, *args) -> None:  # keep the console quiet
        return


def apply_intent(session: LayoutSession, intent: dict) -> None:
    kind = intent.get("type")
    if kind == "select":
        session.select(*intent.get("blockIds", []))
    elif kind == "resize":
        session.resize(intent["blockId"], intent["handle"], float(intent["dx"]), float(intent["dy"]))
    elif kind == "move":
        session.drop(intent["blockId"], int(intent.get("page", 1)), float(intent["x"]), float(intent["y"]))
    elif kind == "release":
        session.release(intent["blockId"])
    elif kind == "span":
        session.set_span(intent["blockId"], int(intent["span"]), intent.get("col"))
    elif kind == "reset":
        session.reset_layout()
    elif kind == "promote":
        session.promote_to_template()


def serve(host: str = "127.0.0.1", port: int = 8899) -> None:
    Handler.session = build_session()
    print(f"Foldok box editor -> http://{host}:{port}")
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
