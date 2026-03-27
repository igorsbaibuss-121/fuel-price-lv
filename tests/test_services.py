import pandas as pd
import pytest

from fuel_price_lv.services import (
    add_google_maps_url_column,
    build_default_output_filename,
    build_google_maps_search_url,
    build_result_title,
    filter_by_city,
    filter_by_fuel_type,
    filter_by_station_name,
    format_price_column,
    load_data,
    prepare_results,
    sort_by_price,
    summarize_cheapest_by_city,
)


def test_build_default_output_filename_returns_basic_filename() -> None:
    result = build_default_output_filename("diesel", "csv", 5)

    assert result == "diesel_top5.csv"


def test_build_default_output_filename_includes_normalized_city() -> None:
    result = build_default_output_filename("diesel", "json", 5, city=" Riga ")

    assert result == "diesel_riga_top5.json"


def test_build_default_output_filename_includes_normalized_station_query() -> None:
    result = build_default_output_filename("diesel", "csv", 5, station_query=" Circle K ")

    assert result == "diesel_circle_k_top5.csv"


def test_build_default_output_filename_includes_city_and_station_query() -> None:
    result = build_default_output_filename("diesel", "json", 5, city="Riga", station_query="Circle K")

    assert result == "diesel_riga_circle_k_top5.json"


def test_build_default_output_filename_returns_summary_by_city_filename() -> None:
    result = build_default_output_filename(
        "diesel",
        "csv",
        5,
        city="Riga",
        station_query="Circle K",
        summary_by_city=True,
    )

    assert result == "diesel_summary_by_city.csv"


def test_add_google_maps_url_column_adds_google_maps_url_column() -> None:
    df = pd.DataFrame([{"address": "Brivibas iela 1", "city": "Riga"}])

    result = add_google_maps_url_column(df)

    assert "google_maps_url" in result.columns


def test_add_google_maps_url_column_does_not_mutate_original_dataframe() -> None:
    df = pd.DataFrame([{"address": "Brivibas iela 1", "city": "Riga"}])

    add_google_maps_url_column(df)

    assert "google_maps_url" not in df.columns


def test_add_google_maps_url_column_generates_encoded_url_from_address_and_city() -> None:
    df = pd.DataFrame([{"address": "Brīvības iela 1", "city": "Rīga"}])

    result = add_google_maps_url_column(df)

    assert (
        result.loc[0, "google_maps_url"]
        == "https://www.google.com/maps/search/?api=1&query=Br%C4%ABv%C4%ABbas+iela+1%2C+R%C4%ABga"
    )


def test_build_google_maps_search_url_with_address_and_city() -> None:
    result = build_google_maps_search_url("Brivibas iela 1", "Riga")

    assert result == "https://www.google.com/maps/search/?api=1&query=Brivibas+iela+1%2C+Riga"


def test_build_google_maps_search_url_with_address_only() -> None:
    result = build_google_maps_search_url("Brivibas iela 1")

    assert result == "https://www.google.com/maps/search/?api=1&query=Brivibas+iela+1"


def test_build_google_maps_search_url_trims_surrounding_whitespace() -> None:
    result = build_google_maps_search_url("  Brivibas iela 1  ", "  Riga  ")

    assert result == "https://www.google.com/maps/search/?api=1&query=Brivibas+iela+1%2C+Riga"


def test_build_google_maps_search_url_encodes_spaces_and_non_ascii_characters() -> None:
    result = build_google_maps_search_url("Brīvības iela 1", "Rīga")

    assert result == "https://www.google.com/maps/search/?api=1&query=Br%C4%ABv%C4%ABbas+iela+1%2C+R%C4%ABga"


def test_build_result_title_returns_base_title() -> None:
    result = build_result_title("diesel", 5)

    assert result == "Top 5 diesel cenas"


def test_build_result_title_appends_city() -> None:
    result = build_result_title("diesel", 5, city="Riga")

    assert result == "Top 5 diesel cenas pilsētā: Riga"


def test_build_result_title_appends_station_query_without_city() -> None:
    result = build_result_title("diesel", 5, station_query="Neste")

    assert result == "Top 5 diesel cenas stacijām, kas satur: Neste"


def test_build_result_title_appends_station_query_after_city() -> None:
    result = build_result_title("diesel", 5, city="Riga", station_query="Neste")

    assert result == "Top 5 diesel cenas pilsētā: Riga, stacijām, kas satur: Neste"


def test_build_result_title_ignores_other_arguments_for_summary_by_city() -> None:
    result = build_result_title(
        "diesel",
        5,
        city="Riga",
        station_query="Neste",
        summary_by_city=True,
    )

    assert result == "Lētākā diesel cena katrā pilsētā"


def test_filter_by_fuel_type_returns_only_matching_rows() -> None:
    df = pd.DataFrame(
        [
            {"station_name": "A", "fuel_type": "diesel", "price": 1.60},
            {"station_name": "B", "fuel_type": "petrol_95", "price": 1.70},
            {"station_name": "C", "fuel_type": "diesel", "price": 1.55},
        ]
    )

    result = filter_by_fuel_type(df, "diesel")

    assert len(result) == 2
    assert set(result["station_name"]) == {"A", "C"}


def test_filter_by_fuel_type_is_case_insensitive_and_trims_input() -> None:
    df = pd.DataFrame(
        [
            {"station_name": "A", "fuel_type": " Diesel ", "price": 1.60},
            {"station_name": "B", "fuel_type": "petrol_95", "price": 1.70},
            {"station_name": "C", "fuel_type": "DIESEL", "price": 1.55},
        ]
    )

    result = filter_by_fuel_type(df, "  diesel  ")

    assert len(result) == 2
    assert set(result["station_name"]) == {"A", "C"}


def test_filter_by_city_is_case_insensitive_and_trims_input() -> None:
    df = pd.DataFrame(
        [
            {"station_name": "A", "city": " Riga ", "price": 1.60},
            {"station_name": "B", "city": "Liepaja", "price": 1.70},
            {"station_name": "C", "city": "RIGA", "price": 1.55},
        ]
    )

    result = filter_by_city(df, "  riga ")

    assert len(result) == 2
    assert set(result["station_name"]) == {"A", "C"}


def test_filter_by_station_name_matches_partially_case_insensitively() -> None:
    df = pd.DataFrame(
        [
            {"station_name": "Neste Riga Center", "price": 1.60},
            {"station_name": "Circle K Riga", "price": 1.70},
            {"station_name": "NESTE Jurmala", "price": 1.55},
        ]
    )

    result = filter_by_station_name(df, "  neste ")

    assert len(result) == 2
    assert set(result["station_name"]) == {"Neste Riga Center", "NESTE Jurmala"}


def test_sort_by_price_sorts_ascending() -> None:
    df = pd.DataFrame(
        [
            {"station_name": "A", "fuel_type": "diesel", "price": 1.60},
            {"station_name": "B", "fuel_type": "diesel", "price": 1.50},
            {"station_name": "C", "fuel_type": "diesel", "price": 1.55},
        ]
    )

    result = sort_by_price(df)

    assert list(result["station_name"]) == ["B", "C", "A"]


def test_sort_by_price_sorts_descending() -> None:
    df = pd.DataFrame(
        [
            {"station_name": "A", "fuel_type": "diesel", "price": 1.60},
            {"station_name": "B", "fuel_type": "diesel", "price": 1.50},
            {"station_name": "C", "fuel_type": "diesel", "price": 1.55},
        ]
    )

    result = sort_by_price(df, "price_desc")

    assert list(result["station_name"]) == ["A", "C", "B"]


def test_format_price_column_formats_prices_to_three_decimal_places() -> None:
    df = pd.DataFrame(
        [
            {"station_name": "A", "price": 1.5},
            {"station_name": "B", "price": 1.555},
        ]
    )

    result = format_price_column(df)

    assert list(result["price"]) == ["1.500", "1.555"]


def test_summarize_cheapest_by_city_returns_cheapest_station_per_city() -> None:
    df = pd.DataFrame(
        [
            {
                "station_name": "A",
                "address": "Addr A",
                "city": "Riga",
                "fuel_type": "diesel",
                "price": 1.60,
            },
            {
                "station_name": "B",
                "address": "Addr B",
                "city": "Riga",
                "fuel_type": "diesel",
                "price": 1.50,
            },
            {
                "station_name": "C",
                "address": "Addr C",
                "city": "Liepaja",
                "fuel_type": "diesel",
                "price": 1.55,
            },
        ]
    )

    result = summarize_cheapest_by_city(df)

    assert list(result["city"]) == ["Riga", "Liepaja"]
    assert list(result["station_name"]) == ["B", "C"]
    assert list(result.columns) == ["city", "station_name", "address", "fuel_type", "price"]
    assert list(result["price"]) == ["1.500", "1.550"]


def test_prepare_results_sorts_selects_columns_and_limits_rows() -> None:
    df = pd.DataFrame(
        [
            {
                "station_name": "A",
                "address": "Addr A",
                "city": "Riga",
                "fuel_type": "diesel",
                "price": 1.60,
                "extra": "ignore",
            },
            {
                "station_name": "B",
                "address": "Addr B",
                "city": "Riga",
                "fuel_type": "diesel",
                "price": 1.50,
                "extra": "ignore",
            },
            {
                "station_name": "C",
                "address": "Addr C",
                "city": "Riga",
                "fuel_type": "diesel",
                "price": 1.55,
                "extra": "ignore",
            },
        ]
    )

    result = prepare_results(df, 2)

    assert list(result["station_name"]) == ["B", "C"]
    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]


def test_load_data_raises_when_required_columns_are_missing(tmp_path) -> None:
    csv_path = tmp_path / "fuel_prices.csv"
    pd.DataFrame(
        [
            {
                "station_name": "A",
                "address": "Addr A",
                "city": "Riga",
                "fuel_type": "diesel",
            }
        ]
    ).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="CSV failā trūkst obligātās kolonnas: price"):
        load_data(csv_path)
