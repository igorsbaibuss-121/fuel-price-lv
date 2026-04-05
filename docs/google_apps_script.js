/**
 * Degvielas cenu Google Sheet
 * ===========================
 * Ielādē datus no GitHub un uztur 3 lapas:
 *   - Šodien   : aktuālās lētākās cenas
 *   - Vēsture  : visi dati (tabula)
 *   - Tendences: cenu izmaiņas laika gaitā (grafiki)
 *
 * Pirmreizējā uzstādīšana (palaid VIENU REIZI):
 *   1. Izvēlies funkciju "uzstadit" → nospied ▶
 *   2. Apstiprina atļaujas (Google lūgs pirmo reizi)
 *   3. Gaidi ~2-3 minūtes — tiek veidoti grafiki
 *
 * Pēc uzstadit() dati atjaunināsies automātiski katru dienu 09:30.
 * Manuāla atjaunināšana: izvēlies "atjauninat" → ▶  (~15 sekundes)
 */

const GITHUB_CSV_URL =
  "https://raw.githubusercontent.com/igorsbaibuss-121/fuel-price-lv/main/data/price_history.csv";

const FUEL_TYPES     = ["petrol_95", "petrol_98", "diesel"];
const FUEL_DISPLAY   = { petrol_95: "Benzīns 95", petrol_98: "Benzīns 98", diesel: "Dīzelis" };
const PROVIDER_ORDER = ["Circle K", "Neste", "Virši", "VIADA"];

const DARK_BLUE  = "#1F3864";
const LIGHT_BLUE = "#EBF3FB";
const MID_BLUE   = "#2E75B6";
const ALT_ROW    = "#D6E4F0";
const GREEN_BG   = "#E2EFDA";


// ── Ātrā ikdienas atjaunināšana (~15 sek) ─────────────────────────────────

function atjauninat() {
  const rows = ieladeCSV();
  if (!rows) return;

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  veidoSodienLapu(ss, rows);
  veidoVestureLapu(ss, rows);
  atjauninatTendencesVertibas(ss, rows); // tikai vērtības, grafiki paliek

  ss.toast("Dati atjaunināti! ✅", "Degvielas cenas", 4);
}


// ── Vienreizējā uzstādīšana (lēna, veido grafikus) ────────────────────────

function uzstadit() {
  const rows = ieladeCSV();
  if (!rows) return;

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  veidoSodienLapu(ss, rows);
  veidoVestureLapu(ss, rows);
  veidoTendencesLapu(ss, rows); // veido grafikus — lēns, bet tikai reizi

  // Uzstāda automātisku atjaunināšanu katru dienu 09:30
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "atjauninat")
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("atjauninat")
    .timeBased().atHour(9).nearMinute(30).everyDays(1).create();

  ss.toast("Uzstādīts! Automātiska atjaunināšana katru dienu 09:30 ✅", "Gatavs", 8);
}


// ── CSV ielāde no GitHub ──────────────────────────────────────────────────

function ieladeCSV() {
  try {
    const resp = UrlFetchApp.fetch(GITHUB_CSV_URL, { muteHttpExceptions: true });
    if (resp.getResponseCode() !== 200) {
      SpreadsheetApp.getUi().alert("Neizdevās ielādēt datus no GitHub. Kods: " + resp.getResponseCode());
      return null;
    }
    return Utilities.parseCsv(resp.getContentText());
  } catch (e) {
    SpreadsheetApp.getUi().alert("Kļūda: " + e.message);
    return null;
  }
}


// ── Lapa "Šodien" ─────────────────────────────────────────────────────────

function veidoSodienLapu(ss, rows) {
  let ws = ss.getSheetByName("Šodien");
  if (!ws) { ws = ss.insertSheet("Šodien", 0); }
  ws.clearContents();
  ws.clearFormats();

  const idx = kolonnas(rows[0]);
  const jaunakais = jaunakaisDatums(rows, idx);
  const sodienDati = rows.slice(1).filter(r => r[idx.date] === jaunakais);

  // Galvene
  galvene(ws, `Lētākās degvielas cenas  •  ${formatDate(jaunakais)}`, 1, 5);
  ws.setRowHeight(1, 36);

  // Kolonnu virsraksti — batch setValues
  ws.getRange(2, 1, 1, 5).setValues([["Piegādātājs", "Benzīns 95", "Benzīns 98", "Dīzelis", "Lētākā"]]);
  stilsGalvene(ws.getRange(2, 1, 1, 5));
  ws.setRowHeight(2, 26);

  // Min cenas katrai kategorijai (lai izcelt zaļo)
  const fuelMins = {};
  FUEL_TYPES.forEach(f => {
    const p = sodienDati.filter(r => r[idx.fuel] === f).map(r => parseFloat(r[idx.min])).filter(v => !isNaN(v));
    fuelMins[f] = p.length ? Math.min(...p) : null;
  });

  // Vērtību un fonu masīvi priekš batch rakstīšanas
  const values = [];
  const bgs    = [];
  const fmts   = [];

  PROVIDER_ORDER.forEach((provider, i) => {
    const pRows = sodienDati.filter(r => r[idx.provider] === provider);
    const prices = {};
    pRows.forEach(r => { prices[r[idx.fuel]] = parseFloat(r[idx.min]); });

    const nums = FUEL_TYPES.map(f => prices[f] || null).filter(v => v !== null);
    const letaka = nums.length ? Math.min(...nums) : null;

    const bg = i % 2 === 0 ? "#FFFFFF" : ALT_ROW;
    const row = [provider,
                 prices["petrol_95"] || null,
                 prices["petrol_98"] || null,
                 prices["diesel"]    || null,
                 letaka];
    values.push(row);

    // Foni: noklusējums bg, zaļš kur lētākais
    const rowBg = [bg, bg, bg, bg, bg];
    FUEL_TYPES.forEach((f, fi) => {
      if (prices[f] && fuelMins[f] !== null && Math.abs(prices[f] - fuelMins[f]) < 0.0005) {
        rowBg[fi + 1] = GREEN_BG;
      }
    });
    bgs.push(rowBg);
    fmts.push(["@", "€0.000", "€0.000", "€0.000", "€0.000"]);
  });

  const dataRange = ws.getRange(3, 1, values.length, 5);
  dataRange.setValues(values);
  dataRange.setBackgrounds(bgs);
  dataRange.setNumberFormats(fmts);
  dataRange.setVerticalAlignment("middle");

  // Bold pirmā kolonna
  ws.getRange(3, 1, values.length, 1).setFontWeight("bold");

  // Rindas augstums
  for (let i = 3; i < 3 + values.length; i++) ws.setRowHeight(i, 24);

  // Leģenda
  const legRow = 3 + values.length + 1;
  ws.getRange(legRow, 1, 1, 5).merge()
    .setValue("✅ Zaļš = lētākā cena šajā kategorijā")
    .setFontStyle("italic").setFontColor("#375623").setBackground(GREEN_BG);

  ws.setColumnWidths(1, 5, 110);
  ws.setFrozenRows(2);
}


// ── Lapa "Vēsture" ────────────────────────────────────────────────────────

function veidoVestureLapu(ss, rows) {
  let ws = ss.getSheetByName("Vēsture");
  if (!ws) ws = ss.insertSheet("Vēsture");
  ws.clearContents();
  ws.clearFormats();
  if (rows.length === 0) return;

  ws.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  stilsGalvene(ws.getRange(1, 1, 1, rows[0].length));

  const idx = kolonnas(rows[0]);
  if (rows.length > 1) {
    ws.getRange(2, idx.min + 1, rows.length - 1, 1).setNumberFormat("0.000");
    ws.getRange(2, idx.avg + 1, rows.length - 1, 1).setNumberFormat("0.000");
  }
  ws.autoResizeColumns(1, rows[0].length);
  ws.setFrozenRows(1);
}


// ── Lapa "Tendences" — izveide ar grafikiem (vienu reizi) ─────────────────

function veidoTendencesLapu(ss, rows) {
  let ws = ss.getSheetByName("Tendences");
  if (!ws) ws = ss.insertSheet("Tendences");
  ws.clearContents();
  ws.clearFormats();
  ws.getCharts().forEach(c => ws.removeChart(c));

  const layout = uzrakstitTendencesTabulas(ws, rows);

  // Izveido grafikus (lēns solis)
  layout.forEach(({ fuelLabel, headerRow, dataStart, dataEnd }) => {
    if (dataEnd < dataStart) return;
    const nCols = 1 + PROVIDER_ORDER.length;
    const chartRange = ws.getRange(headerRow, 1, dataEnd - headerRow + 1, nCols);
    const chart = ws.newChart()
      .setChartType(Charts.ChartType.LINE)
      .addRange(chartRange)
      .setOption("title", `${fuelLabel} — cenu tendence`)
      .setOption("vAxis.title", "Cena (EUR/L)")
      .setOption("hAxis.title", "Datums")
      .setOption("legend.position", "bottom")
      .setOption("width", 520).setOption("height", 300)
      .setPosition(headerRow, nCols + 2, 0, 0)
      .build();
    ws.insertChart(chart);
  });

  ws.setColumnWidth(1, 110);
  PROVIDER_ORDER.forEach((_, i) => ws.setColumnWidth(i + 2, 105));
}


// ── Tendences — tikai vērtību atjaunināšana (ātrs, grafiki paliek) ────────

function atjauninatTendencesVertibas(ss, rows) {
  const ws = ss.getSheetByName("Tendences");
  if (!ws) return; // Nav izveidota — uzstadit() vēl nav palaists
  ws.clearContents();
  ws.clearFormats();
  // Grafiki netiek skarts (getCharts() / removeChart() nav izsaukts)
  uzrakstitTendencesTabulas(ws, rows);
}


// ── Tendences tabulu rakstīšana (kopīgs kods abiem ceļiem) ────────────────

function uzrakstitTendencesTabulas(ws, rows) {
  const idx = kolonnas(rows[0]);
  const allDates = [...new Set(rows.slice(1).map(r => r[idx.date]))].sort();
  const layout = [];
  let currentRow = 1;

  FUEL_TYPES.forEach(fuelType => {
    const fuelLabel = FUEL_DISPLAY[fuelType];

    // Sadaļas virsraksts
    galvene(ws, `${fuelLabel} — lētākās cenas pa piegādātājiem (EUR/L)`,
            currentRow, 1 + PROVIDER_ORDER.length);
    ws.setRowHeight(currentRow, 26);

    const headerRow = currentRow + 1;
    // Kolonnu galvene — batch
    ws.getRange(headerRow, 1, 1, 1 + PROVIDER_ORDER.length)
      .setValues([["Datums", ...PROVIDER_ORDER]]);
    stilsGalvene(ws.getRange(headerRow, 1, 1, 1 + PROVIDER_ORDER.length), MID_BLUE);
    ws.setRowHeight(headerRow, 22);

    const dataStart = headerRow + 1;
    const dataValues = [];
    const dataFmts   = [];
    const dataBgs    = [];

    allDates.forEach((date, i) => {
      const bg = i % 2 === 0 ? "#FFFFFF" : ALT_ROW;
      const rowVals = [formatDate(date)];
      const rowFmts = ["@"];
      const rowBgs  = [bg];

      PROVIDER_ORDER.forEach(provider => {
        const match = rows.slice(1).find(
          r => r[idx.date] === date && r[idx.provider] === provider && r[idx.fuel] === fuelType
        );
        rowVals.push(match ? parseFloat(match[idx.min]) : null);
        rowFmts.push("€0.000");
        rowBgs.push(bg);
      });

      dataValues.push(rowVals);
      dataFmts.push(rowFmts);
      dataBgs.push(rowBgs);
    });

    const dataEnd = dataStart + allDates.length - 1;

    if (dataValues.length > 0) {
      const r = ws.getRange(dataStart, 1, dataValues.length, 1 + PROVIDER_ORDER.length);
      r.setValues(dataValues);
      r.setNumberFormats(dataFmts);
      r.setBackgrounds(dataBgs);
    }

    layout.push({ fuelLabel, headerRow, dataStart, dataEnd });
    currentRow = dataEnd + 3;
  });

  return layout;
}


// ── Palīgfunkcijas ────────────────────────────────────────────────────────

function kolonnas(header) {
  return {
    date:     header.indexOf("date"),
    provider: header.indexOf("provider"),
    fuel:     header.indexOf("fuel_type"),
    min:      header.indexOf("price_min"),
    avg:      header.indexOf("price_avg"),
  };
}

function jaunakaisDatums(rows, idx) {
  const dates = rows.slice(1).map(r => r[idx.date]).filter(d => d).sort();
  return dates[dates.length - 1] || "";
}

function galvene(ws, teksts, rinda, nKolonnas) {
  ws.getRange(rinda, 1, 1, nKolonnas).merge()
    .setValue(teksts)
    .setBackground(LIGHT_BLUE)
    .setFontColor(DARK_BLUE)
    .setFontWeight("bold")
    .setFontSize(12)
    .setVerticalAlignment("middle");
}

function stilsGalvene(range, bg) {
  range.setBackground(bg || DARK_BLUE)
    .setFontColor("white")
    .setFontWeight("bold")
    .setVerticalAlignment("middle");
}

function formatDate(isoDate) {
  if (!isoDate) return "";
  const [y, m, d] = isoDate.split("-");
  return `${d}.${m}.${y}`;
}
