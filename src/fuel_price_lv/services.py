from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd

REQUIRED_COLUMNS = ["station_name", "address", "city", "fuel_type", "price"]


def validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing_columns_str = ", ".join(missing_columns)
        raise ValueError(f"CSV failā trūkst obligātās kolonnas: {missing_columns_str}")


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    validate_required_columns(df)
    return df


def normalize_text_for_compare(value: object) -> str:
    return " ".join(str(value).split()).strip().lower()


def build_canonical_address(address: str, city: str | None = None) -> str:
    canonical_address = normalize_text_for_compare(address)
    if city is None:
        return canonical_address

    normalized_city = normalize_text_for_compare(city)
    if normalized_city and canonical_address.endswith(normalized_city):
        canonical_address = canonical_address[: -len(normalized_city)].strip()
    return canonical_address


def build_price_conflict_key(row: pd.Series) -> tuple:
    return (
        normalize_text_for_compare(row["station_name"]),
        build_canonical_address(row["address"], row.get("city")),
        normalize_text_for_compare(row["fuel_type"]),
    )


def build_dedup_key(row: pd.Series) -> tuple:
    return (*build_price_conflict_key(row), float(row["price"]))


def collect_source_provenance(rows: list[pd.Series]) -> tuple[list[str], int]:
    source_ids: list[str] = []
    seen_source_ids: set[str] = set()
    for row in rows:
        source_id = row.get("source_id")
        if source_id is None:
            continue
        normalized_source_id = str(source_id)
        if normalized_source_id in seen_source_ids:
            continue
        seen_source_ids.add(normalized_source_id)
        source_ids.append(normalized_source_id)
    return source_ids, len(source_ids)


def collect_price_values(rows: list[pd.Series]) -> list[float]:
    seen_prices: set[float] = set()
    price_values: list[float] = []
    for row in rows:
        price = float(row["price"])
        if price in seen_prices:
            continue
        seen_prices.add(price)
        price_values.append(price)
    return sorted(price_values)


def annotate_price_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    grouped_rows: dict[tuple, list[pd.Series]] = {}
    for _, row in df.iterrows():
        conflict_key = build_price_conflict_key(row)
        grouped_rows.setdefault(conflict_key, []).append(row.copy())

    annotated_rows: list[pd.Series] = []
    for _, row in df.iterrows():
        conflict_key = build_price_conflict_key(row)
        group_rows = grouped_rows[conflict_key]
        price_values = collect_price_values(group_rows)
        min_price = min(price_values)
        max_price = max(price_values)
        row_with_conflict = row.copy()
        row_with_conflict["has_price_conflict"] = len(price_values) > 1
        row_with_conflict["min_price"] = min_price
        row_with_conflict["max_price"] = max_price
        row_with_conflict["price_range"] = round(max_price - min_price, 3)
        row_with_conflict["price_values"] = price_values
        row_with_conflict["price_source_count"] = len(price_values)
        annotated_rows.append(row_with_conflict)

    return pd.DataFrame(annotated_rows)


def deduplicate_results(df: pd.DataFrame) -> pd.DataFrame:
    grouped_rows: dict[tuple, list[pd.Series]] = {}
    dedup_key_order: list[tuple] = []

    for _, row in df.iterrows():
        dedup_key = build_price_conflict_key(row) if "has_price_conflict" in df.columns else build_dedup_key(row)
        if dedup_key not in grouped_rows:
            grouped_rows[dedup_key] = []
            dedup_key_order.append(dedup_key)
        grouped_rows[dedup_key].append(row.copy())

    deduplicated_records: list[pd.Series] = []
    for dedup_key in dedup_key_order:
        grouped_record_rows = grouped_rows[dedup_key]
        base_row = grouped_record_rows[0].copy()
        if "source_id" in df.columns:
            source_ids, source_count = collect_source_provenance(grouped_record_rows)
            if source_ids:
                base_row["source_id"] = source_ids[0]
                base_row["source_ids"] = source_ids
                base_row["source_count"] = source_count
        deduplicated_records.append(base_row)

    return pd.DataFrame(deduplicated_records)


def filter_by_fuel_type(df: pd.DataFrame, fuel_type: str) -> pd.DataFrame:
    normalized_fuel_type = fuel_type.strip().lower()
    return df[df["fuel_type"].str.strip().str.lower() == normalized_fuel_type]


def filter_by_city(df: pd.DataFrame, city: str) -> pd.DataFrame:
    normalized_city = city.strip().lower()
    return df[df["city"].str.strip().str.lower() == normalized_city]


def filter_by_station_name(df: pd.DataFrame, station_query: str) -> pd.DataFrame:
    normalized_station_query = station_query.strip().lower()
    return df[df["station_name"].str.strip().str.lower().str.contains(normalized_station_query, regex=False)]


def sort_by_price(df: pd.DataFrame, sort_by: str = "price_asc") -> pd.DataFrame:
    return df.sort_values(by="price", ascending=sort_by == "price_asc")


def build_result_columns(df: pd.DataFrame, summary_by_city: bool = False) -> list[str]:
    if summary_by_city:
        columns = ["city", "station_name", "address", "fuel_type", "price"]
    else:
        columns = ["station_name", "address", "city", "fuel_type", "price"]
    if "source_id" in df.columns:
        columns.append("source_id")
    if "source_ids" in df.columns:
        columns.append("source_ids")
    if "source_count" in df.columns:
        columns.append("source_count")
    if "has_price_conflict" in df.columns:
        columns.extend(["has_price_conflict", "min_price", "max_price", "price_range", "price_values"])
        if "price_source_count" in df.columns:
            columns.append("price_source_count")
    return columns


def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df[build_result_columns(df)]


def format_price_column(df: pd.DataFrame) -> pd.DataFrame:
    formatted_df = df.copy()
    formatted_df["price"] = formatted_df["price"].map(lambda price: f"{price:.3f}")
    return formatted_df


def summarize_cheapest_by_city(df: pd.DataFrame) -> pd.DataFrame:
    summarized_df = sort_by_price(df)
    summarized_df = summarized_df.drop_duplicates(subset="city", keep="first")
    summarized_df = summarized_df[build_result_columns(summarized_df, summary_by_city=True)]
    summarized_df = sort_by_price(summarized_df)
    return format_price_column(summarized_df)


def build_result_title(
    fuel_type: str,
    top_n: int,
    city: str | None = None,
    station_query: str | None = None,
    summary_by_city: bool = False,
) -> str:
    if summary_by_city:
        return f"Lētākā {fuel_type} cena katrā pilsētā"

    title = f"Top {top_n} {fuel_type} cenas"
    if city is not None:
        title += f" pilsētā: {city}"
    if station_query is not None:
        separator = ", " if city is not None else " "
        title += f"{separator}stacijām, kas satur: {station_query}"
    return title


def normalize_filename_part(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def build_default_output_filename(
    fuel_type: str,
    output_format: str,
    top_n: int,
    city: str | None = None,
    station_query: str | None = None,
    summary_by_city: bool = False,
) -> str:
    normalized_fuel_type = normalize_filename_part(fuel_type)
    normalized_output_format = normalize_filename_part(output_format)
    if summary_by_city:
        return f"{normalized_fuel_type}_summary_by_city.{normalized_output_format}"

    filename_parts = [normalized_fuel_type]
    if city is not None:
        filename_parts.append(normalize_filename_part(city))
    if station_query is not None:
        filename_parts.append(normalize_filename_part(station_query))
    filename_parts.append(f"top{top_n}")
    return f"{'_'.join(filename_parts)}.{normalized_output_format}"


def build_history_source_label(
    source_id: str | None = None,
    source_ids: str | None = None,
    input_format: str | None = None,
) -> str:
    if source_id:
        return normalize_filename_part(source_id)
    if source_ids:
        return normalize_filename_part(source_ids.replace(",", "_"))
    if input_format:
        return normalize_filename_part(input_format)
    return "input"


def build_history_snapshot_filename(
    fuel_type: str,
    source_label: str,
    timestamp: datetime | None = None,
) -> str:
    snapshot_time = timestamp or datetime.now()
    return f"{snapshot_time.strftime('%Y-%m-%d_%H%M%S')}_{normalize_filename_part(source_label)}_{normalize_filename_part(fuel_type)}.csv"


def save_history_snapshot(df: pd.DataFrame, filepath: Path) -> None:
    history_df = add_google_maps_url_column(df)
    if "source_ids" in history_df.columns:
        history_df = history_df.copy()
        history_df["source_ids"] = history_df["source_ids"].map(
            lambda value: "|".join(value) if isinstance(value, list) else value
        )
    if "price_values" in history_df.columns:
        history_df = history_df.copy()
        history_df["price_values"] = history_df["price_values"].map(
            lambda value: "|".join(f"{item:.3f}" for item in value) if isinstance(value, list) else value
        )
    filepath.parent.mkdir(parents=True, exist_ok=True)
    history_df.to_csv(filepath, index=False)


def build_google_maps_search_url(address: str, city: str | None = None) -> str:
    query = address.strip()
    if city is not None:
        query = f"{query}, {city.strip()}"
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def add_google_maps_url_column(df: pd.DataFrame) -> pd.DataFrame:
    result_df = df.copy()
    result_df["google_maps_url"] = result_df.apply(
        lambda row: build_google_maps_search_url(row["address"], row["city"]),
        axis=1,
    )
    return result_df


def prepare_results(df: pd.DataFrame, top_n: int, sort_by: str = "price_asc") -> pd.DataFrame:
    return format_price_column(select_columns(sort_by_price(df, sort_by)).head(top_n))
