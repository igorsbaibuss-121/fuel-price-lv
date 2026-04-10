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
    from src.fuel_price_lv.main import load_dataframe_for_source_config
    from src.fuel_price_lv.source_catalog import get_source_config
    from src.fuel_price_lv.services import deduplicate_results

    today = date.today().isoformat()
    rows = []
    failed_sources = []

    for source_id, provider in PROVIDER_LABELS.items():
        print(f"Ielādē {provider}...")
        try:
            cfg = get_source_config(source_id, SOURCE_CATALOG)
            raw_df = load_dataframe_for_source_config(source_id, cfg, SOURCE_CATALOG)
            df = deduplicate_results(raw_df)
            pdf = df[df["source_id"] == source_id]
            station_count = int(pdf["station_name"].nunique())
            for fuel_type in FUEL_TYPES:
                fdf = pdf[pdf["fuel_type"] == fuel_type]["price"]
                if fdf.empty:
                    continue
                rows.append({
                    "date":          today,
                    "provider":      provider,
                    "fuel_type":     fuel_type,
                    "price_min":     round(float(fdf.min()),  3),
                    "price_avg":     round(float(fdf.mean()), 3),
                    "station_count": station_count,
                })
            print(f"  ✅ {provider}: {station_count} stacijas")
        except Exception as exc:
            print(f"  ❌ {provider} kļūda: {exc}", file=sys.stderr)
            failed_sources.append((provider, exc))

    if not rows:
        print("❌ Visi avoti cieta neveiksmi — nekas netiek saglabāts.", file=sys.stderr)
        sys.exit(1)

    if failed_sources:
        print(f"⚠️  {len(failed_sources)} avoti cieta neveiksmi, pārējie saglabāti.", file=sys.stderr)

    new_df = pd.DataFrame(rows)
    failed_provider_names = {provider for provider, _ in failed_sources}
    succeeded_providers = {label for label in PROVIDER_LABELS.values() if label not in failed_provider_names}

    if HISTORY_PATH.exists():
        hist_df = pd.read_csv(HISTORY_PATH)
        # Pārraksta tikai tos avotus kas šoreiz izdevās — neveiksmīgajiem saglabā vecos datus
        mask_today_succeeded = (hist_df["date"] == today) & (hist_df["provider"].isin(succeeded_providers))
        hist_df = hist_df[~mask_today_succeeded]
        combined = pd.concat([hist_df, new_df], ignore_index=True)
    else:
        combined = new_df

    combined.to_csv(HISTORY_PATH, index=False)
    print(f"✅ Saglabāti {len(rows)} ieraksti ({today}) → {HISTORY_PATH}")
    print(new_df.to_string(index=False))


if __name__ == "__main__":
    collect()
