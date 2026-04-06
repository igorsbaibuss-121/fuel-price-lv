"""
Ielādē live degvielas cenas un pievieno rindu data/price_history.csv.
Paredzēts ikdienas automatizācijai (GitHub Actions vai lokāli).

Lietošana:
    python collect_prices.py
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import date
from pathlib import Path

import pandas as pd

HISTORY_PATH = Path("data/price_history.csv")
SOURCE_IDS = ["circlek_live", "neste_live", "virsi_live", "viada_live"]
SOURCE_CATALOG = Path("data/source_catalog.json")
FUEL_TYPES = ["petrol_95", "petrol_98", "diesel", "diesel_plus", "lpg", "cng"]

PROVIDER_LABELS = {
    "circlek_live": "Circle K",
    "neste_live":   "Neste",
    "virsi_live":   "Virši",
    "viada_live":   "VIADA",
}


def collect() -> None:
    from src.fuel_price_lv.main import load_aggregated_source_data
    from src.fuel_price_lv.services import deduplicate_results

    print("Ielādē live datus...")
    raw_df = load_aggregated_source_data(SOURCE_IDS, SOURCE_CATALOG)
    df = deduplicate_results(raw_df)

    today = date.today().isoformat()
    rows = []

    for source_id, provider in PROVIDER_LABELS.items():
        pdf = df[df["source_id"] == source_id]
        for fuel_type in FUEL_TYPES:
            fdf = pdf[pdf["fuel_type"] == fuel_type]["price"]
            if fdf.empty:
                continue
            rows.append({
                "date":      today,
                "provider":  provider,
                "fuel_type": fuel_type,
                "price_min": round(float(fdf.min()),  3),
                "price_avg": round(float(fdf.mean()), 3),
            })

    new_df = pd.DataFrame(rows)

    if HISTORY_PATH.exists():
        hist_df = pd.read_csv(HISTORY_PATH)
        # Ja šodienas ieraksti jau eksistē (atkārtota palaišana) — pārraksta
        hist_df = hist_df[hist_df["date"] != today]
        combined = pd.concat([hist_df, new_df], ignore_index=True)
    else:
        combined = new_df

    combined.to_csv(HISTORY_PATH, index=False)
    print(f"✅ Saglabāti {len(rows)} ieraksti ({today}) → {HISTORY_PATH}")
    print(new_df.to_string(index=False))


if __name__ == "__main__":
    collect()
