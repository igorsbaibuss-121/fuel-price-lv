# fuel-price-lv

Python rīks Latvijas degvielas cenu automātiskai iegūšanai, analīzei un atskaišu ģenerēšanai.

---

## Projekta mērķis

Katru dienu automātiski iegūst degvielas cenas no Circle K, Neste, Virši un VIADA tīmekļa avotiem, saglabā vēsturi un ģenerē vizuālas atskaites — gan kā Excel failu, gan kā Google Sheets izklājlapu.

---

## Ātrā lietošana

### Ikdienas Excel atskaite (manuāli)
```powershell
python generate_report.py
```
Atver: `output/summary_report_final.xlsx`

### Ikdienas datu vākšana (manuāli, ja Actions nav palaists)
```powershell
python collect_prices.py
```

### CLI — konkrēts jautājums
```powershell
fuel-price-lv --source-ids circlek_live,neste_live,virsi_live,viada_live --fuel-type petrol_95 --dedup --top-n 10
```

---

## Automatizācija

### GitHub Actions (`daily_prices.yml`)
- Darbojas katru dienu **06:00 UTC = 09:00 Rīgas laiks (vasarā)**
- Palaiž `collect_prices.py`
- Pievieno jaunu rindu `data/price_history.csv`
- Commitē un pushojam atpakaļ repozitorijā
- **Brīvdienās un svētku dienās** cenas automātiski netiek atjaunotas

### Google Apps Script (izklājlapa)
- Trigger: katru dienu **09:30** nolasa `data/price_history.csv` no GitHub
- Atjaunina lapas: **Šodien**, **Vēsture**, **Tendences**
- Fails: `docs/google_apps_script.js` — kopēt uz Google Sheets Apps Script editoru
- Manuāla atjaunināšana: palaid funkciju `atjauninat()`

---

## Datu plūsma

```
Live tīmekļa avoti (Circle K, Neste, Virši, VIADA)
        │
        ▼
collect_prices.py  ──►  data/price_history.csv  ──►  GitHub repo
        │                                                    │
        ▼                                                    ▼
generate_report.py                              Google Apps Script
        │                                                    │
        ▼                                                    ▼
output/summary_report_final.xlsx          Google Sheets izklājlapa
```

---

## Projekta struktūra

```
fuel-price-lv/
│
├── collect_prices.py          # Ikdienas datu vākšana → price_history.csv
├── generate_report.py         # Excel atskaites ģenerēšana (live dati)
│
├── src/fuel_price_lv/
│   ├── main.py                # Orķestrācija: ielādē, dedup, filtrē, renderē
│   ├── cli.py                 # CLI argumentu parsēšana
│   ├── services.py            # Filtrēšana, deduplicēšana, kārtošana
│   ├── reporting.py           # Multi-failu atskaišu bundle
│   ├── xlsx_report.py         # Excel failu rakstīšana (openpyxl)
│   ├── net.py                 # HTTP ielāde, SSL/CA bundle atbalsts
│   ├── source_catalog.py      # source_catalog.json nolasīšana
│   └── importers/
│       ├── circlek_lv_v1.py   # Circle K web scraper
│       ├── neste_lv_v1.py     # Neste web scraper
│       ├── virsi_lv_v1.py     # Virši web scraper
│       ├── viada_lv_v1.py     # VIADA web scraper
│       ├── standard.py        # Standarta CSV ievade
│       ├── raw_v1.py          # raw_v1 CSV normalizācija
│       ├── excel_v1.py        # Excel ievade
│       └── remote_csv_v1.py   # Attālinātā CSV ievade
│
├── data/
│   ├── price_history.csv      # Vēsturisko cenu uzkrājums (auto-commitēts)
│   └── source_catalog.json    # Avotu katalogs (format + faila ceļš/URL)
│
├── docs/
│   └── google_apps_script.js  # Google Sheets skripts (kopēt manuāli)
│
├── output/
│   ├── summary_report_final.xlsx  # Ģenerētā Excel atskaite
│   ├── cache/circlek_latest.csv   # Circle K cache (lēnais avots)
│   └── history/                   # Timestamped CLI snapshots
│
├── .github/workflows/
│   └── daily_prices.yml       # GitHub Actions konfigurācija
│
└── tests/                     # pytest testi
```

---

## Galvenie faili — ko dara

| Fails | Loma |
|-------|------|
| `collect_prices.py` | Savāc live cenas, pievieno `price_history.csv`. GitHub Actions to palaiž automātiski. |
| `generate_report.py` | Savāc live cenas, izveido `summary_report_final.xlsx` ar 4 lapām. Palaid manuāli. |
| `data/price_history.csv` | Vēsturisko cenu CSV. Kolonnas: `date, provider, fuel_type, price_min, price_avg, station_count`. |
| `docs/google_apps_script.js` | Kopē uz Google Sheets — atjaunina 3 lapas no `price_history.csv`. |

---

## Excel atskaite (`summary_report_final.xlsx`)

Ģenerē: `python generate_report.py`

| Lapa | Saturs |
|------|--------|
| **Kopsavilkums** | Lētākās cenas pa piegādātājiem + degvielas veidu statistika (min/avg/max/starpība) |
| **Analīze** | Vidējo cenu salīdzinājums, staciju skaits, grafiki |
| **Visas cenas** | Pilns saraksts ar Google Maps saitēm uz katru DUS |
| **Tendences** | Cenu izmaiņas laika gaitā pa degvielas veidiem (līniju grafiki) |

Kopsavilkuma lapa automātiski rāda:
- Šodienas datumu virsrakstā
- Brīvdienas/svētku brīdinājumu (ja piemērojams)
- Atrunu par cenu informatīvo raksturu

---

## Google Sheets atskaite

Fails: `docs/google_apps_script.js` — kopēt uz izklājlapas Apps Script editoru.

| Lapa | Saturs |
|------|--------|
| **Šodien** | Kopsavilkums ar abām tabulām (piegādātāji + degvielas veidi), brīvdienu paziņojums, atruna |
| **Vēsture** | Visi `price_history.csv` dati |
| **Tendences** | Cenu tabulas pa degvielas veidiem ar grafikiem |

**Uzstādīšana (pirmo reizi):**
1. Apps Script editorā palaid `uzstadit()` — ievieto datus un uzstāda automātisko triggeri (09:30)
2. Palaid `veidoGrafikus()` — izveido grafikus (tikai vienu reizi, ~2 min)

---

## Datu avoti

| Source ID | Piegādātājs | Tips | Piezīme |
|-----------|-------------|------|---------|
| `circlek_live` | Circle K | Web scraper | Lēns; adrese/pilsēta bieži tukša |
| `neste_live` | Neste | Web scraper | Ātra ielāde |
| `virsi_live` | Virši | Web scraper | Ātra ielāde |
| `viada_live` | VIADA | Web scraper | Ātra ielāde |

Savākšana notiek no publiskiem tīmekļa avotiem. Circle K gadījumā adrese netiek publicēta, tāpēc Google Maps saite nav pieejama.

---

## Degvielas veidi

| Kods | Nosaukums |
|------|-----------|
| `petrol_95` | Benzīns 95 |
| `petrol_98` | Benzīns 98 |
| `diesel` | Dīzelis |
| `diesel_plus` | Dīzelis Plus |
| `lpg` | Autogāze |
| `cng` | CNG |

---

## Uzstādīšana

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

### Atkarības
- `pandas` — datu apstrāde
- `openpyxl` — Excel failu rakstīšana
- `requests` / `beautifulsoup4` — web scraping
- `holidays` — Latvijas svētku datumu aprēķināšana
- `pytest` — testi

---

## CLI lietošana

```powershell
# Lētākās petrol_95 cenas
fuel-price-lv --source-ids circlek_live,neste_live,virsi_live,viada_live \
              --fuel-type petrol_95 --dedup --top-n 10

# Tikai Rīgas stacijas
fuel-price-lv --source-ids neste_live,virsi_live --fuel-type diesel \
              --city Riga --top-n 5

# JSON izvade
fuel-price-lv --source-ids neste_live --fuel-type diesel --output json
```

### Galvenās opcijas

| Opcija | Apraksts |
|--------|----------|
| `--source-ids` | Komatatdalīts source_id saraksts no `source_catalog.json` |
| `--fuel-type` | Degvielas tips, piem. `diesel`, `petrol_95` |
| `--city` | Filtrēt pēc pilsētas |
| `--top-n` | Cik ierakstus rādīt (nokl. 5) |
| `--dedup` | Samazināt dublikātus vairāku avotu gadījumā |
| `--detect-price-conflicts` | Atzīmēt cenu neatbilstības starp avotiem |
| `--output` | `table` / `csv` / `json` |
| `--report` | Izveidot report bundle mapē `output/` |
| `--ca-bundle` | CA bundle SSL verifikācijai (korporatīvie proxy) |

---

## Testi

```powershell
pytest
pytest tests/test_services.py
pytest tests/test_services.py::test_filter_by_fuel_type
```

---

## Svarīgas piezīmes

- **GitHub repozitorijam jābūt publiskam** — Apps Script nolasa `price_history.csv` no raw GitHub URL
- **Brīvdienās/svētku dienās** GitHub Actions nepalaiž cenu vākšanu (crons nedarbojas, bet brīdinājums tiek rādīts atskaitēs)
- **Circle K** cache workflow: vispirms `--refresh-circlek` → saglabā `output/cache/circlek_latest.csv`, tad lasa ar `--input-format standard`
- **SSL proxy**: iestati `SSL_CERT_FILE` vai `REQUESTS_CA_BUNDLE` vides mainīgo, vai izmanto `--ca-bundle`
