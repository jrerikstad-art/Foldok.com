const { useState } = React;
const T = {
  ink: "#16181D",
  paper: "#F2F0EA",
  sheet: "#FFFFFF",
  signal: "#F5C400",
  steel: "#5A6472",
  line: "#DCD9D0",
  ok: "#1E7A46",
  gap: "#C74E19",
  gapbg: "#FDF0E8",
  fact: "#1450B4",
  factbg: "#EAF1FD",
  card: "#FBFAF6"
};
const FILES = [
  { id: "f1", name: "IMG_2841.jpg", cap: "L\xF8fteverkt\xF8y montert, sett forfra", hue: "#8a93a6", k: "IMG" },
  { id: "f2", name: "IMG_2844.jpg", cap: "Merkeskilt: SWL 3.2t, serienr.", hue: "#a6988a", k: "IMG" },
  { id: "f3", name: "lasttest_rapport.pdf", cap: "Lasttest 1.5 \xD7 SWL, EN 13155", hue: "#7d8c7a", k: "PDF" },
  { id: "f7", name: "vekt_dimensjoner.xlsx", cap: "Egenvekt 42 kg, m\xE5l, S355", hue: "#7a8c8a", k: "XLS" }
];
const FACTS = {
  swl: { v: "3,2 t", src: "f2" },
  proof: { v: "4,8 t", src: "f3" },
  std: { v: "EN 13155", src: "f3" },
  wt: { v: "42 kg", src: "f7" }
};
const Chip = ({ f, verified, onHover }) => /* @__PURE__ */ React.createElement(
  "span",
  {
    onMouseEnter: () => onHover(f.src),
    onMouseLeave: () => onHover(null),
    style: {
      fontFamily: "'IBM Plex Mono',monospace",
      fontWeight: 600,
      fontSize: "0.9em",
      color: verified ? T.ok : T.fact,
      background: verified ? "#E8F5EC" : T.factbg,
      borderBottom: `2px solid ${verified ? T.ok : T.fact}`,
      padding: "0 3px",
      borderRadius: 2,
      cursor: "help"
    }
  },
  verified && "\u2713 ",
  f.v
);
window.FoldokEditorV3 = function FoldokEditorV3() {
  const [explorerOpen, setExplorerOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [hover, setHover] = useState(null);
  const [versions, setVersions] = useState([
    { t: "18:02", who: "AI", txt: "Genererte 9 seksjoner" }
  ]);
  const [drawer, setDrawer] = useState(false);
  const [pendingFolder, setPendingFolder] = useState(true);
  const [mangler, setMangler] = useState({ resolved: false, editing: false, val: "" });
  const [warnBlock, setWarnBlock] = useState({
    text: "Opphold under lasten kan medf\xF8re alvorlig personskade eller d\xF8d. Sperr av omr\xE5det f\xF8r l\xF8ft.",
    diff: null
  });
  const [chat, setChat] = useState([
    { who: "ai", txt: "Hei! Velg en blokk og be meg om endringer \u2014 eller sp\xF8r hva som mangler." }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [turns, setTurns] = useState(3);
  const gapsLeft = mangler.resolved ? 0 : 1;
  const lit = hover ? /* @__PURE__ */ new Set([hover]) : null;
  const logV = (who, txt) => setVersions((v) => [{ t: "18:" + (10 + v.length), who, txt }, ...v]);
  const regenWarn = () => setWarnBlock((b) => ({ ...b, diff: "FARE \u2014 Hengende last. Opphold under hengende last er forbudt og kan medf\xF8re livstruende klemskader. Sperr av sonen med fysisk sperring f\xF8r l\xF8ftet starter, og bruk banksmann." }));
  const acceptDiff = () => {
    setWarnBlock((b) => ({ text: b.diff, diff: null }));
    logV("AI", "Advarsel omskrevet (strengere)");
  };
  const rejectDiff = () => setWarnBlock((b) => ({ ...b, diff: null }));
  const saveMangler = () => {
    if (!mangler.val.trim()) return;
    setMangler({ resolved: true, editing: false, val: mangler.val });
    logV("Bruker", `Oppga inspeksjonsintervall: ${mangler.val} (verifisert manuelt)`);
  };
  const send = () => {
    if (!chatInput.trim() || turns >= 20) return;
    const q = chatInput;
    setChatInput("");
    setChat((c) => [...c, { who: "user", txt: q }]);
    setTurns((t) => t + 1);
    setTimeout(() => {
      if (/mangl/i.test(q)) {
        setChat((c) => [...c, { who: "ai", txt: gapsLeft ? "1 blokkerende mangel: inspeksjonsintervall for sakkyndig kontroll finnes ikke i kildene (seksjon 8). Klikk p\xE5 MANGLER-feltet for \xE5 oppgi verdien. (Svar fra mangelregisteret \u2014 0 tokens.)" : "Ingen blokkerende mangler \u2014 dokumentet er klart for eksport. (0 tokens.)" }]);
      } else {
        setChat((c) => [...c, {
          who: "ai",
          proposal: true,
          txt: "Forslag til seksjon 7, punkt 4 \u2014 mer presist spr\xE5k:"
        }]);
      }
    }, 350);
  };
  const acceptProposal = (i) => {
    setChat((c) => c.map((m, ix) => ix === i ? { ...m, accepted: true } : m));
    logV("Chat", "Punkt 4 presisert (akseptert forslag)");
  };
  const S = { fontFamily: "'Archivo',sans-serif" };
  const label = { fontSize: 10, fontWeight: 800, letterSpacing: ".1em", color: T.steel };
  return /* @__PURE__ */ React.createElement("div", { style: { ...S, height: "100vh", display: "flex", flexDirection: "column", background: T.paper, color: T.ink } }, /* @__PURE__ */ React.createElement("style", null, `
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
      `), /* @__PURE__ */ React.createElement("header", { style: { display: "flex", alignItems: "center", gap: 14, height: 52, padding: "0 14px", background: T.ink, color: "#fff", flexShrink: 0 } }, /* @__PURE__ */ React.createElement(
    "button",
    {
      onClick: () => setExplorerOpen((o) => !o),
      title: "Prosjektutforsker",
      style: { width: 30, height: 30, borderRadius: 6, border: "1px solid #ffffff33", background: explorerOpen ? T.signal : "transparent", color: explorerOpen ? T.ink : "#fff", fontWeight: 900 }
    },
    "\u2630"
  ), /* @__PURE__ */ React.createElement("span", { style: { width: 22, height: 22, background: T.signal, borderRadius: 4, display: "inline-flex", alignItems: "center", justifyContent: "center", color: T.ink, fontWeight: 900, fontSize: 13 } }, "F"), /* @__PURE__ */ React.createElement("span", { style: { fontWeight: 900, fontSize: 14 } }, "FOLDOK"), /* @__PURE__ */ React.createElement("span", { style: { fontSize: 12.5, color: "#ffffff88" } }, "Batteripakke l\xF8fteverkt\xF8y \xB7 Teknisk dok.pakke"), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: T.signal } }, "\u20AC0,52 brukt"), /* @__PURE__ */ React.createElement("button", { onClick: () => setDrawer((d) => !d), style: { fontSize: 11.5, fontWeight: 700, padding: "6px 12px", borderRadius: 6, border: "1px solid #ffffff33", background: "transparent", color: "#fff" } }, "Historikk (", versions.length, ")")), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, display: "flex", minHeight: 0 } }, /* @__PURE__ */ React.createElement("aside", { style: { width: explorerOpen ? 240 : 0, transition: "width .18s ease", overflow: "hidden", background: T.paper, borderRight: explorerOpen ? `1px solid ${T.line}` : "none", flexShrink: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { width: 240, padding: 12 } }, /* @__PURE__ */ React.createElement("button", { style: { width: "100%", textAlign: "left", background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 8, padding: "9px 12px", fontWeight: 800, fontSize: 13 } }, "Batteripakke l\xF8fteverkt\xF8y \u25BE"), /* @__PURE__ */ React.createElement("div", { style: { ...label, margin: "16px 0 8px", display: "flex", justifyContent: "space-between" } }, /* @__PURE__ */ React.createElement("span", null, "KILDER"), /* @__PURE__ */ React.createElement("span", { style: { color: T.fact, cursor: "pointer" } }, "+ Koble til")), [
    { n: "Feltbilder", s: "\u2713 34 indeksert", ic: "\u{1F4C1}" },
    { n: "Testrapporter", s: "\u2713 6 indeksert", ic: "\u{1F4C1}" }
  ].map((f) => /* @__PURE__ */ React.createElement("div", { key: f.n, style: { background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 6, padding: "8px 10px", marginBottom: 6, fontSize: 12.5 } }, f.ic, " ", /* @__PURE__ */ React.createElement("b", null, f.n), /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.ok, marginTop: 2 } }, f.s))), /* @__PURE__ */ React.createElement("div", { style: { background: T.sheet, border: `1px solid ${pendingFolder ? T.signal : T.line}`, borderRadius: 6, padding: "8px 10px", marginBottom: 6, fontSize: 12.5 } }, "\u{1F4C1} ", /* @__PURE__ */ React.createElement("b", null, "Leverand\xF8rdok"), pendingFolder ? /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6, marginTop: 4 } }, /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: "#8a6d00" } }, "\u23F3 12 venter \xB7 ~\u20AC0,15"), /* @__PURE__ */ React.createElement(
    "button",
    {
      onClick: () => {
        setPendingFolder(false);
        logV("System", "Indekserte 12 filer i Leverand\xF8rdok (\u20AC0,14)");
      },
      style: { fontSize: 10, fontWeight: 800, background: T.signal, border: "none", borderRadius: 4, padding: "2px 8px" }
    },
    "Indekser"
  )) : /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.ok, marginTop: 2 } }, "\u2713 12 indeksert")), /* @__PURE__ */ React.createElement("div", { style: { ...label, margin: "16px 0 8px", display: "flex", justifyContent: "space-between" } }, /* @__PURE__ */ React.createElement("span", null, "DOKUMENTER"), /* @__PURE__ */ React.createElement("span", { style: { color: T.fact, cursor: "pointer" } }, "+ Nytt")), /* @__PURE__ */ React.createElement("div", { style: { background: "#FFFDF2", border: `1.5px solid ${T.signal}`, borderRadius: 6, padding: "8px 10px", marginBottom: 6, fontSize: 12.5 } }, "\u{1F4C4} ", /* @__PURE__ */ React.createElement("b", null, "Teknisk dok.pakke"), /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: gapsLeft ? T.gap : T.ok, marginTop: 2 } }, gapsLeft ? "\u25CF Utkast \xB7 1 mangel" : "\u25CF Utkast \xB7 klar")), /* @__PURE__ */ React.createElement("div", { style: { background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 6, padding: "8px 10px", fontSize: 12.5 } }, "\u{1F4C4} Samsvarserkl\xE6ring", /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.ok, marginTop: 2 } }, "\u2713 Eksportert \xB7 rev A")))), /* @__PURE__ */ React.createElement("aside", { className: hover ? "dim" : "", style: { width: 230, borderRight: `1px solid ${T.line}`, padding: 12, overflowY: "auto", flexShrink: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { ...label, marginBottom: 8 } }, "KILDER I DOKUMENTET"), FILES.map((f) => /* @__PURE__ */ React.createElement(
    "div",
    {
      key: f.id,
      className: `srcf ${lit?.has(f.id) ? "lit" : ""}`,
      style: { display: "flex", gap: 8, background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 6, padding: 8, marginBottom: 7, transition: "all .15s", fontSize: 11 }
    },
    /* @__PURE__ */ React.createElement("span", { style: { width: 34, height: 34, borderRadius: 4, flexShrink: 0, background: `linear-gradient(135deg,${f.hue},${f.hue}66)`, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'IBM Plex Mono',monospace", fontSize: 8, fontWeight: 700 } }, f.k),
    /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", { style: { fontSize: 11.5 } }, f.name), /* @__PURE__ */ React.createElement("br", null), /* @__PURE__ */ React.createElement("span", { style: { color: T.steel } }, f.cap))
  ))), /* @__PURE__ */ React.createElement("main", { onClick: () => setSelected(null), style: { flex: 1, overflowY: "auto", background: "#E9E7E0", padding: "24px 28px" } }, /* @__PURE__ */ React.createElement("div", { style: { maxWidth: 620, margin: "0 auto", background: T.sheet, borderRadius: 4, boxShadow: "0 2px 14px rgba(20,22,28,.1)", padding: "38px 46px 50px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.steel } }, "TEKNISK DOKUMENTASJONSPAKKE \xB7 REV A \xB7 UTKAST"), /* @__PURE__ */ React.createElement("h1", { style: { fontWeight: 900, fontSize: 26, margin: "6px 0 20px" } }, "L\xF8fteverkt\xF8y for batteripakke"), /* @__PURE__ */ React.createElement("h2", { style: { fontWeight: 800, fontSize: 15, borderBottom: `2px solid ${T.ink}`, paddingBottom: 4, margin: "18px 0 10px" } }, "4 \xB7 Tekniske data"), /* @__PURE__ */ React.createElement("div", { className: `blk ${selected === "tbl" ? "sel" : ""}`, onClick: (e) => {
    e.stopPropagation();
    setSelected("tbl");
  } }, /* @__PURE__ */ React.createElement("div", { className: "bar" }, /* @__PURE__ */ React.createElement("span", null, "\u21BB Regenerer"), /* @__PURE__ */ React.createElement("span", null, "\u232B Tilbakestill")), /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 13 } }, /* @__PURE__ */ React.createElement("tbody", null, [["Sikker arbeidslast (SWL)", FACTS.swl], ["Pr\xF8velast", FACTS.proof], ["Egenvekt", FACTS.wt], ["Teststandard", FACTS.std]].map(([k, f]) => /* @__PURE__ */ React.createElement("tr", { key: k, style: { borderBottom: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 0", color: T.steel, width: "55%" } }, k), /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement(Chip, { f, onHover: setHover })))), /* @__PURE__ */ React.createElement("tr", { style: { borderBottom: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 0", color: T.steel } }, "Sakkyndig kontroll, intervall"), /* @__PURE__ */ React.createElement("td", { onClick: (e) => e.stopPropagation() }, mangler.resolved ? /* @__PURE__ */ React.createElement(Chip, { f: { v: mangler.val, src: "f2" }, verified: true, onHover: setHover }) : mangler.editing ? /* @__PURE__ */ React.createElement("span", { style: { display: "inline-flex", gap: 5 } }, /* @__PURE__ */ React.createElement(
    "input",
    {
      autoFocus: true,
      value: mangler.val,
      onChange: (e) => setMangler((m) => ({ ...m, val: e.target.value })),
      onKeyDown: (e) => e.key === "Enter" && saveMangler(),
      placeholder: "f.eks. 12 mnd",
      style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, padding: "2px 6px", border: `1.5px solid ${T.gap}`, borderRadius: 4, width: 90 }
    }
  ), /* @__PURE__ */ React.createElement("button", { onClick: saveMangler, style: { fontSize: 10.5, fontWeight: 800, background: T.ink, color: "#fff", border: "none", borderRadius: 4, padding: "2px 9px" } }, "Lagre")) : /* @__PURE__ */ React.createElement(
    "button",
    {
      onClick: () => setMangler((m) => ({ ...m, editing: true })),
      title: "Klikk for \xE5 oppgi verdi",
      style: { fontFamily: "'IBM Plex Mono',monospace", fontWeight: 700, fontSize: 10.5, color: T.gap, background: T.gapbg, border: `1.5px dashed ${T.gap}`, padding: "2px 8px", borderRadius: 4 }
    },
    "MANGLER: intervall \u2014 oppgi"
  )))))), /* @__PURE__ */ React.createElement("h2", { style: { fontWeight: 800, fontSize: 15, borderBottom: `2px solid ${T.ink}`, paddingBottom: 4, margin: "24px 0 10px" } }, "7 \xB7 Bruk / drift"), /* @__PURE__ */ React.createElement("div", { className: `blk ${selected === "warn" ? "sel" : ""}`, onClick: (e) => {
    e.stopPropagation();
    setSelected("warn");
  } }, /* @__PURE__ */ React.createElement("div", { className: "bar" }, /* @__PURE__ */ React.createElement("span", { onClick: (e) => {
    e.stopPropagation();
    regenWarn();
  } }, "\u21BB Strengere"), /* @__PURE__ */ React.createElement("span", null, "\u2702 Kort ned"), /* @__PURE__ */ React.createElement("span", null, "\u232B Tilbakestill")), !warnBlock.diff ? /* @__PURE__ */ React.createElement("div", { style: { background: "#FFF8E0", border: `1px solid ${T.signal}`, borderLeft: `5px solid ${T.signal}`, borderRadius: 4, padding: "9px 13px", fontSize: 12.5 } }, /* @__PURE__ */ React.createElement("b", null, "\u26A0 ADVARSEL \u2014 Hengende last."), " ", warnBlock.text) : /* @__PURE__ */ React.createElement("div", { onClick: (e) => e.stopPropagation(), style: { border: `1.5px solid ${T.fact}`, borderRadius: 6, overflow: "hidden" } }, /* @__PURE__ */ React.createElement("div", { style: { padding: "8px 13px", fontSize: 12, background: "#F6F5F1", color: T.steel, textDecoration: "line-through" } }, "\u26A0 ADVARSEL \u2014 Hengende last. ", warnBlock.text), /* @__PURE__ */ React.createElement("div", { style: { padding: "9px 13px", fontSize: 12.5, background: T.factbg } }, /* @__PURE__ */ React.createElement("b", null, "\u26A0 ", warnBlock.diff.split(".")[0], "."), warnBlock.diff.substring(warnBlock.diff.indexOf(".") + 1)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, padding: "8px 13px", background: T.sheet, borderTop: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("button", { onClick: acceptDiff, style: { fontSize: 11.5, fontWeight: 800, background: T.ok, color: "#fff", border: "none", borderRadius: 5, padding: "5px 14px" } }, "\u2713 Godta"), /* @__PURE__ */ React.createElement("button", { onClick: rejectDiff, style: { fontSize: 11.5, fontWeight: 700, background: "transparent", color: T.steel, border: `1px solid ${T.line}`, borderRadius: 5, padding: "5px 14px" } }, "Forkast"), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 10, color: T.steel, alignSelf: "center" } }, "forh\xE5ndsvisning \u2014 ingenting er endret enn\xE5")))), /* @__PURE__ */ React.createElement("div", { className: `blk ${selected === "steps" ? "sel" : ""}`, onClick: (e) => {
    e.stopPropagation();
    setSelected("steps");
  }, style: { marginTop: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "bar" }, /* @__PURE__ */ React.createElement("span", null, "\u21BB Regenerer"), /* @__PURE__ */ React.createElement("span", null, "\u2702 Kort ned")), /* @__PURE__ */ React.createElement("ol", { style: { fontSize: 13, lineHeight: 1.7, paddingLeft: 20, margin: 0 } }, /* @__PURE__ */ React.createElement("li", null, "Kontroller verkt\xF8yet visuelt f\xF8r bruk."), /* @__PURE__ */ React.createElement("li", null, "Fest alle fire sjakler til l\xF8fte\xF8rene. Kontroller splinter."), /* @__PURE__ */ React.createElement("li", null, "L\xF8ft lasten maks 100 mm og kontroller balanse."), /* @__PURE__ */ React.createElement("li", null, "L\xF8ft aldri mer enn ", /* @__PURE__ */ React.createElement(Chip, { f: FACTS.swl, onHover: setHover }), "."))))), /* @__PURE__ */ React.createElement("aside", { style: { width: 290, borderLeft: `1px solid ${T.line}`, background: T.sheet, display: "flex", flexDirection: "column", flexShrink: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { padding: "10px 14px", borderBottom: `1px solid ${T.line}`, display: "flex", alignItems: "center", gap: 8 } }, /* @__PURE__ */ React.createElement("span", { style: { fontWeight: 800, fontSize: 12.5 } }, "Assistent"), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, background: T.paper, border: `1px solid ${T.line}`, borderRadius: 99, padding: "2px 9px", color: T.steel } }, selected ? `Blokk: ${selected === "tbl" ? "Tekniske data" : selected === "warn" ? "Advarsel" : "Bruk pkt. 1\u20134"}` : "Hele dokumentet")), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 10 } }, chat.map((m, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { alignSelf: m.who === "user" ? "flex-end" : "flex-start", maxWidth: "92%" } }, /* @__PURE__ */ React.createElement("div", { style: {
    fontSize: 12,
    lineHeight: 1.5,
    padding: "8px 11px",
    borderRadius: 10,
    background: m.who === "user" ? T.ink : T.paper,
    color: m.who === "user" ? "#fff" : T.ink
  } }, m.txt), m.proposal && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6, border: `1.5px solid ${T.fact}`, borderRadius: 8, overflow: "hidden", fontSize: 11.5 } }, /* @__PURE__ */ React.createElement("div", { style: { padding: "6px 10px", background: "#F6F5F1", color: T.steel, textDecoration: "line-through" } }, "L\xF8ft aldri mer enn 3,2 t."), /* @__PURE__ */ React.createElement("div", { style: { padding: "7px 10px", background: T.factbg } }, "Overskrid aldri sikker arbeidslast p\xE5 ", /* @__PURE__ */ React.createElement("b", null, "3,2 t"), " \u2014 vurder lastens faktiske vekt mot merkeskiltet f\xF8r hvert l\xF8ft."), !m.accepted ? /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, padding: "6px 10px", borderTop: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("button", { onClick: () => acceptProposal(i), style: { fontSize: 10.5, fontWeight: 800, background: T.ok, color: "#fff", border: "none", borderRadius: 4, padding: "3px 10px" } }, "\u2713 Godta"), /* @__PURE__ */ React.createElement("button", { style: { fontSize: 10.5, fontWeight: 700, background: "transparent", color: T.steel, border: `1px solid ${T.line}`, borderRadius: 4, padding: "3px 10px" } }, "Forkast")) : /* @__PURE__ */ React.createElement("div", { style: { padding: "5px 10px", fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, color: T.ok, borderTop: `1px solid ${T.line}` } }, "\u2713 Godtatt \xB7 ny versjon opprettet"))))), /* @__PURE__ */ React.createElement("div", { style: { padding: 10, borderTop: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6 } }, /* @__PURE__ */ React.createElement(
    "input",
    {
      value: chatInput,
      onChange: (e) => setChatInput(e.target.value),
      onKeyDown: (e) => e.key === "Enter" && send(),
      placeholder: 'Pr\xF8v: "hva mangler?"',
      style: { flex: 1, fontFamily: "'Archivo',sans-serif", fontSize: 12, padding: "8px 10px", border: `1px solid ${T.line}`, borderRadius: 7, background: T.paper }
    }
  ), /* @__PURE__ */ React.createElement("button", { onClick: send, style: { fontWeight: 900, background: T.signal, border: "none", borderRadius: 7, padding: "0 13px" } }, "\u2192")), /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, color: T.steel, marginTop: 6 } }, turns, " / 20 samtaleturer \xB7 6 / 30 regenereringer"))), drawer && /* @__PURE__ */ React.createElement("aside", { style: { position: "absolute", right: 0, top: 52, bottom: 40, width: 290, background: T.sheet, borderLeft: `2px solid ${T.ink}`, boxShadow: "-8px 0 24px rgba(0,0,0,.12)", zIndex: 20, padding: 14, overflowY: "auto" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", marginBottom: 12 } }, /* @__PURE__ */ React.createElement("b", { style: { fontSize: 13 } }, "Versjonshistorikk"), /* @__PURE__ */ React.createElement("button", { onClick: () => setDrawer(false), style: { marginLeft: "auto", border: "none", background: "none", fontSize: 16 } }, "\xD7")), versions.map((v, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { borderLeft: `3px solid ${v.who === "Bruker" ? T.ok : v.who === "Chat" ? T.fact : T.signal}`, padding: "6px 10px", marginBottom: 8, background: T.card, borderRadius: "0 6px 6px 0" } }, /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono',monospace", fontSize: 9.5, color: T.steel } }, v.t, " \xB7 ", v.who), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 12 } }, v.txt), i === 0 && versions.length > 1 && /* @__PURE__ */ React.createElement("button", { style: { fontSize: 10, fontWeight: 700, marginTop: 4, background: "transparent", border: `1px solid ${T.line}`, borderRadius: 4, padding: "2px 8px", color: T.steel } }, "\u21A9 Tilbakestill"))))), /* @__PURE__ */ React.createElement("footer", { style: { display: "flex", alignItems: "center", gap: 16, height: 40, padding: "0 16px", background: T.sheet, borderTop: `1px solid ${T.line}`, flexShrink: 0, fontSize: 12 } }, /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", { style: { color: T.ok } }, mangler.resolved ? 5 : 4, " fakta sitert"), " \xB7 alle sporbare"), /* @__PURE__ */ React.createElement("span", { style: { color: gapsLeft ? T.gap : T.ok, fontWeight: 700 } }, gapsLeft ? "\u25CF 1 blokkerende mangel" : "\u2713 Ingen mangler"), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", fontFamily: "'IBM Plex Mono',monospace", fontSize: 10.5, color: T.steel } }, "klikk en blokk \xB7 hover et tall \xB7 pr\xF8v chatten"), /* @__PURE__ */ React.createElement("button", { disabled: !!gapsLeft, style: { fontWeight: 800, fontSize: 12, background: gapsLeft ? "#E4E1D8" : T.signal, color: gapsLeft ? T.steel : T.ink, border: "none", borderRadius: 6, padding: "7px 16px", cursor: gapsLeft ? "not-allowed" : "pointer" } }, "Eksporter PDF \xB7 \u20AC19")));
};
