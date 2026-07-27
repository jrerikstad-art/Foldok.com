import React, { useState, useRef, useEffect } from "react";

/* ────────────────────────────────────────────────────────────
   FOLDOK — Tegnelag (annotation layer) prototype, WORKORDER_0.56
   The drawing is a POINTING DEVICE: every mark resolves in code to
   the block(s) it overlaps and becomes a structured command.
   Try: pick a tool → draw on the document → watch the chip resolve →
   [Utfør] to apply. Arrows move blocks. ✕ deletes. Box+note inserts.
   Select text with the ⌖ tool for the inline toolbar.
   ──────────────────────────────────────────────────────────── */

const T = { ink:"#16181D", paper:"#F2F0EA", sheet:"#fff", signal:"#F5C400",
  steel:"#5A6472", line:"#DCD9D0", ok:"#1E7A46", gap:"#C74E19", fact:"#1450B4" };

const TOOLS = [
  { id:"pen",   icon:"✏", label:"Penn" },
  { id:"box",   icon:"▢", label:"Boks" },
  { id:"arrow", icon:"→", label:"Pil" },
  { id:"del",   icon:"✕", label:"Slett" },
  { id:"note",  icon:"T", label:"Notat" },
  { id:"sel",   icon:"⌖", label:"Velg tekst" },
];

const INITIAL_BLOCKS = [
  { id:"b1", sec:"1", type:"heading", text:"Minirenseanlegg Demo Veien 1" },
  { id:"b2", sec:"1", type:"h2", text:"Identifikasjon og anleggsdata" },
  { id:"b3", sec:"1", type:"table", text:"Adresse · Demo Veien 1 | Gnr./bnr. · 1/1 | Kommune · Demo kommune | Anleggstype · Biologisk/kjemisk" },
  { id:"b4", sec:"2", type:"h2", text:"2 · Systemoversikt" },
  { id:"b5", sec:"2", type:"prose", text:"Anlegget behandler sanitært avløpsvann fra to fritidsboliger. Renset vann føres i utslippsledning til demodyp på minimum 2 m dyp." },
  { id:"b6", sec:"3", type:"h2", type2:true, text:"3 · Tekniske data" },
  { id:"b7", sec:"3", type:"table", text:"Kapasitet · 10 PE | Utslippsdybde · ≥ 2 m | P-reduksjon · 60 % | BOF₅-reduksjon · 70 %" },
  { id:"b8", sec:"4", type:"h2", text:"4 · Installasjon" },
  { id:"b9", sec:"4", type:"prose", text:"Graving utføres i berggrunn med tynt torvdekke. Sprengning kan være nødvendig — se sikkerhetsavsnitt." },
];

export default function AnnotationPrototype() {
  const [tool, setTool] = useState("arrow");
  const [blocks, setBlocks] = useState(INITIAL_BLOCKS);
  const [marks, setMarks] = useState([]);
  const [drawing, setDrawing] = useState(null);
  const [rects, setRects] = useState({});
  const [sel, setSel] = useState(null);
  const [log, setLog] = useState([]);
  const docRef = useRef(null);

  /* measure block boxes (this is what makes marks resolvable) */
  useEffect(() => {
    const measure = () => {
      if (!docRef.current) return;
      const base = docRef.current.getBoundingClientRect();
      const r = {};
      docRef.current.querySelectorAll("[data-block-id]").forEach(el => {
        const b = el.getBoundingClientRect();
        r[el.dataset.blockId] = { x:b.left-base.left, y:b.top-base.top, w:b.width, h:b.height };
      });
      setRects(r);
    };
    measure();
    const t = setTimeout(measure, 60);
    window.addEventListener("resize", measure);
    return () => { clearTimeout(t); window.removeEventListener("resize", measure); };
  }, [blocks]);

  const hit = (x, y) => {
    for (const [id, r] of Object.entries(rects))
      if (x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h) return id;
    return null;
  };
  const nearestAnchor = (y) => {
    let best = null, bd = 1e9;
    for (const [id, r] of Object.entries(rects)) {
      const dTop = Math.abs(y - r.y), dBot = Math.abs(y - (r.y + r.h));
      if (dTop < bd) { bd = dTop; best = { anchor:`før ${label(id)}`, ref:id, pos:"before" }; }
      if (dBot < bd) { bd = dBot; best = { anchor:`etter ${label(id)}`, ref:id, pos:"after" }; }
    }
    return best;
  };
  const label = id => {
    const b = blocks.find(x => x.id === id);
    if (!b) return id;
    return b.type === "table" ? `tabell §${b.sec}` :
           b.type.startsWith("h") ? `«${b.text.slice(0, 22)}»` : `avsnitt §${b.sec}`;
  };

  /* resolve a raw mark → structured command (THE KEY STEP, all code) */
  const resolve = (m) => {
    const { kind, x1, y1, x2, y2 } = m;
    const from = hit(x1, y1);
    if (kind === "arrow") {
      const to = hit(x2, y2);
      if (from && to && from !== to)
        return { action:"move", targets:[from], anchor:`etter ${label(to)}`, ref:to, pos:"after",
                 chip:`Flytt ${label(from)} → etter ${label(to)}`, tokens:0 };
      const a = nearestAnchor(y2);
      return from && a
        ? { action:"move", targets:[from], ...a, chip:`Flytt ${label(from)} → ${a.anchor}`, tokens:0 }
        : { action:"unclear", chip:"Uklart mål — tegn til en blokk", tokens:0 };
    }
    if (kind === "del")
      return from ? { action:"delete", targets:[from], chip:`Slett ${label(from)}`, tokens:0 }
                  : { action:"unclear", chip:"Ingen blokk truffet", tokens:0 };
    if (kind === "box") {
      const inside = Object.entries(rects).filter(([, r]) => {
        const ox = Math.max(0, Math.min(x2, r.x+r.w) - Math.max(x1, r.x));
        const oy = Math.max(0, Math.min(y2, r.y+r.h) - Math.max(y1, r.y));
        return (ox*oy) / (r.w*r.h) > 0.3;
      }).map(([id]) => id);
      if (inside.length)
        return { action:"group", targets:inside, chip:`Merket ${inside.length} blokk(er) — skriv notat`, tokens:0 };
      const a = nearestAnchor((y1+y2)/2);
      return { action:"insert", ...a, chip:`Sett inn her (${a?.anchor}) — velg innhold`, tokens:0 };
    }
    if (kind === "pen")
      return from ? { action:"mark", targets:[from], chip:`Merket ${label(from)} — skriv notat`, tokens:0 }
                  : { action:"unclear", chip:"Ingen blokk truffet", tokens:0 };
    if (kind === "note")
      return { action:"note", targets: from ? [from] : [], chip: from ? `Notat på ${label(from)}` : "Fritt notat", tokens:0.004 };
    return { action:"unclear", chip:"—", tokens:0 };
  };

  /* drawing handlers */
  const start = e => {
    if (tool === "sel") return;
    const b = docRef.current.getBoundingClientRect();
    setDrawing({ kind:tool, x1:e.clientX-b.left, y1:e.clientY-b.top,
                 x2:e.clientX-b.left, y2:e.clientY-b.top });
  };
  const move = e => {
    if (!drawing) return;
    const b = docRef.current.getBoundingClientRect();
    setDrawing(d => ({ ...d, x2:e.clientX-b.left, y2:e.clientY-b.top }));
  };
  const end = () => {
    if (!drawing) return;
    const dist = Math.hypot(drawing.x2-drawing.x1, drawing.y2-drawing.y1);
    if (dist < 6 && drawing.kind !== "del" && drawing.kind !== "pen" && drawing.kind !== "note")
      { setDrawing(null); return; }
    const cmd = resolve(drawing);
    setMarks(m => [...m, { ...drawing, id:`m${Date.now()}`, cmd, note:"" }]);
    setDrawing(null);
  };

  /* execute batch — zero-token actions run in code */
  const execute = () => {
    let bs = [...blocks];
    const done = [];
    marks.forEach(m => {
      const c = m.cmd;
      if (c.action === "move") {
        const i = bs.findIndex(b => b.id === c.targets[0]);
        if (i < 0) return;
        const [blk] = bs.splice(i, 1);
        let j = bs.findIndex(b => b.id === c.ref);
        if (j < 0) j = bs.length - 1;
        bs.splice(c.pos === "before" ? j : j + 1, 0, blk);
        done.push(c.chip);
      } else if (c.action === "delete") {
        bs = bs.filter(b => b.id !== c.targets[0]);
        done.push(c.chip);
      } else if (c.action === "insert") {
        const j = bs.findIndex(b => b.id === c.ref);
        const nb = { id:`n${Date.now()}`, sec:"—", type:"figure",
                     text: m.note || "[bilde — velg fra kilder]" };
        bs.splice(c.pos === "before" ? Math.max(j,0) : j + 1, 0, nb);
        done.push(`Satt inn figur (${c.anchor})`);
      } else if (c.action === "note" || c.action === "mark" || c.action === "group") {
        done.push(`${c.chip}${m.note ? `: «${m.note}»` : ""} → sendt til assistenten`);
      }
    });
    setBlocks(bs);
    setLog(l => [{ t:new Date().toLocaleTimeString().slice(0,5), items:done }, ...l]);
    setMarks([]);
  };

  const cost = marks.reduce((s, m) => s + (m.cmd.tokens || 0), 0);
  const S = { fontFamily:"'Archivo',system-ui,sans-serif" };

  return (
    <div style={{ ...S, display:"flex", height:"100vh", background:T.paper, color:T.ink }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800;900&family=IBM+Plex+Mono:wght@500;600&display=swap');
        *{box-sizing:border-box} button{font-family:inherit;cursor:pointer}
        .blk{position:relative;padding:7px 10px;border-radius:6px;border:2px solid transparent}
        .blk:hover{background:#FBFAF6}
        .selectable::selection{background:${T.signal}}
      `}</style>

      {/* TOOLS RAIL */}
      <aside style={{ width:132, borderRight:`1px solid ${T.line}`, padding:12, flexShrink:0 }}>
        <div style={{ fontSize:10, fontWeight:800, letterSpacing:".1em", color:T.steel, marginBottom:10 }}>TOOLS</div>
        {TOOLS.map(t => (
          <button key={t.id} onClick={() => setTool(t.id)}
            style={{ display:"flex", alignItems:"center", gap:8, width:"100%", marginBottom:5,
              padding:"7px 9px", borderRadius:7, fontSize:12.5, fontWeight:700, textAlign:"left",
              border:`1.5px solid ${tool===t.id?T.ink:T.line}`,
              background: tool===t.id ? T.signal : T.sheet }}>
            <span style={{ fontSize:14, width:16 }}>{t.icon}</span>{t.label}
          </button>
        ))}
        <button onClick={() => setMarks([])} disabled={!marks.length}
          style={{ width:"100%", marginTop:8, padding:"6px 9px", borderRadius:7, fontSize:11.5,
            fontWeight:700, border:`1px solid ${T.line}`, background:"transparent",
            color: marks.length ? T.ink : "#bbb" }}>↺ Tøm merker</button>
        <div style={{ marginTop:16, fontSize:10.5, color:T.steel, lineHeight:1.45 }}>
          Tegn på dokumentet. Hvert merke tolkes i kode til en kommando — ikke et bilde.
        </div>
      </aside>

      {/* DOCUMENT + OVERLAY */}
      <main style={{ flex:1, overflow:"auto", padding:"22px 26px", background:"#E9E7E0" }}>
        <div ref={docRef} onMouseDown={start} onMouseMove={move} onMouseUp={end}
          onMouseUp2={undefined}
          style={{ position:"relative", maxWidth:620, margin:"0 auto", background:T.sheet,
            borderRadius:4, boxShadow:"0 2px 14px rgba(20,22,28,.1)", padding:"34px 40px 46px",
            cursor: tool==="sel" ? "text" : "crosshair", userSelect: tool==="sel" ? "text" : "none" }}>
          {blocks.map(b => (
            <div key={b.id} data-block-id={b.id} className={`blk ${tool==="sel"?"selectable":""}`}
              onMouseUp={() => { if (tool==="sel") { const s=window.getSelection()?.toString(); if (s&&s.length>2) setSel({ block:b.id, text:s }); } }}>
              {b.type === "heading" && <h1 style={{ fontWeight:900, fontSize:23, margin:"2px 0 12px" }}>{b.text}</h1>}
              {b.type === "h2" && <h2 style={{ fontWeight:800, fontSize:14.5, borderBottom:`2px solid ${T.ink}`, paddingBottom:3, margin:"14px 0 8px" }}>{b.text}</h2>}
              {b.type === "prose" && <p style={{ fontSize:12.5, lineHeight:1.55, color:"#25282F" }}>{b.text}</p>}
              {b.type === "figure" && (
                <div style={{ border:`1.5px dashed ${T.fact}`, background:"#EAF1FD", borderRadius:6,
                  padding:"16px 12px", textAlign:"center", fontSize:11.5, color:T.fact, fontWeight:700 }}>
                  🖼 {b.text}</div>)}
              {b.type === "table" && (
                <table style={{ width:"100%", borderCollapse:"collapse", fontSize:11.5 }}><tbody>
                  {b.text.split("|").map((row,i) => {
                    const [k,v] = row.split("·");
                    return (<tr key={i} style={{ borderBottom:`1px solid ${T.line}` }}>
                      <td style={{ padding:"5px 0", color:T.steel, width:"52%" }}>{k?.trim()}</td>
                      <td style={{ fontFamily:"'IBM Plex Mono',monospace", color:T.fact }}>{v?.trim()}</td>
                    </tr>);})}
                </tbody></table>)}
            </div>
          ))}

          {/* SVG OVERLAY */}
          <svg style={{ position:"absolute", inset:0, pointerEvents:"none" }}>
            {[...marks, ...(drawing ? [{ ...drawing, id:"tmp", cmd:resolve(drawing) }] : [])].map(m => {
              const c = m.cmd || {};
              const col = c.action === "delete" ? T.gap : c.action === "unclear" ? "#999" : T.fact;
              if (m.kind === "arrow") {
                const mx = (m.x1 + m.x2) / 2;
                return (<g key={m.id}>
                  <path d={`M${m.x1},${m.y1} C${mx},${m.y1} ${mx},${m.y2} ${m.x2},${m.y2}`}
                    fill="none" stroke={col} strokeWidth="2.4" strokeDasharray="7,4"/>
                  <circle cx={m.x2} cy={m.y2} r="5" fill={col}/>
                </g>);
              }
              if (m.kind === "box" || m.kind === "note")
                return <rect key={m.id} x={Math.min(m.x1,m.x2)} y={Math.min(m.y1,m.y2)}
                  width={Math.abs(m.x2-m.x1)} height={Math.abs(m.y2-m.y1)} rx="5"
                  fill={`${col}14`} stroke={col} strokeWidth="2.2" strokeDasharray="6,4"/>;
              if (m.kind === "del")
                return (<g key={m.id} stroke={T.gap} strokeWidth="3">
                  <line x1={m.x1-11} y1={m.y1-11} x2={m.x1+11} y2={m.y1+11}/>
                  <line x1={m.x1+11} y1={m.y1-11} x2={m.x1-11} y2={m.y1+11}/></g>);
              return <line key={m.id} x1={m.x1} y1={m.y1} x2={m.x2} y2={m.y2}
                stroke={T.signal} strokeWidth="4" strokeLinecap="round"/>;
            })}
          </svg>

          {/* CHIPS — the resolved interpretation, shown before executing */}
          {marks.map(m => (
            <div key={`c${m.id}`} style={{ position:"absolute", left:Math.min(m.x1,m.x2),
              top:Math.min(m.y1,m.y2)-19, background:T.ink, color:"#fff", fontSize:10,
              fontWeight:700, padding:"2px 7px", borderRadius:5, whiteSpace:"nowrap" }}>
              {m.cmd.chip}{m.cmd.tokens ? ` · €${m.cmd.tokens.toFixed(3)}` : " · gratis"}
            </div>
          ))}
        </div>
      </main>

      {/* RIGHT PANEL */}
      <aside style={{ width:290, borderLeft:`1px solid ${T.line}`, background:T.sheet,
        display:"flex", flexDirection:"column", flexShrink:0 }}>
        <div style={{ padding:"10px 13px", borderBottom:`1px solid ${T.line}`, fontWeight:800, fontSize:12.5 }}>
          Merker ({marks.length})
        </div>
        <div style={{ flex:1, overflowY:"auto", padding:11 }}>
          {!marks.length && !sel && (
            <div style={{ fontSize:11.5, color:T.steel, lineHeight:1.5 }}>
              Velg et verktøy og tegn.<br/><br/>
              <b>Pil</b> fra en blokk til et sted = flytt.<br/>
              <b>✕</b> på en blokk = slett.<br/>
              <b>Boks</b> i tomt felt = sett inn her.<br/>
              <b>Notat</b> = fri instruksjon til assistenten.
            </div>)}
          {sel && (
            <div style={{ border:`1.5px solid ${T.signal}`, borderRadius:8, padding:10, marginBottom:10 }}>
              <div style={{ fontSize:10, fontWeight:800, color:T.steel, marginBottom:5 }}>VALGT TEKST</div>
              <div style={{ fontSize:11.5, fontStyle:"italic", marginBottom:8 }}>«{sel.text.slice(0,90)}…»</div>
              <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
                {["✎ Rediger","↻ Skriv om","🔗 Sitér kilde"].map(a => (
                  <button key={a} onClick={() => { setLog(l=>[{t:"nå",items:[`${a} på valgt tekst`]},...l]); setSel(null); }}
                    style={{ fontSize:10.5, fontWeight:700, padding:"4px 8px", borderRadius:5,
                      border:`1px solid ${T.line}`, background:T.paper }}>{a}</button>))}
              </div>
            </div>)}
          {marks.map((m,i) => (
            <div key={m.id} style={{ border:`1px solid ${T.line}`, borderRadius:8, padding:9, marginBottom:8 }}>
              <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:5 }}>
                <span style={{ fontSize:9.5, fontWeight:800, background:T.paper, borderRadius:4,
                  padding:"1px 6px", color:T.steel }}>{i+1}</span>
                <b style={{ fontSize:11.5 }}>{m.cmd.chip}</b>
              </div>
              <input value={m.note} placeholder="Notat (valgfritt)…"
                onChange={e => setMarks(ms => ms.map(x => x.id===m.id ? {...x, note:e.target.value} : x))}
                style={{ width:"100%", fontSize:11, padding:"5px 7px", borderRadius:5,
                  border:`1px solid ${T.line}`, background:T.paper, fontFamily:"inherit" }}/>
            </div>))}
        </div>
        <div style={{ padding:11, borderTop:`1px solid ${T.line}` }}>
          <button onClick={execute} disabled={!marks.length}
            style={{ width:"100%", padding:"11px", borderRadius:8, border:"none", fontWeight:900,
              fontSize:13, background: marks.length ? T.signal : "#E4E1D8",
              color: marks.length ? T.ink : T.steel }}>
            Utfør ({marks.length}) {cost > 0 ? `· €${cost.toFixed(3)}` : "· gratis"}
          </button>
          {log.length > 0 && (
            <div style={{ marginTop:10, maxHeight:120, overflowY:"auto" }}>
              {log.map((e,i) => (
                <div key={i} style={{ borderLeft:`3px solid ${T.ok}`, paddingLeft:7, marginBottom:6 }}>
                  <div style={{ fontSize:9, color:T.steel, fontFamily:"'IBM Plex Mono',monospace" }}>{e.t}</div>
                  {e.items.map((s,j) => <div key={j} style={{ fontSize:10.5 }}>{s}</div>)}
                </div>))}
            </div>)}
        </div>
      </aside>
    </div>
  );
}
