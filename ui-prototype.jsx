import React, { useState } from "react";

/* ────────────────────────────────────────────────────────────
   FOLDOK — Compiler UI prototype v2 (i18n: NO / EN / PL)
   Adding a language = one object in STRINGS. UI, artifact model,
   sections, import flow and the document itself all switch.
   ──────────────────────────────────────────────────────────── */

const T = {
  ink: "#16181D", paper: "#F2F0EA", sheet: "#FFFFFF", signal: "#F5C400",
  steel: "#5A6472", line: "#DCD9D0", ok: "#1E7A46", gap: "#C74E19",
  fact: "#1450B4", factBg: "#EAF1FD", gapBg: "#FDF0E8",
};

/* ── i18n ──────────────────────────────────────────────────── */
const STRINGS = {
  no: {
    steps: ["Kilder", "Forstå", "Struktur", "Bygg", "Eksport"],
    projectName: "Batteripakke løfteverktøy — Kranprosjekt",
    ownTemplate: "+ Egen mal", used: "brukt",
    // Understand
    cpA: "SJEKKPUNKT A", understandH: "Her er hva jeg tror dette er",
    understandSub: "Rett meg før vi bygger noe. Alt nedenfor kan redigeres.",
    artifactName: "Løfteverktøy for batteripakke",
    artifactDesc: "Løfteredskap · brukes til å heise batterimoduler med kran, fire festepunkter",
    sure: "sikker", components: "HOVEDKOMPONENTER", hazards: "IDENTIFISERTE FARER",
    compList: ["Løfteramme (S355)", "4 × løfteører", "Sjakler med splint", "Kjettingsett 4-part"],
    hazList: ["Hengende last", "Klemfare ved tilkobling", "Utstyrssvikt / slitasje"],
    lifecycle: ["transport", "installasjon", "bruk", "vedlikehold", "inspeksjon"],
    confirmBtn: "Dette stemmer — fortsett", confirmedBtn: "✓ Bekreftet", editBtn: "Rediger",
    // Structure
    cpB: "SJEKKPUNKT B", structureH: "Foreslått struktur",
    structureSub: (n, f) => `Teknisk dokumentasjonspakke · ${n} seksjoner · ${f} kilder kartlagt`,
    blockingW: "blokkerende", warningW: "advarsel", facts: "fakta", noPhotos: "ingen bilder",
    generateBtn: "Generer utkast →", estCalls: "est. 9 kall · ~€0,14",
    sections: ["Forside og identifikasjon", "Tiltenkt bruk og begrensninger", "Sikkerhetsinformasjon", "Tekniske data", "Produktbeskrivelse", "Installasjon / montering", "Bruk / drift", "Vedlikehold og inspeksjon", "Test- og verifikasjonsdok."],
    gapTorque: "Tiltrekkingsmoment ikke funnet",
    gapInterval: "Inspeksjonsintervall mangler — påkrevd for løfteutstyr",
    // Build
    sources: "KILDER", indexed: "filer · indeksert",
    docType: "TEKNISK DOKUMENTASJONSPAKKE · REV A", draft: "UTKAST",
    serialLbl: "Serienr.", docTitle: "Løfteverktøy for batteripakke",
    secTech: "4 · Tekniske data", secOper: "7 · Bruk / drift", secMaint: "8 · Vedlikehold og inspeksjon",
    techRows: ["Sikker arbeidslast (SWL)", "Prøvelast (1,5 × SWL)", "Egenvekt", "Ytre mål (L × B × H)", "Hovedmateriale", "Teststandard"],
    warnTitle: "⚠ ADVARSEL — Hengende last.",
    warnBody: "Opphold under lasten kan medføre alvorlig personskade eller død. Sperr av området før løft.",
    steps4: ["Kontroller verktøyet visuelt før bruk (se pkt. 8).", "Fest alle fire sjakler til løfteørene. Kontroller at splinter er montert.", "Løft lasten maks 100 mm og kontroller balanse før videre heising.", "Løft aldri mer enn"],
    maintCols: ["Hva", "Intervall", "Utføres av"],
    maintRow1: ["Visuell kontroll (sprekker, deformasjon)", "Før hver bruk", "Operatør"],
    maintRow2Who: "Sakkyndig virksomhet", maintRow2What: "Sakkyndig kontroll",
    manglerLbl: "MANGLER", manglerKey: "inspeksjonsintervall",
    gapMsg: "intervall for sakkyndig kontroll finnes ikke i kildene.",
    blockingLbl: "Blokkerende:", provideBtn: "Oppgi verdi",
    blockActions: ["↻ Regenerer", "✂ Kort ned", "⌫ Tilbakestill"],
    factsTraced: "fakta sitert", allTraceable: "alle sporbare",
    oneBlocking: "1 blokkerende mangel", oneWarning: "1 advarsel",
    hoverHint: "hover en verdi → se kilden", exportBtn: "Eksporter PDF · €19",
    srcTip: "Kilde", conf: "konfidens",
    // Export
    exportH: "Klar for eksport?", exportBlock: "1 blokkerende mangel må løses først: inspeksjonsintervall.",
    exportInfo: "Når mangelen er løst: ansvarsbekreftelse → betaling €19 → ren PDF uten vannmerke.",
    backBtn: "← Tilbake til dokumentet",
    // Import
    ownLbl: "EGEN MAL", importH: "Importer din egen mal",
    importSub: "Last opp skjemaet dere bruker i dag — Word, PDF eller et foto av papirskjemaet. Foldok leser strukturen og fyller det for deg på hver jobb.",
    dropZone: "Slipp fil her eller klikk for å velge", dropHint: "docx · pdf · jpg — demo: Dartec-testrapport-v3.docx",
    foundH: "Fant 3 seksjoner og 10 felt",
    foundSub: "Dartec-testrapport-v3.docx · trykk på kravnivå for å endre. Blokkerende felt må fylles før eksport.",
    foundCost: "1 uttrekkskall · €0,02 · kjøres aldri igjen for denne filen",
    foundSecs: "SEKSJONER: Utstyrsdata · Kontrollresultater · Signering",
    ownField: "eget felt", reqB: "Blokkerende", reqW: "Advarsel", reqI: "Valgfritt",
    boilerNote: "Fast tekst funnet:", boilerBody: "erklæringsavsnitt nederst i skjemaet beholdes ordrett — AI endrer aldri juridisk tekst fra importerte maler.",
    saveTemplate: "Lagre som firmamal →", doneH: "✓ Malen er klar",
    doneBody: ["«Dartec testrapport» ligger nå i malvelgeren ved siden av de innebygde.", "Hver jobb fremover: ta bilder av utstyret, snakk inn observasjonene — feltene fylles automatisk, med kildesporing på hver verdi. Logo og stempel fra firmaprofilen legges på ved eksport."],
    useBtn: "Bruk på et prosjekt",
    importFields: ["Serienr. / ID-merking", "Utstyrstype", "SWL / WLL", "Fabrikat", "Kontrolldato", "Neste kontroll", "Visuell kontroll (OK/Avvik)", "NDT-resultat", "Anmerkninger", "Kontrollør"],
    fileCaps: ["Løfteverktøy montert på batteripakke, sett forfra. Gul ramme, fire løftepunkter.", "Merkeskilt: SWL 3.2t, serienr. BLT-2026-011, produsent stemplet.", "Lasttest utført til 1.5 × SWL (4.8t) uten deformasjon. EN 13155. Testinstans: TI-Lab AS.", "Sjakkel festes til løfteøre, splint synlig montert.", "Alle fire løftepunkter tilkoblet, kjettingsett i vinkel ca. 45°.", "Nærbilde slitasjemerke på krokspiss — innenfor toleranse.", "Egenvekt 42 kg. Ytre mål 1240 × 860 × 310 mm. Materiale S355.", "Verktøyet hengende i kranhake, fri høyde, verksted."],
  },
  en: {
    steps: ["Sources", "Understand", "Structure", "Build", "Export"],
    projectName: "Battery Pack Lifting Tool — Crane Project",
    ownTemplate: "+ Own template", used: "used",
    cpA: "CHECKPOINT A", understandH: "Here's what I think this is",
    understandSub: "Correct me before we build anything. Everything below is editable.",
    artifactName: "Battery pack lifting tool",
    artifactDesc: "Lifting device · used to hoist battery modules by crane, four attachment points",
    sure: "confident", components: "MAIN COMPONENTS", hazards: "IDENTIFIED HAZARDS",
    compList: ["Lifting frame (S355)", "4 × lifting eyes", "Shackles with split pins", "4-leg chain set"],
    hazList: ["Suspended load", "Crush hazard during hook-up", "Equipment failure / wear"],
    lifecycle: ["transport", "installation", "operation", "maintenance", "inspection"],
    confirmBtn: "This is correct — continue", confirmedBtn: "✓ Confirmed", editBtn: "Edit",
    cpB: "CHECKPOINT B", structureH: "Proposed structure",
    structureSub: (n, f) => `Technical documentation package · ${n} sections · ${f} sources mapped`,
    blockingW: "blocking", warningW: "warning", facts: "facts", noPhotos: "no photos",
    generateBtn: "Generate draft →", estCalls: "est. 9 calls · ~€0.14",
    sections: ["Cover & identification", "Intended use & limitations", "Safety information", "Technical data", "Product description", "Installation / assembly", "Operation", "Maintenance & inspection", "Test & verification docs"],
    gapTorque: "Torque values not found",
    gapInterval: "Inspection interval missing — required for lifting equipment",
    sources: "SOURCES", indexed: "files · indexed",
    docType: "TECHNICAL DOCUMENTATION PACKAGE · REV A", draft: "DRAFT",
    serialLbl: "Serial no.", docTitle: "Battery Pack Lifting Tool",
    secTech: "4 · Technical data", secOper: "7 · Operation", secMaint: "8 · Maintenance & inspection",
    techRows: ["Safe working load (SWL)", "Proof load (1.5 × SWL)", "Dead weight", "Overall dimensions (L × W × H)", "Main material", "Test standard"],
    warnTitle: "⚠ WARNING — Suspended load.",
    warnBody: "Standing under the load may result in serious injury or death. Barrier the area before lifting.",
    steps4: ["Visually inspect the tool before use (see section 8).", "Attach all four shackles to the lifting eyes. Verify split pins are fitted.", "Lift the load max 100 mm and check balance before continuing.", "Never lift more than"],
    maintCols: ["What", "Interval", "Performed by"],
    maintRow1: ["Visual check (cracks, deformation)", "Before each use", "Operator"],
    maintRow2Who: "Competent body", maintRow2What: "Thorough examination",
    manglerLbl: "MISSING", manglerKey: "inspection interval",
    gapMsg: "interval for thorough examination not found in sources.",
    blockingLbl: "Blocking:", provideBtn: "Provide value",
    blockActions: ["↻ Regenerate", "✂ Shorten", "⌫ Revert"],
    factsTraced: "facts cited", allTraceable: "all traceable",
    oneBlocking: "1 blocking gap", oneWarning: "1 warning",
    hoverHint: "hover a value → see its source", exportBtn: "Export PDF · €19",
    srcTip: "Source", conf: "confidence",
    exportH: "Ready to export?", exportBlock: "1 blocking gap must be resolved first: inspection interval.",
    exportInfo: "Once resolved: responsibility confirmation → payment €19 → clean PDF without watermark.",
    backBtn: "← Back to document",
    ownLbl: "OWN TEMPLATE", importH: "Import your own template",
    importSub: "Upload the form you use today — Word, PDF or a photo of the paper form. Foldok reads the structure and fills it for you on every job.",
    dropZone: "Drop file here or click to choose", dropHint: "docx · pdf · jpg — demo: Dartec-testrapport-v3.docx",
    foundH: "Found 3 sections and 10 fields",
    foundSub: "Dartec-testrapport-v3.docx · tap the requirement level to change it. Blocking fields must be filled before export.",
    foundCost: "1 extraction call · €0.02 · never runs again for this file",
    foundSecs: "SECTIONS: Equipment data · Inspection results · Sign-off",
    ownField: "custom field", reqB: "Blocking", reqW: "Warning", reqI: "Optional",
    boilerNote: "Fixed text found:", boilerBody: "the declaration paragraph at the bottom of the form is kept verbatim — AI never rewrites legal text from imported templates.",
    saveTemplate: "Save as company template →", doneH: "✓ Template is ready",
    doneBody: ["\u201CDartec test report\u201D now sits in the template picker next to the built-ins.", "Every job from now on: photograph the equipment, speak your observations — the fields fill automatically, with source tracing on every value. Logo and stamp from your company profile are applied at export."],
    useBtn: "Use on a project",
    importFields: ["Serial no. / ID marking", "Equipment type", "SWL / WLL", "Manufacturer", "Inspection date", "Next inspection", "Visual check (OK/Deviation)", "NDT result", "Remarks", "Inspector"],
    fileCaps: ["Lifting tool mounted on battery pack, front view. Yellow frame, four lifting points.", "Nameplate: SWL 3.2t, serial no. BLT-2026-011, manufacturer stamped.", "Load test performed to 1.5 × SWL (4.8t) without deformation. EN 13155. Test body: TI-Lab AS.", "Shackle attached to lifting eye, split pin visibly fitted.", "All four lifting points connected, chain set at approx. 45° angle.", "Close-up of wear mark on hook tip — within tolerance.", "Dead weight 42 kg. Dimensions 1240 × 860 × 310 mm. Material S355.", "Tool hanging in crane hook, free height, workshop."],
  },
  pl: {
    steps: ["Źródła", "Zrozum", "Struktura", "Buduj", "Eksport"],
    projectName: "Trawersa do pakietu baterii — Projekt dźwigowy",
    ownTemplate: "+ Własny szablon", used: "zużyto",
    cpA: "PUNKT KONTROLNY A", understandH: "Oto co myślę, że to jest",
    understandSub: "Popraw mnie zanim cokolwiek zbudujemy. Wszystko poniżej można edytować.",
    artifactName: "Trawersa do pakietu baterii",
    artifactDesc: "Zawiesie · służy do podnoszenia modułów baterii dźwigiem, cztery punkty mocowania",
    sure: "pewności", components: "GŁÓWNE KOMPONENTY", hazards: "ZIDENTYFIKOWANE ZAGROŻENIA",
    compList: ["Rama nośna (S355)", "4 × ucha transportowe", "Szekle z zawleczkami", "Zawiesie łańcuchowe 4-cięgnowe"],
    hazList: ["Wiszący ładunek", "Ryzyko zgniecenia przy podpinaniu", "Awaria sprzętu / zużycie"],
    lifecycle: ["transport", "montaż", "eksploatacja", "konserwacja", "przegląd"],
    confirmBtn: "Zgadza się — kontynuuj", confirmedBtn: "✓ Potwierdzono", editBtn: "Edytuj",
    cpB: "PUNKT KONTROLNY B", structureH: "Proponowana struktura",
    structureSub: (n, f) => `Pakiet dokumentacji technicznej · ${n} sekcji · ${f} źródeł przypisanych`,
    blockingW: "blokujące", warningW: "ostrzeżenie", facts: "faktów", noPhotos: "brak zdjęć",
    generateBtn: "Generuj szkic →", estCalls: "szac. 9 zapytań · ~0,14 €",
    sections: ["Strona tytułowa i identyfikacja", "Przeznaczenie i ograniczenia", "Informacje bezpieczeństwa", "Dane techniczne", "Opis produktu", "Montaż / instalacja", "Eksploatacja", "Konserwacja i przeglądy", "Dokumentacja badań"],
    gapTorque: "Nie znaleziono momentów dokręcania",
    gapInterval: "Brak okresu przeglądu — wymagany dla sprzętu dźwigowego",
    sources: "ŹRÓDŁA", indexed: "plików · zindeksowano",
    docType: "PAKIET DOKUMENTACJI TECHNICZNEJ · REW. A", draft: "SZKIC",
    serialLbl: "Nr seryjny", docTitle: "Trawersa do pakietu baterii",
    secTech: "4 · Dane techniczne", secOper: "7 · Eksploatacja", secMaint: "8 · Konserwacja i przeglądy",
    techRows: ["Dopuszczalne obciążenie (SWL)", "Obciążenie próbne (1,5 × SWL)", "Masa własna", "Wymiary (D × S × W)", "Materiał główny", "Norma badawcza"],
    warnTitle: "⚠ OSTRZEŻENIE — Wiszący ładunek.",
    warnBody: "Przebywanie pod ładunkiem grozi poważnymi obrażeniami lub śmiercią. Wygrodź strefę przed podnoszeniem.",
    steps4: ["Sprawdź wzrokowo narzędzie przed użyciem (patrz pkt 8).", "Podepnij wszystkie cztery szekle do uch. Sprawdź zawleczki.", "Podnieś ładunek maks. 100 mm i sprawdź wyważenie przed dalszym podnoszeniem.", "Nigdy nie podnoś więcej niż"],
    maintCols: ["Co", "Okres", "Wykonuje"],
    maintRow1: ["Kontrola wzrokowa (pęknięcia, odkształcenia)", "Przed każdym użyciem", "Operator"],
    maintRow2Who: "Jednostka uprawniona", maintRow2What: "Przegląd okresowy",
    manglerLbl: "BRAK", manglerKey: "okres przeglądu",
    gapMsg: "okres przeglądu okresowego nie występuje w źródłach.",
    blockingLbl: "Blokujące:", provideBtn: "Podaj wartość",
    blockActions: ["↻ Generuj ponownie", "✂ Skróć", "⌫ Cofnij"],
    factsTraced: "faktów cytowanych", allTraceable: "wszystkie identyfikowalne",
    oneBlocking: "1 brak blokujący", oneWarning: "1 ostrzeżenie",
    hoverHint: "najedź na wartość → zobacz źródło", exportBtn: "Eksportuj PDF · 19 €",
    srcTip: "Źródło", conf: "pewność",
    exportH: "Gotowe do eksportu?", exportBlock: "Najpierw usuń 1 brak blokujący: okres przeglądu.",
    exportInfo: "Po usunięciu: potwierdzenie odpowiedzialności → płatność 19 € → czysty PDF bez znaku wodnego.",
    backBtn: "← Wróć do dokumentu",
    ownLbl: "WŁASNY SZABLON", importH: "Importuj własny szablon",
    importSub: "Prześlij formularz, którego używacie dziś — Word, PDF lub zdjęcie papierowego formularza. Foldok odczyta strukturę i wypełni go za Ciebie przy każdej pracy.",
    dropZone: "Upuść plik tutaj lub kliknij, aby wybrać", dropHint: "docx · pdf · jpg — demo: Dartec-testrapport-v3.docx",
    foundH: "Znaleziono 3 sekcje i 10 pól",
    foundSub: "Dartec-testrapport-v3.docx · dotknij poziomu wymogu, aby zmienić. Pola blokujące muszą być wypełnione przed eksportem.",
    foundCost: "1 zapytanie ekstrakcji · 0,02 € · nigdy nie uruchomi się ponownie dla tego pliku",
    foundSecs: "SEKCJE: Dane sprzętu · Wyniki kontroli · Podpisy",
    ownField: "pole własne", reqB: "Blokujące", reqW: "Ostrzeżenie", reqI: "Opcjonalne",
    boilerNote: "Znaleziono stały tekst:", boilerBody: "akapit deklaracji na dole formularza zachowany dosłownie — AI nigdy nie przepisuje tekstu prawnego z importowanych szablonów.",
    saveTemplate: "Zapisz jako szablon firmowy →", doneH: "✓ Szablon gotowy",
    doneBody: ["„Dartec raport z badań\u201D znajduje się teraz w wyborze szablonów obok wbudowanych.", "Każda praca od teraz: sfotografuj sprzęt, nagraj obserwacje — pola wypełniają się automatycznie, z identyfikacją źródła każdej wartości. Logo i pieczęć z profilu firmy nakładane przy eksporcie."],
    useBtn: "Użyj w projekcie",
    importFields: ["Nr seryjny / oznaczenie", "Typ sprzętu", "SWL / WLL", "Producent", "Data kontroli", "Następna kontrola", "Kontrola wzrokowa (OK/Uwagi)", "Wynik NDT", "Uwagi", "Kontroler"],
    fileCaps: ["Trawersa zamontowana na pakiecie baterii, widok z przodu. Żółta rama, cztery punkty podnoszenia.", "Tabliczka: SWL 3.2t, nr ser. BLT-2026-011, producent wybity.", "Próba obciążeniowa do 1.5 × SWL (4.8t) bez odkształceń. EN 13155. Jednostka: TI-Lab AS.", "Szekla podpięta do ucha, zawleczka widocznie zamontowana.", "Wszystkie cztery punkty podpięte, łańcuchy pod kątem ok. 45°.", "Zbliżenie śladu zużycia na końcówce haka — w tolerancji.", "Masa własna 42 kg. Wymiary 1240 × 860 × 310 mm. Materiał S355.", "Narzędzie wiszące na haku dźwigu, wolna wysokość, warsztat."],
  },
};

/* ── Mock data (language-independent parts) ────────────────── */
const FILE_META = [
  { id: "f1", name: "IMG_2841.jpg", kind: "photo", tags: ["overview", "frame"], hue: "#8a93a6" },
  { id: "f2", name: "IMG_2844.jpg", kind: "photo", tags: ["nameplate", "swl"], hue: "#a6988a" },
  { id: "f3", name: "lasttest_rapport.pdf", kind: "pdf", tags: ["test", "EN 13155"], hue: "#7d8c7a" },
  { id: "f4", name: "IMG_2851.jpg", kind: "photo", tags: ["assembly", "shackle"], hue: "#96848f" },
  { id: "f5", name: "IMG_2852.jpg", kind: "photo", tags: ["assembly", "rigging"], hue: "#8a93a6" },
  { id: "f6", name: "IMG_2860.jpg", kind: "photo", tags: ["wear", "inspection"], hue: "#a68a8a" },
  { id: "f7", name: "vekt_dimensjoner.xlsx", kind: "sheet", tags: ["weight", "dims"], hue: "#7a8c8a" },
  { id: "f8", name: "IMG_2839.jpg", kind: "photo", tags: ["overview", "crane"], hue: "#8a93a6" },
];

const FACTS = [
  { id: "swl", value: "3,2", unit: "t", src: "f2", conf: 0.97 },
  { id: "serial", value: "BLT-2026-011", unit: "", src: "f2", conf: 0.95 },
  { id: "test", value: "EN 13155", unit: "", src: "f3", conf: 0.96 },
  { id: "proof", value: "4,8", unit: "t", src: "f3", conf: 0.94 },
  { id: "weight", value: "42", unit: "kg", src: "f7", conf: 0.92 },
  { id: "dims", value: "1240 × 860 × 310", unit: "mm", src: "f7", conf: 0.9 },
  { id: "mat", value: "S355", unit: "", src: "f7", conf: 0.88 },
];

const SECTION_META = [
  { key: "cover", files: ["f1"], facts: 3, gaps: [] },
  { key: "intended", files: [], facts: 1, gaps: [] },
  { key: "safety", files: ["f6"], facts: 2, gaps: [] },
  { key: "tech", files: ["f2", "f7"], facts: 6, gaps: [] },
  { key: "desc", files: ["f1", "f8"], facts: 0, gaps: [] },
  { key: "install", files: ["f4", "f5"], facts: 0, gaps: [{ sev: "warning", t: "gapTorque" }] },
  { key: "operation", files: ["f5", "f8"], facts: 1, gaps: [] },
  { key: "maint", files: ["f6"], facts: 0, gaps: [{ sev: "blocking", t: "gapInterval" }] },
  { key: "testdoc", files: ["f3"], facts: 2, gaps: [] },
];

const IMPORT_META = [
  { key: "serial_no", canonical: true, req: "blocking" },
  { key: "equipment_type", canonical: true, req: "blocking" },
  { key: "swl", canonical: true, req: "blocking" },
  { key: "manufacturer", canonical: true, req: "warning" },
  { key: "control_date", canonical: true, req: "blocking" },
  { key: "next_control", canonical: true, req: "blocking" },
  { key: "visual_result", canonical: false, req: "blocking" },
  { key: "ndt_result", canonical: false, req: "warning" },
  { key: "remarks", canonical: false, req: "info" },
  { key: "inspector_name", canonical: true, req: "blocking" },
];

/* ── Small pieces ──────────────────────────────────────────── */
const FileThumb = ({ f, cap, lit, dim, onHover }) => (
  <div
    onMouseEnter={() => onHover && onHover(f.id)}
    onMouseLeave={() => onHover && onHover(null)}
    style={{
      display: "flex", gap: 10, padding: 10, borderRadius: 6, cursor: "default",
      background: lit ? "#FFF6CE" : T.sheet,
      border: `1px solid ${lit ? T.signal : T.line}`,
      boxShadow: lit ? `0 0 0 2px ${T.signal}` : "none",
      opacity: dim ? 0.38 : 1, transition: "all .18s ease",
    }}
  >
    <div style={{
      width: 52, height: 52, borderRadius: 4, flexShrink: 0,
      background: `linear-gradient(135deg, ${f.hue}, ${f.hue}66)`,
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "#fff", fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, fontWeight: 600,
    }}>
      {f.kind === "photo" ? "IMG" : f.kind === "pdf" ? "PDF" : "XLS"}
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{f.name}</div>
      <div style={{ fontSize: 11, color: T.steel, lineHeight: 1.35, marginTop: 2, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{cap}</div>
      <div style={{ display: "flex", gap: 4, marginTop: 5, flexWrap: "wrap" }}>
        {f.tags.map(t => (
          <span key={t} style={{ fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", padding: "1px 5px", background: T.paper, border: `1px solid ${T.line}`, borderRadius: 3, color: T.steel }}>{t}</span>
        ))}
      </div>
    </div>
  </div>
);

const Fact = ({ f, t, onHover }) => (
  <span
    onMouseEnter={() => onHover(f.src)}
    onMouseLeave={() => onHover(null)}
    title={`${t.srcTip}: ${FILE_META.find(x => x.id === f.src)?.name} · ${t.conf} ${Math.round(f.conf * 100)}%`}
    style={{
      fontFamily: "'IBM Plex Mono', monospace", fontSize: "0.92em", fontWeight: 600,
      color: T.fact, background: T.factBg, borderBottom: `2px solid ${T.fact}`,
      padding: "0 3px", borderRadius: 2, cursor: "help", whiteSpace: "nowrap",
    }}
  >
    {f.value}{f.unit ? ` ${f.unit}` : ""}
  </span>
);

const Mangler = ({ t }) => (
  <span style={{
    fontFamily: "'IBM Plex Mono', monospace", fontSize: "0.85em", fontWeight: 700,
    color: T.gap, background: T.gapBg, border: `1.5px dashed ${T.gap}`,
    padding: "1px 7px", borderRadius: 3, whiteSpace: "nowrap",
  }}>
    {t.manglerLbl}: {t.manglerKey}
  </span>
);

const SevDot = ({ sev }) => (
  <span style={{ width: 8, height: 8, borderRadius: 99, flexShrink: 0, marginTop: 5, background: sev === "blocking" ? T.gap : T.signal }} />
);

const H2 = ({ children }) => (
  <h2 style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 26, margin: "0 0 6px", letterSpacing: "-0.01em" }}>{children}</h2>
);
const Eyebrow = ({ children }) => (
  <div style={{ fontFamily: "'Archivo', sans-serif", fontSize: 11, letterSpacing: "0.14em", fontWeight: 700, color: T.steel, marginBottom: 8 }}>{children}</div>
);
const PrimaryBtn = ({ children, onClick, bg = T.ink, color = "#fff" }) => (
  <button onClick={onClick} style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 14, background: bg, color, border: "none", borderRadius: 6, padding: "12px 22px", cursor: "pointer" }}>{children}</button>
);

/* ── Checkpoint A ──────────────────────────────────────────── */
const StepUnderstand = ({ t, onConfirm, confirmed }) => (
  <div style={{ maxWidth: 640, margin: "0 auto", padding: "40px 24px" }}>
    <Eyebrow>{t.cpA}</Eyebrow>
    <H2>{t.understandH}</H2>
    <p style={{ color: T.steel, fontSize: 14, margin: "0 0 24px" }}>{t.understandSub}</p>

    <div style={{ background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 8, overflow: "hidden" }}>
      <div style={{ padding: "18px 22px", borderBottom: `1px solid ${T.line}`, display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <div style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 19 }}>{t.artifactName}</div>
          <div style={{ fontSize: 13, color: T.steel, marginTop: 3 }}>{t.artifactDesc}</div>
        </div>
        <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: T.ok, fontWeight: 700 }}>91% {t.sure}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        <div style={{ padding: "16px 22px", borderRight: `1px solid ${T.line}` }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: T.steel, marginBottom: 10 }}>{t.components}</div>
          {t.compList.map(c => (
            <div key={c} style={{ fontSize: 13.5, padding: "5px 0", borderBottom: `1px dotted ${T.line}` }}>{c}</div>
          ))}
        </div>
        <div style={{ padding: "16px 22px" }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: T.steel, marginBottom: 10 }}>{t.hazards}</div>
          {t.hazList.map(h => (
            <div key={h} style={{ fontSize: 13.5, padding: "5px 0", borderBottom: `1px dotted ${T.line}`, display: "flex", gap: 8, alignItems: "flex-start" }}>
              <SevDot sev="warning" />{h}
            </div>
          ))}
        </div>
      </div>

      <div style={{ padding: "14px 22px", borderTop: `1px solid ${T.line}`, background: T.paper, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {t.lifecycle.map(s => (
          <span key={s} style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, padding: "3px 9px", background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 99 }}>{s}</span>
        ))}
      </div>
    </div>

    <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
      <PrimaryBtn onClick={onConfirm} bg={confirmed ? T.ok : T.ink}>{confirmed ? t.confirmedBtn : t.confirmBtn}</PrimaryBtn>
      <button style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 600, fontSize: 14, background: "transparent", color: T.steel, border: `1px solid ${T.line}`, borderRadius: 6, padding: "12px 18px", cursor: "pointer" }}>{t.editBtn}</button>
    </div>
  </div>
);

/* ── Checkpoint B ──────────────────────────────────────────── */
const StepStructure = ({ t, onNext }) => {
  const blocking = SECTION_META.flatMap(s => s.gaps).filter(g => g.sev === "blocking").length;
  const warnings = SECTION_META.flatMap(s => s.gaps).filter(g => g.sev === "warning").length;
  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "40px 24px" }}>
      <Eyebrow>{t.cpB}</Eyebrow>
      <H2>{t.structureH}</H2>
      <p style={{ color: T.steel, fontSize: 14, margin: "0 0 20px" }}>
        {t.structureSub(SECTION_META.length, FILE_META.length)} ·{" "}
        <span style={{ color: T.gap, fontWeight: 700 }}>{blocking} {t.blockingW}</span> · <span style={{ fontWeight: 700 }}>{warnings} {t.warningW}</span>
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {SECTION_META.map((s, i) => (
          <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 14, background: T.sheet, border: `1px solid ${s.gaps.some(g => g.sev === "blocking") ? T.gap : T.line}`, borderRadius: 6, padding: "12px 16px" }}>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: T.steel, width: 20 }}>{String(i + 1).padStart(2, "0")}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>{t.sections[i]}</div>
              {s.gaps.map(g => (
                <div key={g.t} style={{ fontSize: 12, color: g.sev === "blocking" ? T.gap : "#8a6d00", marginTop: 3, display: "flex", gap: 6, alignItems: "flex-start" }}>
                  <SevDot sev={g.sev} />{t[g.t]}
                </div>
              ))}
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {s.files.map(fid => {
                const f = FILE_META.find(x => x.id === fid);
                return <div key={fid} title={f.name} style={{ width: 26, height: 26, borderRadius: 4, background: `linear-gradient(135deg, ${f.hue}, ${f.hue}66)` }} />;
              })}
              {s.files.length === 0 && <span style={{ fontSize: 11, color: T.steel, fontStyle: "italic" }}>{t.noPhotos}</span>}
            </div>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: s.facts > 0 ? T.fact : T.steel, width: 58, textAlign: "right" }}>{s.facts} {t.facts}</span>
            <span style={{ cursor: "grab", color: T.line, fontSize: 16, userSelect: "none" }}>⠿</span>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 22 }}>
        <PrimaryBtn onClick={onNext}>{t.generateBtn}</PrimaryBtn>
        <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: T.steel }}>{t.estCalls}</span>
      </div>
    </div>
  );
};

/* ── Checkpoint C ──────────────────────────────────────────── */
const BlockToolbar = ({ t }) => (
  <div className="blockbar" style={{
    position: "absolute", top: -14, right: 8, display: "flex", gap: 4,
    background: T.ink, borderRadius: 6, padding: "4px 6px",
    opacity: 0, transition: "opacity .15s", pointerEvents: "none",
  }}>
    {t.blockActions.map(a => (
      <span key={a} style={{ fontSize: 10.5, color: "#fff", fontFamily: "'Archivo', sans-serif", fontWeight: 600, padding: "2px 7px", cursor: "pointer", borderRadius: 3 }}>{a}</span>
    ))}
  </div>
);

const DocBlock = ({ t, children }) => (
  <div className="docblock" style={{ position: "relative", padding: "4px 8px", margin: "0 -8px", borderRadius: 4 }}>
    <BlockToolbar t={t} />
    {children}
  </div>
);

const StepBuild = ({ t, hover, setHover }) => {
  const fx = id => FACTS.find(f => f.id === id);
  const litFiles = hover ? new Set([hover]) : null;
  const secH = { fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 16, borderBottom: `2px solid ${T.ink}`, paddingBottom: 5, margin: "26px 0 12px" };
  return (
    <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", height: "100%", minHeight: 0 }}>
      <div style={{ borderRight: `1px solid ${T.line}`, overflowY: "auto", padding: 14, background: T.paper }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
          <span style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 12, letterSpacing: "0.1em" }}>{t.sources}</span>
          <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: T.steel }}>{FILE_META.length} {t.indexed}</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {FILE_META.map((f, i) => (
            <FileThumb key={f.id} f={f} cap={t.fileCaps[i]} lit={litFiles?.has(f.id)} dim={litFiles && !litFiles.has(f.id)} />
          ))}
        </div>
      </div>

      <div style={{ overflowY: "auto", padding: "26px 34px", background: "#E9E7E0" }}>
        <div style={{
          maxWidth: 660, margin: "0 auto", background: T.sheet, borderRadius: 3,
          boxShadow: "0 2px 14px rgba(20,22,28,0.10)", padding: "44px 52px 56px", position: "relative",
        }}>
          <div style={{ position: "absolute", top: 16, right: 20, fontFamily: "'Archivo', sans-serif", fontWeight: 900, fontSize: 12, letterSpacing: "0.2em", color: "#00000018", border: "2px solid #00000014", padding: "3px 10px", transform: "rotate(3deg)" }}>{t.draft}</div>

          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: T.steel, letterSpacing: "0.06em" }}>{t.docType}</div>
          <h1 style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 900, fontSize: 30, letterSpacing: "-0.015em", margin: "8px 0 2px" }}>{t.docTitle}</h1>
          <div style={{ fontSize: 13.5, color: T.steel, marginBottom: 26 }}>
            {t.serialLbl} <Fact f={fx("serial")} t={t} onHover={setHover} /> · The Fuzzy Front
          </div>

          <h2 style={secH}>{t.secTech}</h2>
          <DocBlock t={t}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
              <tbody>
                {[fx("swl"), fx("proof"), fx("weight"), fx("dims"), fx("mat"), fx("test")].map((f, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${T.line}` }}>
                    <td style={{ padding: "7px 0", color: T.steel, width: "55%" }}>{t.techRows[i]}</td>
                    <td style={{ padding: "7px 0" }}><Fact f={f} t={t} onHover={setHover} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </DocBlock>

          <h2 style={{ ...secH, marginTop: 30 }}>{t.secOper}</h2>
          <DocBlock t={t}>
            <div style={{ background: "#FFF8E0", border: `1px solid ${T.signal}`, borderLeft: `5px solid ${T.signal}`, borderRadius: 4, padding: "10px 14px", margin: "6px 0 14px", fontSize: 13 }}>
              <strong style={{ fontFamily: "'Archivo', sans-serif" }}>{t.warnTitle}</strong>{" "}{t.warnBody}
            </div>
          </DocBlock>
          <DocBlock t={t}>
            <ol style={{ fontSize: 13.5, lineHeight: 1.75, paddingLeft: 22, margin: 0 }}>
              <li>{t.steps4[0]}</li>
              <li>{t.steps4[1]}</li>
              <li>{t.steps4[2]}</li>
              <li>{t.steps4[3]} <Fact f={fx("swl")} t={t} onHover={setHover} />.</li>
            </ol>
          </DocBlock>

          <h2 style={{ ...secH, marginTop: 30 }}>{t.secMaint}</h2>
          <DocBlock t={t}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${T.ink}` }}>
                  {t.maintCols.map(h => <th key={h} style={{ textAlign: "left", padding: "6px 0", fontFamily: "'Archivo', sans-serif", fontSize: 12 }}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: `1px solid ${T.line}` }}>
                  <td style={{ padding: "8px 0" }}>{t.maintRow1[0]}</td>
                  <td>{t.maintRow1[1]}</td><td>{t.maintRow1[2]}</td>
                </tr>
                <tr style={{ borderBottom: `1px solid ${T.line}` }}>
                  <td style={{ padding: "8px 0" }}>{t.maintRow2What}</td>
                  <td><Mangler t={t} /></td>
                  <td>{t.maintRow2Who}</td>
                </tr>
              </tbody>
            </table>
            <div style={{ marginTop: 10, fontSize: 12, color: T.gap, display: "flex", gap: 8, alignItems: "center" }}>
              <SevDot sev="blocking" />
              <span><strong>{t.blockingLbl}</strong> {t.gapMsg}</span>
              <button style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 700, fontSize: 11, background: T.gapBg, color: T.gap, border: `1px solid ${T.gap}`, borderRadius: 4, padding: "3px 10px", cursor: "pointer" }}>{t.provideBtn}</button>
            </div>
          </DocBlock>
        </div>
      </div>
    </div>
  );
};

/* ── Template import ───────────────────────────────────────── */
const TemplateImport = ({ t, onDone }) => {
  const [phase, setPhase] = useState(0);
  const [reqs, setReqs] = useState(Object.fromEntries(IMPORT_META.map(f => [f.key, f.req])));
  const cycle = k => setReqs(r => ({ ...r, [k]: r[k] === "blocking" ? "warning" : r[k] === "warning" ? "info" : "blocking" }));
  const reqStyle = r => r === "blocking"
    ? { background: T.gapBg, color: T.gap, border: `1px solid ${T.gap}` }
    : r === "warning"
      ? { background: "#FFF8E0", color: "#8a6d00", border: `1px solid ${T.signal}` }
      : { background: T.paper, color: T.steel, border: `1px solid ${T.line}` };
  const reqLabel = r => r === "blocking" ? t.reqB : r === "warning" ? t.reqW : t.reqI;

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "40px 24px" }}>
      <Eyebrow>{t.ownLbl}</Eyebrow>

      {phase === 0 && (<>
        <H2>{t.importH}</H2>
        <p style={{ color: T.steel, fontSize: 14, margin: "0 0 24px" }}>{t.importSub}</p>
        <button onClick={() => setPhase(1)} style={{
          width: "100%", padding: "44px 20px", background: T.sheet, borderRadius: 8, cursor: "pointer",
          border: `2px dashed ${T.line}`, fontFamily: "'Archivo', sans-serif", color: T.steel, fontSize: 14,
        }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>⬆</div>
          <strong style={{ color: T.ink }}>{t.dropZone}</strong>
          <div style={{ fontSize: 12, marginTop: 6 }}>{t.dropHint}</div>
        </button>
      </>)}

      {phase === 1 && (<>
        <H2>{t.foundH}</H2>
        <p style={{ color: T.steel, fontSize: 14, margin: "0 0 6px" }}>{t.foundSub}</p>
        <p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: T.steel, margin: "0 0 18px" }}>{t.foundCost}</p>

        <div style={{ background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 8, overflow: "hidden" }}>
          <div style={{ padding: "12px 18px", borderBottom: `1px solid ${T.line}`, background: T.paper, fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 12, letterSpacing: "0.08em" }}>
            {t.foundSecs}
          </div>
          {IMPORT_META.map((f, i) => (
            <div key={f.key} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 18px", borderBottom: `1px solid ${T.line}` }}>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 13.5, fontWeight: 600 }}>{t.importFields[i]}</span>
                {f.canonical
                  ? <span style={{ marginLeft: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: T.fact }}>→ {f.key}</span>
                  : <span style={{ marginLeft: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: T.steel }}>{t.ownField}</span>}
              </div>
              <button onClick={() => cycle(f.key)} style={{
                fontFamily: "'Archivo', sans-serif", fontWeight: 700, fontSize: 11, padding: "3px 12px",
                borderRadius: 99, cursor: "pointer", ...reqStyle(reqs[f.key]),
              }}>
                {reqLabel(reqs[f.key])}
              </button>
            </div>
          ))}
          <div style={{ padding: "12px 18px", background: "#FFF8E0", fontSize: 12.5, borderTop: `1px solid ${T.signal}` }}>
            <strong>{t.boilerNote}</strong> {t.boilerBody}
          </div>
        </div>

        <div style={{ marginTop: 20 }}>
          <PrimaryBtn onClick={() => setPhase(2)}>{t.saveTemplate}</PrimaryBtn>
        </div>
      </>)}

      {phase === 2 && (<>
        <H2>{t.doneH}</H2>
        <p style={{ fontSize: 14, color: T.steel, lineHeight: 1.6 }}>
          <strong style={{ color: T.ink }}>{t.doneBody[0]}</strong><br />{t.doneBody[1]}
        </p>
        <div style={{ marginTop: 18 }}>
          <PrimaryBtn onClick={onDone} bg={T.signal} color={T.ink}>{t.useBtn}</PrimaryBtn>
        </div>
      </>)}
    </div>
  );
};

/* ── App ───────────────────────────────────────────────────── */
export default function FoldokCompiler() {
  const [lang, setLang] = useState("no");
  const [step, setStep] = useState(1);
  const [confirmed, setConfirmed] = useState(false);
  const [hover, setHover] = useState(null);
  const [view, setView] = useState("project");
  const t = STRINGS[lang];
  const blocking = 1;

  return (
    <div style={{ fontFamily: "'Archivo', sans-serif", color: T.ink, background: T.paper, height: "100vh", display: "flex", flexDirection: "column" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800;900&family=IBM+Plex+Mono:wght@400;600;700&display=swap');
        * { box-sizing: border-box; }
        button:focus-visible { outline: 3px solid ${T.signal}; outline-offset: 2px; }
        .docblock:hover { background: #FBFAF6; }
        .docblock:hover .blockbar { opacity: 1; pointer-events: auto; }
        @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
      `}</style>

      <header style={{ display: "flex", alignItems: "center", gap: 16, padding: "0 18px", height: 54, background: T.ink, color: "#fff", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 22, height: 22, background: T.signal, borderRadius: 3, display: "inline-flex", alignItems: "center", justifyContent: "center", color: T.ink, fontWeight: 900, fontSize: 13 }}>F</span>
          <span style={{ fontWeight: 900, letterSpacing: "0.02em", fontSize: 15 }}>FOLDOK</span>
        </div>
        <span style={{ fontSize: 13, color: "#ffffff99", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t.projectName}</span>

        <nav style={{ display: "flex", gap: 2, marginLeft: "auto" }}>
          {t.steps.map((s, i) => {
            const active = view === "project" && i === step, done = i < step;
            return (
              <button key={s} onClick={() => { setView("project"); setStep(i); }} style={{
                fontFamily: "'Archivo', sans-serif", fontSize: 12, fontWeight: 700, letterSpacing: "0.04em",
                padding: "6px 14px", borderRadius: 99, border: "none", cursor: "pointer",
                background: active ? T.signal : "transparent",
                color: active ? T.ink : done ? "#fff" : "#ffffff66",
              }}>
                {done ? "✓ " : ""}{s}
              </button>
            );
          })}
          <button onClick={() => setView("templates")} style={{
            fontFamily: "'Archivo', sans-serif", fontSize: 12, fontWeight: 700, letterSpacing: "0.04em",
            padding: "6px 14px", borderRadius: 99, cursor: "pointer",
            border: `1px solid ${view === "templates" ? T.signal : "#ffffff33"}`,
            background: view === "templates" ? T.signal : "transparent",
            color: view === "templates" ? T.ink : "#ffffffcc",
            marginLeft: 10,
          }}>
            {t.ownTemplate}
          </button>
        </nav>

        {/* Language switch */}
        <div style={{ display: "flex", gap: 2, borderLeft: "1px solid #ffffff33", paddingLeft: 14 }}>
          {["no", "en", "pl"].map(l => (
            <button key={l} onClick={() => setLang(l)} aria-label={l} style={{
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700,
              padding: "4px 8px", borderRadius: 4, border: "none", cursor: "pointer",
              textTransform: "uppercase",
              background: lang === l ? T.signal : "transparent",
              color: lang === l ? T.ink : "#ffffff88",
            }}>
              {l}
            </button>
          ))}
        </div>

        <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: T.signal }}>
          €0,47 {t.used}
        </div>
      </header>

      <main style={{ flex: 1, minHeight: 0, overflowY: view === "project" && step === 3 ? "hidden" : "auto" }}>
        {view === "templates" && <TemplateImport t={t} onDone={() => { setView("project"); setStep(1); }} />}
        {view === "project" && step <= 1 && <StepUnderstand t={t} confirmed={confirmed} onConfirm={() => { setConfirmed(true); setTimeout(() => setStep(2), 350); }} />}
        {view === "project" && step === 2 && <StepStructure t={t} onNext={() => setStep(3)} />}
        {view === "project" && step === 3 && <StepBuild t={t} hover={hover} setHover={setHover} />}
        {view === "project" && step === 4 && (
          <div style={{ maxWidth: 560, margin: "0 auto", padding: "60px 24px", textAlign: "center" }}>
            <h2 style={{ fontFamily: "'Archivo', sans-serif", fontWeight: 900, fontSize: 26 }}>{t.exportH}</h2>
            <p style={{ color: T.gap, fontWeight: 700, fontSize: 14 }}>{t.exportBlock}</p>
            <p style={{ color: T.steel, fontSize: 13.5 }}>{t.exportInfo}</p>
            <PrimaryBtn onClick={() => setStep(3)}>{t.backBtn}</PrimaryBtn>
          </div>
        )}
      </main>

      {view === "project" && step === 3 && (
        <footer style={{ display: "flex", alignItems: "center", gap: 18, padding: "0 18px", height: 46, background: T.sheet, borderTop: `1px solid ${T.line}`, flexShrink: 0 }}>
          <span style={{ fontSize: 12.5 }}><strong style={{ color: T.ok }}>7 {t.factsTraced}</strong> · {t.allTraceable}</span>
          <span style={{ fontSize: 12.5, color: T.gap, display: "flex", gap: 6, alignItems: "center" }}><SevDot sev="blocking" /> {t.oneBlocking}</span>
          <span style={{ fontSize: 12.5, color: "#8a6d00", display: "flex", gap: 6, alignItems: "center" }}><SevDot sev="warning" /> {t.oneWarning}</span>
          <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: T.steel, marginLeft: "auto" }}>{t.hoverHint}</span>
          <button onClick={() => setStep(4)} style={{
            fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 13,
            background: blocking ? "#E4E1D8" : T.signal, color: blocking ? T.steel : T.ink,
            border: "none", borderRadius: 6, padding: "9px 18px", cursor: "pointer",
          }}>
            {t.exportBtn}
          </button>
        </footer>
      )}
    </div>
  );
}
