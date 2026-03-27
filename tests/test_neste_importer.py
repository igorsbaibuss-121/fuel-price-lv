from pathlib import Path
import sys

import pytest

from fuel_price_lv.importers import load_input_data
from fuel_price_lv.importers.neste_lv_v1 import (
    build_neste_dataset,
    is_valid_neste_station_record,
    load_neste_lv_v1_data,
    parse_neste_prices,
    parse_neste_stations,
)
from fuel_price_lv.main import main


def test_parse_neste_prices_extracts_network_wide_entries() -> None:
    html = """
    <table>
      <tr><th>Degviela</th><th>Cena</th><th>Piezīmes</th></tr>
      <tr><td>Neste Futura D</td><td>1.604 EUR</td><td>Visās stacijās cenas vienādas</td></tr>
      <tr><td>Neste Futura 95</td><td>1.734 EUR</td><td>Visās stacijās cenas vienādas</td></tr>
    </table>
    """

    result = parse_neste_prices(html)

    assert result == [
        {
            "fuel_type": "diesel",
            "price": 1.604,
            "scope": "network",
            "source_fuel_label": "Neste Futura D",
        },
        {
            "fuel_type": "petrol_95",
            "price": 1.734,
            "scope": "network",
            "source_fuel_label": "Neste Futura 95",
        },
    ]


def test_parse_neste_stations_extracts_station_names_and_addresses() -> None:
    html = """
    Neste A7
    Rīgas iela 1, Ķekava
    Neste Brīvības
    Brīvības gatve 123, Rīga
    """

    result = parse_neste_stations(html)

    assert result == [
        {
            "station_name": "Neste A7",
            "address": "Rīgas iela 1, Ķekava",
            "city": "Ķekava",
        },
        {
            "station_name": "Neste Brīvības",
            "address": "Brīvības gatve 123, Rīga",
            "city": "Rīga",
        },
    ]


def test_parse_neste_stations_cleans_nested_html_and_whitespace() -> None:
    html = """
    <table>
      <tr>
        <td>
          <strong>Neste Ulmaņa gatve</strong><br />
          <span>Ulmaņa gatve 84, Rīga</span>
        </td>
      </tr>
      <tr>
        <td>
          <strong> Neste Jugla </strong><br/>
          <span>
            Brīvības gatve 401,   Rīga
          </span>
        </td>
      </tr>
    </table>
    """

    result = parse_neste_stations(html)

    assert result == [
        {
            "station_name": "Neste Ulmaņa gatve",
            "address": "Ulmaņa gatve 84, Rīga",
            "city": "Rīga",
        },
        {
            "station_name": "Neste Jugla",
            "address": "Brīvības gatve 401, Rīga",
            "city": "Rīga",
        },
    ]
    assert all("<" not in station["station_name"] for station in result)
    assert all(">" not in station["station_name"] for station in result)
    assert all("<" not in station["address"] for station in result)
    assert all(">" not in station["address"] for station in result)
    assert all("<" not in station["city"] for station in result)
    assert all(">" not in station["city"] for station in result)


def test_is_valid_neste_station_record_rejects_polluted_fake_record() -> None:
    assert not is_valid_neste_station_record(
        "Neste DUS saraksts | Neste oil (function(window, document, dataLayerName, id) { ...",
        "window.document.dataLayer 123",
        "Rīga",
    )


def test_is_valid_neste_station_record_accepts_real_station() -> None:
    assert is_valid_neste_station_record(
        "Neste Lucavsala",
        "Mūkusalas iela 78, Rīga",
        "Rīga",
    )


def test_parse_neste_stations_rejects_noise_and_keeps_valid_stations() -> None:
    html = """
    <div>
      <strong>Neste DUS saraksts | Neste oil (function(window, document, dataLayerName, id) { ...</strong><br />
      <span>window.document.dataLayer 123, Rīga</span>
    </div>
    <div>
      <strong>Neste Ulmaņa gatve</strong><br />
      <span>Ulmaņa gatve 84, Rīga</span>
    </div>
    <div>
      <strong>Neste Lucavsala</strong><br />
      <span>Mūkusalas iela 78, Rīga</span>
    </div>
    """

    result = parse_neste_stations(html)

    assert result == [
        {
            "station_name": "Neste Ulmaņa gatve",
            "address": "Ulmaņa gatve 84, Rīga",
            "city": "Rīga",
        },
        {
            "station_name": "Neste Lucavsala",
            "address": "Mūkusalas iela 78, Rīga",
            "city": "Rīga",
        },
    ]


def test_build_neste_dataset_expands_network_wide_prices_across_stations() -> None:
    prices = [
        {"fuel_type": "diesel", "price": 1.604, "scope": "network"},
        {"fuel_type": "petrol_95", "price": 1.734, "scope": "network"},
    ]
    stations = [
        {"station_name": "Neste A7", "address": "Rīgas iela 1, Ķekava", "city": "Ķekava"},
        {"station_name": "Neste Brīvības", "address": "Brīvības gatve 123, Rīga", "city": "Rīga"},
    ]

    result = build_neste_dataset(prices, stations)

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert len(result) == 4
    assert set(result["fuel_type"]) == {"diesel", "petrol_95"}


def test_load_input_data_supports_neste_lv_v1_with_mocked_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.neste_lv_v1.fetch_neste_prices_page",
        lambda: """
        <table>
          <tr><td>Neste Futura D</td><td>1.604 EUR</td><td>Visās stacijās cenas vienādas</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.neste_lv_v1.fetch_neste_station_list_page",
        lambda: """
        <strong>Neste A7</strong><br />
        <span>Rīgas iela 1, Ķekava</span>
        """,
    )

    result = load_input_data(csv_path=tmp_path / "unused.csv", input_format="neste_lv_v1")

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert result.loc[0, "station_name"] == "Neste A7"
    assert result.loc[0, "fuel_type"] == "diesel"
    assert result.loc[0, "price"] == 1.604


def test_load_neste_lv_v1_data_reports_missing_prices(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("fuel_price_lv.importers.neste_lv_v1.fetch_neste_prices_page", lambda: "<html></html>")

    with pytest.raises(ValueError, match="Neizdevās atrast Neste degvielas cenas avotā"):
        load_neste_lv_v1_data(tmp_path / "unused.csv")


def test_load_neste_lv_v1_data_reports_missing_stations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.neste_lv_v1.fetch_neste_prices_page",
        lambda: """
        <table>
          <tr><td>Neste Futura D</td><td>1.604 EUR</td><td>Visās stacijās cenas vienādas</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr("fuel_price_lv.importers.neste_lv_v1.fetch_neste_station_list_page", lambda: "<html></html>")

    with pytest.raises(ValueError, match="Neizdevās atrast Neste stacijas avotā"):
        load_neste_lv_v1_data(tmp_path / "unused.csv")


def test_main_supports_neste_lv_v1_input_format(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.neste_lv_v1.fetch_neste_prices_page",
        lambda: """
        <table>
          <tr><td>Neste Futura D</td><td>1.604 EUR</td><td>Visās stacijās cenas vienādas</td></tr>
        </table>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.neste_lv_v1.fetch_neste_station_list_page",
        lambda: """
        <strong>Neste A7</strong><br />
        <span>Rīgas iela 1, Ķekava</span>
        """,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "neste_lv_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 1 diesel cenas" in captured.out
    assert "Neste A7" in captured.out


def test_neste_fetch_uses_shared_network_helper_with_ca_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_fetch_url_text(url: str, timeout: int = 20, ca_bundle: str | None = None) -> str:
        calls.append((url, ca_bundle))
        return "<html></html>"

    monkeypatch.setattr("fuel_price_lv.importers.neste_lv_v1.fetch_url_text", fake_fetch_url_text)

    from fuel_price_lv.importers.neste_lv_v1 import fetch_neste_prices_page

    fetch_neste_prices_page(ca_bundle="/custom/ca.pem")

    assert calls == [("https://www.neste.lv/lv/content/degvielas-cenas", "/custom/ca.pem")]
