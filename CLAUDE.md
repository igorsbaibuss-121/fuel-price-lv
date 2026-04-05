# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies and package in editable mode
pip install -r requirements.txt
pip install -e .

# Run all tests
pytest

# Run a single test file
pytest tests/test_services.py

# Run a single test by name
pytest tests/test_services.py::test_filter_by_fuel_type

# Run the CLI
fuel-price-lv --fuel-type diesel --top-n 5
python -m src.fuel_price_lv.main --fuel-type diesel --top-n 5
```

## Architecture

The tool is a Python CLI that fetches/loads fuel price data from multiple sources, normalizes it to a common schema, and outputs filtered/sorted results.

**Data flow:**
1. `cli.py` — parses args
2. `main.py` — orchestrates: resolves source, loads data, applies dedup/conflict annotation, filters, and renders output
3. `importers/` — each importer loads raw data and normalizes it to the standard schema (`station_name`, `address`, `city`, `fuel_type`, `price`)
4. `services.py` — filtering, deduplication, conflict annotation, sorting, filename generation
5. `reporting.py` — multi-file report bundle generation and output rendering (table/csv/json)

**Input sources (`--input-format`):**
- `standard` — local CSV already in standard schema
- `raw_v1`, `excel_v1` — local files requiring normalization
- `remote_csv_v1` — remote CSV via `--source-url`
- `circlek_lv_v1`, `neste_lv_v1`, `virsi_lv_v1` — live web scrapers using `net.py`

**Source catalog** (`data/source_catalog.json`) maps named `source_id` entries to their format and file/URL. `--source-id` loads one; `--source-ids` (comma-separated) loads and concatenates multiple.

**Multi-source workflow:** `--source-ids` concatenates DataFrames, then `--dedup` collapses duplicates by `(station_name, address, fuel_type)` key while tracking `source_ids`/`source_count` provenance. `--detect-price-conflicts` (run before dedup) annotates rows where the same station has different prices across sources.

**Adding a new importer:** create `src/fuel_price_lv/importers/<name>.py` with a `load_<name>_data()` function that returns a DataFrame in the standard schema, then register it in `importers/__init__.py`'s `load_input_data()` dispatch and in `main.py`'s `input_format_uses_local_file()`.

**SSL/CA bundle:** `net.py` checks `--ca-bundle` arg, then `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` env vars. Needed for corporate proxies intercepting HTTPS.

**Circle K cache workflow:** Circle K live fetching is slow; the recommended pattern is `--refresh-circlek` to save `output/cache/circlek_latest.csv`, then re-read it with `--input-format standard`.
