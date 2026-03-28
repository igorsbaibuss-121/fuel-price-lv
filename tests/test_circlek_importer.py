from pathlib import Path
import sys

import pytest

from fuel_price_lv.importers import load_input_data
from fuel_price_lv.importers.circlek_lv_v1 import (
    build_circlek_dataset,
    load_circlek_lv_v1_data,
    normalize_circlek_fuel_type,
    parse_circlek_prices,
    parse_circlek_stations,
)
from fuel_price_lv.main import main


def test_parse_circlek_prices_extracts_network_wide_entries() -> None:
    html = """
    <table>
      <tr><th>Degviela</th><th>Cena EUR</th><th></th></tr>
      <tr><td>95miles</td><td>1.654 EUR</td><td>Degvielas cena visos DUS ir vienāda</td></tr>
      <tr><td>Dmiles</td><td>1.904 EUR</td><td>Degvielas cena visos DUS ir vienāda</td></tr>
    </table>
    """

    result = parse_circlek_prices(html)

    assert result == [
        {
            "fuel_type": "petrol_95",
            "price": 1.654,
            "scope": "network",
            "station_address": None,
            "source_fuel_label": "95miles",
        },
        {
            "fuel_type": "diesel",
            "price": 1.904,
            "scope": "network",
            "station_address": None,
            "source_fuel_label": "Dmiles",
        },
    ]


def test_normalize_circlek_fuel_type_maps_95_labels_to_petrol_95() -> None:
    assert normalize_circlek_fuel_type("95miles") == "petrol_95"
    assert normalize_circlek_fuel_type("Benzīns miles 95") == "petrol_95"


def test_parse_circlek_prices_handles_station_specific_entry() -> None:
    html = """
    <table>
      <tr><td>miles+ XTL</td><td>2.570 EUR</td><td>Krasta iela 93</td></tr>
    </table>
    """

    result = parse_circlek_prices(html)

    assert result == [
        {
            "fuel_type": "diesel_xtl",
            "price": 2.57,
            "scope": "station",
            "station_address": "Krasta iela 93",
            "source_fuel_label": "miles+ XTL",
        }
    ]


def test_parse_circlek_stations_extracts_station_names_and_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    station_list_html = """
    <ul>
      <li><a href="/station/circle-k-krasta-2">CIRCLE K KRASTA 2</a></li>
      <li><a href="/station/circle-k-jugla">CIRCLE K JUGLA</a></li>
    </ul>
    """
    station_pages = {
        "https://www.circlek.lv/station/circle-k-krasta-2": "<h2>Krasta iela 93, Rīga, LV-1019, LV</h2>",
        "https://www.circlek.lv/station/circle-k-jugla": "<h2>Brīvības gatve 401, Rīga, LV-1024, LV</h2>",
    }

    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_page",
        lambda station_url: station_pages[station_url],
    )

    result = parse_circlek_stations(station_list_html)

    assert result == [
        {
            "station_name": "CIRCLE K KRASTA 2",
            "address": "Krasta iela 93, Rīga, LV-1019, LV",
            "city": "Rīga",
            "station_url": "https://www.circlek.lv/station/circle-k-krasta-2",
        },
        {
            "station_name": "CIRCLE K JUGLA",
            "address": "Brīvības gatve 401, Rīga, LV-1024, LV",
            "city": "Rīga",
            "station_url": "https://www.circlek.lv/station/circle-k-jugla",
        },
    ]


def test_build_circlek_dataset_expands_network_wide_and_matches_station_specific() -> None:
    prices = [
        {"fuel_type": "diesel", "price": 1.904, "scope": "network", "station_address": None},
        {"fuel_type": "diesel_xtl", "price": 2.57, "scope": "station", "station_address": "Krasta iela 93"},
    ]
    stations = [
        {
            "station_name": "CIRCLE K KRASTA 2",
            "address": "Krasta iela 93, Rīga, LV-1019, LV",
            "city": "Rīga",
            "station_url": "https://www.circlek.lv/station/circle-k-krasta-2",
        },
        {
            "station_name": "CIRCLE K JUGLA",
            "address": "Brīvības gatve 401, Rīga, LV-1024, LV",
            "city": "Rīga",
            "station_url": "https://www.circlek.lv/station/circle-k-jugla",
        },
    ]

    result = build_circlek_dataset(prices, stations)

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert len(result) == 3
    assert len(result[result["fuel_type"] == "diesel"]) == 2
    xtl_rows = result[result["fuel_type"] == "diesel_xtl"]
    assert len(xtl_rows) == 1
    assert xtl_rows.iloc[0]["station_name"] == "CIRCLE K KRASTA 2"


def test_build_circlek_dataset_includes_petrol_95_rows() -> None:
    prices = [
        {"fuel_type": "petrol_95", "price": 1.654, "scope": "network", "station_address": None},
    ]
    stations = [
        {
            "station_name": "CIRCLE K KRASTA 2",
            "address": "Krasta iela 93, Rīga, LV-1019, LV",
            "city": "Rīga",
            "station_url": "https://www.circlek.lv/station/circle-k-krasta-2",
        },
        {
            "station_name": "CIRCLE K JUGLA",
            "address": "Brīvības gatve 401, Rīga, LV-1024, LV",
            "city": "Rīga",
            "station_url": "https://www.circlek.lv/station/circle-k-jugla",
        },
    ]

    result = build_circlek_dataset(prices, stations)

    assert len(result) == 2
    assert set(result["fuel_type"]) == {"petrol_95"}


def test_load_input_data_supports_circlek_lv_v1_with_mocked_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_prices_page",
        lambda: """
        <table>
          <tr><td>Dmiles</td><td>1.904 EUR</td><td>Degvielas cena visos DUS ir vienāda</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_list_page",
        lambda: """
        <ul>
          <li><a href="/station/circle-k-krasta-2">CIRCLE K KRASTA 2</a></li>
        </ul>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_page",
        lambda _station_url: "<h2>Krasta iela 93, Rīga, LV-1019, LV</h2>",
    )

    result = load_input_data(csv_path=tmp_path / "unused.csv", input_format="circlek_lv_v1")

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert result.loc[0, "station_name"] == "CIRCLE K KRASTA 2"
    assert result.loc[0, "fuel_type"] == "diesel"
    assert result.loc[0, "price"] == 1.904


def test_load_circlek_lv_v1_data_reports_missing_prices(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_prices_page", lambda: "<html></html>")

    with pytest.raises(ValueError, match="Neizdevās atrast Circle K degvielas cenas avotā"):
        load_circlek_lv_v1_data(tmp_path / "unused.csv")


def test_load_circlek_lv_v1_data_reports_missing_stations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_prices_page",
        lambda: """
        <table>
          <tr><td>Dmiles</td><td>1.904 EUR</td><td>Degvielas cena visos DUS ir vienāda</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr("fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_list_page", lambda: "<html></html>")

    with pytest.raises(ValueError, match="Neizdevās atrast Circle K stacijas avotā"):
        load_circlek_lv_v1_data(tmp_path / "unused.csv")


def test_main_supports_circlek_lv_v1_input_format(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_prices_page",
        lambda: """
        <table>
          <tr><td>Dmiles</td><td>1.904 EUR</td><td>Degvielas cena visos DUS ir vienāda</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_list_page",
        lambda: """
        <ul>
          <li><a href="/station/circle-k-krasta-2">CIRCLE K KRASTA 2</a></li>
        </ul>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_page",
        lambda _station_url: "<h2>Krasta iela 93, Rīga, LV-1019, LV</h2>",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "circlek_lv_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 1 diesel cenas" in captured.out
    assert "CIRCLE K KRASTA 2" in captured.out


def test_main_supports_circlek_lv_v1_input_format_for_petrol_95(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_prices_page",
        lambda: """
        <table>
          <tr><td>95miles</td><td>1.654 EUR</td><td>Degvielas cena visos DUS ir vienāda</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_list_page",
        lambda: """
        <ul>
          <li><a href="/station/circle-k-krasta-2">CIRCLE K KRASTA 2</a></li>
        </ul>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_page",
        lambda _station_url: "<h2>Krasta iela 93, Rīga, LV-1019, LV</h2>",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "circlek_lv_v1",
            "--fuel-type",
            "petrol_95",
            "--top-n",
            "1",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 1 petrol_95 cenas" in captured.out
    assert "CIRCLE K KRASTA 2" in captured.out


def test_main_report_uses_circlek_source_label_instead_of_default_csv_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_prices_page",
        lambda: """
        <table>
          <tr><td>Dmiles</td><td>1.904 EUR</td><td>Degvielas cena visos DUS ir vienÄda</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_list_page",
        lambda: """
        <ul>
          <li><a href="/station/circle-k-krasta-2">CIRCLE K KRASTA 2</a></li>
        </ul>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.circlek_lv_v1.fetch_circlek_station_page",
        lambda _station_url: "<h2>Krasta iela 93, RÄ«ga, LV-1019, LV</h2>",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "circlek_lv_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "5",
            "--report",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Avots: circlek_lv_v1" in captured.out
    assert "data/sample_prices.csv" not in captured.out


def test_circlek_fetch_uses_shared_network_helper_with_ca_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_fetch_url_text(url: str, timeout: int = 20, ca_bundle: str | None = None) -> str:
        calls.append((url, ca_bundle))
        return "<html></html>"

    monkeypatch.setattr("fuel_price_lv.importers.circlek_lv_v1.fetch_url_text", fake_fetch_url_text)

    from fuel_price_lv.importers.circlek_lv_v1 import fetch_circlek_prices_page

    fetch_circlek_prices_page(ca_bundle="/custom/ca.pem")

    assert calls == [("https://www.circlek.lv/degviela-miles/degvielas-cenas", "/custom/ca.pem")]
