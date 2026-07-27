import React, { useState } from "react";

/* ────────────────────────────────────────────────────────────
   FOLDOK — UI prototype v3: THE EDITOR EXPERIENCE
   Working reference for EDITOR_SPEC + NAVIGATION_SPEC:
   · Explorer rail (collapsed by default in Bygg, expandable)
   · Selection model → block toolbar → regenerate with DIFF PREVIEW
   · MANGLER inline resolve → verified fact
   · Chat panel: scope = selection, proposals as accept/reject cards
   · Version history with revert · traceable-ink hover
   Norwegian only — i18n via STRINGS pattern from v2 when ported.
   ──────────────────────────────────────────────────────────── */

const T = {
  ink: "#16181D", paper: "#F2F0EA", sheet: "#FFFFFF", signal: "#F5C400",
  steel: "#5A6472", line: "#DCD9D0", ok: "#1E7A46", gap: "#C74E19",
  gapbg: "#FDF0E8", fact: "#1450B4", factbg: "#EAF1FD", card: "#FBFAF6",
};

const FILES = [
  { id: "f1", name: "IMG_2841.jpg", cap: "Løfteverktøy montert, sett forfra", hue: "#8a93a6", k: "IMG" },
  { id: "f2", name: "IMG_2844.jpg", cap: "Merkeskilt: SWL 3.2t, serienr.", hue: "#a6988a", k: "IMG" },
  { id: "f3", name: "lasttest_rapport.pdf", cap: "Lasttest 1.5 × SWL, EN 13155", hue: "#7d8c7a", k: "PDF" },
  { id: "f7", name: "vekt_dimensjoner.xlsx", cap: "Egenvekt 42 kg, mål, S355", hue: "#7a8c8a", k: "XLS" },
];
const FACTS = {
  swl: { v: "3,2 t", src: "f2" }, proof: { v: "4,8 t", src: "f3" },
  std: { v: "EN 13155", src: "f3" }, wt: { v: "42 kg", src: "f7" },
};

const Chip = ({ f, verified, onHover }) => (
  <span onMouseEnter={() => onHover(f.src)} onMouseLeave={() => onHover(null)}
    style={{ fontFamily: "'IBM Plex Mono',monospace", fontWeight: 600, fontSize: "0.9em",
      color: verified ? T.ok : T.fact, background: verified ? "#E8F5EC" : T.factbg,
      borderBottom: `2px solid ${verified ? T.ok : T.fact}`, padding: "0 3px", borderRadius: 2, cursor: "help" }}>
    {verified && "✓ "}{f.v}
  </span>
);

export default function FoldokEditorV3() {
  const [explorerOpen, setExplorerOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [hover, setHover] = useState(null);
  const [versions, setVersions] = useState([
    { t: "18:02", who: "AI", txt: "Genererte 9 seksjoner" },
  ]);
  const [drawer, setDrawer] = useState(false);
  const [pendingFolder, setPendingFolder] = useState(true);
  const [mangler, setMangler] = useState({ resolved: false, editing: false, val: "" });
  const [warnBlock, setWarnBlock] = useState({
    text: "Opphold under lasten kan medføre alvorlig personskade eller død. Sperr av området før løft.",
    diff: null,
  });
  const [chat, setChat] = useState([
    { who: "ai", txt: "Hei! Velg en blokk og be meg om endringer — eller spør hva som mangler." },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [turns, setTurns] = useState(3);

  const gapsLeft = mangler.resolved ? 0 : 1;
  const lit = hover ? new Set([hover]) : null;

  const logV = (who, txt) => setVersions(v => [{ t: "18:" + (10 + v.length), who, txt }, ...v]);

  /* block toolbar action: regenerate → diff preview */
  const regenWarn = () => setWarnBlock(b => ({ ...b, diff:
    "FARE — Hengende last. Opphold under hengende last er forbudt og kan medføre livstruende klemskader. Sperr av sonen med fysisk sperring før løftet starter, og bruk banksmann." }));
  const acceptDiff = () => { setWarnBlock(b => ({ text: b.diff, diff: null })); logV("AI", "Advarsel omskrevet (strengere)"); };
  const rejectDiff = () => setWarnBlock(b => ({ ...b, diff: null }));

  /* mangler resolve */
  const saveMangler = () => {
    if (!mangler.val.trim()) return;
    setMangler({ resolved: true, editing: false, val: mangler.val });
    logV("Bruker", `Oppga inspeksjonsintervall: ${mangler.val} (verifisert manuelt)`);
  };

  /* chat */
  const send = () => {
    if (!chatInput.trim() || turns >= 20) return;
    const q = chatInput; setChatInput("");
    setChat(c => [...c, { who: "user", txt: q }]);
    setTurns(t => t + 1);
    setTimeout(() => {
      if (/mangl/i.test(q)) {
        setChat(c => [...c, { who: "ai", txt: gapsLeft
          ? "1 blokkerende mangel: inspeksjonsintervall for sakkyndig kontroll finnes ikke i kildene (seksjon 8). Klikk på MANGLER-feltet for å oppgi verdien. (Svar fra mangelregisteret — 0 tokens.)"
          : "Ingen blokkerende mangler — dokumentet er klart for eksport. (0 tokens.)" }]);
      } else {
        setChat(c => [...c, { who: "ai", proposal: true,
          txt: "Forslag til seksjon 7, punkt 4 — mer presist språk:" }]);
      }
    }, 350);
  };
  const acceptProposal = i => {
    setChat(c => c.map((m, ix) => ix === i ? { ...m, accepted: true } : m));
    logV("Chat", "Punkt 4 presisert (akseptert forslag)");
  };

  const S = { fontFamily: "'Archivo',sans-serif" };
  const label = { fontSize: 10, fontWeight: 800, letterSpacing: ".1em", color: T.steel };

  return (
    <div style={{ ...S, height: "100vh", display: "flex", flexDirection: "column", background: T.paper, color: T.ink }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800;900&family=IBM+Plex+Mono:wght@500;600;700&display=swap');
        *{box-sizing:border-box} button{font-family:'Archivo',sans-serif;cursor:pointer}
        .blk{position:relative;padding:6px 10px;margin:0 -10px;border-radius:6px;border:2px solid transparent}
        .blk:hover{background:${T.card}}
        .blk.sel{border-color:${T.signal};background:#FFFDF2}
        .bar{position:absolute;top:-15px;right:6px;display:none;gap:4px;background:${T.ink};border-radius:6px;padding:4px 6px;z-index:5}
        .blk.sel .bar{display:flex}
        .bar span{font-size:10.5px;color:#fff;font-weight:600;padding:2px 8px;border-radius:3px}
        .bar span:hover{background:#ffffff22}
        .srcf.lit{background:#FFF6CE!important;border-color:${T.signal}!important;box-shadow:0 0 0 2px ${T.signal}}
        .dim .srcf:not(.lit){opacity:.35}
      `}</style>

      {/* HEADER */}
      <header style={{ display: "flex", alignItems: "center", gap: 14, height: 52, padding: "0 14px", background: T.ink, color: "#fff", flexShrink: 0 }}>
        <button onClick={() => setExplorerOpen(o => !o)} title="Prosjektutforsker"
          style={{ width: 30, height: 30, borderRadius: 6, border: "1px solid #ffffff33", background: explorerOpen ? T.signal : "transparent", color: explorerOpen ? T.ink : "#fff", fontWeight: 900 }}>☰</button>
        <span style={{ width: 22, height: 22, background: T.signal, borderRadius: 4, display: "inline-flex", alignItems: "center", justifyContent: "center", color: T.ink, fontWeight: 900, fontSize: 13 }}>F</span>
        <span style={{ fontWeight: 900, fontSize: 14 }}>FOLDOK</span>
        <span style={{ fontSize: 12.5, color: "#ffffff88" }}>Batteripakke løfteverktøy · Teknisk dok.pakke</span>
        <span style={{ marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: T.signal }}>€0,52 brukt</span>
        <button onClick={() => setDrawer(d => !d)} style={{ fontSize: 11.5, fontWeight: 700, padding: "6px 12px", borderRadius: 6, border: "1px solid #ffffff33", background: "transparent", color: "#fff" }}>
          Historikk ({versions.length})
        </button>
      </header>

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>

        {/* EXPLORER RAIL */}
        <aside style={{ width: explorerOpen ? 240 : 0, transition: "width .18s ease", overflow: "hidden", background: T.paper, borderRight: explorerOpen ? `1px solid ${T.line}` : "none", flexShrink: 0 }}>
          <div style={{ width: 240, padding: 12 }}>
            <button style={{ width: "100%", textAlign: "left", background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 8, padding: "9px 12px", fontWeight: 800, fontSize: 13 }}>
              Batteripakke løfteverktøy ▾
            </button>
            <div style={{ ...label, margin: "16px 0 8px", display: "flex", justifyContent: "space-between" }}>
              <span>KILDER</span><span style={{ color: T.fact, cursor: "pointer" }}>+ Koble til</span>
            </div>
            {[
              { n: "Feltbilder", s: "✓ 34 indeksert", ic: "📁" },
              { n: "Testrapporter", s: "✓ 6 indeksert", ic: "📁" },
            ].map(f => (
              <div key={f.n} style={{ background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 6, padding: "8px 10px", marginBottom: 6, fontSize: 12.5 }}>
                {f.ic} <b>{f.n}</b>
                <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.ok, marginTop: 2 }}>{f.s}</div>
              </div>
            ))}
            <div style={{ background: T.sheet, border: `1px solid ${pendingFolder ? T.signal : T.line}`, borderRadius: 6, padding: "8px 10px", marginBottom: 6, fontSize: 12.5 }}>
              📁 <b>Leverandørdok</b>
              {pendingFolder ? (
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                  <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: "#8a6d00" }}>⏳ 12 venter · ~€0,15</span>
                  <button onClick={() => { setPendingFolder(false); logV("System", "Indekserte 12 filer i Leverandørdok (€0,14)"); }}
                    style={{ fontSize: 10, fontWeight: 800, background: T.signal, border: "none", borderRadius: 4, padding: "2px 8px" }}>Indekser</button>
                </div>
              ) : <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.ok, marginTop: 2 }}>✓ 12 indeksert</div>}
            </div>
            <div style={{ ...label, margin: "16px 0 8px", display: "flex", justifyContent: "space-between" }}>
              <span>DOKUMENTER</span><span style={{ color: T.fact, cursor: "pointer" }}>+ Nytt</span>
            </div>
            <div style={{ background: "#FFFDF2", border: `1.5px solid ${T.signal}`, borderRadius: 6, padding: "8px 10px", marginBottom: 6, fontSize: 12.5 }}>
              📄 <b>Teknisk dok.pakke</b>
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: gapsLeft ? T.gap : T.ok, marginTop: 2 }}>
                {gapsLeft ? "● Utkast · 1 mangel" : "● Utkast · klar"}
              </div>
            </div>
            <div style={{ background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 6, padding: "8px 10px", fontSize: 12.5 }}>
              📄 Samsvarserklæring
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.ok, marginTop: 2 }}>✓ Eksportert · rev A</div>
            </div>
          </div>
        </aside>

        {/* SOURCES */}
        <aside className={hover ? "dim" : ""} style={{ width: 230, borderRight: `1px solid ${T.line}`, padding: 12, overflowY: "auto", flexShrink: 0 }}>
          <div style={{ ...label, marginBottom: 8 }}>KILDER I DOKUMENTET</div>
          {FILES.map(f => (
            <div key={f.id} className={`srcf ${lit?.has(f.id) ? "lit" : ""}`}
              style={{ display: "flex", gap: 8, background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 6, padding: 8, marginBottom: 7, transition: "all .15s", fontSize: 11 }}>
              <span style={{ width: 34, height: 34, borderRadius: 4, flexShrink: 0, background: `linear-gradient(135deg,${f.hue},${f.hue}66)`, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'IBM Plex Mono',monospace", fontSize: 8, fontWeight: 700 }}>{f.k}</span>
              <span><b style={{ fontSize: 11.5 }}>{f.name}</b><br /><span style={{ color: T.steel }}>{f.cap}</span></span>
            </div>
          ))}
        </aside>

        {/* DOCUMENT CANVAS */}
        <main onClick={() => setSelected(null)} style={{ flex: 1, overflowY: "auto", background: "#E9E7E0", padding: "24px 28px" }}>
          <div style={{ maxWidth: 620, margin: "0 auto", background: T.sheet, borderRadius: 4, boxShadow: "0 2px 14px rgba(20,22,28,.1)", padding: "38px 46px 50px" }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.steel }}>TEKNISK DOKUMENTASJONSPAKKE · REV A · UTKAST</div>
            <h1 style={{ fontWeight: 900, fontSize: 26, margin: "6px 0 20px" }}>Løfteverktøy for batteripakke</h1>

            {/* TABLE BLOCK */}
            <h2 style={{ fontWeight: 800, fontSize: 15, borderBottom: `2px solid ${T.ink}`, paddingBottom: 4, margin: "18px 0 10px" }}>4 · Tekniske data</h2>
            <div className={`blk ${selected === "tbl" ? "sel" : ""}`} onClick={e => { e.stopPropagation(); setSelected("tbl"); }}>
              <div className="bar"><span>↻ Regenerer</span><span>⌫ Tilbakestill</span></div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <tbody>
                  {[["Sikker arbeidslast (SWL)", FACTS.swl], ["Prøvelast", FACTS.proof], ["Egenvekt", FACTS.wt], ["Teststandard", FACTS.std]].map(([k, f]) => (
                    <tr key={k} style={{ borderBottom: `1px solid ${T.line}` }}>
                      <td style={{ padding: "6px 0", color: T.steel, width: "55%" }}>{k}</td>
                      <td><Chip f={f} onHover={setHover} /></td>
                    </tr>
                  ))}
                  <tr style={{ borderBottom: `1px solid ${T.line}` }}>
                    <td style={{ padding: "6px 0", color: T.steel }}>Sakkyndig kontroll, intervall</td>
                    <td onClick={e => e.stopPropagation()}>
                      {mangler.resolved ? <Chip f={{ v: mangler.val, src: "f2" }} verified onHover={setHover} />
                        : mangler.editing ? (
                          <span style={{ display: "inline-flex", gap: 5 }}>
                            <input autoFocus value={mangler.val} onChange={e => setMangler(m => ({ ...m, val: e.target.value }))}
                              onKeyDown={e => e.key === "Enter" && saveMangler()} placeholder="f.eks. 12 mnd"
                              style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, padding: "2px 6px", border: `1.5px solid ${T.gap}`, borderRadius: 4, width: 90 }} />
                            <button onClick={saveMangler} style={{ fontSize: 10.5, fontWeight: 800, background: T.ink, color: "#fff", border: "none", borderRadius: 4, padding: "2px 9px" }}>Lagre</button>
                          </span>
                        ) : (
                          <button onClick={() => setMangler(m => ({ ...m, editing: true }))} title="Klikk for å oppgi verdi"
                            style={{ fontFamily: "'IBM Plex Mono',monospace", fontWeight: 700, fontSize: 10.5, color: T.gap, background: T.gapbg, border: `1.5px dashed ${T.gap}`, padding: "2px 8px", borderRadius: 4 }}>
                            MANGLER: intervall — oppgi
                          </button>
                        )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* WARNING BLOCK with diff preview */}
            <h2 style={{ fontWeight: 800, fontSize: 15, borderBottom: `2px solid ${T.ink}`, paddingBottom: 4, margin: "24px 0 10px" }}>7 · Bruk / drift</h2>
            <div className={`blk ${selected === "warn" ? "sel" : ""}`} onClick={e => { e.stopPropagation(); setSelected("warn"); }}>
              <div className="bar"><span onClick={e => { e.stopPropagation(); regenWarn(); }}>↻ Strengere</span><span>✂ Kort ned</span><span>⌫ Tilbakestill</span></div>
              {!warnBlock.diff ? (
                <div style={{ background: "#FFF8E0", border: `1px solid ${T.signal}`, borderLeft: `5px solid ${T.signal}`, borderRadius: 4, padding: "9px 13px", fontSize: 12.5 }}>
                  <b>⚠ ADVARSEL — Hengende last.</b> {warnBlock.text}
                </div>
              ) : (
                <div onClick={e => e.stopPropagation()} style={{ border: `1.5px solid ${T.fact}`, borderRadius: 6, overflow: "hidden" }}>
                  <div style={{ padding: "8px 13px", fontSize: 12, background: "#F6F5F1", color: T.steel, textDecoration: "line-through" }}>⚠ ADVARSEL — Hengende last. {warnBlock.text}</div>
                  <div style={{ padding: "9px 13px", fontSize: 12.5, background: T.factbg }}><b>⚠ {warnBlock.diff.split(".")[0]}.</b>{warnBlock.diff.substring(warnBlock.diff.indexOf(".") + 1)}</div>
                  <div style={{ display: "flex", gap: 8, padding: "8px 13px", background: T.sheet, borderTop: `1px solid ${T.line}` }}>
                    <button onClick={acceptDiff} style={{ fontSize: 11.5, fontWeight: 800, background: T.ok, color: "#fff", border: "none", borderRadius: 5, padding: "5px 14px" }}>✓ Godta</button>
                    <button onClick={rejectDiff} style={{ fontSize: 11.5, fontWeight: 700, background: "transparent", color: T.steel, border: `1px solid ${T.line}`, borderRadius: 5, padding: "5px 14px" }}>Forkast</button>
                    <span style={{ marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.steel, alignSelf: "center" }}>forhåndsvisning — ingenting er endret ennå</span>
                  </div>
                </div>
              )}
            </div>

            <div className={`blk ${selected === "steps" ? "sel" : ""}`} onClick={e => { e.stopPropagation(); setSelected("steps"); }} style={{ marginTop: 10 }}>
              <div className="bar"><span>↻ Regenerer</span><span>✂ Kort ned</span></div>
              <ol style={{ fontSize: 13, lineHeight: 1.7, paddingLeft: 20, margin: 0 }}>
                <li>Kontroller verktøyet visuelt før bruk.</li>
                <li>Fest alle fire sjakler til løfteørene. Kontroller splinter.</li>
                <li>Løft lasten maks 100 mm og kontroller balanse.</li>
                <li>Løft aldri mer enn <Chip f={FACTS.swl} onHover={setHover} />.</li>
              </ol>
            </div>
          </div>
        </main>

        {/* CHAT PANEL */}
        <aside style={{ width: 290, borderLeft: `1px solid ${T.line}`, background: T.sheet, display: "flex", flexDirection: "column", flexShrink: 0 }}>
          <div style={{ padding: "10px 14px", borderBottom: `1px solid ${T.line}`, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontWeight: 800, fontSize: 12.5 }}>Assistent</span>
            <span style={{ marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, background: T.paper, border: `1px solid ${T.line}`, borderRadius: 99, padding: "2px 9px", color: T.steel }}>
              {selected ? `Blokk: ${selected === "tbl" ? "Tekniske data" : selected === "warn" ? "Advarsel" : "Bruk pkt. 1–4"}` : "Hele dokumentet"}
            </span>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
            {chat.map((m, i) => (
              <div key={i} style={{ alignSelf: m.who === "user" ? "flex-end" : "flex-start", maxWidth: "92%" }}>
                <div style={{ fontSize: 12, lineHeight: 1.5, padding: "8px 11px", borderRadius: 10,
                  background: m.who === "user" ? T.ink : T.paper, color: m.who === "user" ? "#fff" : T.ink }}>
                  {m.txt}
                </div>
                {m.proposal && (
                  <div style={{ marginTop: 6, border: `1.5px solid ${T.fact}`, borderRadius: 8, overflow: "hidden", fontSize: 11.5 }}>
                    <div style={{ padding: "6px 10px", background: "#F6F5F1", color: T.steel, textDecoration: "line-through" }}>Løft aldri mer enn 3,2 t.</div>
                    <div style={{ padding: "7px 10px", background: T.factbg }}>Overskrid aldri sikker arbeidslast på <b>3,2 t</b> — vurder lastens faktiske vekt mot merkeskiltet før hvert løft.</div>
                    {!m.accepted ? (
                      <div style={{ display: "flex", gap: 6, padding: "6px 10px", borderTop: `1px solid ${T.line}` }}>
                        <button onClick={() => acceptProposal(i)} style={{ fontSize: 10.5, fontWeight: 800, background: T.ok, color: "#fff", border: "none", borderRadius: 4, padding: "3px 10px" }}>✓ Godta</button>
                        <button style={{ fontSize: 10.5, fontWeight: 700, background: "transparent", color: T.steel, border: `1px solid ${T.line}`, borderRadius: 4, padding: "3px 10px" }}>Forkast</button>
                      </div>
                    ) : <div style={{ padding: "5px 10px", fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, color: T.ok, borderTop: `1px solid ${T.line}` }}>✓ Godtatt · ny versjon opprettet</div>}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div style={{ padding: 10, borderTop: `1px solid ${T.line}` }}>
            <div style={{ display: "flex", gap: 6 }}>
              <input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()}
                placeholder='Prøv: "hva mangler?"'
                style={{ flex: 1, fontFamily: "'Archivo',sans-serif", fontSize: 12, padding: "8px 10px", border: `1px solid ${T.line}`, borderRadius: 7, background: T.paper }} />
              <button onClick={send} style={{ fontWeight: 900, background: T.signal, border: "none", borderRadius: 7, padding: "0 13px" }}>→</button>
            </div>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, color: T.steel, marginTop: 6 }}>{turns} / 20 samtaleturer · 6 / 30 regenereringer</div>
          </div>
        </aside>

        {/* VERSION DRAWER */}
        {drawer && (
          <aside style={{ position: "absolute", right: 0, top: 52, bottom: 40, width: 290, background: T.sheet, borderLeft: `2px solid ${T.ink}`, boxShadow: "-8px 0 24px rgba(0,0,0,.12)", zIndex: 20, padding: 14, overflowY: "auto" }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
              <b style={{ fontSize: 13 }}>Versjonshistorikk</b>
              <button onClick={() => setDrawer(false)} style={{ marginLeft: "auto", border: "none", background: "none", fontSize: 16 }}>×</button>
            </div>
            {versions.map((v, i) => (
              <div key={i} style={{ borderLeft: `3px solid ${v.who === "Bruker" ? T.ok : v.who === "Chat" ? T.fact : T.signal}`, padding: "6px 10px", marginBottom: 8, background: T.card, borderRadius: "0 6px 6px 0" }}>
                <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, color: T.steel }}>{v.t} · {v.who}</div>
                <div style={{ fontSize: 12 }}>{v.txt}</div>
                {i === 0 && versions.length > 1 && <button style={{ fontSize: 10, fontWeight: 700, marginTop: 4, background: "transparent", border: `1px solid ${T.line}`, borderRadius: 4, padding: "2px 8px", color: T.steel }}>↩ Tilbakestill</button>}
              </div>
            ))}
          </aside>
        )}
      </div>

      {/* FOOTER */}
      <footer style={{ display: "flex", alignItems: "center", gap: 16, height: 40, padding: "0 16px", background: T.sheet, borderTop: `1px solid ${T.line}`, flexShrink: 0, fontSize: 12 }}>
        <span><b style={{ color: T.ok }}>{mangler.resolved ? 5 : 4} fakta sitert</b> · alle sporbare</span>
        <span style={{ color: gapsLeft ? T.gap : T.ok, fontWeight: 700 }}>{gapsLeft ? "● 1 blokkerende mangel" : "✓ Ingen mangler"}</span>
        <span style={{ marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 10.5, color: T.steel }}>klikk en blokk · hover et tall · prøv chatten</span>
        <button disabled={!!gapsLeft} style={{ fontWeight: 800, fontSize: 12, background: gapsLeft ? "#E4E1D8" : T.signal, color: gapsLeft ? T.steel : T.ink, border: "none", borderRadius: 6, padding: "7px 16px", cursor: gapsLeft ? "not-allowed" : "pointer" }}>
        Eksporter PDF · €19</button>
      </footer>
    </div>
  );
}
