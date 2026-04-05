/**
 * Degvielas cenu Google Sheet
 * ===========================
 * Ielādē datus no GitHub un atjaunina 3 lapas:
 *   - Šodien   : aktuālās lētākās cenas
 *   - Vēsture  : visi dati (tabula)
 *   - Tendences: līniju grafiki pa degvielas veidiem
 *
 * Pirmreizējā uzstādīšana:
 *   1. Atver Apps Script (Paplašinājumi → Apps Script)
 *   2. Ieliec šo kodu, saglabā
 *   3. Palaid funkciju "uzstadit" (▶ pogu)
 *   4. Apstiprina atļaujas
 *
 * Pēc tam dati atjauninās automātiski katru dienu pulksten 09:30.
 * Manuāla atjaunināšana: nospied pogu lapā "Šodien" vai palaid "atjauninat".
 */

const GITHUB_CSV_URL =
  "https://raw.githubusercontent.com/igorsbaibuss-121/fuel-price-lv/main/data/price_history.csv";

const FUEL_DISPLAY = {
  petrol_95: "Benzīns 95",
  petrol_98: "Benzīns 98",
  diesel:    "Dīzelis",
};

const PROVIDER_ORDER = ["Circle K", "Neste", "Virši", "VIADA"];

const DARK_BLUE  = "#1F3864";
const LIGHT_BLUE = "#EBF3FB";
const MID_BLUE   = "#2E75B6";
const ALT_ROW    = "#D6E4F0";
const GREEN_BG   = "#E2EFDA";
const ORANGE_BG  = "#FCE4D6";


// ── Galvenā ieejas funkcija ────────────────────────────────────────────────

function atjauninat() {
  const rows = ieladeCSV();
  if (!rows) return;

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  veidoSodienLapu(ss, rows);
  veidoVestureLapu(ss, rows);
  veidoTendencesLapu(ss, rows);

  ss.toast("Dati atjaunināti! ✅", "Degvielas cenas", 4);
}


// ── CSV ielāde no GitHub ──────────────────────────────────────────────────

function ieladeCSV() {
  try {
    const resp = UrlFetchApp.fetch(GITHUB_CSV_URL, { muteHttpExceptions: true });
    if (resp.getResponseCode() !== 200) {
      SpreadsheetApp.getUi().alert("Neizdevās ielādēt datus no GitHub.");
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
  if (!ws) ws = ss.insertSheet("Šodien", 0);
  ws.clearContents();
  ws.clearFormats();

  const { dateIdx, providerIdx, fuelIdx, minIdx } = kolonnas(rows[0]);

  // Iegūst jaunāko pieejamo datumu
  const dates = rows.slice(1).map(r => r[dateIdx]).filter(d => d).sort();
  const jaunakais = dates[dates.length - 1];

  const sodienDati = rows.slice(1).filter(r => r[dateIdx] === jaunakais);

  // Galvene
  galvene(ws, `Lētākās degvielas cenas  •  ${formatDate(jaunakais)}`, 1, 5);
  ws.setRowHeight(1, 40);

  // Kolonnu virsraksti
  setRow(ws, 2, ["Piegādātājs", "Benzīns 95", "Benzīns 98", "Dīzelis", "Lētākā"], DARK_BLUE, "white", true);
  ws.setRowHeight(2, 28);

  // Aprēķina min katram degvielas tipam
  const fuelMins = {};
  Object.keys(FUEL_DISPLAY).forEach(fuel => {
    const prices = sodienDati
      .filter(r => r[fuelIdx] === fuel)
      .map(r => parseFloat(r[minIdx]))
      .filter(v => !isNaN(v));
    fuelMins[fuel] = prices.length ? Math.min(...prices) : null;
  });

  // Dati pa piegādātājiem
  let dataRow = 3;
  PROVIDER_ORDER.forEach((provider, i) => {
    const pDati = sodienDati.filter(r => r[providerIdx] === provider);
    const bg = i % 2 === 0 ? "white" : ALT_ROW;

    const prices = {};
    pDati.forEach(r => { prices[r[fuelIdx]] = parseFloat(r[minIdx]); });

    const vals = Object.keys(FUEL_DISPLAY).map(f => prices[f] || "");
    const letaka = vals.filter(v => v !== "").length
      ? Math.min(...vals.filter(v => v !== ""))
      : "";

    ws.getRange(dataRow, 1).setValue(provider).setFontWeight("bold");
    ws.getRange(dataRow, 1, 1, 5).setBackground(bg).setVerticalAlignment("middle");
    ws.setRowHeight(dataRow, 24);

    Object.keys(FUEL_DISPLAY).forEach((fuel, col) => {
      const cell = ws.getRange(dataRow, col + 2);
      const val = prices[fuel];
      if (val) {
        cell.setValue(val).setNumberFormat("€#,##0.000");
        // Zaļš ja šī piegādātāja cena ir viszemākā šajā kategorijā
        if (fuelMins[fuel] !== null && Math.abs(val - fuelMins[fuel]) < 0.0005) {
          cell.setBackground(GREEN_BG).setFontWeight("bold");
        }
      } else {
        cell.setValue("—").setFontColor("#AAAAAA");
      }
    });

    if (letaka !== "") {
      ws.getRange(dataRow, 5).setValue(letaka).setNumberFormat("€#,##0.000").setFontWeight("bold");
    }

    dataRow++;
  });

  // Leģenda
  ws.getRange(dataRow + 1, 1, 1, 5).merge()
    .setValue("✅ Zaļš = lētākā cena šajā kategorijā")
    .setFontStyle("italic").setFontColor("#375623").setBackground(GREEN_BG);

  // Poga manuālai atjaunināšanai
  try {
    const drawings = ws.getDrawings();
    drawings.forEach(d => d.remove());
  } catch(e) {}

  // Kolonnu platumi
  ws.setColumnWidth(1, 100);
  [2, 3, 4, 5].forEach(c => ws.setColumnWidth(c, 110));

  // Nofiksē pirmo rindu
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

  // Formatē galveni
  ws.getRange(1, 1, 1, rows[0].length)
    .setBackground(DARK_BLUE).setFontColor("white").setFontWeight("bold");

  // Formatē cenu kolonnas
  const { minIdx, avgIdx } = kolonnas(rows[0]);
  if (rows.length > 1) {
    ws.getRange(2, minIdx + 1, rows.length - 1, 1).setNumberFormat("0.000");
    ws.getRange(2, avgIdx + 1, rows.length - 1, 1).setNumberFormat("0.000");
  }

  ws.autoResizeColumns(1, rows[0].length);
  ws.setFrozenRows(1);
}


// ── Lapa "Tendences" ──────────────────────────────────────────────────────

function veidoTendencesLapu(ss, rows) {
  let ws = ss.getSheetByName("Tendences");
  if (!ws) ws = ss.insertSheet("Tendences");
  ws.clearContents();
  ws.clearFormats();

  // Dzēš vecos grafikus
  const charts = ws.getCharts();
  charts.forEach(c => ws.removeChart(c));

  const { dateIdx, providerIdx, fuelIdx, minIdx } = kolonnas(rows[0]);

  // Sakārto unikālos datumus
  const allDates = [...new Set(rows.slice(1).map(r => r[dateIdx]))].sort();

  let currentRow = 1;

  Object.entries(FUEL_DISPLAY).forEach(([fuelType, fuelLabel]) => {
    // Sadaļas virsraksts
    galvene(ws, `${fuelLabel} — lētākās cenas pa piegādātājiem (EUR/L)`,
            currentRow, 1 + PROVIDER_ORDER.length);
    ws.setRowHeight(currentRow, 28);

    // Galvene: Datums | Provider1 | Provider2 | ...
    setRow(ws, currentRow + 1,
           ["Datums", ...PROVIDER_ORDER],
           MID_BLUE, "white", true);
    ws.setRowHeight(currentRow + 1, 24);

    const dataStart = currentRow + 2;

    // Aizpilda datus
    allDates.forEach((date, i) => {
      const r = dataStart + i;
      ws.getRange(r, 1).setValue(formatDate(date));
      ws.setRowHeight(r, 20);
      const bg = i % 2 === 0 ? "white" : ALT_ROW;
      ws.getRange(r, 1, 1, 1 + PROVIDER_ORDER.length).setBackground(bg);

      PROVIDER_ORDER.forEach((provider, p) => {
        const match = rows.slice(1).find(
          row => row[dateIdx] === date &&
                 row[providerIdx] === provider &&
                 row[fuelIdx] === fuelType
        );
        const cell = ws.getRange(r, p + 2);
        if (match) {
          cell.setValue(parseFloat(match[minIdx])).setNumberFormat("€0.000");
        }
      });
    });

    const dataEnd = dataStart + allDates.length - 1;

    // Līniju grafiks
    const chartRange = ws.getRange(currentRow + 1, 1, allDates.length + 1,
                                   1 + PROVIDER_ORDER.length);
    const chart = ws.newChart()
      .setChartType(Charts.ChartType.LINE)
      .addRange(chartRange)
      .setOption("title", `${fuelLabel} — cenu tendence`)
      .setOption("vAxis.title", "Cena (EUR/L)")
      .setOption("hAxis.title", "Datums")
      .setOption("legend.position", "bottom")
      .setOption("width",  550)
      .setOption("height", 320)
      .setPosition(currentRow, 2 + PROVIDER_ORDER.length, 10, 10)
      .build();
    ws.insertChart(chart);

    currentRow = dataEnd + 3;
  });

  ws.setColumnWidth(1, 100);
  PROVIDER_ORDER.forEach((_, i) => ws.setColumnWidth(i + 2, 100));
  ws.setFrozenRows(0);
}


// ── Palīgfunkcijas ────────────────────────────────────────────────────────

function kolonnas(header) {
  return {
    dateIdx:     header.indexOf("date"),
    providerIdx: header.indexOf("provider"),
    fuelIdx:     header.indexOf("fuel_type"),
    minIdx:      header.indexOf("price_min"),
    avgIdx:      header.indexOf("price_avg"),
  };
}

function galvene(ws, teksts, rinda, nKolonnas) {
  const range = ws.getRange(rinda, 1, 1, nKolonnas);
  range.merge()
    .setValue(teksts)
    .setBackground(LIGHT_BLUE)
    .setFontColor(DARK_BLUE)
    .setFontWeight("bold")
    .setFontSize(12)
    .setVerticalAlignment("middle");
}

function setRow(ws, rinda, vertibas, bg, fg, bold) {
  const range = ws.getRange(rinda, 1, 1, vertibas.length);
  range.setValues([vertibas])
    .setBackground(bg)
    .setFontColor(fg)
    .setFontWeight(bold ? "bold" : "normal")
    .setVerticalAlignment("middle");
}

function formatDate(isoDate) {
  if (!isoDate) return "";
  const parts = isoDate.split("-");
  return `${parts[2]}.${parts[1]}.${parts[0]}`;
}


// ── Uzstādīšana (palaid vienu reizi) ──────────────────────────────────────

function uzstadit() {
  // Izveido lapas un ielādē datus pirmoreiz
  atjauninat();

  // Uzstāda automātisku atjaunināšanu katru dienu 09:30
  // (dzēš vecos triggerus lai nedublētu)
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "atjauninat")
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger("atjauninat")
    .timeBased()
    .atHour(9)
    .nearMinute(30)
    .everyDays(1)
    .create();

  SpreadsheetApp.getActiveSpreadsheet()
    .toast("Uzstādīts! Dati atjaunināsies automātiski katru dienu 09:30 ✅", "Gatavs", 6);
}
