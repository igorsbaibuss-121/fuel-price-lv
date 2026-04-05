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

const FUEL_TYPES     = ["petrol_95", "petrol_98", "diesel"];
const FUEL_DISPLAY   = { petrol_95: "Benzīns 95", petrol_98: "Benzīns 98", diesel: "Dīzelis" };
const PROVIDER_ORDER = ["Circle K", "Neste", "Virši", "VIADA"];

const DARK_BLUE  = "#1F3864";
const LIGHT_BLUE = "#EBF3FB";
const MID_BLUE   = "#2E75B6";
const ALT_ROW    = "#D6E4F0";
const GREEN_BG   = "#E2EFDA";


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


// ── Lapa "Šodien" ─────────────────────────────────────────────────────────

function veidoSodienLapu(ss, rows) {
  let ws = ss.getSheetByName("Šodien");
  if (!ws) ws = ss.insertSheet("Šodien", 0);
  ws.clearContents();

  const idx = kolonnas(rows[0]);
  const jaunakais = jaunakaisDatums(rows, idx);
  const dienasDati = rows.slice(1).filter(r => r[idx.date] === jaunakais);

  // Galvene
  ws.getRange(1, 1, 1, 5).merge()
    .setValue("Lētākās degvielas cenas  •  " + formatDate(jaunakais))
    .setBackground(LIGHT_BLUE).setFontColor(DARK_BLUE)
    .setFontWeight("bold").setFontSize(13)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");
  ws.setRowHeight(1, 36);

  // Virsraksti
  ws.getRange(2, 1, 1, 5)
    .setValues([["Piegādātājs", "Benzīns 95", "Benzīns 98", "Dīzelis", "Lētākā"]])
    .setBackground(DARK_BLUE).setFontColor("white").setFontWeight("bold")
    .setHorizontalAlignment("center");
  ws.setRowHeight(2, 26);

  // Min katram degvielas tipam
  const fuelMins = {};
  FUEL_TYPES.forEach(f => {
    const p = dienasDati.filter(r => r[idx.fuel] === f)
                        .map(r => parseFloat(r[idx.min])).filter(v => !isNaN(v));
    fuelMins[f] = p.length ? Math.min(...p) : null;
  });

  // Dati
  const values = [], bgs = [], fmts = [], aligns = [];
  PROVIDER_ORDER.forEach((provider, i) => {
    const pRows = dienasDati.filter(r => r[idx.provider] === provider);
    const prices = {};
    pRows.forEach(r => { prices[r[idx.fuel]] = parseFloat(r[idx.min]); });
    const nums = Object.values(prices).filter(v => !isNaN(v));
    const letaka = nums.length ? Math.min(...nums) : "";

    const bg = i % 2 === 0 ? "#FFFFFF" : ALT_ROW;
    values.push([provider,
                 prices["petrol_95"] || "",
                 prices["petrol_98"] || "",
                 prices["diesel"]    || "",
                 letaka || ""]);

    const rowBg = [bg, bg, bg, bg, bg];
    FUEL_TYPES.forEach((f, fi) => {
      if (prices[f] && fuelMins[f] !== null && Math.abs(prices[f] - fuelMins[f]) < 0.0005)
        rowBg[fi + 1] = GREEN_BG;
    });
    bgs.push(rowBg);
    fmts.push(["@", "€0.000", "€0.000", "€0.000", "€0.000"]);
    aligns.push(["left", "center", "center", "center", "center"]);
  });

  const dr = ws.getRange(3, 1, values.length, 5);
  dr.setValues(values).setBackgrounds(bgs).setNumberFormats(fmts)
    .setHorizontalAlignments(aligns).setVerticalAlignment("middle");
  ws.getRange(3, 1, values.length, 1).setFontWeight("bold");
  for (let i = 3; i < 3 + values.length; i++) ws.setRowHeight(i, 24);

  // Leģenda
  ws.getRange(3 + values.length + 1, 1, 1, 5).merge()
    .setValue("✅ Zaļš = lētākā cena šajā kategorijā")
    .setFontStyle("italic").setFontColor("#375623").setBackground(GREEN_BG);

  ws.setColumnWidths(1, 5, 115);
  ws.setFrozenRows(2);
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

  ws.setFrozenRows(2);
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
