# Fuel Price LV

## Problema / merkis
Python CLI prototips degvielas cenu datu apskatei Latvija. Tas ielade datus no vairakiem ievades formatiem, filtree rezultatus un var paradit top N cenas vai letako cenu katra pilseta.

## Projekta struktura
- `src/fuel_price_lv/main.py` - programmas entrypoint
- `src/fuel_price_lv/cli.py` - CLI argumenti un validacija
- `src/fuel_price_lv/services.py` - filtri, rezultatu sagatavosana un failu nosaukumi
- `src/fuel_price_lv/reporting.py` - report workflow bundle izveide
- `data/` - sample dati un source catalog
- `tests/` - pytest testi

## Ka palaist

### 1. Izveidot virtualo vidi
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Uzinstalet atkaribas
```powershell
pip install -r requirements.txt
```

### 3. Uzinstalet projektu editable rezima
```powershell
pip install -e .
```

### 4. Palaist CLI
```powershell
fuel-price-lv --fuel-type diesel
```

### 5. Palaist ar veco module stilu
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel
```

## CLI opcijas
- `--fuel-type` - obligats degvielas tips, piemeram, `diesel` vai `petrol_95`
- `--city` - filtrs pec pilsetas, piemeram, `Riga`
- `--station` - filtrs pec DUS nosaukuma dalas, piemeram, `Neste`
- `--source-id` - avota identifikators no source catalog JSON faila
- `--source-catalog` - source catalog JSON faila cels, noklusejums `data/source_catalog.json`
- `--csv-path` - cels uz CSV failu, noklusejums `data/sample_prices.csv`
- `--source-url` - attalinata CSV avota URL formatam `remote_csv_v1`
- `--input-format` - ievades formats: `standard`, `raw_v1`, `excel_v1` vai `remote_csv_v1`
- `--top-n` - cik ierakstus radit, noklusejums `5`
- `--sort-by` - kartot pec cenas: `price_asc` vai `price_desc`
- `--output` - izvades formats: `table`, `csv` vai `json`
- `--output-file` - saglaba rezultatu lietotaja noraditaja faila cela
- `--save` - saglaba rezultatu mape `output/` ar automatiski generetu faila nosaukumu
- `--summary-by-city` - rada letako izveletas degvielas cenu katra pilseta
- `--report` - izveido report bundle mape `output/`

## Piemeri

### 1. Basic top N
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --top-n 5
```

### 2. Filtret pec pilsetas
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --city Riga
```

### 3. Filtret pec stacijas
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --station Neste
```

### 4. Kartot dilstosi
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --sort-by price_desc
```

### 5. Izvade JSON formata
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --output json
```

### 6. Izvade CSV formata
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --output csv
```

### 7. Kopsavilkums pa pilsetam
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --summary-by-city
```

### 8. Saglabat JSON mape output/
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --output json --save
```

### 9. Saglabat kopsavilkumu CSV mape output/
```powershell
python -m src.fuel_price_lv.main --fuel-type diesel --summary-by-city --output csv --save
```

### 10. Lietot raw_v1 ievadi
```powershell
python -m src.fuel_price_lv.main --csv-path data/sample_raw_prices_v1.csv --input-format raw_v1 --fuel-type diesel
```

### 11. Lietot dirty raw_v1 ievadi
```powershell
python -m src.fuel_price_lv.main --csv-path data/sample_raw_dirty_prices_v1.csv --input-format raw_v1 --fuel-type diesel
```

### 12. Lietot excel_v1 ievadi
```powershell
python -m src.fuel_price_lv.main --csv-path data/sample_excel_prices_v1.xlsx --input-format excel_v1 --fuel-type diesel
```

### 13. Lietot remote_csv_v1 ievadi
```powershell
python -m src.fuel_price_lv.main --input-format remote_csv_v1 --source-url https://example.com/fuel_prices.csv --fuel-type diesel --top-n 3
```

### 14. Lietot source-id katalogu raw_v1 avotam
```powershell
python -m src.fuel_price_lv.main --source-id demo_raw_v1 --fuel-type diesel
```

### 15. Lietot source-id katalogu excel_v1 avotam
```powershell
python -m src.fuel_price_lv.main --source-id demo_excel_v1 --fuel-type diesel
```

### 16. Izveidot report bundle
```powershell
python -m src.fuel_price_lv.main --source-id demo_excel_v1 --fuel-type diesel --top-n 3 --report
```

`--report` izveido tris failus mape `output/`:
- `diesel_top3.csv`
- `diesel_top3.json`
- `diesel_summary_by_city.csv`

## Piezime par izvadi
- `table` izvadei konsole tiek pievienots cilvekam saprotams virsraksts
- `json` izvadei katra rezultata rinda tiek pievienots `google_maps_url`
- `csv` izvadei katra rezultata rinda tiek pievienots `google_maps_url`
- `json` un `csv` izvadei virsraksts netiek pievienots
- `--output-file` saglaba rezultatu tiesi lietotaja noraditajaja cela
- `--save` saglaba rezultatu mape `output/` ar automatiski generetu faila nosaukumu
- ja tiek lietoti abi, `--output-file` ir prioritate
- `--report` ignore `--output` un `--output-file` galvena rezultata drukasanas cela un pats izveido report failus

## Piezime par importu
- ievades apstrade iekseji notiek caur import adapteriem
- `raw_v1`, `excel_v1` un `remote_csv_v1` ievade pirms filtresanas un izvades tiek normalizeta uz standarta shemu
- source katalogs atrodas faila `data/source_catalog.json`, un `--source-id` var izmantot taja definetos ievades iestatijumus

## Piezime par failu nosaukumiem
- automatiski generetu failu piemeri: `diesel_top3.json`, `diesel_summary_by_city.csv`
