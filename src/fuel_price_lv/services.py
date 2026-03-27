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


def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df[["station_name", "address", "city", "fuel_type", "price"]]


def format_price_column(df: pd.DataFrame) -> pd.DataFrame:
    formatted_df = df.copy()
    formatted_df["price"] = formatted_df["price"].map(lambda price: f"{price:.3f}")
    return formatted_df


def summarize_cheapest_by_city(df: pd.DataFrame) -> pd.DataFrame:
    summarized_df = sort_by_price(df)
    summarized_df = summarized_df.drop_duplicates(subset="city", keep="first")
    summarized_df = summarized_df[["city", "station_name", "address", "fuel_type", "price"]]
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
