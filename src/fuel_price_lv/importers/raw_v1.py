from pathlib import Path

import pandas as pd

from .common import normalize_price_value, normalize_text_value

RAW_V1_REQUIRED_COLUMNS = {
    "station",
    "street_address",
    "city_name",
    "product",
    "price_eur",
}


def load_raw_v1_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV fails nav atrasts: {csv_path}")
    return pd.read_csv(csv_path)
def normalize_raw_v1_prices(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = [column for column in RAW_V1_REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing_columns_str = ", ".join(sorted(missing_columns))
        raise ValueError(f"Raw CSV failā trūkst obligātās kolonnas: {missing_columns_str}")

    normalized_df = pd.DataFrame(
        {
            "station_name": df["station"].map(normalize_text_value),
            "address": df["street_address"].map(normalize_text_value),
            "city": df["city_name"].map(normalize_text_value),
            "fuel_type": df["product"].map(lambda value: normalize_text_value(value, lowercase=True)),
            "price": df["price_eur"].map(lambda value: normalize_price_value(value, "price_eur")),
        }
    )
    return normalized_df[["station_name", "address", "city", "fuel_type", "price"]]
