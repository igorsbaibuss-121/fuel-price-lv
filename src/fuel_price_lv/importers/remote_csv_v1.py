from urllib.parse import urlparse

import pandas as pd

from .common import normalize_price_value, normalize_text_value

REMOTE_CSV_V1_REQUIRED_COLUMNS = {
    "station_name",
    "address",
    "city",
    "fuel_type",
    "price",
}


def validate_source_url(source_url: str | None) -> str:
    if source_url is None or not source_url.strip():
        raise ValueError("source-url is required for remote_csv_v1")

    normalized_source_url = source_url.strip()
    parsed_url = urlparse(normalized_source_url)
    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Atbalstīti tikai http/https source-url")
    return normalized_source_url


def load_remote_csv_v1_data(source_url: str | None) -> pd.DataFrame:
    validated_source_url = validate_source_url(source_url)
    try:
        return pd.read_csv(validated_source_url)
    except Exception as error:
        raise ValueError(f"Neizdevās nolasīt attālināto CSV avotu: {error}") from error


def normalize_remote_csv_v1_data(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = [column for column in REMOTE_CSV_V1_REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing_columns_str = ", ".join(sorted(missing_columns))
        raise ValueError(f"Attālinātajā CSV failā trūkst obligātās kolonnas: {missing_columns_str}")

    normalized_df = pd.DataFrame(
        {
            "station_name": df["station_name"].map(normalize_text_value),
            "address": df["address"].map(normalize_text_value),
            "city": df["city"].map(normalize_text_value),
            "fuel_type": df["fuel_type"].map(lambda value: normalize_text_value(value, lowercase=True)),
            "price": df["price"].map(lambda value: normalize_price_value(value, "price")),
        }
    )
    return normalized_df[["station_name", "address", "city", "fuel_type", "price"]]
