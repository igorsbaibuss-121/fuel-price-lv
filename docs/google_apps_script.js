/**
 * Degvielas cenu Google Sheet
 * ===========================
 * Ielādē datus no GitHub un uztur 3 lapas:
 *   - Šodien   : aktuālās lētākās cenas
 *   - Vēsture  : visi dati
 *   - Tendences: cenu izmaiņas pa dienām (tabula)
 *
 * Pirmreizējā uzstādīšana:
 *   1. Izvēlies "uzstadit"    → ▶  (dati + auto-triggers, ~20 sek)
 *   2. Izvēlies "veidoGrafikus" → ▶  (grafiki, ~2-3 min, tikai reizi!)
 *   3. Apstiprina atļaujas kad Google lūdz
 *
 * Pēc tam dati un grafiki atjaunināsies automātiski katru dienu 09:30.
 * Manuāla atjaunināšana: izvēlies "atjauninat" → ▶  (~20 sek)
 *
 * SVARĪGI: GitHub repozitorijam jābūt publiskam!
 * github.com → repozitorijs → Settings → Change visibility → Public
 */

const GITHUB_CSV_URL =
  "https://raw.githubusercontent.com/igorsbaibuss-121/fuel-price-lv/main/data/price_history.csv";

const FUEL_TYPES     = ["petrol_95", "petrol_98", "diesel"];  // Tendences lapai
const FUEL_DISPLAY   = {
  petrol_95:   "Benzīns 95",
  petrol_98:   "Benzīns 98",
  diesel:      "Dīzelis",
  diesel_plus: "Dīzelis Plus",
  lpg:         "Autogāze",
  cng:         "CNG",
};
// Vēlamā kārtība degvielas veidu tabulā
const FUEL_ORDER = ["petrol_95", "petrol_98", "diesel", "diesel_plus", "lpg", "cng"];
const PROVIDER_ORDER = ["Circle K", "Neste", "Virši", "VIADA"];

const DARK_BLUE  = "#1F3864";
const LIGHT_BLUE = "#EBF3FB";
const MID_BLUE   = "#2E75B6";
const ALT_ROW    = "#D6E4F0";
const GREEN_BG   = "#E2EFDA";
const HOLIDAY_BG = "#FFF2CC";
const HOLIDAY_FG = "#7F3F00";

const DISCLAIMER =
  "Cenām ir informatīvs raksturs, tās var mainīties vairākkārtīgi dienas laikā " +
  "un atšķirties dažādās degvielas uzpildes stacijās. " +
  "Informācija par degvielas cenām netiek atjaunota brīvdienās un svētku dienās.";


// ── Ikdienas atjaunināšana ────────────────────────────────────────────────

function atjauninat() {
  const rows = ieladeCSV();
  if (!rows) return;
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  veidoSodienLapu(ss, rows);
  veidoVestureLapu(ss, rows);
  veidoTendencesLapu(ss, rows);
  ss.toast("Dati atjaunināti! ✅", "Degvielas cenas", 4);
}


// ── Vienreizējā uzstādīšana ───────────────────────────────────────────────

function uzstadit() {
  atjauninat();

  // Uzstāda automātisku atjaunināšanu katru dienu 09:30
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "atjauninat")
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("atjauninat")
    .timeBased().atHour(9).nearMinute(30).everyDays(1).create();

  SpreadsheetApp.getActiveSpreadsheet()
    .toast("Uzstādīts! Tagad palaid 'veidoGrafikus' grafikiem ✅", "Gatavs", 8);
}


// ── Grafiku izveide (palaid vienu reizi, ~2-3 min) ────────────────────────
// Pēc tam grafiki auto-atjauninās kopā ar datiem katru dienu.
// Ja pēc daudziem mēnešiem grafiki neietver jaunākos datumus —
// palaid šo funkciju vēlreiz.

function veidoGrafikus() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ws = ss.getSheetByName("Tendences");
  if (!ws) {
    SpreadsheetApp.getUi().alert("Vispirms palaid 'uzstadit'!");
    return;
  }

  // Noņem vecos grafikus
  ws.getCharts().forEach(c => ws.removeChart(c));

  const lastRow = ws.getLastRow();
  // +500 rindas nākotnei (~1.5 gads), tukšas rindas grafikā tiek ignorētas
  const maxRow  = lastRow + 500;
  const sectW   = 1 + PROVIDER_ORDER.length; // 5 kolonnas katrai sekcijai

  FUEL_TYPES.forEach((fuelType, fi) => {
    const fuelLabel = FUEL_DISPLAY[fuelType];
    const startCol  = 1 + fi * (sectW + 1); // atstarpe 1 kolonna starp sekcijām

    // Datu diapazons: galvene (rinda 2) + dati (līdz maxRow)
    const dataRange = ws.getRange(2, startCol, maxRow - 1, sectW);

    const chart = ws.newChart()
      .setChartType(Charts.ChartType.LINE)
      .addRange(dataRange)
      .setOption("title",              fuelLabel + " — cenu tendence")
      .setOption("vAxis.title",        "Cena (EUR/L)")
      .setOption("hAxis.title",        "Datums")
      .setOption("legend.position",    "bottom")
      .setOption("interpolateNulls",   true)
      .setOption("width",  500)
      .setOption("height", 300)
      .setPosition(lastRow + 3, startCol, 0, 0)
      .build();

    ws.insertChart(chart);
  });

  ss.toast("Grafiki izveidoti! ✅", "Tendences", 5);
}


// ── CSV ielāde no GitHub ──────────────────────────────────────────────────

function ieladeCSV() {
  const resp = UrlFetchApp.fetch(GITHUB_CSV_URL, { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) {
    SpreadsheetApp.getUi().alert(
      "Neizdevās ielādēt datus.\n\n" +
      "Pārbaudi vai GitHub repozitorijs ir PUBLISKS:\n" +
      "github.com → repozitorijs → Settings → Change visibility → Public\n\n" +
      "HTTP kods: " + resp.getResponseCode()
    );
    return null;
  }
  return Utilities.parseCsv(resp.getContentText());
}


// ── Brīvdienu/svētku pārbaude ────────────────────────────────────────────

/** Aprēķina Lieldienu datumu pēc Gregoriānā algoritma. */
function easterDate(year) {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day   = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}

/** Atgriež Latvijas valsts svētku sarakstu norādītajam gadam. */
function latvijasHolidays(year) {
  const add = (d, n) => { const r = new Date(d); r.setDate(r.getDate() + n); return r; };
  const easter = easterDate(year);

  // Mātes diena — otrā svētdiena maijā
  let matesD = new Date(year, 4, 1);
  let sunCount = 0;
  while (sunCount < 2) {
    if (matesD.getDay() === 0) sunCount++;
    if (sunCount < 2) matesD.setDate(matesD.getDate() + 1);
  }

  return [
    { date: new Date(year, 0,  1),  name: "Jaunais Gads" },
    { date: add(easter, -2),        name: "Lielā Piektdiena" },
    { date: easter,                 name: "Lieldienas" },
    { date: add(easter,  1),        name: "Otrās Lieldienas" },
    { date: new Date(year, 4,  1),  name: "Darba svētki" },
    { date: new Date(year, 4,  4),  name: "Latvijas Republikas Neatkarības atjaunošanas diena" },
    { date: matesD,                 name: "Mātes diena" },
    { date: new Date(year, 5, 23),  name: "Līgo diena" },
    { date: new Date(year, 5, 24),  name: "Jāņu diena" },
    { date: new Date(year, 10, 18), name: "Latvijas Republikas proklamēšanas diena" },
    { date: new Date(year, 11, 24), name: "Ziemassvētku vakars" },
    { date: new Date(year, 11, 25), name: "Ziemassvētki" },
    { date: new Date(year, 11, 26), name: "Otrie Ziemassvētki" },
    { date: new Date(year, 11, 31), name: "Vecgada vakars" },
  ];
}

const LV_WEEKDAYS = ["svētdiena", "pirmdiena", "otrdiena", "trešdiena",
                     "ceturtdiena", "piektdiena", "sestdiena"];

/**
 * Atgriež null ja parastā darba diena,
 * vai apraksta tekstu ja brīvdiena/svētku diena.
 */
function getHolidayInfo(date) {
  const dow = date.getDay(); // 0=svētdiena, 6=sestdiena
  if (dow === 0 || dow === 6) return "Šodien ir " + LV_WEEKDAYS[dow];

  const ds = date.toDateString();
  const found = latvijasHolidays(date.getFullYear()).find(h => h.date.toDateString() === ds);
  if (found) return "Šodien ir svētku diena: " + found.name;

  return null;
}


// ── Lapa "Šodien" ─────────────────────────────────────────────────────────

const COMPARE_FUELS    = ["petrol_95", "petrol_98", "diesel"];  // piegādātāju tabulas kolonnas
const FUEL_LABEL_FULL  = FUEL_DISPLAY;  // alias — izmanto FUEL_DISPLAY
const ORANGE_BG          = "#FCE4D6";
const N_COLS             = 7;

function r3(v) { return Math.round(v * 1000) / 1000; }

function veidoSodienLapu(ss, rows) {
  let ws = ss.getSheetByName("Šodien");
  if (!ws) ws = ss.insertSheet("Šodien", 0);
  ws.clear();

  const idx      = kolonnas(rows[0]);
  const jaunakais = jaunakaisDatums(rows, idx);
  const dd        = rows.slice(1).filter(r => r[idx.date] === jaunakais);

  let row = 1;

  // ── Virsraksts ──
  ws.getRange(row, 1, 1, N_COLS).merge()
    .setValue("🔍 Degvielas cenu kopsavilkums — Latvija  •  " + formatDate(jaunakais))
    .setBackground(LIGHT_BLUE).setFontColor(DARK_BLUE)
    .setFontWeight("bold").setFontSize(14)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  ws.setRowHeight(row++, 34);

  // ── Subtituls ──
  ws.getRange(row, 1, 1, N_COLS).merge()
    .setValue("Vidējās mazumtirdzniecības cenas EUR/L (ieskaitot PVN)")
    .setBackground(LIGHT_BLUE).setFontColor("#595959").setFontStyle("italic")
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  ws.setRowHeight(row++, 20);

  // ── Atjaunināšanas laiks ──
  const now = new Date();
  const refreshLabel = "Atjaunots: " + Utilities.formatDate(
    now, Session.getScriptTimeZone(), "dd.MM.yyyy, HH:mm"
  );
  ws.getRange(row, 1, 1, N_COLS).merge()
    .setValue(refreshLabel)
    .setBackground(LIGHT_BLUE).setFontColor("#595959").setFontSize(9)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  ws.setRowHeight(row++, 16);


  // ── Brīvdienas/svētku paziņojums ──
  const holidayInfo = getHolidayInfo(new Date());
  if (holidayInfo) {
    ws.getRange(row, 1, 1, N_COLS).merge()
      .setValue("⚠️  " + holidayInfo + " — degvielas cenu informācija var nebūt atjaunināta")
      .setBackground(HOLIDAY_BG).setFontColor(HOLIDAY_FG)
      .setFontWeight("bold").setFontSize(11)
      .setHorizontalAlignment("center").setVerticalAlignment("middle");
    ws.setRowHeight(row++, 24);
  }

  // ── 1. tabula: piegādātāju salīdzinājums ──
  // Virsraksti
  ws.getRange(row, 1, 1, N_COLS)
    .setValues([["Piegādātājs", "Benzīns 95", "Benzīns 98", "Dīzelis", "Lētākā degviela", "Min cena", "Staciju skaits"]])
    .setBackground(DARK_BLUE).setFontColor("white").setFontWeight("bold")
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  ws.setRowHeight(row++, 22);

  // Lētākā cena katrā degvielas kolonnā (zaļš izcēlums)
  const colMin = {};
  COMPARE_FUELS.forEach(f => {
    const vals = dd.filter(r => r[idx.fuel] === f).map(r => parseFloat(r[idx.min])).filter(v => !isNaN(v));
    colMin[f] = vals.length ? Math.min(...vals) : null;
  });

  PROVIDER_ORDER.forEach((provider, i) => {
    const pRows = dd.filter(r => r[idx.provider] === provider);
    const prices = {};
    pRows.forEach(r => { prices[r[idx.fuel]] = parseFloat(r[idx.min]); });

    const validEntries = Object.entries(prices).filter(([, v]) => !isNaN(v));
    const cheapEntry   = validEntries.length ? validEntries.reduce((a, b) => a[1] < b[1] ? a : b) : null;
    const cheapFuel    = cheapEntry ? (FUEL_LABEL_FULL[cheapEntry[0]] || cheapEntry[0]) : "";
    const minPrice     = cheapEntry ? cheapEntry[1] : null;

    const bg   = i % 2 === 0 ? "#FFFFFF" : ALT_ROW;
    const rowBg = [bg, bg, bg, bg, bg, bg, bg];
    COMPARE_FUELS.forEach((f, fi) => {
      if (prices[f] != null && !isNaN(prices[f]) && colMin[f] != null && Math.abs(prices[f] - colMin[f]) < 0.0005)
        rowBg[fi + 1] = GREEN_BG;
    });

    // Staciju skaits — ņem pirmo pieejamo vērtību no šī piegādātāja rindām
    const stationRow = pRows.find(r => idx.stations >= 0 && r[idx.stations] !== "");
    const stationCount = stationRow ? parseInt(stationRow[idx.stations]) || "" : "";

    ws.getRange(row, 1, 1, N_COLS).setValues([[
      provider,
      !isNaN(prices["petrol_95"]) ? prices["petrol_95"] : "",
      !isNaN(prices["petrol_98"]) ? prices["petrol_98"] : "",
      !isNaN(prices["diesel"])    ? prices["diesel"]    : "",
      cheapFuel,
      minPrice !== null ? minPrice : "",
      stationCount
    ]]).setBackgrounds([rowBg]).setVerticalAlignment("middle");
    ws.getRange(row, 1).setFontWeight("bold").setHorizontalAlignment("left");
    ws.getRange(row, 2, 1, 3).setNumberFormat("€0.000").setHorizontalAlignment("center");
    ws.getRange(row, 5, 1, 1).setHorizontalAlignment("center");
    ws.getRange(row, 6, 1, 1).setNumberFormat("€0.000").setHorizontalAlignment("center");
    ws.getRange(row, 7, 1, 1).setHorizontalAlignment("center");
    ws.setRowHeight(row++, 18);
  });

  // Leģenda
  row++;
  ws.getRange(row, 1, 1, N_COLS).merge()
    .setValue("✅ Zaļš fons = lētākā cena šajā kategorijā")
    .setFontStyle("italic").setFontColor("#375623").setBackground(GREEN_BG);
  ws.setRowHeight(row++, 18);

  // ── 2. tabula: degvielas veidu kopsavilkums ──
  row++;
  ws.getRange(row, 1, 1, N_COLS)
    .setValues([["Degviela", "Min cena", "Vidējā cena", "Max cena", "Starpība", "Lētākais", "Dārgākais"]])
    .setBackground(MID_BLUE).setFontColor("white").setFontWeight("bold")
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  ws.setRowHeight(row++, 22);

  // Rāda visus degvielas veidus kas ir datos, FUEL_ORDER kārtībā
  const fuelsInData = FUEL_ORDER.filter(f => dd.some(r => r[idx.fuel] === f));
  fuelsInData.forEach((fuel, i) => {
    const fRows = dd.filter(r => r[idx.fuel] === fuel);
    if (!fRows.length) return;

    const mins = fRows.map(r => parseFloat(r[idx.min])).filter(v => !isNaN(v));
    const avgs = fRows.map(r => parseFloat(r[idx.avg])).filter(v => !isNaN(v));
    if (!mins.length) return;

    const minVal = Math.min(...mins);
    const maxVal = Math.max(...mins);
    const avgVal = avgs.length ? avgs.reduce((a, b) => a + b, 0) / avgs.length : minVal;

    const byProv = {};
    fRows.forEach(r => { const v = parseFloat(r[idx.min]); if (!isNaN(v)) byProv[r[idx.provider]] = v; });
    const entries   = Object.entries(byProv);
    const cheapest  = entries.length ? entries.reduce((a, b) => a[1] < b[1] ? a : b)[0] : "";
    const dearest   = entries.length ? entries.reduce((a, b) => a[1] > b[1] ? a : b)[0] : "";

    const bg    = i % 2 === 0 ? "#FFFFFF" : ALT_ROW;
    ws.getRange(row, 1, 1, N_COLS).setValues([[
      FUEL_LABEL_FULL[fuel] || fuel,
      r3(minVal), r3(avgVal), r3(maxVal), r3(maxVal - minVal),
      cheapest, dearest
    ]]).setBackgrounds([[bg, GREEN_BG, bg, ORANGE_BG, bg, bg, bg]])
      .setVerticalAlignment("middle");
    ws.getRange(row, 1).setHorizontalAlignment("left");
    ws.getRange(row, 2, 1, 5).setNumberFormat("€0.000").setHorizontalAlignment("center");
    ws.getRange(row, 6, 1, 2).setHorizontalAlignment("center");
    ws.setRowHeight(row++, 18);
  });

  // ── Atruna ──
  row++;
  ws.getRange(row, 1, 1, N_COLS).merge()
    .setValue(DISCLAIMER)
    .setFontStyle("italic").setFontSize(9).setFontColor("#595959")
    .setHorizontalAlignment("left").setVerticalAlignment("middle").setWrap(true);
  ws.setRowHeight(row, 40);

  // Kolonnu platumi
  [130, 85, 85, 85, 150, 85, 85].forEach((w, i) => ws.setColumnWidth(i + 1, w));
  ws.setFrozenRows(holidayInfo ? 0 : 0);
}


// ── Lapa "Vēsture" ────────────────────────────────────────────────────────

function veidoVestureLapu(ss, rows) {
  let ws = ss.getSheetByName("Vēsture");
  if (!ws) ws = ss.insertSheet("Vēsture");
  ws.clearContents();
  if (rows.length === 0) return;

  ws.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  ws.getRange(1, 1, 1, rows[0].length)
    .setBackground(DARK_BLUE).setFontColor("white").setFontWeight("bold");

  const idx = kolonnas(rows[0]);
  if (rows.length > 1) {
    ws.getRange(2, idx.min + 1, rows.length - 1, 1).setNumberFormat("0.000");
    ws.getRange(2, idx.avg + 1, rows.length - 1, 1).setNumberFormat("0.000");
  }
  ws.autoResizeColumns(1, rows[0].length);
  ws.setFrozenRows(1);
}


// ── Lapa "Tendences" (tabula pa degvielas veidiem) ────────────────────────

function veidoTendencesLapu(ss, rows) {
  let ws = ss.getSheetByName("Tendences");
  if (!ws) ws = ss.insertSheet("Tendences");
  ws.clearContents();

  const idx = kolonnas(rows[0]);
  const allDates = [...new Set(rows.slice(1).map(r => r[idx.date]))].sort().reverse();

  // Indeksē datus pēc "date|provider|fuel" atslēgas ātrai meklēšanai
  const lookup = {};
  rows.slice(1).forEach(r => {
    lookup[`${r[idx.date]}|${r[idx.provider]}|${r[idx.fuel]}`] = parseFloat(r[idx.min]);
  });

  let col = 1;

  FUEL_TYPES.forEach(fuelType => {
    const label = FUEL_DISPLAY[fuelType];

    // Sadaļas virsraksts
    ws.getRange(1, col, 1, 1 + PROVIDER_ORDER.length).merge()
      .setValue(label).setBackground(LIGHT_BLUE).setFontColor(DARK_BLUE)
      .setFontWeight("bold").setFontSize(12).setHorizontalAlignment("center");

    // Kolonnu virsraksti
    ws.getRange(2, col, 1, 1 + PROVIDER_ORDER.length)
      .setValues([["Datums", ...PROVIDER_ORDER]])
      .setBackground(MID_BLUE).setFontColor("white").setFontWeight("bold")
      .setHorizontalAlignment("center");

    // Dati
    const values = [], bgs = [], fmts = [];
    allDates.forEach((date, i) => {
      const bg = i % 2 === 0 ? "#FFFFFF" : ALT_ROW;
      const rowVals = [formatDate(date)];
      const rowBgs  = [bg];
      const rowFmts = ["@"];

      const prices = PROVIDER_ORDER.map(p => {
        const v = lookup[`${date}|${p}|${fuelType}`];
        return isNaN(v) ? null : v;
      });
      const minVal = Math.min(...prices.filter(v => v !== null));

      prices.forEach(v => {
        rowVals.push(v !== null ? v : "");
        rowFmts.push("€0.000");
        rowBgs.push(v !== null && Math.abs(v - minVal) < 0.0005 ? GREEN_BG : bg);
      });

      values.push(rowVals);
      bgs.push(rowBgs);
      fmts.push(rowFmts);
    });

    if (values.length > 0) {
      const r = ws.getRange(3, col, values.length, 1 + PROVIDER_ORDER.length);
      r.setValues(values).setBackgrounds(bgs).setNumberFormats(fmts);
    }

    ws.setColumnWidth(col, 100);
    PROVIDER_ORDER.forEach((_, i) => ws.setColumnWidth(col + 1 + i, 100));
    col += PROVIDER_ORDER.length + 2; // atstarpe starp degvielas veidiem
  });

  ws.setFrozenRows(0);
  ws.setRowHeight(1, 28);
  ws.setRowHeight(2, 22);
}


// ── Palīgfunkcijas ────────────────────────────────────────────────────────

function kolonnas(header) {
  return {
    date:     header.indexOf("date"),
    provider: header.indexOf("provider"),
    fuel:     header.indexOf("fuel_type"),
    min:      header.indexOf("price_min"),
    avg:      header.indexOf("price_avg"),
    stations: header.indexOf("station_count"),  // -1 ja vecs CSV bez šīs kolonnas
  };
}

function jaunakaisDatums(rows, idx) {
  const dates = rows.slice(1).map(r => r[idx.date]).filter(d => d).sort();
  return dates[dates.length - 1] || "";
}

function formatDate(isoDate) {
  if (!isoDate) return "";
  const [y, m, d] = isoDate.split("-");
  return `${d}.${m}.${y}`;
}
