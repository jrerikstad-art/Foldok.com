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
  fact: "#1450B4",
  factBg: "#EAF1FD",
  gapBg: "#FDF0E8"
};
const STRINGS = {
  no: {
    steps: ["Kilder", "Forst\xE5", "Struktur", "Bygg", "Eksport"],
    projectName: "Batteripakke l\xF8fteverkt\xF8y \u2014 Kranprosjekt",
    ownTemplate: "+ Egen mal",
    used: "brukt",
    // Understand
    cpA: "SJEKKPUNKT A",
    understandH: "Her er hva jeg tror dette er",
    understandSub: "Rett meg f\xF8r vi bygger noe. Alt nedenfor kan redigeres.",
    artifactName: "L\xF8fteverkt\xF8y for batteripakke",
    artifactDesc: "L\xF8fteredskap \xB7 brukes til \xE5 heise batterimoduler med kran, fire festepunkter",
    sure: "sikker",
    components: "HOVEDKOMPONENTER",
    hazards: "IDENTIFISERTE FARER",
    compList: ["L\xF8fteramme (S355)", "4 \xD7 l\xF8fte\xF8rer", "Sjakler med splint", "Kjettingsett 4-part"],
    hazList: ["Hengende last", "Klemfare ved tilkobling", "Utstyrssvikt / slitasje"],
    lifecycle: ["transport", "installasjon", "bruk", "vedlikehold", "inspeksjon"],
    confirmBtn: "Dette stemmer \u2014 fortsett",
    confirmedBtn: "\u2713 Bekreftet",
    editBtn: "Rediger",
    // Structure
    cpB: "SJEKKPUNKT B",
    structureH: "Foresl\xE5tt struktur",
    structureSub: (n, f) => `Teknisk dokumentasjonspakke \xB7 ${n} seksjoner \xB7 ${f} kilder kartlagt`,
    blockingW: "blokkerende",
    warningW: "advarsel",
    facts: "fakta",
    noPhotos: "ingen bilder",
    generateBtn: "Generer utkast \u2192",
    estCalls: "est. 9 kall \xB7 ~\u20AC0,14",
    sections: ["Forside og identifikasjon", "Tiltenkt bruk og begrensninger", "Sikkerhetsinformasjon", "Tekniske data", "Produktbeskrivelse", "Installasjon / montering", "Bruk / drift", "Vedlikehold og inspeksjon", "Test- og verifikasjonsdok."],
    gapTorque: "Tiltrekkingsmoment ikke funnet",
    gapInterval: "Inspeksjonsintervall mangler \u2014 p\xE5krevd for l\xF8fteutstyr",
    // Build
    sources: "KILDER",
    indexed: "filer \xB7 indeksert",
    docType: "TEKNISK DOKUMENTASJONSPAKKE \xB7 REV A",
    draft: "UTKAST",
    serialLbl: "Serienr.",
    docTitle: "L\xF8fteverkt\xF8y for batteripakke",
    secTech: "4 \xB7 Tekniske data",
    secOper: "7 \xB7 Bruk / drift",
    secMaint: "8 \xB7 Vedlikehold og inspeksjon",
    techRows: ["Sikker arbeidslast (SWL)", "Pr\xF8velast (1,5 \xD7 SWL)", "Egenvekt", "Ytre m\xE5l (L \xD7 B \xD7 H)", "Hovedmateriale", "Teststandard"],
    warnTitle: "\u26A0 ADVARSEL \u2014 Hengende last.",
    warnBody: "Opphold under lasten kan medf\xF8re alvorlig personskade eller d\xF8d. Sperr av omr\xE5det f\xF8r l\xF8ft.",
    steps4: ["Kontroller verkt\xF8yet visuelt f\xF8r bruk (se pkt. 8).", "Fest alle fire sjakler til l\xF8fte\xF8rene. Kontroller at splinter er montert.", "L\xF8ft lasten maks 100 mm og kontroller balanse f\xF8r videre heising.", "L\xF8ft aldri mer enn"],
    maintCols: ["Hva", "Intervall", "Utf\xF8res av"],
    maintRow1: ["Visuell kontroll (sprekker, deformasjon)", "F\xF8r hver bruk", "Operat\xF8r"],
    maintRow2Who: "Sakkyndig virksomhet",
    maintRow2What: "Sakkyndig kontroll",
    manglerLbl: "MANGLER",
    manglerKey: "inspeksjonsintervall",
    gapMsg: "intervall for sakkyndig kontroll finnes ikke i kildene.",
    blockingLbl: "Blokkerende:",
    provideBtn: "Oppgi verdi",
    blockActions: ["\u21BB Regenerer", "\u2702 Kort ned", "\u232B Tilbakestill"],
    factsTraced: "fakta sitert",
    allTraceable: "alle sporbare",
    oneBlocking: "1 blokkerende mangel",
    oneWarning: "1 advarsel",
    hoverHint: "hover en verdi \u2192 se kilden",
    exportBtn: "Eksporter PDF \xB7 \u20AC19",
    srcTip: "Kilde",
    conf: "konfidens",
    // Export
    exportH: "Klar for eksport?",
    exportBlock: "1 blokkerende mangel m\xE5 l\xF8ses f\xF8rst: inspeksjonsintervall.",
    exportInfo: "N\xE5r mangelen er l\xF8st: ansvarsbekreftelse \u2192 betaling \u20AC19 \u2192 ren PDF uten vannmerke.",
    backBtn: "\u2190 Tilbake til dokumentet",
    // Import
    ownLbl: "EGEN MAL",
    importH: "Importer din egen mal",
    importSub: "Last opp skjemaet dere bruker i dag \u2014 Word, PDF eller et foto av papirskjemaet. Foldok leser strukturen og fyller det for deg p\xE5 hver jobb.",
    dropZone: "Slipp fil her eller klikk for \xE5 velge",
    dropHint: "docx \xB7 pdf \xB7 jpg \u2014 demo: Dartec-testrapport-v3.docx",
    foundH: "Fant 3 seksjoner og 10 felt",
    foundSub: "Dartec-testrapport-v3.docx \xB7 trykk p\xE5 kravniv\xE5 for \xE5 endre. Blokkerende felt m\xE5 fylles f\xF8r eksport.",
    foundCost: "1 uttrekkskall \xB7 \u20AC0,02 \xB7 kj\xF8res aldri igjen for denne filen",
    foundSecs: "SEKSJONER: Utstyrsdata \xB7 Kontrollresultater \xB7 Signering",
    ownField: "eget felt",
    reqB: "Blokkerende",
    reqW: "Advarsel",
    reqI: "Valgfritt",
    boilerNote: "Fast tekst funnet:",
    boilerBody: "erkl\xE6ringsavsnitt nederst i skjemaet beholdes ordrett \u2014 AI endrer aldri juridisk tekst fra importerte maler.",
    saveTemplate: "Lagre som firmamal \u2192",
    doneH: "\u2713 Malen er klar",
    doneBody: ["\xABDartec testrapport\xBB ligger n\xE5 i malvelgeren ved siden av de innebygde.", "Hver jobb fremover: ta bilder av utstyret, snakk inn observasjonene \u2014 feltene fylles automatisk, med kildesporing p\xE5 hver verdi. Logo og stempel fra firmaprofilen legges p\xE5 ved eksport."],
    useBtn: "Bruk p\xE5 et prosjekt",
    importFields: ["Serienr. / ID-merking", "Utstyrstype", "SWL / WLL", "Fabrikat", "Kontrolldato", "Neste kontroll", "Visuell kontroll (OK/Avvik)", "NDT-resultat", "Anmerkninger", "Kontroll\xF8r"],
    fileCaps: ["L\xF8fteverkt\xF8y montert p\xE5 batteripakke, sett forfra. Gul ramme, fire l\xF8ftepunkter.", "Merkeskilt: SWL 3.2t, serienr. BLT-2026-011, produsent stemplet.", "Lasttest utf\xF8rt til 1.5 \xD7 SWL (4.8t) uten deformasjon. EN 13155. Testinstans: TI-Lab AS.", "Sjakkel festes til l\xF8fte\xF8re, splint synlig montert.", "Alle fire l\xF8ftepunkter tilkoblet, kjettingsett i vinkel ca. 45\xB0.", "N\xE6rbilde slitasjemerke p\xE5 krokspiss \u2014 innenfor toleranse.", "Egenvekt 42 kg. Ytre m\xE5l 1240 \xD7 860 \xD7 310 mm. Materiale S355.", "Verkt\xF8yet hengende i kranhake, fri h\xF8yde, verksted."]
  },
  en: {
    steps: ["Sources", "Understand", "Structure", "Build", "Export"],
    projectName: "Battery Pack Lifting Tool \u2014 Crane Project",
    ownTemplate: "+ Own template",
    used: "used",
    cpA: "CHECKPOINT A",
    understandH: "Here's what I think this is",
    understandSub: "Correct me before we build anything. Everything below is editable.",
    artifactName: "Battery pack lifting tool",
    artifactDesc: "Lifting device \xB7 used to hoist battery modules by crane, four attachment points",
    sure: "confident",
    components: "MAIN COMPONENTS",
    hazards: "IDENTIFIED HAZARDS",
    compList: ["Lifting frame (S355)", "4 \xD7 lifting eyes", "Shackles with split pins", "4-leg chain set"],
    hazList: ["Suspended load", "Crush hazard during hook-up", "Equipment failure / wear"],
    lifecycle: ["transport", "installation", "operation", "maintenance", "inspection"],
    confirmBtn: "This is correct \u2014 continue",
    confirmedBtn: "\u2713 Confirmed",
    editBtn: "Edit",
    cpB: "CHECKPOINT B",
    structureH: "Proposed structure",
    structureSub: (n, f) => `Technical documentation package \xB7 ${n} sections \xB7 ${f} sources mapped`,
    blockingW: "blocking",
    warningW: "warning",
    facts: "facts",
    noPhotos: "no photos",
    generateBtn: "Generate draft \u2192",
    estCalls: "est. 9 calls \xB7 ~\u20AC0.14",
    sections: ["Cover & identification", "Intended use & limitations", "Safety information", "Technical data", "Product description", "Installation / assembly", "Operation", "Maintenance & inspection", "Test & verification docs"],
    gapTorque: "Torque values not found",
    gapInterval: "Inspection interval missing \u2014 required for lifting equipment",
    sources: "SOURCES",
    indexed: "files \xB7 indexed",
    docType: "TECHNICAL DOCUMENTATION PACKAGE \xB7 REV A",
    draft: "DRAFT",
    serialLbl: "Serial no.",
    docTitle: "Battery Pack Lifting Tool",
    secTech: "4 \xB7 Technical data",
    secOper: "7 \xB7 Operation",
    secMaint: "8 \xB7 Maintenance & inspection",
    techRows: ["Safe working load (SWL)", "Proof load (1.5 \xD7 SWL)", "Dead weight", "Overall dimensions (L \xD7 W \xD7 H)", "Main material", "Test standard"],
    warnTitle: "\u26A0 WARNING \u2014 Suspended load.",
    warnBody: "Standing under the load may result in serious injury or death. Barrier the area before lifting.",
    steps4: ["Visually inspect the tool before use (see section 8).", "Attach all four shackles to the lifting eyes. Verify split pins are fitted.", "Lift the load max 100 mm and check balance before continuing.", "Never lift more than"],
    maintCols: ["What", "Interval", "Performed by"],
    maintRow1: ["Visual check (cracks, deformation)", "Before each use", "Operator"],
    maintRow2Who: "Competent body",
    maintRow2What: "Thorough examination",
    manglerLbl: "MISSING",
    manglerKey: "inspection interval",
    gapMsg: "interval for thorough examination not found in sources.",
    blockingLbl: "Blocking:",
    provideBtn: "Provide value",
    blockActions: ["\u21BB Regenerate", "\u2702 Shorten", "\u232B Revert"],
    factsTraced: "facts cited",
    allTraceable: "all traceable",
    oneBlocking: "1 blocking gap",
    oneWarning: "1 warning",
    hoverHint: "hover a value \u2192 see its source",
    exportBtn: "Export PDF \xB7 \u20AC19",
    srcTip: "Source",
    conf: "confidence",
    exportH: "Ready to export?",
    exportBlock: "1 blocking gap must be resolved first: inspection interval.",
    exportInfo: "Once resolved: responsibility confirmation \u2192 payment \u20AC19 \u2192 clean PDF without watermark.",
    backBtn: "\u2190 Back to document",
    ownLbl: "OWN TEMPLATE",
    importH: "Import your own template",
    importSub: "Upload the form you use today \u2014 Word, PDF or a photo of the paper form. Foldok reads the structure and fills it for you on every job.",
    dropZone: "Drop file here or click to choose",
    dropHint: "docx \xB7 pdf \xB7 jpg \u2014 demo: Dartec-testrapport-v3.docx",
    foundH: "Found 3 sections and 10 fields",
    foundSub: "Dartec-testrapport-v3.docx \xB7 tap the requirement level to change it. Blocking fields must be filled before export.",
    foundCost: "1 extraction call \xB7 \u20AC0.02 \xB7 never runs again for this file",
    foundSecs: "SECTIONS: Equipment data \xB7 Inspection results \xB7 Sign-off",
    ownField: "custom field",
    reqB: "Blocking",
    reqW: "Warning",
    reqI: "Optional",
    boilerNote: "Fixed text found:",
    boilerBody: "the declaration paragraph at the bottom of the form is kept verbatim \u2014 AI never rewrites legal text from imported templates.",
    saveTemplate: "Save as company template \u2192",
    doneH: "\u2713 Template is ready",
    doneBody: ["\u201CDartec test report\u201D now sits in the template picker next to the built-ins.", "Every job from now on: photograph the equipment, speak your observations \u2014 the fields fill automatically, with source tracing on every value. Logo and stamp from your company profile are applied at export."],
    useBtn: "Use on a project",
    importFields: ["Serial no. / ID marking", "Equipment type", "SWL / WLL", "Manufacturer", "Inspection date", "Next inspection", "Visual check (OK/Deviation)", "NDT result", "Remarks", "Inspector"],
    fileCaps: ["Lifting tool mounted on battery pack, front view. Yellow frame, four lifting points.", "Nameplate: SWL 3.2t, serial no. BLT-2026-011, manufacturer stamped.", "Load test performed to 1.5 \xD7 SWL (4.8t) without deformation. EN 13155. Test body: TI-Lab AS.", "Shackle attached to lifting eye, split pin visibly fitted.", "All four lifting points connected, chain set at approx. 45\xB0 angle.", "Close-up of wear mark on hook tip \u2014 within tolerance.", "Dead weight 42 kg. Dimensions 1240 \xD7 860 \xD7 310 mm. Material S355.", "Tool hanging in crane hook, free height, workshop."]
  },
  pl: {
    steps: ["\u0179r\xF3d\u0142a", "Zrozum", "Struktura", "Buduj", "Eksport"],
    projectName: "Trawersa do pakietu baterii \u2014 Projekt d\u017Awigowy",
    ownTemplate: "+ W\u0142asny szablon",
    used: "zu\u017Cyto",
    cpA: "PUNKT KONTROLNY A",
    understandH: "Oto co my\u015Bl\u0119, \u017Ce to jest",
    understandSub: "Popraw mnie zanim cokolwiek zbudujemy. Wszystko poni\u017Cej mo\u017Cna edytowa\u0107.",
    artifactName: "Trawersa do pakietu baterii",
    artifactDesc: "Zawiesie \xB7 s\u0142u\u017Cy do podnoszenia modu\u0142\xF3w baterii d\u017Awigiem, cztery punkty mocowania",
    sure: "pewno\u015Bci",
    components: "G\u0141\xD3WNE KOMPONENTY",
    hazards: "ZIDENTYFIKOWANE ZAGRO\u017BENIA",
    compList: ["Rama no\u015Bna (S355)", "4 \xD7 ucha transportowe", "Szekle z zawleczkami", "Zawiesie \u0142a\u0144cuchowe 4-ci\u0119gnowe"],
    hazList: ["Wisz\u0105cy \u0142adunek", "Ryzyko zgniecenia przy podpinaniu", "Awaria sprz\u0119tu / zu\u017Cycie"],
    lifecycle: ["transport", "monta\u017C", "eksploatacja", "konserwacja", "przegl\u0105d"],
    confirmBtn: "Zgadza si\u0119 \u2014 kontynuuj",
    confirmedBtn: "\u2713 Potwierdzono",
    editBtn: "Edytuj",
    cpB: "PUNKT KONTROLNY B",
    structureH: "Proponowana struktura",
    structureSub: (n, f) => `Pakiet dokumentacji technicznej \xB7 ${n} sekcji \xB7 ${f} \u017Ar\xF3de\u0142 przypisanych`,
    blockingW: "blokuj\u0105ce",
    warningW: "ostrze\u017Cenie",
    facts: "fakt\xF3w",
    noPhotos: "brak zdj\u0119\u0107",
    generateBtn: "Generuj szkic \u2192",
    estCalls: "szac. 9 zapyta\u0144 \xB7 ~0,14 \u20AC",
    sections: ["Strona tytu\u0142owa i identyfikacja", "Przeznaczenie i ograniczenia", "Informacje bezpiecze\u0144stwa", "Dane techniczne", "Opis produktu", "Monta\u017C / instalacja", "Eksploatacja", "Konserwacja i przegl\u0105dy", "Dokumentacja bada\u0144"],
    gapTorque: "Nie znaleziono moment\xF3w dokr\u0119cania",
    gapInterval: "Brak okresu przegl\u0105du \u2014 wymagany dla sprz\u0119tu d\u017Awigowego",
    sources: "\u0179R\xD3D\u0141A",
    indexed: "plik\xF3w \xB7 zindeksowano",
    docType: "PAKIET DOKUMENTACJI TECHNICZNEJ \xB7 REW. A",
    draft: "SZKIC",
    serialLbl: "Nr seryjny",
    docTitle: "Trawersa do pakietu baterii",
    secTech: "4 \xB7 Dane techniczne",
    secOper: "7 \xB7 Eksploatacja",
    secMaint: "8 \xB7 Konserwacja i przegl\u0105dy",
    techRows: ["Dopuszczalne obci\u0105\u017Cenie (SWL)", "Obci\u0105\u017Cenie pr\xF3bne (1,5 \xD7 SWL)", "Masa w\u0142asna", "Wymiary (D \xD7 S \xD7 W)", "Materia\u0142 g\u0142\xF3wny", "Norma badawcza"],
    warnTitle: "\u26A0 OSTRZE\u017BENIE \u2014 Wisz\u0105cy \u0142adunek.",
    warnBody: "Przebywanie pod \u0142adunkiem grozi powa\u017Cnymi obra\u017Ceniami lub \u015Bmierci\u0105. Wygrod\u017A stref\u0119 przed podnoszeniem.",
    steps4: ["Sprawd\u017A wzrokowo narz\u0119dzie przed u\u017Cyciem (patrz pkt 8).", "Podepnij wszystkie cztery szekle do uch. Sprawd\u017A zawleczki.", "Podnie\u015B \u0142adunek maks. 100 mm i sprawd\u017A wywa\u017Cenie przed dalszym podnoszeniem.", "Nigdy nie podno\u015B wi\u0119cej ni\u017C"],
    maintCols: ["Co", "Okres", "Wykonuje"],
    maintRow1: ["Kontrola wzrokowa (p\u0119kni\u0119cia, odkszta\u0142cenia)", "Przed ka\u017Cdym u\u017Cyciem", "Operator"],
    maintRow2Who: "Jednostka uprawniona",
    maintRow2What: "Przegl\u0105d okresowy",
    manglerLbl: "BRAK",
    manglerKey: "okres przegl\u0105du",
    gapMsg: "okres przegl\u0105du okresowego nie wyst\u0119puje w \u017Ar\xF3d\u0142ach.",
    blockingLbl: "Blokuj\u0105ce:",
    provideBtn: "Podaj warto\u015B\u0107",
    blockActions: ["\u21BB Generuj ponownie", "\u2702 Skr\xF3\u0107", "\u232B Cofnij"],
    factsTraced: "fakt\xF3w cytowanych",
    allTraceable: "wszystkie identyfikowalne",
    oneBlocking: "1 brak blokuj\u0105cy",
    oneWarning: "1 ostrze\u017Cenie",
    hoverHint: "najed\u017A na warto\u015B\u0107 \u2192 zobacz \u017Ar\xF3d\u0142o",
    exportBtn: "Eksportuj PDF \xB7 19 \u20AC",
    srcTip: "\u0179r\xF3d\u0142o",
    conf: "pewno\u015B\u0107",
    exportH: "Gotowe do eksportu?",
    exportBlock: "Najpierw usu\u0144 1 brak blokuj\u0105cy: okres przegl\u0105du.",
    exportInfo: "Po usuni\u0119ciu: potwierdzenie odpowiedzialno\u015Bci \u2192 p\u0142atno\u015B\u0107 19 \u20AC \u2192 czysty PDF bez znaku wodnego.",
    backBtn: "\u2190 Wr\xF3\u0107 do dokumentu",
    ownLbl: "W\u0141ASNY SZABLON",
    importH: "Importuj w\u0142asny szablon",
    importSub: "Prze\u015Blij formularz, kt\xF3rego u\u017Cywacie dzi\u015B \u2014 Word, PDF lub zdj\u0119cie papierowego formularza. Foldok odczyta struktur\u0119 i wype\u0142ni go za Ciebie przy ka\u017Cdej pracy.",
    dropZone: "Upu\u015B\u0107 plik tutaj lub kliknij, aby wybra\u0107",
    dropHint: "docx \xB7 pdf \xB7 jpg \u2014 demo: Dartec-testrapport-v3.docx",
    foundH: "Znaleziono 3 sekcje i 10 p\xF3l",
    foundSub: "Dartec-testrapport-v3.docx \xB7 dotknij poziomu wymogu, aby zmieni\u0107. Pola blokuj\u0105ce musz\u0105 by\u0107 wype\u0142nione przed eksportem.",
    foundCost: "1 zapytanie ekstrakcji \xB7 0,02 \u20AC \xB7 nigdy nie uruchomi si\u0119 ponownie dla tego pliku",
    foundSecs: "SEKCJE: Dane sprz\u0119tu \xB7 Wyniki kontroli \xB7 Podpisy",
    ownField: "pole w\u0142asne",
    reqB: "Blokuj\u0105ce",
    reqW: "Ostrze\u017Cenie",
    reqI: "Opcjonalne",
    boilerNote: "Znaleziono sta\u0142y tekst:",
    boilerBody: "akapit deklaracji na dole formularza zachowany dos\u0142ownie \u2014 AI nigdy nie przepisuje tekstu prawnego z importowanych szablon\xF3w.",
    saveTemplate: "Zapisz jako szablon firmowy \u2192",
    doneH: "\u2713 Szablon gotowy",
    doneBody: ["\u201EDartec raport z bada\u0144\u201D znajduje si\u0119 teraz w wyborze szablon\xF3w obok wbudowanych.", "Ka\u017Cda praca od teraz: sfotografuj sprz\u0119t, nagraj obserwacje \u2014 pola wype\u0142niaj\u0105 si\u0119 automatycznie, z identyfikacj\u0105 \u017Ar\xF3d\u0142a ka\u017Cdej warto\u015Bci. Logo i piecz\u0119\u0107 z profilu firmy nak\u0142adane przy eksporcie."],
    useBtn: "U\u017Cyj w projekcie",
    importFields: ["Nr seryjny / oznaczenie", "Typ sprz\u0119tu", "SWL / WLL", "Producent", "Data kontroli", "Nast\u0119pna kontrola", "Kontrola wzrokowa (OK/Uwagi)", "Wynik NDT", "Uwagi", "Kontroler"],
    fileCaps: ["Trawersa zamontowana na pakiecie baterii, widok z przodu. \u017B\xF3\u0142ta rama, cztery punkty podnoszenia.", "Tabliczka: SWL 3.2t, nr ser. BLT-2026-011, producent wybity.", "Pr\xF3ba obci\u0105\u017Ceniowa do 1.5 \xD7 SWL (4.8t) bez odkszta\u0142ce\u0144. EN 13155. Jednostka: TI-Lab AS.", "Szekla podpi\u0119ta do ucha, zawleczka widocznie zamontowana.", "Wszystkie cztery punkty podpi\u0119te, \u0142a\u0144cuchy pod k\u0105tem ok. 45\xB0.", "Zbli\u017Cenie \u015Bladu zu\u017Cycia na ko\u0144c\xF3wce haka \u2014 w tolerancji.", "Masa w\u0142asna 42 kg. Wymiary 1240 \xD7 860 \xD7 310 mm. Materia\u0142 S355.", "Narz\u0119dzie wisz\u0105ce na haku d\u017Awigu, wolna wysoko\u015B\u0107, warsztat."]
  }
};
const FILE_META = [
  { id: "f1", name: "IMG_2841.jpg", kind: "photo", tags: ["overview", "frame"], hue: "#8a93a6" },
  { id: "f2", name: "IMG_2844.jpg", kind: "photo", tags: ["nameplate", "swl"], hue: "#a6988a" },
  { id: "f3", name: "lasttest_rapport.pdf", kind: "pdf", tags: ["test", "EN 13155"], hue: "#7d8c7a" },
  { id: "f4", name: "IMG_2851.jpg", kind: "photo", tags: ["assembly", "shackle"], hue: "#96848f" },
  { id: "f5", name: "IMG_2852.jpg", kind: "photo", tags: ["assembly", "rigging"], hue: "#8a93a6" },
  { id: "f6", name: "IMG_2860.jpg", kind: "photo", tags: ["wear", "inspection"], hue: "#a68a8a" },
  { id: "f7", name: "vekt_dimensjoner.xlsx", kind: "sheet", tags: ["weight", "dims"], hue: "#7a8c8a" },
  { id: "f8", name: "IMG_2839.jpg", kind: "photo", tags: ["overview", "crane"], hue: "#8a93a6" }
];
const FACTS = [
  { id: "swl", value: "3,2", unit: "t", src: "f2", conf: 0.97 },
  { id: "serial", value: "BLT-2026-011", unit: "", src: "f2", conf: 0.95 },
  { id: "test", value: "EN 13155", unit: "", src: "f3", conf: 0.96 },
  { id: "proof", value: "4,8", unit: "t", src: "f3", conf: 0.94 },
  { id: "weight", value: "42", unit: "kg", src: "f7", conf: 0.92 },
  { id: "dims", value: "1240 \xD7 860 \xD7 310", unit: "mm", src: "f7", conf: 0.9 },
  { id: "mat", value: "S355", unit: "", src: "f7", conf: 0.88 }
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
  { key: "testdoc", files: ["f3"], facts: 2, gaps: [] }
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
  { key: "inspector_name", canonical: true, req: "blocking" }
];
const FileThumb = ({ f, cap, lit, dim, onHover }) => /* @__PURE__ */ React.createElement(
  "div",
  {
    onMouseEnter: () => onHover && onHover(f.id),
    onMouseLeave: () => onHover && onHover(null),
    style: {
      display: "flex",
      gap: 10,
      padding: 10,
      borderRadius: 6,
      cursor: "default",
      background: lit ? "#FFF6CE" : T.sheet,
      border: `1px solid ${lit ? T.signal : T.line}`,
      boxShadow: lit ? `0 0 0 2px ${T.signal}` : "none",
      opacity: dim ? 0.38 : 1,
      transition: "all .18s ease"
    }
  },
  /* @__PURE__ */ React.createElement("div", { style: {
    width: 52,
    height: 52,
    borderRadius: 4,
    flexShrink: 0,
    background: `linear-gradient(135deg, ${f.hue}, ${f.hue}66)`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    fontWeight: 600
  } }, f.kind === "photo" ? "IMG" : f.kind === "pdf" ? "PDF" : "XLS"),
  /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" } }, f.name), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 11, color: T.steel, lineHeight: 1.35, marginTop: 2, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" } }, cap), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4, marginTop: 5, flexWrap: "wrap" } }, f.tags.map((t) => /* @__PURE__ */ React.createElement("span", { key: t, style: { fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", padding: "1px 5px", background: T.paper, border: `1px solid ${T.line}`, borderRadius: 3, color: T.steel } }, t))))
);
const Fact = ({ f, t, onHover }) => /* @__PURE__ */ React.createElement(
  "span",
  {
    onMouseEnter: () => onHover(f.src),
    onMouseLeave: () => onHover(null),
    title: `${t.srcTip}: ${FILE_META.find((x) => x.id === f.src)?.name} \xB7 ${t.conf} ${Math.round(f.conf * 100)}%`,
    style: {
      fontFamily: "'IBM Plex Mono', monospace",
      fontSize: "0.92em",
      fontWeight: 600,
      color: T.fact,
      background: T.factBg,
      borderBottom: `2px solid ${T.fact}`,
      padding: "0 3px",
      borderRadius: 2,
      cursor: "help",
      whiteSpace: "nowrap"
    }
  },
  f.value,
  f.unit ? ` ${f.unit}` : ""
);
const Mangler = ({ t }) => /* @__PURE__ */ React.createElement("span", { style: {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: "0.85em",
  fontWeight: 700,
  color: T.gap,
  background: T.gapBg,
  border: `1.5px dashed ${T.gap}`,
  padding: "1px 7px",
  borderRadius: 3,
  whiteSpace: "nowrap"
} }, t.manglerLbl, ": ", t.manglerKey);
const SevDot = ({ sev }) => /* @__PURE__ */ React.createElement("span", { style: { width: 8, height: 8, borderRadius: 99, flexShrink: 0, marginTop: 5, background: sev === "blocking" ? T.gap : T.signal } });
const H2 = ({ children }) => /* @__PURE__ */ React.createElement("h2", { style: { fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 26, margin: "0 0 6px", letterSpacing: "-0.01em" } }, children);
const Eyebrow = ({ children }) => /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'Archivo', sans-serif", fontSize: 11, letterSpacing: "0.14em", fontWeight: 700, color: T.steel, marginBottom: 8 } }, children);
const PrimaryBtn = ({ children, onClick, bg = T.ink, color = "#fff" }) => /* @__PURE__ */ React.createElement("button", { onClick, style: { fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 14, background: bg, color, border: "none", borderRadius: 6, padding: "12px 22px", cursor: "pointer" } }, children);
const StepUnderstand = ({ t, onConfirm, confirmed }) => /* @__PURE__ */ React.createElement("div", { style: { maxWidth: 640, margin: "0 auto", padding: "40px 24px" } }, /* @__PURE__ */ React.createElement(Eyebrow, null, t.cpA), /* @__PURE__ */ React.createElement(H2, null, t.understandH), /* @__PURE__ */ React.createElement("p", { style: { color: T.steel, fontSize: 14, margin: "0 0 24px" } }, t.understandSub), /* @__PURE__ */ React.createElement("div", { style: { background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 8, overflow: "hidden" } }, /* @__PURE__ */ React.createElement("div", { style: { padding: "18px 22px", borderBottom: `1px solid ${T.line}`, display: "flex", justifyContent: "space-between", alignItems: "baseline" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 19 } }, t.artifactName), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 13, color: T.steel, marginTop: 3 } }, t.artifactDesc)), /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: T.ok, fontWeight: 700 } }, "91% ", t.sure)), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr" } }, /* @__PURE__ */ React.createElement("div", { style: { padding: "16px 22px", borderRight: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: T.steel, marginBottom: 10 } }, t.components), t.compList.map((c) => /* @__PURE__ */ React.createElement("div", { key: c, style: { fontSize: 13.5, padding: "5px 0", borderBottom: `1px dotted ${T.line}` } }, c))), /* @__PURE__ */ React.createElement("div", { style: { padding: "16px 22px" } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color: T.steel, marginBottom: 10 } }, t.hazards), t.hazList.map((h) => /* @__PURE__ */ React.createElement("div", { key: h, style: { fontSize: 13.5, padding: "5px 0", borderBottom: `1px dotted ${T.line}`, display: "flex", gap: 8, alignItems: "flex-start" } }, /* @__PURE__ */ React.createElement(SevDot, { sev: "warning" }), h)))), /* @__PURE__ */ React.createElement("div", { style: { padding: "14px 22px", borderTop: `1px solid ${T.line}`, background: T.paper, display: "flex", gap: 8, flexWrap: "wrap" } }, t.lifecycle.map((s) => /* @__PURE__ */ React.createElement("span", { key: s, style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, padding: "3px 9px", background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 99 } }, s)))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, marginTop: 20 } }, /* @__PURE__ */ React.createElement(PrimaryBtn, { onClick: onConfirm, bg: confirmed ? T.ok : T.ink }, confirmed ? t.confirmedBtn : t.confirmBtn), /* @__PURE__ */ React.createElement("button", { style: { fontFamily: "'Archivo', sans-serif", fontWeight: 600, fontSize: 14, background: "transparent", color: T.steel, border: `1px solid ${T.line}`, borderRadius: 6, padding: "12px 18px", cursor: "pointer" } }, t.editBtn)));
const StepStructure = ({ t, onNext }) => {
  const blocking = SECTION_META.flatMap((s) => s.gaps).filter((g) => g.sev === "blocking").length;
  const warnings = SECTION_META.flatMap((s) => s.gaps).filter((g) => g.sev === "warning").length;
  return /* @__PURE__ */ React.createElement("div", { style: { maxWidth: 720, margin: "0 auto", padding: "40px 24px" } }, /* @__PURE__ */ React.createElement(Eyebrow, null, t.cpB), /* @__PURE__ */ React.createElement(H2, null, t.structureH), /* @__PURE__ */ React.createElement("p", { style: { color: T.steel, fontSize: 14, margin: "0 0 20px" } }, t.structureSub(SECTION_META.length, FILE_META.length), " \xB7", " ", /* @__PURE__ */ React.createElement("span", { style: { color: T.gap, fontWeight: 700 } }, blocking, " ", t.blockingW), " \xB7 ", /* @__PURE__ */ React.createElement("span", { style: { fontWeight: 700 } }, warnings, " ", t.warningW)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 8 } }, SECTION_META.map((s, i) => /* @__PURE__ */ React.createElement("div", { key: s.key, style: { display: "flex", alignItems: "center", gap: 14, background: T.sheet, border: `1px solid ${s.gaps.some((g) => g.sev === "blocking") ? T.gap : T.line}`, borderRadius: 6, padding: "12px 16px" } }, /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: T.steel, width: 20 } }, String(i + 1).padStart(2, "0")), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, minWidth: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { fontWeight: 700, fontSize: 14 } }, t.sections[i]), s.gaps.map((g) => /* @__PURE__ */ React.createElement("div", { key: g.t, style: { fontSize: 12, color: g.sev === "blocking" ? T.gap : "#8a6d00", marginTop: 3, display: "flex", gap: 6, alignItems: "flex-start" } }, /* @__PURE__ */ React.createElement(SevDot, { sev: g.sev }), t[g.t]))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, s.files.map((fid) => {
    const f = FILE_META.find((x) => x.id === fid);
    return /* @__PURE__ */ React.createElement("div", { key: fid, title: f.name, style: { width: 26, height: 26, borderRadius: 4, background: `linear-gradient(135deg, ${f.hue}, ${f.hue}66)` } });
  }), s.files.length === 0 && /* @__PURE__ */ React.createElement("span", { style: { fontSize: 11, color: T.steel, fontStyle: "italic" } }, t.noPhotos)), /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: s.facts > 0 ? T.fact : T.steel, width: 58, textAlign: "right" } }, s.facts, " ", t.facts), /* @__PURE__ */ React.createElement("span", { style: { cursor: "grab", color: T.line, fontSize: 16, userSelect: "none" } }, "\u283F")))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 14, marginTop: 22 } }, /* @__PURE__ */ React.createElement(PrimaryBtn, { onClick: onNext }, t.generateBtn), /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: T.steel } }, t.estCalls)));
};
const BlockToolbar = ({ t }) => /* @__PURE__ */ React.createElement("div", { className: "blockbar", style: {
  position: "absolute",
  top: -14,
  right: 8,
  display: "flex",
  gap: 4,
  background: T.ink,
  borderRadius: 6,
  padding: "4px 6px",
  opacity: 0,
  transition: "opacity .15s",
  pointerEvents: "none"
} }, t.blockActions.map((a) => /* @__PURE__ */ React.createElement("span", { key: a, style: { fontSize: 10.5, color: "#fff", fontFamily: "'Archivo', sans-serif", fontWeight: 600, padding: "2px 7px", cursor: "pointer", borderRadius: 3 } }, a)));
const DocBlock = ({ t, children }) => /* @__PURE__ */ React.createElement("div", { className: "docblock", style: { position: "relative", padding: "4px 8px", margin: "0 -8px", borderRadius: 4 } }, /* @__PURE__ */ React.createElement(BlockToolbar, { t }), children);
const StepBuild = ({ t, hover, setHover }) => {
  const fx = (id) => FACTS.find((f) => f.id === id);
  const litFiles = hover ? /* @__PURE__ */ new Set([hover]) : null;
  const secH = { fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 16, borderBottom: `2px solid ${T.ink}`, paddingBottom: 5, margin: "26px 0 12px" };
  return /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "340px 1fr", height: "100%", minHeight: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { borderRight: `1px solid ${T.line}`, overflowY: "auto", padding: 14, background: T.paper } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 } }, /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 12, letterSpacing: "0.1em" } }, t.sources), /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: T.steel } }, FILE_META.length, " ", t.indexed)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 8 } }, FILE_META.map((f, i) => /* @__PURE__ */ React.createElement(FileThumb, { key: f.id, f, cap: t.fileCaps[i], lit: litFiles?.has(f.id), dim: litFiles && !litFiles.has(f.id) })))), /* @__PURE__ */ React.createElement("div", { style: { overflowY: "auto", padding: "26px 34px", background: "#E9E7E0" } }, /* @__PURE__ */ React.createElement("div", { style: {
    maxWidth: 660,
    margin: "0 auto",
    background: T.sheet,
    borderRadius: 3,
    boxShadow: "0 2px 14px rgba(20,22,28,0.10)",
    padding: "44px 52px 56px",
    position: "relative"
  } }, /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: 16, right: 20, fontFamily: "'Archivo', sans-serif", fontWeight: 900, fontSize: 12, letterSpacing: "0.2em", color: "#00000018", border: "2px solid #00000014", padding: "3px 10px", transform: "rotate(3deg)" } }, t.draft), /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: T.steel, letterSpacing: "0.06em" } }, t.docType), /* @__PURE__ */ React.createElement("h1", { style: { fontFamily: "'Archivo', sans-serif", fontWeight: 900, fontSize: 30, letterSpacing: "-0.015em", margin: "8px 0 2px" } }, t.docTitle), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 13.5, color: T.steel, marginBottom: 26 } }, t.serialLbl, " ", /* @__PURE__ */ React.createElement(Fact, { f: fx("serial"), t, onHover: setHover }), " \xB7 The Fuzzy Front"), /* @__PURE__ */ React.createElement("h2", { style: secH }, t.secTech), /* @__PURE__ */ React.createElement(DocBlock, { t }, /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 13.5 } }, /* @__PURE__ */ React.createElement("tbody", null, [fx("swl"), fx("proof"), fx("weight"), fx("dims"), fx("mat"), fx("test")].map((f, i) => /* @__PURE__ */ React.createElement("tr", { key: i, style: { borderBottom: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "7px 0", color: T.steel, width: "55%" } }, t.techRows[i]), /* @__PURE__ */ React.createElement("td", { style: { padding: "7px 0" } }, /* @__PURE__ */ React.createElement(Fact, { f, t, onHover: setHover }))))))), /* @__PURE__ */ React.createElement("h2", { style: { ...secH, marginTop: 30 } }, t.secOper), /* @__PURE__ */ React.createElement(DocBlock, { t }, /* @__PURE__ */ React.createElement("div", { style: { background: "#FFF8E0", border: `1px solid ${T.signal}`, borderLeft: `5px solid ${T.signal}`, borderRadius: 4, padding: "10px 14px", margin: "6px 0 14px", fontSize: 13 } }, /* @__PURE__ */ React.createElement("strong", { style: { fontFamily: "'Archivo', sans-serif" } }, t.warnTitle), " ", t.warnBody)), /* @__PURE__ */ React.createElement(DocBlock, { t }, /* @__PURE__ */ React.createElement("ol", { style: { fontSize: 13.5, lineHeight: 1.75, paddingLeft: 22, margin: 0 } }, /* @__PURE__ */ React.createElement("li", null, t.steps4[0]), /* @__PURE__ */ React.createElement("li", null, t.steps4[1]), /* @__PURE__ */ React.createElement("li", null, t.steps4[2]), /* @__PURE__ */ React.createElement("li", null, t.steps4[3], " ", /* @__PURE__ */ React.createElement(Fact, { f: fx("swl"), t, onHover: setHover }), "."))), /* @__PURE__ */ React.createElement("h2", { style: { ...secH, marginTop: 30 } }, t.secMaint), /* @__PURE__ */ React.createElement(DocBlock, { t }, /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 13.5 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { borderBottom: `2px solid ${T.ink}` } }, t.maintCols.map((h) => /* @__PURE__ */ React.createElement("th", { key: h, style: { textAlign: "left", padding: "6px 0", fontFamily: "'Archivo', sans-serif", fontSize: 12 } }, h)))), /* @__PURE__ */ React.createElement("tbody", null, /* @__PURE__ */ React.createElement("tr", { style: { borderBottom: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "8px 0" } }, t.maintRow1[0]), /* @__PURE__ */ React.createElement("td", null, t.maintRow1[1]), /* @__PURE__ */ React.createElement("td", null, t.maintRow1[2])), /* @__PURE__ */ React.createElement("tr", { style: { borderBottom: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("td", { style: { padding: "8px 0" } }, t.maintRow2What), /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement(Mangler, { t })), /* @__PURE__ */ React.createElement("td", null, t.maintRow2Who)))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: 10, fontSize: 12, color: T.gap, display: "flex", gap: 8, alignItems: "center" } }, /* @__PURE__ */ React.createElement(SevDot, { sev: "blocking" }), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("strong", null, t.blockingLbl), " ", t.gapMsg), /* @__PURE__ */ React.createElement("button", { style: { fontFamily: "'Archivo', sans-serif", fontWeight: 700, fontSize: 11, background: T.gapBg, color: T.gap, border: `1px solid ${T.gap}`, borderRadius: 4, padding: "3px 10px", cursor: "pointer" } }, t.provideBtn))))));
};
const TemplateImport = ({ t, onDone }) => {
  const [phase, setPhase] = useState(0);
  const [reqs, setReqs] = useState(Object.fromEntries(IMPORT_META.map((f) => [f.key, f.req])));
  const cycle = (k) => setReqs((r) => ({ ...r, [k]: r[k] === "blocking" ? "warning" : r[k] === "warning" ? "info" : "blocking" }));
  const reqStyle = (r) => r === "blocking" ? { background: T.gapBg, color: T.gap, border: `1px solid ${T.gap}` } : r === "warning" ? { background: "#FFF8E0", color: "#8a6d00", border: `1px solid ${T.signal}` } : { background: T.paper, color: T.steel, border: `1px solid ${T.line}` };
  const reqLabel = (r) => r === "blocking" ? t.reqB : r === "warning" ? t.reqW : t.reqI;
  return /* @__PURE__ */ React.createElement("div", { style: { maxWidth: 640, margin: "0 auto", padding: "40px 24px" } }, /* @__PURE__ */ React.createElement(Eyebrow, null, t.ownLbl), phase === 0 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(H2, null, t.importH), /* @__PURE__ */ React.createElement("p", { style: { color: T.steel, fontSize: 14, margin: "0 0 24px" } }, t.importSub), /* @__PURE__ */ React.createElement("button", { onClick: () => setPhase(1), style: {
    width: "100%",
    padding: "44px 20px",
    background: T.sheet,
    borderRadius: 8,
    cursor: "pointer",
    border: `2px dashed ${T.line}`,
    fontFamily: "'Archivo', sans-serif",
    color: T.steel,
    fontSize: 14
  } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 28, marginBottom: 8 } }, "\u2B06"), /* @__PURE__ */ React.createElement("strong", { style: { color: T.ink } }, t.dropZone), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 12, marginTop: 6 } }, t.dropHint))), phase === 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(H2, null, t.foundH), /* @__PURE__ */ React.createElement("p", { style: { color: T.steel, fontSize: 14, margin: "0 0 6px" } }, t.foundSub), /* @__PURE__ */ React.createElement("p", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: T.steel, margin: "0 0 18px" } }, t.foundCost), /* @__PURE__ */ React.createElement("div", { style: { background: T.sheet, border: `1px solid ${T.line}`, borderRadius: 8, overflow: "hidden" } }, /* @__PURE__ */ React.createElement("div", { style: { padding: "12px 18px", borderBottom: `1px solid ${T.line}`, background: T.paper, fontFamily: "'Archivo', sans-serif", fontWeight: 800, fontSize: 12, letterSpacing: "0.08em" } }, t.foundSecs), IMPORT_META.map((f, i) => /* @__PURE__ */ React.createElement("div", { key: f.key, style: { display: "flex", alignItems: "center", gap: 12, padding: "10px 18px", borderBottom: `1px solid ${T.line}` } }, /* @__PURE__ */ React.createElement("div", { style: { flex: 1 } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 13.5, fontWeight: 600 } }, t.importFields[i]), f.canonical ? /* @__PURE__ */ React.createElement("span", { style: { marginLeft: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: T.fact } }, "\u2192 ", f.key) : /* @__PURE__ */ React.createElement("span", { style: { marginLeft: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: T.steel } }, t.ownField)), /* @__PURE__ */ React.createElement("button", { onClick: () => cycle(f.key), style: {
    fontFamily: "'Archivo', sans-serif",
    fontWeight: 700,
    fontSize: 11,
    padding: "3px 12px",
    borderRadius: 99,
    cursor: "pointer",
    ...reqStyle(reqs[f.key])
  } }, reqLabel(reqs[f.key])))), /* @__PURE__ */ React.createElement("div", { style: { padding: "12px 18px", background: "#FFF8E0", fontSize: 12.5, borderTop: `1px solid ${T.signal}` } }, /* @__PURE__ */ React.createElement("strong", null, t.boilerNote), " ", t.boilerBody)), /* @__PURE__ */ React.createElement("div", { style: { marginTop: 20 } }, /* @__PURE__ */ React.createElement(PrimaryBtn, { onClick: () => setPhase(2) }, t.saveTemplate))), phase === 2 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(H2, null, t.doneH), /* @__PURE__ */ React.createElement("p", { style: { fontSize: 14, color: T.steel, lineHeight: 1.6 } }, /* @__PURE__ */ React.createElement("strong", { style: { color: T.ink } }, t.doneBody[0]), /* @__PURE__ */ React.createElement("br", null), t.doneBody[1]), /* @__PURE__ */ React.createElement("div", { style: { marginTop: 18 } }, /* @__PURE__ */ React.createElement(PrimaryBtn, { onClick: onDone, bg: T.signal, color: T.ink }, t.useBtn))));
};
window.FoldokCompiler = function FoldokCompiler() {
  const [lang, setLang] = useState("no");
  const [step, setStep] = useState(1);
  const [confirmed, setConfirmed] = useState(false);
  const [hover, setHover] = useState(null);
  const [view, setView] = useState("project");
  const t = STRINGS[lang];
  const blocking = 1;
  return /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'Archivo', sans-serif", color: T.ink, background: T.paper, height: "100vh", display: "flex", flexDirection: "column" } }, /* @__PURE__ */ React.createElement("style", null, `
        @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800;900&family=IBM+Plex+Mono:wght@400;600;700&display=swap');
        * { box-sizing: border-box; }
        button:focus-visible { outline: 3px solid ${T.signal}; outline-offset: 2px; }
        .docblock:hover { background: #FBFAF6; }
        .docblock:hover .blockbar { opacity: 1; pointer-events: auto; }
        @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
      `), /* @__PURE__ */ React.createElement("header", { style: { display: "flex", alignItems: "center", gap: 16, padding: "0 18px", height: 54, background: T.ink, color: "#fff", flexShrink: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8 } }, /* @__PURE__ */ React.createElement("span", { style: { width: 22, height: 22, background: T.signal, borderRadius: 3, display: "inline-flex", alignItems: "center", justifyContent: "center", color: T.ink, fontWeight: 900, fontSize: 13 } }, "F"), /* @__PURE__ */ React.createElement("span", { style: { fontWeight: 900, letterSpacing: "0.02em", fontSize: 15 } }, "FOLDOK")), /* @__PURE__ */ React.createElement("span", { style: { fontSize: 13, color: "#ffffff99", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" } }, t.projectName), /* @__PURE__ */ React.createElement("nav", { style: { display: "flex", gap: 2, marginLeft: "auto" } }, t.steps.map((s, i) => {
    const active = view === "project" && i === step, done = i < step;
    return /* @__PURE__ */ React.createElement("button", { key: s, onClick: () => {
      setView("project");
      setStep(i);
    }, style: {
      fontFamily: "'Archivo', sans-serif",
      fontSize: 12,
      fontWeight: 700,
      letterSpacing: "0.04em",
      padding: "6px 14px",
      borderRadius: 99,
      border: "none",
      cursor: "pointer",
      background: active ? T.signal : "transparent",
      color: active ? T.ink : done ? "#fff" : "#ffffff66"
    } }, done ? "\u2713 " : "", s);
  }), /* @__PURE__ */ React.createElement("button", { onClick: () => setView("templates"), style: {
    fontFamily: "'Archivo', sans-serif",
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: "0.04em",
    padding: "6px 14px",
    borderRadius: 99,
    cursor: "pointer",
    border: `1px solid ${view === "templates" ? T.signal : "#ffffff33"}`,
    background: view === "templates" ? T.signal : "transparent",
    color: view === "templates" ? T.ink : "#ffffffcc",
    marginLeft: 10
  } }, t.ownTemplate)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 2, borderLeft: "1px solid #ffffff33", paddingLeft: 14 } }, ["no", "en", "pl"].map((l) => /* @__PURE__ */ React.createElement("button", { key: l, onClick: () => setLang(l), "aria-label": l, style: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    fontWeight: 700,
    padding: "4px 8px",
    borderRadius: 4,
    border: "none",
    cursor: "pointer",
    textTransform: "uppercase",
    background: lang === l ? T.signal : "transparent",
    color: lang === l ? T.ink : "#ffffff88"
  } }, l))), /* @__PURE__ */ React.createElement("div", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: T.signal } }, "\u20AC0,47 ", t.used)), /* @__PURE__ */ React.createElement("main", { style: { flex: 1, minHeight: 0, overflowY: view === "project" && step === 3 ? "hidden" : "auto" } }, view === "templates" && /* @__PURE__ */ React.createElement(TemplateImport, { t, onDone: () => {
    setView("project");
    setStep(1);
  } }), view === "project" && step <= 1 && /* @__PURE__ */ React.createElement(StepUnderstand, { t, confirmed, onConfirm: () => {
    setConfirmed(true);
    setTimeout(() => setStep(2), 350);
  } }), view === "project" && step === 2 && /* @__PURE__ */ React.createElement(StepStructure, { t, onNext: () => setStep(3) }), view === "project" && step === 3 && /* @__PURE__ */ React.createElement(StepBuild, { t, hover, setHover }), view === "project" && step === 4 && /* @__PURE__ */ React.createElement("div", { style: { maxWidth: 560, margin: "0 auto", padding: "60px 24px", textAlign: "center" } }, /* @__PURE__ */ React.createElement("h2", { style: { fontFamily: "'Archivo', sans-serif", fontWeight: 900, fontSize: 26 } }, t.exportH), /* @__PURE__ */ React.createElement("p", { style: { color: T.gap, fontWeight: 700, fontSize: 14 } }, t.exportBlock), /* @__PURE__ */ React.createElement("p", { style: { color: T.steel, fontSize: 13.5 } }, t.exportInfo), /* @__PURE__ */ React.createElement(PrimaryBtn, { onClick: () => setStep(3) }, t.backBtn))), view === "project" && step === 3 && /* @__PURE__ */ React.createElement("footer", { style: { display: "flex", alignItems: "center", gap: 18, padding: "0 18px", height: 46, background: T.sheet, borderTop: `1px solid ${T.line}`, flexShrink: 0 } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 12.5 } }, /* @__PURE__ */ React.createElement("strong", { style: { color: T.ok } }, "7 ", t.factsTraced), " \xB7 ", t.allTraceable), /* @__PURE__ */ React.createElement("span", { style: { fontSize: 12.5, color: T.gap, display: "flex", gap: 6, alignItems: "center" } }, /* @__PURE__ */ React.createElement(SevDot, { sev: "blocking" }), " ", t.oneBlocking), /* @__PURE__ */ React.createElement("span", { style: { fontSize: 12.5, color: "#8a6d00", display: "flex", gap: 6, alignItems: "center" } }, /* @__PURE__ */ React.createElement(SevDot, { sev: "warning" }), " ", t.oneWarning), /* @__PURE__ */ React.createElement("span", { style: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: T.steel, marginLeft: "auto" } }, t.hoverHint), /* @__PURE__ */ React.createElement("button", { onClick: () => setStep(4), style: {
    fontFamily: "'Archivo', sans-serif",
    fontWeight: 800,
    fontSize: 13,
    background: blocking ? "#E4E1D8" : T.signal,
    color: blocking ? T.steel : T.ink,
    border: "none",
    borderRadius: 6,
    padding: "9px 18px",
    cursor: "pointer"
  } }, t.exportBtn)));
};
